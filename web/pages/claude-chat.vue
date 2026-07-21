<template>
  <div class="claude-chat-page">
    <!-- ═══ Header (fixed top) ═══ -->
    <div class="chat-header-wrapper">
      <div class="chat-header">
        <div>
          <h2><RobotOutlined /> {{ $t('chat.title') }}</h2>
          <p class="hint">{{ $t('chat.subtitle') }}</p>
        </div>
        <div class="header-actions">
          <a-tooltip title="新建对话（不打断当前流式，后台继续）">
            <a-button type="primary" ghost @click="newConversation" :disabled="!messages.length && !streaming">
              <PlusSquareOutlined /> {{ $t('chat.newChat') }}
            </a-button>
          </a-tooltip>
          <a-button @click="panelOpen = true"><AppstoreOutlined /> {{ $t('chat.env') }}</a-button>
          <a-button @click="loadSessions" :loading="loadingSessions"><HistoryOutlined /> {{ $t('chat.history') }}</a-button>
          <a-button @click="clearChat"><ClearOutlined /> {{ $t('chat.clear') }}</a-button>
        </div>
      </div>

      <!-- Toolbar -->
      <div class="toolbar">
        <div class="workspace-selector">
          <a-select
            v-model:value="cwd"
            :options="workspaceOptions"
            :placeholder="$t('chat.workspacePlaceholder')"
            show-search
            allow-clear
            style="min-width:320px;flex:1"
            @change="onWorkspaceChange"
          >
            <template #option="{ label, value, desc, pin }">
              <div class="ws-option">
                <div class="ws-option-main">
                  <PushpinOutlined v-if="pin" style="color:var(--kb-amber);font-size:11px;margin-right:4px" />
                  <FolderOpenOutlined style="margin-right:6px;color:var(--kb-primary)" />
                  <span style="font-weight:600">{{ label }}</span>
                </div>
                <div class="ws-option-path">{{ value }}</div>
                <div v-if="desc" class="ws-option-desc">{{ desc }}</div>
              </div>
            </template>
          </a-select>
          <a-tooltip :title="$t('chat.manageWorkspace')">
            <a-button @click="wsManagerOpen = true"><FolderOpenOutlined /></a-button>
          </a-tooltip>
          <a-tooltip :title="$t('chat.addWorkspace')">
            <a-button @click="addCurrentWorkspace"><PlusOutlined /></a-button>
          </a-tooltip>
        </div>

        <a-select v-model:value="permissionMode" style="width:140px">
          <a-select-option v-for="m in PERMISSION_MODES" :key="m" :value="m">{{ PERMISSION_MODE_INFO[m as PermissionMode].label }}</a-select-option>
        </a-select>
        <a-tooltip :title="PERMISSION_MODE_INFO[permissionMode as PermissionMode].desc"><InfoCircleOutlined style="cursor:help" /></a-tooltip>
        <a-input v-model:value="model" placeholder="Model (leave empty for default)" style="width:160px" allow-clear />
        <a-tooltip title="推理深度（越高越慢但思考越深入，Ultracode=max+workflows模式）">
          <a-select v-model:value="reasoningEffort" style="width:120px" size="small">
            <a-select-option value="auto">🤖 Auto</a-select-option>
            <a-select-option value="low">⚡ Low</a-select-option>
            <a-select-option value="medium">🔋 Medium</a-select-option>
            <a-select-option value="high">🧠 High</a-select-option>
            <a-select-option value="xhigh">🔥 X-High</a-select-option>
            <a-select-option value="max">🚀 Max (Ultracode)</a-select-option>
          </a-select>
        </a-tooltip>
      </div>

      <!-- meta bar -->
      <div v-if="(currentSessionId || initInfo.model) || bgSessions.length" class="meta-bar">
        <a-tag v-if="currentSessionId" color="green">active session {{ currentSessionId.slice(0, 12) }}…</a-tag>
        <a-tag v-if="initInfo.model" color="blue">{{ initInfo.model }}</a-tag>
        <a-tag v-for="m in initInfo.mcpServers" :key="m.name" :color="m.status === 'ready' ? 'green' : 'orange'">🔌 {{ m.name }} · {{ m.status }}</a-tag>
        <template v-for="bg in bgSessions" :key="bg.id">
          <a-tooltip :title="'后台运行中: ' + bg.prompt.slice(0, 60) + '… — 点击切换回来'">
            <a-tag color="processing" style="cursor:pointer" @click="switchToBg(bg)">
              <SyncOutlined spin /> {{ bg.id.slice(0, 8) }}…
            </a-tag>
          </a-tooltip>
        </template>
      </div>
    </div>

    <!-- ═══ Chat messages (natural height — scrolls with .page-content) ═══ -->
    <div class="messages" ref="msgRef">

      <div v-if="!messages.length && !streamingText" class="empty">
        <RobotOutlined style="font-size:40px;color:var(--kb-primary)" />
        <p>{{ $t('chat.title') }}</p>
        <p class="muted">{{ $t('chat.subtitle') }}</p>
      </div>

      <div v-for="m in messages" :key="m.id" :class="['msg', m.kind]">
        <!-- user -->
        <template v-if="m.kind === 'user'">
          <div class="msg-head"><UserOutlined /> You</div>
          <div class="msg-text" v-html="md(m.text)"></div>
        </template>

        <!-- assistant -->
        <template v-else-if="m.kind === 'assistant'">
          <div class="msg-head"><RobotOutlined /> Claude</div>
          <div class="msg-text" v-html="md(m.html)"></div>
        </template>

        <!-- thinking -->
        <template v-else-if="m.kind === 'thinking'">
          <details class="think-details">
            <summary><BulbOutlined /> Thinking <span class="muted">({{ m.text.length }} chars)</span></summary>
            <div class="think-body">{{ m.text }}</div>
          </details>
        </template>

        <!-- tool_use -->
        <template v-else-if="m.kind === 'tool_use'">
          <div class="tool-card use">
            <div class="tool-head">
              <span class="tool-badge" :class="{ mcp: m.isMcp }"><CodeOutlined /> {{ m.display }}</span>
              <span class="tool-preview">{{ preview(m.toolName, m.input) }}</span>
            </div>
            <details><summary class="muted">Input</summary><pre class="tool-input">{{ fmt(m.input) }}</pre></details>
          </div>
        </template>

        <!-- tool_result -->
        <template v-else-if="m.kind === 'tool_result'">
          <div class="tool-card result" :class="{ err: m.isError }">
            <div class="tool-head">
              <span class="tool-badge">{{ m.isError ? 'Failed' : 'Done' }} · {{ m.display }}</span>
            </div>
            <details open><summary class="muted">{{ m.result.length }} chars</summary><pre class="tool-result-pre">{{ m.result.slice(0, 3000) }}{{ m.result.length > 3000 ? '\n...(truncated)' : '' }}</pre></details>
          </div>
        </template>

        <!-- plan -->
        <template v-else-if="m.kind === 'plan'">
          <div class="plan-card">
            <div class="plan-head"><FileTextOutlined /> Plan</div>
            <div class="plan-body" v-html="md(m.plan)"></div>
          </div>
        </template>

        <!-- todo -->
        <template v-else-if="m.kind === 'todo'">
          <div class="todo-card">
            <div class="todo-head"><CheckSquareOutlined /> Task List</div>
            <div v-for="(t, i) in m.todos" :key="i" :class="['todo-item', t.status]">
              <span class="todo-check">{{ t.status === 'completed' ? '✓' : t.status === 'in_progress' ? '◐' : '○' }}</span>
              <span>{{ t.content }}</span>
            </div>
          </div>
        </template>

        <!-- ask_user (interactive Q&A) -->
        <template v-else-if="m.kind === 'ask_user'">
          <div class="ask-card">
            <div class="ask-head"><QuestionCircleOutlined /> {{ m.header }}</div>
            <div class="ask-question">{{ m.question }}</div>
            <div v-if="m.options.length" class="ask-options">
              <button v-for="opt in m.options" :key="opt.label" class="ask-opt" :disabled="m.answered" @click="answerAsk(m, opt.label)">
                <strong>{{ opt.label }}</strong>
                <span v-if="opt.description" class="muted">{{ opt.description }}</span>
              </button>
            </div>
            <a-input v-if="m.answered" :value="m.answer" disabled size="small" />
          </div>
        </template>

        <!-- system -->
        <template v-else-if="m.kind === 'system'">
          <details class="sys-details">
            <summary class="sys-head"><ThunderboltOutlined /> System · {{ m.subtype }}</summary>
            <div class="sys-body" v-html="md(m.text)"></div>
          </details>
        </template>

        <!-- result -->
        <template v-else-if="m.kind === 'result'">
          <div class="result-card" :class="{ err: m.isError }">
            <div class="msg-text" v-html="md(m.html)"></div>
          </div>
        </template>

        <!-- error -->
        <template v-else-if="m.kind === 'error'">
          <div class="err-card">❌ {{ m.text }}</div>
        </template>
      </div>

      <!-- ⭐ Streaming bubble: real-time text from stream_event -->
      <div v-if="streamingText" class="msg assistant streaming-msg">
        <div class="msg-head"><RobotOutlined /> Claude</div>
        <div class="msg-text" v-html="md(streamingText)"></div>
        <span v-if="showStreamingCursor" class="stream-cursor"></span>
      </div>

      <!-- ⭐ Working indicator (dot animation when no streaming text) -->
      <div v-if="streaming && !streamingText" class="msg assistant typing-msg">
        <div class="msg-head"><RobotOutlined /> Claude</div>
        <div class="typing-dots"><span></span><span></span><span></span></div>
      </div>

      <!-- ⭐ Jump to latest button (floating when not at bottom) -->
      <transition name="jump-fade">
        <div v-if="!isAtBottom && (streaming || messages.length)" class="jump-latest" @click="scrollToBottom()">
          <VerticalAlignBottomOutlined />
          <span v-if="unreadCount" class="jump-badge">{{ unreadCount }}</span>
        </div>
      </transition>
    </div>

    <!-- 弹性占位：内容少时把 footer 顶到底部，保证输入区始终贴底 -->
    <div class="chat-spacer" aria-hidden="true"></div>

    <!-- ═══ Footer (fixed bottom) ═══ -->
    <div class="chat-footer-wrapper">
      <!-- ⭐ Quick Action Pills -->
      <div class="quick-actions" v-if="!streaming">
      <span class="qa-label">⚡</span>
      <div class="qa-scroll">
        <span v-for="act in QUICK_ACTIONS" :key="act.label" class="qa-pill" @click="queueAction(act)">
          {{ act.icon }} {{ act.label }}
        </span>
      </div>
    </div>

    <!-- ⭐ Message Queue Panel (production-grade with context snapshots) -->
    <div v-if="messageQueue.length" class="queue-panel">
      <div class="queue-head">
        <OrderedListOutlined /> 消息队列 ({{ queueCounts.pending }} 待发{{ queueCounts.sending ? ', ' + queueCounts.sending + ' 发送中' : '' }}{{ queueCounts.failed ? ', ' + queueCounts.failed + ' 失败' : '' }})
        <span class="queue-head-actions">
          <a-tooltip :title="queuePaused ? '恢复队列' : '暂停队列'">
            <a-button size="small" type="text" @click="toggleQueuePause">
              <PauseCircleOutlined v-if="!queuePaused" />
              <CaretRightOutlined v-else style="color: var(--kb-emerald)" />
            </a-button>
          </a-tooltip>
          <a-tooltip title="重试所有失败">
            <a-button size="small" type="text" :disabled="!queueCounts.failed" @click="retryAllFailed">
              <SyncOutlined />
            </a-button>
          </a-tooltip>
          <a-button size="small" type="link" @click="clearQueue"><DeleteOutlined /> 清空待发</a-button>
        </span>
      </div>
      <div v-for="(item, i) in messageQueue" :key="item.id" :class="['queue-item', item.status]">
        <template v-if="item.status === 'editing'">
          <a-input v-model:value="queueEditText" size="small" style="flex:1" @keyup.enter="confirmEdit(item)" />
          <a-button size="small" type="primary" @click="confirmEdit(item)">✓</a-button>
          <a-button size="small" @click="cancelEdit(item)">✗</a-button>
        </template>
        <template v-else>
          <!-- Status indicator -->
          <span class="queue-status-dot" :class="item.status" :title="statusLabel(item.status)"></span>
          <span class="queue-idx">{{ i + 1 }}.</span>
          <span class="queue-text">{{ item.text.slice(0, 60) }}{{ item.text.length > 60 ? '…' : '' }}</span>
          <!-- Context tags (when different from current) -->
          <span class="queue-context">
            <a-tag v-if="item.model && item.model !== model" color="blue" size="small" class="queue-tag">🤖 {{ item.model }}</a-tag>
            <a-tag v-if="item.reasoningEffort && item.reasoningEffort !== 'auto'" color="purple" size="small" class="queue-tag">{{ item.reasoningEffort }}</a-tag>
            <a-tag v-if="item.permissionMode !== permissionMode" color="orange" size="small" class="queue-tag">{{ PERMISSION_MODE_INFO[item.permissionMode as PermissionMode]?.label || item.permissionMode }}</a-tag>
          </span>
          <!-- Error message (on hover) -->
          <a-tooltip v-if="item.status === 'failed' && item.error" :title="item.error">
            <span class="queue-error-icon">⚠</span>
          </a-tooltip>
          <span class="queue-actions">
            <a-tooltip title="编辑">
              <a-button size="small" type="text" @click="startEdit(item)" :disabled="item.status === 'sending'"><EditOutlined /></a-button>
            </a-tooltip>
            <a-tooltip title="删除">
              <a-button size="small" type="text" danger @click="removeFromQueue(item.id)" :disabled="item.status === 'sending'"><DeleteOutlined /></a-button>
            </a-tooltip>
            <!-- Retry button (failed items only) -->
            <a-tooltip v-if="item.status === 'failed'" title="重试发送">
              <a-button size="small" type="primary" ghost @click="retryQueueItem(item)"><SyncOutlined /></a-button>
            </a-tooltip>
            <!-- Manual send (skip line) -->
            <a-tooltip v-if="item.status === 'pending'" title="立即发送（跳过队列）">
              <a-button size="small" type="primary" ghost :disabled="streaming" @click="sendQueueItem(item)"><SendOutlined /></a-button>
            </a-tooltip>
          </span>
        </template>
      </div>
      <!-- Paused indicator -->
      <div v-if="queuePaused && queueCounts.pending" class="queue-paused-banner">
        <PauseCircleOutlined /> 队列已暂停 — {{ queueCounts.pending }} 条等待中
      </div>
    </div>

    <!-- Input area + slash menu -->
    <div class="input-area">
      <!-- ⭐ Attachment preview bar -->
      <div v-if="attachments.length" class="att-bar">
        <div v-for="att in attachments" :key="att.id" class="att-chip">
          <span class="att-icon">{{ attIcon(att) }}</span>
          <div class="att-meta">
            <span class="att-name">{{ att.name }}</span>
            <span class="att-type">{{ attTypeLabel(att) }} · {{ formatSize(att.size) }}</span>
          </div>
          <a-tooltip title="移除">
            <a-button type="text" size="small" danger @click="removeAttachment(att.id)">
              <CloseOutlined />
            </a-button>
          </a-tooltip>
        </div>
      </div>

      <!-- KB selector row (visible when KB-enhanced mode is on) -->
      <div v-if="kbEnhanced" class="kb-selector-row">
        <span class="kb-selector-label"><DatabaseOutlined /> KBs:</span>
        <a-select
          v-model:value="selectedKbIds"
          mode="multiple"
          :options="kbOptions"
          :loading="loadingKbs"
          placeholder="Select KBs (default: search all)"
          style="min-width: 240px; flex: 1; max-width: 560px"
          size="small"
          :max-tag-count="3"
          allow-clear
          :filter-option="filterKbOption"
          @change="onKbSelectionChange"
        >
          <template #notFoundContent>
            <span v-if="loadingKbs">Loading KBs...</span>
            <span v-else>No KBs found</span>
          </template>
        </a-select>
        <span v-if="selectedKbIds.length === 0" class="kb-hint">All KBs will be searched</span>
        <span v-else class="kb-hint selected">{{ selectedKbIds.length }} KB(s) selected</span>
      </div>

      <div v-if="slashOpen && filteredSlash.length" class="slash-menu">
        <div class="slash-menu-head">指令（{{ filteredSlash.length }}/{{ allSlashCommands.length }}）<span class="muted">↑↓ 选择 · Enter 确认</span></div>
        <div
          v-for="(cmd, i) in filteredSlash"
          :key="cmd"
          :class="['slash-item', { active: i === slashIdx }]"
          @click="pickSlash(cmd)"
          @mouseenter="slashIdx = i"
        >
          <span class="slash-cmd">/{{ cmd }}</span>
          <span v-if="slashDescriptions[cmd]" class="slash-desc">{{ slashDescriptions[cmd] }}</span>
        </div>
      </div>
      <div class="input-bar">
        <!-- Attachment button + hidden file input -->
        <a-tooltip title="添加附件（图片/PDF/文档）">
          <a-button class="att-btn" @click="triggerFilePicker">
            <PaperClipOutlined />
          </a-button>
        </a-tooltip>

        <!-- KB-enhanced toggle -->
        <a-tooltip :title="kbEnhanced ? 'KB-enhanced ON (click to disable)' : 'KB-enhanced: answer from knowledge base'">
          <a-button
            class="kb-btn"
            :class="{ active: kbEnhanced }"
            @click="toggleKbEnhanced"
          >
            <DatabaseOutlined />
          </a-button>
        </a-tooltip>

        <input
          ref="fileInputRef" type="file" multiple hidden
          :accept="ACCEPTED_TYPES"
          @change="onFilePicked"
        />
        <a-textarea
          v-model:value="input" ref="inputRef"
          :placeholder="streaming ? '回答中… 输入消息可加入队列 (Enter/Shift+Enter 发送)' : inputPlaceholder"
          :auto-size="{ minRows: 1, maxRows: 6 }"
          @keydown="onKeydown"
        />
        <a-tooltip :title="streaming ? '加入队列（回答结束后自动发送）' : '发送 (Enter)'">
          <a-button type="primary" :disabled="!input.trim() && !attachments.length" @click="send">
            <SendOutlined />{{ streaming ? ' 队列' : '' }}
          </a-button>
        </a-tooltip>
        <a-button v-if="streaming" danger @click="abort">中断</a-button>
      </div>
    </div>
    </div>

    <!-- Environment (tools/MCP/skills) panel -->
    <a-drawer v-model:open="panelOpen" title="Claude Code 环境" width="600" placement="right">
      <a-tabs>
        <!-- ⭐ Built-in tools (categorized) -->
        <a-tab-pane key="builtin" :tab="`内置工具 (${BUILT_IN_TOOLS.length})`">
          <a-input-search v-model:value="toolSearch" placeholder="搜索工具…" style="margin-bottom:12px" allow-clear />
          <div v-for="cat in TOOL_CATEGORY_ORDER" :key="cat">
            <template v-if="filteredToolsByCategory(cat).length">
              <div class="cat-header">{{ cat }} · {{ filteredToolsByCategory(cat).length }}</div>
              <div v-for="t in filteredToolsByCategory(cat)" :key="t.name" class="env-item tool-env">
                <span class="tool-icon">{{ t.icon }}</span>
                <div class="tool-info">
                  <span class="tool-name">{{ t.name }}</span>
                  <span class="tool-desc">{{ t.description }}</span>
                </div>
              </div>
            </template>
          </div>
        </a-tab-pane>

        <!-- ⭐ Session active tools (from init) -->
        <a-tab-pane key="tools" :tab="`会话工具 (${initInfo.tools.length})`">
          <p class="muted" v-if="!initInfo.tools.length">会话启动后从 init 消息加载</p>
          <div v-for="t in initInfo.tools" :key="t" class="env-item">
            <a-tag>{{ t.startsWith('mcp__') ? '🔌' : '🛠' }}</a-tag> {{ t }}
          </div>
        </a-tab-pane>

        <a-tab-pane key="mcp" :tab="`MCP (${initInfo.mcpServers.length})`">
          <p class="muted" v-if="!initInfo.mcpServers.length">会话启动后加载</p>
          <div v-for="m in initInfo.mcpServers" :key="m.name" class="env-item">
            <a-tag :color="m.status === 'ready' ? 'green' : 'orange'">{{ m.status }}</a-tag>
            <strong>{{ m.name }}</strong>
          </div>
        </a-tab-pane>

        <!-- ⭐ Skills (with descriptions) -->
        <a-tab-pane key="skills" :tab="`Skills (${skillCatalog.length})`">
          <a-input-search v-model:value="skillSearch" placeholder="搜索 Skill…" style="margin-bottom:12px" allow-clear />
          <div v-for="s in filteredSkills" :key="s.name" class="env-item skill-env" @click="useSlash(s.name)">
            <div class="skill-info">
              <span class="slash-cmd">/{{ s.name }}</span>
              <a-tag v-if="s.source === 'project'" color="blue" style="margin-left:6px">项目</a-tag>
              <a-tag v-else color="purple" style="margin-left:6px">用户</a-tag>
              <div class="skill-desc">{{ s.description }}</div>
            </div>
          </div>
          <p class="muted" v-if="!filteredSkills.length">无匹配 Skill</p>
        </a-tab-pane>

        <!-- ⭐ Slash commands (loaded from SDK init) -->
        <a-tab-pane key="slash" :tab="`Slash 指令 (${slashCommands.length})`">
          <p class="muted" v-if="!slashCommands.length">会话启动后加载</p>
          <div v-for="c in slashCommands" :key="c" class="env-item slash-env" @click="useSlash(c)">
            <span class="slash-cmd">/{{ c }}</span>
          </div>
        </a-tab-pane>
      </a-tabs>
    </a-drawer>

    <!-- ⭐ Workspace manager -->
    <a-modal v-model:open="wsManagerOpen" title="工作区管理" width="620" :footer="null">
      <div class="ws-manager-body">
        <div class="ws-manager-header">
          <p class="muted">保存常用工作目录，快速切换 Claude Code 运行上下文（加载对应 .claude/skills + .mcp.json）</p>
        </div>

        <!-- New workspace form -->
        <div class="ws-form">
          <a-input v-model:value="wsForm.name" placeholder="工作区名称（如 RAG知识库）" style="flex:2" />
          <a-input v-model:value="wsForm.path" placeholder="绝对路径" style="flex:3" />
          <a-button type="primary" @click="saveWorkspace" :disabled="!wsForm.name || !wsForm.path">
            <SaveOutlined /> 保存
          </a-button>
        </div>

        <!-- Saved workspace list -->
        <div class="ws-list">
          <div v-for="ws in workspaces" :key="ws.id" class="ws-item">
            <div class="ws-item-info" @click="selectWorkspace(ws)">
              <div class="ws-item-name">
                <PushpinOutlined v-if="ws.pin_order" style="color:var(--kb-amber);font-size:11px" />
                <FolderOpenOutlined style="color:var(--kb-primary)" />
                <strong>{{ ws.name }}</strong>
              </div>
              <div class="ws-item-path">{{ ws.path }}</div>
              <div v-if="ws.description" class="ws-item-desc">{{ ws.description }}</div>
              <div v-if="ws.last_used" class="ws-item-meta">上次使用: {{ new Date(ws.last_used).toLocaleString() }}</div>
            </div>
            <div class="ws-item-actions">
              <a-tooltip title="选择并开始对话">
                <a-button size="small" type="primary" ghost @click="selectWorkspace(ws)"><ArrowRightOutlined /></a-button>
              </a-tooltip>
              <a-tooltip title="置顶切换">
                <a-button size="small" @click="togglePin(ws)">
                  <PushpinOutlined :style="ws.pin_order ? {color:'var(--kb-amber)'} : {}" />
                </a-button>
              </a-tooltip>
              <a-popconfirm title="删除此工作区？" @confirm="deleteWorkspace(ws.id)">
                <a-button size="small" danger><DeleteOutlined /></a-button>
              </a-popconfirm>
            </div>
          </div>
          <div v-if="!workspaces.length" class="ws-empty">
            <FolderOpenOutlined style="font-size:32px;color:var(--kb-fg-mute)" />
            <p>还没有保存的工作区</p>
            <p class="muted">填写上方表单添加第一个工作区</p>
          </div>
        </div>
      </div>
    </a-modal>

    <!-- History sessions -->
    <a-modal v-model:open="sessionsVisible" title="历史会话（SQLite 持久化）" width="680">
      <template #extra>
        <a-button v-if="loadingSessions" loading size="small">加载中…</a-button>
      </template>
      <a-list :data-source="sessions" size="small" :loading="loadingSessions">
        <template #renderItem="{ item }">
          <a-list-item class="history-item" @click="loadHistory(item.session_id)">
            <a-list-item-meta>
              <template #title>
                <span class="history-title">{{ item.title || item.session_id.slice(0, 16) + '…' }}</span>
              </template>
              <template #description>
                {{ new Date(item.updated_at).toLocaleString() }} · {{ item.message_count }} 条消息
                <span v-if="item.model" class="muted">· {{ item.model }}</span>
              </template>
              <template #avatar><MessageOutlined style="font-size:20px;color:#1677ff" /></template>
            </a-list-item-meta>
            <template #extra>
              <a-popconfirm title="删除此会话及其消息？" @confirm.stop="deleteHistory(item.session_id)">
                <a-button size="small" danger @click.stop><DeleteOutlined /></a-button>
              </a-popconfirm>
            </template>
          </a-list-item>
        </template>
        <template #footer><span class="muted">点击整行加载历史消息并继续对话</span></template>
      </a-list>
    </a-modal>

    <!-- Permission dialog (default/acceptEdits/plan mode) -->
    <a-modal
      :open="!!permissionReq"
      :closable="false"
      :maskClosable="false"
      :keyboard="false"
      width="600"
      title="工具权限请求"
    >
      <div v-if="permissionReq" class="perm-body">
        <p class="perm-hint">Claude 想使用工具 <a-tag color="orange">{{ permissionReq.display }}</a-tag></p>
        <div class="perm-input-block">
          <div class="muted">Input:</div>
          <pre class="perm-input">{{ fmt(permissionReq.input) }}</pre>
        </div>
        <p class="muted" style="margin-top:10px">允许则 Claude 继续执行；拒绝则该工具被跳过。</p>
      </div>
      <template #footer>
        <a-button danger @click="denyPermission">拒绝 (Deny)</a-button>
        <a-button type="primary" @click="allowPermission">允许 (Allow)</a-button>
      </template>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, nextTick, onMounted, watch } from 'vue'
import { parseMarkdown } from '~/utils/markdown'
import { useMarkdownRenderer } from '~/composables/useMarkdownRenderer'
import 'katex/dist/katex.min.css'
import { message as antMessage } from 'ant-design-vue'
import {
  RobotOutlined, UserOutlined, InfoCircleOutlined,
  AppstoreOutlined, HistoryOutlined, ClearOutlined,
  MessageOutlined, DeleteOutlined, BulbOutlined,
  CodeOutlined, FileTextOutlined, CheckSquareOutlined,
  QuestionCircleOutlined, LockOutlined, ThunderboltOutlined,
  FolderOpenOutlined, PlusOutlined, SaveOutlined,
  PushpinOutlined, ArrowRightOutlined,
  PaperClipOutlined, CloseOutlined,
  VerticalAlignBottomOutlined,
  SearchOutlined, DatabaseOutlined, BookOutlined,
  OrderedListOutlined, EditOutlined, SendOutlined,
  PlusSquareOutlined, SyncOutlined,
  PauseCircleOutlined, CaretRightOutlined,
} from '@ant-design/icons-vue'
import { PERMISSION_MODES, PERMISSION_MODE_INFO, type PermissionMode } from '~/utils/claude'
import { MessageProcessor, type UIMessage } from '~/utils/claude-messages'
import {
  BUILT_IN_TOOLS, TOOL_CATEGORY_ORDER,
  formatSize, attachmentIcon as attIcon, attachmentTypeLabel as attTypeLabel,
  type Attachment,
} from '~/utils/claude-tools'

const cwd = ref('')
const permissionMode = ref<PermissionMode>('bypassPermissions')
const model = ref('')
const input = ref('')
const messages = reactive<UIMessage[]>([])
const streaming = ref(false)
const currentSessionId = ref('')
// 回放的消息里是否已包含用户提问气泡（新会话有，旧会话没有）。
// 主题卡片仅在「没有用户气泡」时显示，避免与真实用户消息重复。
const msgRef = ref<HTMLElement | null>(null)
const inputRef = ref<any>(null)
const abortController = ref<AbortController | null>(null)
const processor = new MessageProcessor()

// ⭐ Reasoning effort control
const reasoningEffort = ref<'auto' | 'low' | 'medium' | 'high' | 'xhigh' | 'max'>('auto')

// ⭐ Message queue — production-grade FIFO with context snapshots
interface QueueItem {
  id: string
  text: string
  status: 'pending' | 'editing' | 'sending' | 'sent' | 'failed'
  created_at: number
  /** Context snapshot at queue time (ensures consistency even if user changes settings later) */
  cwd: string
  permissionMode: PermissionMode
  model: string
  reasoningEffort: string
  /** Original attachments (snapshot of names — actual files already uploaded at queue time) */
  attachmentNames: string[]
  /** Error message if status === 'failed' */
  error?: string
  /** Sent count increments each retry attempt */
  retryCount: number
}
const messageQueue = ref<QueueItem[]>([])
const queueEditText = ref('')
let queueIdCounter = 0
/** When true, queue auto-consumption is paused */
const queuePaused = ref(false)
/** Maximum auto-retries before marking as failed */
const MAX_QUEUE_RETRIES = 3
/** localStorage persistence key */
const QUEUE_STORAGE_KEY = 'claude-chat-queue'

// ⭐ Background sessions (running conversation continues after "New Chat")
interface BgSession {
  id: string
  prompt: string
  cwd: string
  permissionMode: string
  model: string
  reasoningEffort: string
  abortController: AbortController | null
  reader: ReadableStreamDefaultReader<Uint8Array> | null
  sessionId: string
  messages: UIMessage[]
  streamingText: string
  streamingThinking: string
  createdAt: number
}
const bgSessions = ref<BgSession[]>([])
const activeBgId = ref<string | null>(null)
// ⭐ Stream generation ID: incremented on newConversation, guards against old SSE leaking into new state
let streamGenId = 0
// Reader detached → streaming continues but UI won't process events
let detachedReader: ReadableStreamDefaultReader<Uint8Array> | null = null
let detachedAbortController: AbortController | null = null

/**
 * New conversation — detach current stream (continues in background), preserve input, reset UI.
 */
function newConversation() {
  const savedInput = input.value

  // ⭐ Queue survives new conversation — it represents user intent
  //    that was explicitly added. Do NOT clear it here.

  // If streaming: detach current SSE stream (keep it alive, don't abort)
  if (streaming.value && abortController.value) {
    // Save current state as background session
    const bg: BgSession = {
      id: 'bg_' + Date.now().toString(36),
      prompt: messages.filter(m => m.kind === 'user').pop()?.text || '(无文本)',
      cwd: cwd.value,
      permissionMode: permissionMode.value,
      model: model.value,
      reasoningEffort: reasoningEffort.value,
      abortController: abortController.value,
      reader: null, // SSE reader isn't accessible after initial setup; the fetch continues
      sessionId: currentSessionId.value,
      messages: [...messages],
      streamingText: streamingText.value,
      streamingThinking: streamingThinking.value,
      createdAt: Date.now(),
    }
    bgSessions.value.push(bg)
    activeBgId.value = bg.id

    // Detach: zero-out refs so the old stream's events are silently discarded
    // The fetch/SSE stream continues in background. When done, will call
    // streaming=false etc., but those are now harmless since we reset the state.
    streaming.value = false
    abortController.value = null
    showStreamingCursor.value = false
    streamingText.value = ''
    streamingThinking.value = ''
  }

  // Reset UI to fresh conversation
  messages.length = 0
  processor.reset()
  currentSessionId.value = ''
  initInfo.tools = []
  initInfo.mcpServers = []
  initInfo.model = ''
  slashCommands.value = []
  unreadCount.value = 0
  isAtBottom.value = true
  streamGenId++ // Prevent old SSE events from leaking into new UI state

  // Keep input text
  input.value = savedInput
  nextTick(() => inputRef.value?.focus?.())
  antMessage.success('新对话已创建' + (bgSessions.value.length ? `（${bgSessions.value.length} 个对话在后台继续）` : ''))
}

/**
 * Switch back to a background session
 */
function switchToBg(bg: BgSession) {
  // Save current state as another bg session if active
  if (streaming.value || messages.length > 0) {
    newConversation()
  }
  // Remove this bg session from list and restore its state
  bgSessions.value = bgSessions.value.filter(s => s.id !== bg.id)
  messages.splice(0, messages.length, ...bg.messages)
  cwd.value = bg.cwd
  permissionMode.value = bg.permissionMode as any
  model.value = bg.model
  reasoningEffort.value = bg.reasoningEffort as any
  currentSessionId.value = bg.sessionId
  // Allow abort of the background session now that it's active
  abortController.value = bg.abortController
  antMessage.success('已切换到后台对话')
}

/**
 * Remove a background session (no switch)
 */
function removeBg(id: string) {
  const bg = bgSessions.value.find(s => s.id === id)
  if (bg?.abortController) {
    try { bg.abortController.abort() } catch { /* already done */ }
  }
  bgSessions.value = bgSessions.value.filter(s => s.id !== id)
}

// ⭐ Quick action buttons
const QUICK_ACTIONS = [
  { icon: '❓', label: '/help', action: '/help' },
  { icon: '🗂', label: '/skills', action: '/skills' },
  { icon: '🔌', label: '/mcp', action: '/mcp' },
  { icon: '📋', label: '/list', action: '/list' },
  { icon: '🔍', label: 'Search KB', action: 'search KB: ' },
  { icon: '📖', label: 'Show KBs', action: 'show me all knowledge bases' },
  { icon: '🧹', label: 'Audit KB', action: 'please verify all knowledge bases' },
  { icon: '⚡', label: 'Clear', action: '/clear' },
]

function queueAction(act: typeof QUICK_ACTIONS[0]) {
  input.value = act.action + (act.action.endsWith(' ') ? '' : ' ')
  nextTick(() => inputRef.value?.focus?.())
}

/**
 * ═══════════════════════════════════════════════════════════════════
 * ⭐ Production-Grade Message Queue
 *
 * Design:
 * 1. Context snapshot at queue time — KB settings, model, permission mode
 *    are captured and locked so queue items don't change behavior mid-queue.
 * 2. Explicit state machine: pending → sending → sent | failed
 * 3. Retry with configurable max attempts (MAX_QUEUE_RETRIES)
 * 4. localStorage persistence for crash recovery (page refresh = queue survives)
 * 5. Pause/resume for manual control
 * 6. Sequential consumption — one item at a time, only when streaming is idle
 *     AND the previous item's result has fully returned
 * ═══════════════════════════════════════════════════════════════════
 */

// Persistence helpers
function saveQueueToStorage() {
  try {
    const serializable = messageQueue.value.map((item) => ({
      id: item.id,
      text: item.text,
      status: item.status,
      created_at: item.created_at,
      cwd: item.cwd,
      permissionMode: item.permissionMode,
      model: item.model,
      reasoningEffort: item.reasoningEffort,
      attachmentNames: item.attachmentNames,
      error: item.error,
      retryCount: item.retryCount,
    }))
    localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(serializable))
  } catch {
    /* localStorage may be full or unavailable */
  }
}

function loadQueueFromStorage() {
  try {
    const raw = localStorage.getItem(QUEUE_STORAGE_KEY)
    if (!raw) return
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return
    // Reset any 'sending' items back to 'pending' (crashed mid-send)
    messageQueue.value = parsed.map((item: any) => ({
      ...item,
      status: item.status === 'sending' ? 'pending' : item.status,
      retryCount: item.retryCount ?? 0,
      attachmentNames: item.attachmentNames ?? [],
      error: item.status === 'sending' ? '上次发送中断，重试中...' : item.error,
    }))
    // Restore ID counter
    const maxNum = messageQueue.value.reduce((max: number, item: QueueItem) => {
      const num = parseInt(item.id.replace('q_', ''), 10)
      return Number.isNaN(num) ? max : Math.max(max, num)
    }, 0)
    queueIdCounter = maxNum
  } catch {
    /* Corrupt localStorage entry — ignore */
  }
}

/**
 * Core: add a message to the end of the queue with full context snapshot.
 * If the queue is empty and no streaming is active, the item is consumed immediately
 * (it's a direct send, not actually queued).
 */
function addToQueue() {
  const text = input.value.trim()
  if (!text) return

  messageQueue.value.push({
    id: `q_${++queueIdCounter}`,
    text,
    status: 'pending',
    created_at: Date.now(),
    cwd: cwd.value,
    permissionMode: permissionMode.value,
    model: model.value,
    reasoningEffort: reasoningEffort.value,
    attachmentNames: attachments.value.map((a) => a.name),
    retryCount: 0,
  })

  input.value = ''
  saveQueueToStorage()
  antMessage.success(`已加入队列 (${queueCounts.value.pending + 1})`)
}

/**
 * Remove a specific item from the queue (bypassing the sequential order).
 * Does NOT affect the currently-sending item.
 */
function removeFromQueue(id: string) {
  const idx = messageQueue.value.findIndex((item) => item.id === id)
  if (idx === -1) return
  if (messageQueue.value[idx].status === 'sending') {
    antMessage.warning('当前正在发送中，无法删除')
    return
  }
  messageQueue.value.splice(idx, 1)
  saveQueueToStorage()
}

/**
 * Clear all PENDING items. The currently-sending item (if any) is not cleared.
 */
function clearQueue() {
  messageQueue.value = messageQueue.value.filter((item) => item.status === 'sending')
  saveQueueToStorage()
  antMessage.success('队列已清空')
}

/**
 * ⭐ Toggle queue pause/resume.
 * When paused, auto-consumption is suspended but current send continues.
 * When resumed, the next pending item starts immediately.
 */
function toggleQueuePause() {
  queuePaused.value = !queuePaused.value
  if (!queuePaused.value && !streaming.value) {
    consumeQueue()
  }
  antMessage.info(queuePaused.value ? '队列已暂停' : '队列已恢复')
}

/**
 * ⭐ Core queue consumer — sends the next PENDING item in FIFO order.
 *
 * Called ONLY from the streaming → false watch callback (the response-completed
 * hook). Never called directly by the user. Checks pause + streaming guard
 * to prevent double-send, then fires sendRaw for the head-of-line item.
 */
function consumeQueue() {
  if (queuePaused.value) return
  if (streaming.value) return         // safety—should never be true here

  const nextIdx = messageQueue.value.findIndex((item) => item.status === 'pending')
  if (nextIdx === -1) return

  const item = messageQueue.value[nextIdx]
  item.status = 'sending'
  item.error = undefined
  saveQueueToStorage()

  // Restore the context snapshot captured at queue time
  const savedCwd = cwd.value
  const savedPm = permissionMode.value
  const savedModel = model.value
  const savedEffort = reasoningEffort.value

  cwd.value = item.cwd
  permissionMode.value = item.permissionMode as any
  model.value = item.model
  reasoningEffort.value = item.reasoningEffort as any

  // Push user bubble + fire (sendRaw handles streaming=true internally)
  messages.push({ kind: 'user', text: item.text, id: Date.now() })

  nextTick(() => {
    sendRaw(item.text)
      .then(() => {
        item.status = 'sent'
        saveQueueToStorage()
        setTimeout(() => {
          messageQueue.value = messageQueue.value.filter((q) => q.id !== item.id)
          saveQueueToStorage()
        }, 800)
      })
      .catch((err) => {
        item.error = err?.message || String(err)
        item.retryCount++
        if (item.retryCount < MAX_QUEUE_RETRIES) {
          item.status = 'pending'
          antMessage.warning(`队列消息发送失败 (${item.retryCount}/${MAX_QUEUE_RETRIES}): ${item.error}. 将自动重试...`)
        } else {
          item.status = 'failed'
          antMessage.error(`队列消息发送彻底失败 (${MAX_QUEUE_RETRIES} 次重试均已失败): ${item.error}`)
        }
        saveQueueToStorage()
      })
      .finally(() => {
        cwd.value = savedCwd
        permissionMode.value = savedPm as any
        model.value = savedModel
        reasoningEffort.value = savedEffort
      })
  })
}

// ══════ Auto-consumption hook: streaming changed ══════

watch(streaming, (newVal: boolean, oldVal: boolean | undefined) => {
  // Only care about true→false transitions (stream just ended).
  // Guard against phantom firings (newVal === oldVal) and the initial
  // mount (newVal is false and oldVal is undefined).
  if (!newVal && oldVal !== undefined && newVal !== oldVal) {
    setTimeout(() => consumeQueue(), 300)
  }
})

// ── Queue item actions (from UI) ──

function startEdit(item: QueueItem) {
  if (item.status === 'sending') return
  item.status = 'editing'
  queueEditText.value = item.text
}

function confirmEdit(item: QueueItem) {
  if (queueEditText.value.trim()) {
    item.text = queueEditText.value.trim()
  }
  item.status = 'pending'
  saveQueueToStorage()
}

function cancelEdit(item: QueueItem) {
  item.status = 'pending'
  queueEditText.value = ''
}

/** Manually send a specific queue item immediately (skip the line) */
function sendQueueItem(item: QueueItem) {
  if (streaming.value) {
    antMessage.warning('正在回答中，请等待当前回答完成')
    return
  }
  messageQueue.value = messageQueue.value.filter((q) => q.id !== item.id)
  saveQueueToStorage()

  // Restore context snapshot from this item
  const prevCwd = cwd.value
  const prevPm = permissionMode.value
  const prevModel = model.value
  const prevEffort = reasoningEffort.value
  cwd.value = item.cwd
  permissionMode.value = item.permissionMode as any
  model.value = item.model
  reasoningEffort.value = item.reasoningEffort as any

  messages.push({ kind: 'user', text: item.text, id: Date.now() })
  nextTick(() => {
    sendRaw(item.text).finally(() => {
      cwd.value = prevCwd
      permissionMode.value = prevPm as any
      model.value = prevModel
      reasoningEffort.value = prevEffort
    })
  })
}

/** Retry a failed queue item — goes back to pending, then the next consumeQueue cycle picks it up */
function retryQueueItem(item: QueueItem) {
  if (item.status !== 'failed') return
  item.status = 'pending'
  item.error = undefined
  item.retryCount = 0
  saveQueueToStorage()
  // If idle right now, send immediately
  if (!streaming.value) consumeQueue()
}

/** Retry all failed items */
function retryAllFailed() {
  for (const item of messageQueue.value) {
    if (item.status === 'failed') {
      item.status = 'pending'
      item.error = undefined
      item.retryCount = 0
    }
  }
  saveQueueToStorage()
  if (!streaming.value) consumeQueue()
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: '等待发送',
    sending: '发送中…',
    sent: '已发送 ✓',
    failed: '发送失败 ✗',
    editing: '编辑中',
  }
  return map[status] || status
}

/** Queue counts by status */
const queueCounts = computed(() => {
  let pending = 0, sending = 0, sent = 0, failed = 0
  for (const item of messageQueue.value) {
    if (item.status === 'pending') pending++
    else if (item.status === 'sending') sending++
    else if (item.status === 'sent') sent++
    else if (item.status === 'failed') failed++
  }
  return { pending, sending, sent, failed }
})

// ⭐ Workspace state
const wsManagerOpen = ref(false)
const workspaces = ref<any[]>([])
const wsForm = ref({ name: '', path: '', description: '' })
const workspaceOptions = computed(() => {
  return workspaces.value.map((ws: any) => ({
    label: ws.name,
    value: ws.path,
    desc: ws.description,
    pin: !!ws.pin_order,
  }))
})

// ⭐ Attachment state
const attachments = ref<Attachment[]>([])
const fileInputRef = ref<HTMLInputElement | null>(null)
const ACCEPTED_TYPES = 'image/* ,.pdf,.md,.txt,.json,.yaml,.yml,.xml,.js,.ts,.jsx,.tsx,.py,.java,.go,.rs,.c,.cpp,.h,.html,.css,.vue,.sh,.bat,.sql,.csv,.log,.docx,.pptx,.xlsx'
const inputPlaceholder = computed(() =>
  attachments.value.length
    ? `描述你想让 Claude 对附件做什么（Enter 发送 · Shift+Enter 换行）…`
    : '问 Claude（Enter 发送 · 输入 / 触发指令 · 📎加附件 · Shift+Enter 换行）…'
)

// KB-enhanced answer state
const kbEnhanced = ref(false)
const selectedKbIds = ref<string[]>([])
const availableKbs = ref<Array<{ kbId: string; name: string; description: string; documentCount: number }>>([])
const loadingKbs = ref(false)
const kbOptions = computed(() =>
  availableKbs.value.map((kb) => ({
    label: `${kb.name} (${kb.documentCount} docs)`,
    value: kb.kbId,
    desc: kb.description,
  }))
)

// ⭐ Tool/skill catalog state
const toolSearch = ref('')
const skillSearch = ref('')
const skillCatalog = ref<any[]>([])
const filteredSkills = computed(() => {
  const q = skillSearch.value.trim().toLowerCase()
  if (!q) return skillCatalog.value
  return skillCatalog.value.filter((s: any) =>
    s.name.toLowerCase().includes(q) || (s.description || '').toLowerCase().includes(q)
  )
})
function filteredToolsByCategory(cat: string) {
  const q = toolSearch.value.trim().toLowerCase()
  const tools = BUILT_IN_TOOLS.filter(t => t.category === cat)
  if (!q) return tools
  return tools.filter(t => t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q))
}

// Environment info (from init message)
const initInfo = reactive<{
  tools: string[]
  mcpServers: { name: string; status: string }[]
  model: string
}>({ tools: [], mcpServers: [], model: '' })
const slashCommands = ref<string[]>([])

// Slash command menu — merged: SDK slash_commands + project/user skills from catalog
const allSlashCommands = computed(() => {
  const set = new Set<string>(slashCommands.value)
  for (const s of skillCatalog.value) set.add(s.name)
  return Array.from(set)
})
const slashOpen = computed(() => input.value.startsWith('/') && allSlashCommands.value.length > 0)
const filteredSlash = computed(() => {
  const q = input.value.slice(1).toLowerCase()
  return allSlashCommands.value
    .filter((c) => c.toLowerCase().includes(q))
    .slice(0, 20)
})
const slashIdx = ref(0)
// ⭐ Merged SDK slash_commands + SkillCatalog descriptions
const slashDescriptions = computed(() => {
  const map: Record<string, string> = {}
  for (const s of skillCatalog.value) {
    map[s.name] = s.description
  }
  return map
})

// Panel / Modals
const panelOpen = ref(false)
const sessionsVisible = ref(false)
const sessions = ref<any[]>([])
const loadingSessions = ref(false)

// Permission approval (canUseTool)
const permissionReq = ref<{
  open: boolean
  toolName: string
  display: string
  input: any
  toolUseId: string
  sessionId: string
} | null>(null)

function md(t: string) {
  if (!t) return ''
  try {
    return parseMarkdown(t)
  } catch {
    return '<pre>' + t.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</pre>'
  }
}

/**
 * 代码块增强：给每个 <pre> 加复制按钮 + 语言标签角标（仅处理一次，幂等）。
 * 在每条消息渲染后调用。
 */
function enhanceCodeBlocks() {
  const root = msgRef.value
  if (!root) return
  const pres = root.querySelectorAll('pre')
  pres.forEach((pre) => {
    if ((pre as HTMLElement).dataset.enhanced) return
    const code = pre.querySelector('code')
    const lang = (code?.className || '').match(/language-([\w+-]+)/)?.[1] || ''
    const el = pre as HTMLElement
    el.dataset.enhanced = '1'
    el.classList.add('code-block')
    if (lang) { el.dataset.lang = lang; el.classList.add('has-lang') }
    const btn = document.createElement('button')
    btn.className = 'code-copy-btn'
    btn.type = 'button'
    btn.textContent = '复制'
    btn.addEventListener('click', () => {
      const text = code?.textContent || pre.textContent || ''
      navigator.clipboard?.writeText(text).then(() => {
        btn.textContent = '已复制 ✓'
        setTimeout(() => { btn.textContent = '复制' }, 1500)
      }).catch(() => {})
    })
    pre.appendChild(btn)
  })
}

// ── Mermaid diagram rendering after content updates ──
const { initMermaid } = useMarkdownRenderer()
let mermaidTimer: ReturnType<typeof setTimeout> | null = null

/** Debounced scan of the message area for Mermaid blocks.
 *  Re-renders only diagrams that have not yet been processed. */
function scheduleMermaidRender() {
  if (mermaidTimer) clearTimeout(mermaidTimer)
  mermaidTimer = setTimeout(async () => {
    if (!msgRef.value) return
    try {
      await initMermaid(msgRef.value)
    } catch (err) {
      console.debug('Mermaid init skipped:', err)
    }
  }, 300)
}

function fmt(o: any) { try { return JSON.stringify(o, null, 2).slice(0, 800) } catch { return String(o) } }
function preview(name: string, inp: any) { return MessageProcessor.formatInputPreview(name, inp) }

// ══════ Smart scroll: auto-follow at bottom, otherwise show"↓ new messages" ══════
const isAtBottom = ref(true)
const unreadCount = ref(0)
const SCROLL_THRESHOLD = 80 // px — 距底部多少以内算"在底部"

/**
 * 真正的滚动容器：现在 .messages 自己 overflow:auto 滚动（三段式布局）。
 * 从 .messages 向上找最近的滚动祖先（兼容性兜底）。
 */
function getScrollEl(): HTMLElement | null {
  let el: HTMLElement | null = msgRef.value
  while (el) {
    const ov = getComputedStyle(el).overflowY
    if (ov === 'auto' || ov === 'scroll') return el
    el = el.parentElement
  }
  return msgRef.value
}

function onMessagesScroll() {
  const el = getScrollEl()
  if (!el) return
  const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
  isAtBottom.value = distFromBottom < SCROLL_THRESHOLD
  // Reset unread count when back at bottom
  if (isAtBottom.value) unreadCount.value = 0
}

function scrollToBottom(behavior: ScrollBehavior = 'smooth') {
  nextTick(() => {
    const el = getScrollEl()
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior })
    isAtBottom.value = true
    unreadCount.value = 0
  })
}

// RAF throttle: max one scroll per frame to avoid jank
let rafPending = false
function scrollToBottomRAF() {
  if (rafPending) return
  rafPending = true
  requestAnimationFrame(() => {
    rafPending = false
    const el = getScrollEl()
    if (!el) return
    el.scrollTop = el.scrollHeight // instant（高频流式不用 smooth）
  })
}

/** Smart scroll: follow only when at bottom */
function smartScroll() {
  if (isAtBottom.value) {
    scrollToBottom('smooth')
  } else {
    // Not at bottom -> accumulate unread
    unreadCount.value++
  }
}

/* * Streaming scroll: RAF throttle + instant */
function streamScroll() {
  if (isAtBottom.value) {
    scrollToBottomRAF()
  }
}

/* * Streaming typewriter text (accumulated) */
const streamingText = ref('')
const streamingThinking = ref('')
const showStreamingCursor = ref(false)

// ── Mermaid watchers (must be AFTER streamingText is defined) ──
watch(() => messages.length, () => { nextTick(scheduleMermaidRender) })
watch(streamingText, (val) => {
  if (val && val.includes('```mermaid')) { nextTick(scheduleMermaidRender) }
})
watch(streaming, (val) => {
  if (!val) nextTick(scheduleMermaidRender)
})

/* * Handle stream_event (token-level delta) — typewriter */
function handleStreamEvent(sdkMsg: any) {
  const evt = sdkMsg.event
  if (!evt || !evt.type) return

  if (evt.type === 'content_block_start' && evt.index !== undefined) {
    const block = evt.content_block
    if (block?.type === 'text') {
      // New text block → accumulate into streamingText
      showStreamingCursor.value = true
    } else if (block?.type === 'thinking') {
      streamingThinking.value = ''
    }
  } else if (evt.type === 'content_block_delta') {
    const delta = evt.delta
    if (delta?.type === 'text_delta' && delta.text) {
      streamingText.value += delta.text
      showStreamingCursor.value = true
      streamScroll() // 流式专用 RAF 节流滚动
    } else if (delta?.type === 'thinking_delta' && delta.thinking) {
      streamingThinking.value += delta.thinking
    }
  } else if (evt.type === 'content_block_stop') {
    // Block ends, keep text (replaced by full assistant message)
  } else if (evt.type === 'message_stop') {
    showStreamingCursor.value = false
  }
}

function handleSdkMessage(sdkMsg: any) {
  // ⭐ Streaming partial message → typewriter delta
  if (sdkMsg.type === 'stream_event') {
    handleStreamEvent(sdkMsg)
    return
  }

  // ⭐ Full assistant message → clear streaming buffer
  if (sdkMsg.type === 'assistant') {
    streamingText.value = ''
    streamingThinking.value = ''
  }

  const uiMsgs = processor.process(sdkMsg)
  for (const m of uiMsgs) messages.push(m)
  if (sdkMsg.type === 'system' && sdkMsg.subtype === 'init') {
    currentSessionId.value = sdkMsg.session_id || ''
    initInfo.tools = sdkMsg.tools || []
    initInfo.mcpServers = (sdkMsg.mcp_servers || []).map((m: any) => ({ name: m.name, status: m.status }))
    initInfo.model = sdkMsg.model || ''
    slashCommands.value = sdkMsg.slash_commands || []
  }
  if (sdkMsg.type === 'result') {
    streaming.value = false
    showStreamingCursor.value = false
  }
  smartScroll()
  nextTick(enhanceCodeBlocks)
}

function handleSseBlock(block: string) {
  const lines = block.split('\n')
  let evt = 'message', data = ''
  for (const l of lines) {
    if (l.startsWith('event: ')) evt = l.slice(7).trim()
    else if (l.startsWith('data: ')) data += l.slice(6)
  }
  if (!data) return
  let obj: any
  try { obj = JSON.parse(data) } catch { return }
  if (evt === 'meta') return
  if (evt === 'permission_request') {
    // canUseTool request → show approval dialog
    const parsed = parseToolDisplay(obj.toolName)
    permissionReq.value = {
      open: true,
      toolName: obj.toolName,
      display: parsed,
      input: obj.input,
      toolUseId: obj.toolUseId,
      sessionId: obj.sessionId,
    }
    return
  }
  if (evt === 'error') {
    messages.push({ kind: 'error', text: obj.error || '未知错误', id: Date.now() })
    streaming.value = false
    return
  }
  if (evt === 'done') { handleSdkMessage(obj); streaming.value = false; return }
  handleSdkMessage(obj)
}

async function sendRaw(prompt: string, atts?: Attachment[]): Promise<void> {
  streaming.value = true
  const myGenId = streamGenId // Capture which generation this stream belongs to
  // User sends → force scroll to bottom to follow
  isAtBottom.value = true
  unreadCount.value = 0
  scrollToBottom('smooth')
  abortController.value = new AbortController()
  try {
    const resp = await fetch('/api/claude/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        cwd: cwd.value.trim() || undefined,
        permissionMode: permissionMode.value,
        model: model.value.trim() || undefined,
        resume: currentSessionId.value || undefined,
        attachments: atts && atts.length ? atts : undefined,
        kbEnhanced: kbEnhanced.value || undefined,
        kbIds: kbEnhanced.value && selectedKbIds.value.length ? selectedKbIds.value : undefined,
        reasoningEffort: reasoningEffort.value === 'auto' ? undefined : reasoningEffort.value,
      }),
      signal: abortController.value.signal,
    })
    if (myGenId !== streamGenId) return // Detached: silently ignore response
    if (!resp.ok || !resp.body) {
      const t = await resp.text()
      throw new Error(`HTTP ${resp.status}: ${t}`)
    }
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      if (myGenId !== streamGenId) {
        // This stream was detached — cancel reading but let backend finish
        reader.cancel().catch(() => {})
        return
      }
      buf += decoder.decode(value, { stream: true })
      let i: number
      while ((i = buf.indexOf('\n\n')) >= 0) {
        const b = buf.slice(0, i); buf = buf.slice(i + 2); handleSseBlock(b)
      }
    }
  } catch (e: any) {
    if (myGenId !== streamGenId) return // Silently ignore errors from detached streams
    if (e.name === 'AbortError') {
      messages.push({ kind: 'system', subtype: 'abort', text: '_已中断_', id: Date.now() })
    } else {
      const errMsg = e?.message || String(e)
      antMessage.error(errMsg)
      messages.push({ kind: 'error', text: errMsg, id: Date.now() })
      // ⭐ Re-throw so queue consumer can detect failures
      throw e
    }
  } finally {
    // Only update state if this is still the active stream
    if (myGenId === streamGenId) {
      streaming.value = false
      abortController.value = null
      showStreamingCursor.value = false
      streamingText.value = ''
      streamingThinking.value = ''
      smartScroll()
    }
    // Clean up background session when its stream finishes
    bgSessions.value = bgSessions.value.filter(s => {
      if (s.abortController === abortController.value || s.id === activeBgId.value) {
        antMessage.info('后台对话已完成: ' + (s.prompt?.slice(0, 40) || '') + '…')
        return false
      }
      return true
    })
  }
}

function send() {
  const prompt = input.value.trim()
  const atts = [...attachments.value]
  if (!prompt && !atts.length) return

  // ⭐ Streaming → auto-queue. User presses Enter/Send → goes to the back
  //    of the queue. The model is busy; their message waits calmly.
  if (streaming.value) {
    if (!prompt) {
      antMessage.warning('回答中暂不支持仅附件排队，请输入文本或等待回答完成')
      return
    }
    addToQueue()
    return
  }

  // ⭐ Idle → send directly (not through the queue).
  const attSummary = atts.length
    ? `\n\n📎 Attachments (${atts.length}): ${atts.map(a => a.name).join(', ')}`
    : ''
  const kbSummary = kbEnhanced.value
    ? (selectedKbIds.value.length
      ? `\n\n🔍 KB-enhanced: searching ${selectedKbIds.value.length} KB(s)`
      : '\n\n🔍 KB-enhanced: searching all KBs')
    : ''
  messages.push({ kind: 'user', text: prompt + attSummary + kbSummary, id: Date.now() })
  input.value = ''
  attachments.value = []
  slashIdx.value = 0
  sendRaw(prompt || 'Please analyze the attached files', atts)
}

// ══════ Attachment handling ══════

function triggerFilePicker() {
  fileInputRef.value?.click()
}

async function onFilePicked(e: Event) {
  const target = e.target as HTMLInputElement
  const files = target.files
  if (!files || !files.length) return

  const fd = new FormData()
  for (const f of Array.from(files)) fd.append('files', f)

  try {
    const d: any = await $fetch('/api/claude/upload', {
      method: 'POST',
      body: fd,
    })
    if (d.attachments) {
      attachments.value.push(...d.attachments)
      antMessage.success(`已添加 ${d.count} 个附件`)
    }
  } catch (e: any) {
    antMessage.error('上传失败: ' + (e?.message || e?.data?.statusMessage || e))
  } finally {
    target.value = '' // 允许重复选择同一文件
  }
}

function removeAttachment(id: string) {
  attachments.value = attachments.value.filter(a => a.id !== id)
}

// KB-enhanced answer functions
function toggleKbEnhanced() {
  kbEnhanced.value = !kbEnhanced.value
  if (kbEnhanced.value && !availableKbs.value.length) {
    loadKbCatalog()
  }
}

async function loadKbCatalog() {
  loadingKbs.value = true
  try {
    const d: any = await $fetch('/api/kb/catalog')
    availableKbs.value = (d.knowledgeBases || []).map((kb: any) => ({
      kbId: kb.kbId,
      name: kb.name,
      description: kb.description || '',
      documentCount: kb.documentCount || 0,
    }))
  } catch (e: any) {
    antMessage.error('Failed to load KB catalog: ' + (e?.message || e))
  } finally {
    loadingKbs.value = false
  }
}

function filterKbOption(input: string, option: any) {
  const q = input.toLowerCase()
  return (
    option.label.toLowerCase().includes(q) ||
    (option.desc || '').toLowerCase().includes(q)
  )
}

function onKbSelectionChange(value: string[]) {
  selectedKbIds.value = value
}

function answerAsk(msg: any, answer: string) {
  if (msg.answered) return
  msg.answered = true
  msg.answer = answer
  messages.push({ kind: 'user', text: answer, id: Date.now() })
  sendRaw(answer)
}
function onKeydown(e: KeyboardEvent) {
  if (slashOpen.value && filteredSlash.value.length) {
    if (e.key === 'ArrowDown') { e.preventDefault(); slashIdx.value = (slashIdx.value + 1) % filteredSlash.value.length; return }
    if (e.key === 'ArrowUp') { e.preventDefault(); slashIdx.value = (slashIdx.value - 1 + filteredSlash.value.length) % filteredSlash.value.length; return }
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); pickSlash(filteredSlash.value[slashIdx.value]); return }
    if (e.key === 'Escape') { e.preventDefault(); input.value = ''; return }
  }
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    if (streaming.value) {
      // Answer in progress → auto-queue, don't block user
      if (input.value.trim()) addToQueue()
    } else {
      send()
    }
  }
}

function pickSlash(cmd: string) {
  input.value = '/' + cmd + ' '
  nextTick(() => inputRef.value?.focus?.())
}
function useSlash(cmd: string) {
  panelOpen.value = false
  input.value = '/' + cmd + ' '
  nextTick(() => inputRef.value?.focus?.())
}

function abort() { abortController.value?.abort() }

// Permission approval
function parseToolDisplay(name: string): string {
  if (name.startsWith('mcp__')) {
    const rest = name.slice(4)
    const idx = rest.indexOf('__')
    if (idx > 0) return `${rest.slice(0, idx)} › ${rest.slice(idx + 2)}`
  }
  return name
}
async function allowPermission() {
  const req = permissionReq.value
  if (!req) return
  try {
    await $fetch('/api/claude/permission', {
      method: 'POST',
      body: {
        sessionId: req.sessionId,
        toolUseId: req.toolUseId,
        behavior: 'allow',
      },
    })
  } catch (e: any) {
    antMessage.error('审批发送失败: ' + (e?.message || e))
  }
  permissionReq.value = null
}
async function denyPermission() {
  const req = permissionReq.value
  if (!req) return
  try {
    await $fetch('/api/claude/permission', {
      method: 'POST',
      body: {
        sessionId: req.sessionId,
        toolUseId: req.toolUseId,
        behavior: 'deny',
        message: 'User denied via web UI',
      },
    })
  } catch {}
  permissionReq.value = null
}
function clearChat() {
  messages.length = 0
  processor.reset()
  currentSessionId.value = ''
  initInfo.tools = []
  initInfo.mcpServers = []
  initInfo.model = ''
  slashCommands.value = []
  streamingText.value = ''
  streamingThinking.value = ''
  showStreamingCursor.value = false
  unreadCount.value = 0
  isAtBottom.value = true
  kbEnhanced.value = false
  selectedKbIds.value = []
  // ⭐ Queue preserved: it's independent of chat state
  // Abort all background sessions
  for (const bg of bgSessions.value) {
    try { bg.abortController?.abort() } catch { /* already done */ }
  }
  bgSessions.value = []
}

// -- Workspace management --

/* * Load all workspaces */
async function loadWorkspaces() {
  try {
    const d: any = await $fetch('/api/claude/workspaces')
    workspaces.value = d.workspaces || []
  } catch { /* Silently ignore */ }
}

/* * Save current workspace */
async function saveWorkspace() {
  const name = wsForm.value.name.trim()
  const path = wsForm.value.path.trim()
  if (!name || !path) return
  try {
    await $fetch('/api/claude/workspaces', {
      method: 'POST',
      body: {
        name,
        path,
        description: wsForm.value.description?.trim() || undefined,
      },
    })
    antMessage.success(`工作区「${name}」已保存`)
    wsForm.value = { name: '', path: '', description: '' }
    await loadWorkspaces()
  } catch (e: any) {
    antMessage.error('保存失败: ' + (e?.message || e?.data?.statusMessage || e))
  }
}

/* * Select workspace: set cwd + close + record */
function selectWorkspace(ws: any) {
  cwd.value = ws.path
  wsManagerOpen.value = false
  // Async update usage time
  $fetch('/api/claude/workspaces', {
    method: 'POST',
    body: { name: ws.name, path: ws.path },
  }).catch(() => {})
  antMessage.success(`已切换到工作区: ${ws.name}`)
}

/* * Toggle pin */
async function togglePin(ws: any) {
  try {
    await $fetch('/api/claude/workspaces', {
      method: 'POST',
      body: {
        name: ws.name,
        path: ws.path,
        pin_order: ws.pin_order ? null : 1,
      },
    })
    await loadWorkspaces()
  } catch { /* Silently ignore */ }
}

/* * Delete workspace */
async function deleteWorkspace(id: number) {
  try {
    await $fetch(`/api/claude/workspaces/${id}`, { method: 'DELETE' })
    await loadWorkspaces()
    antMessage.success('已删除')
  } catch (e: any) {
    antMessage.error('删除失败: ' + (e?.message || e))
  }
}

/* * Quick add current cwd (if not already in workspace list) */
async function addCurrentWorkspace() {
  const path = cwd.value.trim()
  if (!path) {
    antMessage.warning('请先输入或选择一个工作目录路径')
    return
  }
  const existing = workspaces.value.find((ws: any) => ws.path === path)
  if (existing) {
    antMessage.info(`「${existing.name}」已存在`)
    return
  }
  const name = path.split(/[\\/]/).pop() || path
  wsForm.value = { name, path, description: '' }
  wsManagerOpen.value = true
}

/* * Clear session when switching workspace */
function onWorkspaceChange(path: string | undefined) {
  if (path && path !== cwd.value) {
    // Directory changed; suggest clearing session (not forced)
    if (messages.length > 0) {
      clearChat()
      antMessage.info('工作目录已切换，会话已重置')
    }
  }
}

// ⭐ 滚动监听挂在真正的滚动容器上（.messages 自己 overflow:auto 滚动）
let _boundScrollEl: HTMLElement | null = null
function bindScrollListener() {
  _boundScrollEl?.removeEventListener('scroll', onMessagesScroll)
  _boundScrollEl = getScrollEl()
  _boundScrollEl?.addEventListener('scroll', onMessagesScroll, { passive: true })
}

onMounted(() => {
  loadWorkspaces()
  loadSkillCatalog()
  loadKbCatalog()
  loadQueueFromStorage()
  nextTick(bindScrollListener)
  // If queue was restored from localStorage with pending items,
  // try consuming now (will only fire if streaming is idle)
  if (messageQueue.value.some(item => item.status === 'pending')) {
    nextTick(() => consumeQueue())
  }
})

/* * Load Skills catalog (with descriptions from SKILL.md frontmatter) */
async function loadSkillCatalog() {
  try {
    const d: any = await $fetch('/api/claude/skills', {
      params: { cwd: cwd.value.trim() || undefined },
    })
    skillCatalog.value = d.skills || []
  } catch { /* Silently ignore */ }
}

// Refresh Skills on cwd change
watch(cwd, () => loadSkillCatalog())

async function loadSessions() {
  loadingSessions.value = true
  try {
    const d = await $fetch('/api/claude/history')
    sessions.value = (d as any).sessions || []
    sessionsVisible.value = true
  } catch (e: any) {
    antMessage.error('加载历史失败: ' + (e?.message || e))
  } finally {
    loadingSessions.value = false
  }
}

async function loadHistory(sid: string) {
  sessionsVisible.value = false
  const loadingMsg = antMessage.loading('正在加载历史会话…', 0)
  try {
    const d: any = await $fetch(`/api/claude/history/${encodeURIComponent(sid)}`)
    clearChat()
    currentSessionId.value = sid
    // Sequential replay of SDK messages -> MessageProcessor paired rendering (tool_use/result, thinking, etc.)
    // Skip stream_event (incremental) and stream_event Content blocks -- full messages are in subsequent assistant/result
    const replayObjs: any[] = []
    for (const row of d.messages || []) {
      let obj: any
      try { obj = JSON.parse(row.content) } catch { continue }
      if (!obj || obj.type === 'stream_event') continue
      replayObjs.push(obj)
    }
    // Safety net: old data may have duplicate results (legacy SSE dual-emit bug), keep only the last
    let seenResult = false
    for (let i = replayObjs.length - 1; i >= 0; i--) {
      if (replayObjs[i].type === 'result') {
        if (seenResult) replayObjs.splice(i, 1)
        else seenResult = true
      }
    }
    let replayedCount = 0
    for (const obj of replayObjs) {
      try {
        handleSdkMessage(obj)
        replayedCount++
      } catch { /* Single replay failure does not affect others */ }
    }
    loadingMsg()
    antMessage.success(`已加载历史会话（${d.count} 条消息，渲染 ${replayedCount} 条），继续对话自动续接`)
  } catch (e: any) {
    loadingMsg()
    antMessage.error('加载历史失败: ' + (e?.message || e?.data?.statusMessage || e))
  }
}

async function deleteHistory(sid: string) {
  try {
    await $fetch(`/api/claude/history/${encodeURIComponent(sid)}`, { method: 'DELETE' })
    sessions.value = sessions.value.filter((s: any) => s.session_id !== sid)
    antMessage.success('已删除')
  } catch (e: any) {
    antMessage.error('删除失败: ' + (e?.message || e))
  }
}
</script>

<style scoped>
/* ═══════════════════════════════════════════════════
 * Claude Chat — ChatGPT-style layout
 * Header (fixed) → Messages (scrollable) → Footer (fixed)
 * ═══════════════════════════════════════════════════ */

.claude-chat-page {
  display: flex; flex-direction: column;
  flex: 1 1 auto;        /* 拉伸填满 .page-content（flex 方式，绕过 container-type 对百分比高度的破坏） */
  min-height: 0;         /* 允许收缩，让内部 messages 的 overflow 生效 */
  box-sizing: border-box;
  padding: var(--kb-space-lg);
  gap: 0;
  max-width: 1100px; margin: 0 auto; width: 100%;
  overflow: hidden;      /* 自身不滚，滚动交给 messages */
}

/* ── Header wrapper (own flex row — never overlaps messages) ── */
.chat-header-wrapper {
  flex-shrink: 0;
  display: flex; flex-direction: column;
  gap: var(--kb-space-sm);
  padding-bottom: var(--kb-space-sm);
  border-bottom: 1px solid var(--kb-border);
  background: var(--kb-bg);
}

/* ── Header ── */
.chat-header { display: flex; justify-content: space-between; align-items: center; gap: var(--kb-space); }
.chat-header h2 {
  margin: 0; font-size: 22px; font-weight: 600; font-style: italic;
  font-family: var(--kb-font-serif);
  letter-spacing: 0; color: var(--kb-fg);
  display: flex; align-items: center; gap: 10px;
}
.chat-header h2 :deep(.anticon) { color: var(--kb-primary); }
.chat-header .hint { margin: 3px 0 0; color: var(--kb-fg-mute); font-size: 12px; }
.chat-header .hint code {
  background: var(--kb-primary-soft); color: var(--kb-primary);
  padding: 1px 6px; border-radius: var(--kb-radius-sm);
  font-family: var(--kb-font-mono); font-size: 11px; font-weight: 600;
}
.header-actions { display: flex; gap: var(--kb-space-xs); flex-shrink: 0; }

/* ── Toolbar (轻量化：去掉框/阴影，融入 header，控件紧凑) ── */
.toolbar {
  display: flex; gap: 6px; align-items: center; flex-wrap: wrap; flex-shrink: 0;
  padding: 4px 0;
  background: transparent;
  border: none;
  box-shadow: none;
}
.toolbar :deep(.ant-select-selector),
.toolbar :deep(.ant-input) { min-height: 30px; font-size: 12.5px; }
.toolbar :deep(.ant-select) { }
.toolbar > .ant-input { flex: 1; min-width: 200px; }
.workspace-selector { display: flex; gap: 6px; align-items: center; flex: 1; min-width: 280px; }
.ws-option { padding: 4px 0; }
.ws-option-main { display: flex; align-items: center; font-size: 13px; }
.ws-option-path { font-size: 11px; color: var(--kb-fg-mute); font-family: var(--kb-font-mono); margin-top: 2px; word-break: break-all; }
.ws-option-desc { font-size: 11px; color: var(--kb-fg-mute); margin-top: 1px; }
.meta-bar {
  display: flex; gap: 6px; align-items: center; flex-wrap: wrap;
  padding: 0;
  font-size: 11px;
  opacity: 0.85;
}
.meta-bar :deep(.ant-tag) { margin-right: 0; font-size: 11px; padding: 0 7px; line-height: 18px; }

/* ── Messages container (independent scroll area between header & footer) ── */
.messages {
  flex: 1 1 auto;
  min-height: 0;           /* 关键：允许 flex item 收缩，overflow 才能生效 */
  overflow-y: auto;        /* 只有消息区滚动，header/footer 永远不会被卷走或遮挡 */
  /* 去掉外框/阴影/独立背景 —— 消息融入页面，最大化阅读空间（ChatGPT 风格） */
  background: transparent;
  border: none;
  border-radius: 0;
  box-shadow: none;
  padding: var(--kb-space-lg) var(--kb-space-lg) var(--kb-space);
  scroll-behavior: smooth;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--kb-space);
}

/* 弹性占位（保留，内容少时把 footer 顶到底） */
.chat-spacer { display: none; }

.empty { text-align: center; padding: 100px 20px; }
.empty :deep(.anticon) { font-size: 48px; color: var(--kb-gold-bright); margin-bottom: var(--kb-space); filter: drop-shadow(0 0 18px var(--kb-gold-glow)); animation: empty-glow 3s ease-in-out infinite; }
.empty :deep(.anticon) svg { display: block; }
.empty p:first-of-type {
  font-family: var(--kb-font-serif);
  font-size: 28px; font-weight: 600; font-style: italic;
  color: var(--kb-fg-2);
  margin: var(--kb-space) 0 var(--kb-space-sm);
  letter-spacing: 0.02em;
}
.empty p.muted {
  font-size: 13px; color: var(--kb-fg-mute); margin: 0;
  font-family: var(--kb-font-serif); font-style: italic;
}
/* Gold ornament between title and subtitle */
.empty p:first-of-type::after {
  content: '❦';
  display: block;
  font-style: normal;
  font-size: 18px;
  color: var(--kb-gold);
  margin-top: var(--kb-space-sm);
  opacity: 0.65;
}
.empty code {
  background: var(--kb-gold-soft); color: var(--kb-gold-deep);
  padding: 1px 7px; border-radius: 4px;
  font-family: var(--kb-font-mono); font-size: 11px; font-weight: 600;
}
@keyframes empty-glow {
  0%, 100% { filter: drop-shadow(0 0 12px var(--kb-gold-glow)); transform: translateY(0); }
  50% { filter: drop-shadow(0 0 28px var(--kb-gold-glow)); transform: translateY(-3px); }
}
.muted { color: var(--kb-fg-mute); font-size: 11px; }

/* ═══ Message rows — ChatGPT-style alignment (assistant left, user right) ═══ */
.msg {
  width: 100%;
  max-width: 768px;        /* 阅读最佳宽度，居中 */
  margin: 0 auto;          /* 居中 */
  animation: kb-fade-up 0.3s var(--kb-ease) both;
  padding: 0;              /* 默认无内边距，由子类型自定义 */
  border: none;
  background: transparent;
  box-shadow: none;
  border-radius: 0;
}

/* User — 右对齐气泡（主色），无标签头，纯气泡 */
.msg.user {
  align-self: flex-end;
  max-width: 78%;
  margin: 0;
  background: linear-gradient(160deg, var(--kb-primary) 0%, var(--kb-primary-hover) 100%);
  color: #fff;
  border-radius: 18px 18px 4px 18px;
  padding: 10px 16px;
  box-shadow:
    0 2px 8px var(--kb-primary-glow),
    inset 0 1px 0 rgba(255,255,255,0.15);
}

/* Assistant — 左对齐，无框，带头像（消息直接展示，最大可读性） */
.msg.assistant {
  align-self: flex-start;
  max-width: 768px;
  background: transparent;
  border: none;
  box-shadow: none;
  padding: 0;
}

/* Thinking — 紧凑可折叠，弱化 */
.msg.thinking {
  align-self: center;
  max-width: 768px;
  background: transparent; border: none; box-shadow: none; padding: 0;
}

/* Tool use / result — 紧凑卡片，全宽居中，弱化视觉 */
.msg.tool_use, .msg.tool_result {
  align-self: center;
  max-width: 768px;
  background: var(--kb-bg-subtle);
  border: 1px solid var(--kb-border);
  padding: 8px 12px;
  border-radius: var(--kb-radius-sm);
}
.msg.tool_result {
  border-color: var(--kb-emerald-soft);
  background: var(--kb-emerald-soft);
}
.msg.tool_result.err {
  border-color: var(--kb-rose-soft);
  background: var(--kb-rose-soft);
}

/* Plan — Purple */
.msg.plan {
  align-self: center;
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-violet);
  border-left: 4px solid var(--kb-violet);
  border-radius: var(--kb-radius);
  padding: var(--kb-space) var(--kb-space-lg);
}

/* Todo — Amber */
.msg.todo {
  align-self: center;
  background: var(--kb-amber-soft);
  border: 1px solid var(--kb-amber);
  border-radius: var(--kb-radius);
  padding: var(--kb-space) var(--kb-space-lg);
}

/* Ask user — Interactive card */
.msg.ask_user {
  align-self: center;
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-amber);
  border-left: 4px solid var(--kb-amber);
  border-radius: var(--kb-radius);
  padding: var(--kb-space) var(--kb-space-lg);
}

/* System — Info Card */
.msg.system {
  align-self: center;
  background: var(--kb-bg-subtle);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius-sm);
  font-size: 12px;
  padding: var(--kb-space-sm) var(--kb-space);
}

/* Result — Completion summary */
.msg.result {
  align-self: center;
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border-strong);
  border-top: 3px solid var(--kb-primary);
  border-radius: var(--kb-radius);
  padding: var(--kb-space) var(--kb-space-lg);
  margin-top: var(--kb-space-sm);
}
.msg.result.err { border-top-color: var(--kb-rose); }

/* Error */
.msg.error {
  align-self: center;
  background: var(--kb-rose-soft);
  border: 1px solid var(--kb-rose);
}

/* ── Message head: avatar circle + name (assistant only; user bubbles hide it) ── */
.msg-head {
  font-size: 13px; font-weight: 600;
  color: var(--kb-fg);
  margin-bottom: 6px;
  display: flex; align-items: center; gap: 8px;
}
.msg-head :deep(.anticon),
.msg-head > svg {
  display: inline-grid; place-items: center;
  width: 28px; height: 28px;
  border-radius: 50%;
  background: var(--kb-gold-soft);
  color: var(--kb-gold-deep);
  font-size: 14px;
}
.msg.assistant .msg-head :deep(.anticon) {
  background: linear-gradient(135deg, var(--kb-primary), var(--kb-gold-deep));
  color: #fff;
  box-shadow: 0 2px 8px var(--kb-primary-glow);
}
/* 用户气泡：隐藏头部标签，气泡本身即标识 */
.msg.user .msg-head { display: none; }
.msg.tool_use .msg-head { color: var(--kb-amber); }

.msg-text {
  line-height: 1.75; word-break: break-word;
  color: var(--kb-fg); font-size: 15px;
  text-wrap: pretty;
  font-feature-settings: 'kern' 1, 'liga' 1;
}
/* 用户气泡内文字为白色 */
.msg.user .msg-text { color: #fff; }
.msg.user .msg-text :deep(strong) { color: #fff; }
.msg.user .msg-text :deep(code) { background: rgba(255,255,255,0.18); color: #fff; }
.msg.user .msg-text :deep(a) { color: #fff; text-decoration: underline; }

/* ── Markdown rendering: illuminated manuscript typography ── */
.msg-text :deep(h1),
.msg-text :deep(h2),
.msg-text :deep(h3) {
  font-family: var(--kb-font-serif);
  font-weight: 600; font-style: italic;
  letter-spacing: -0.01em; line-height: 1.35;
  margin: var(--kb-space) 0 var(--kb-space-sm);
  color: var(--kb-fg);
}
.msg-text :deep(h1) { font-size: 22px; }
.msg-text :deep(h2) { font-size: 18px; }
.msg-text :deep(h3) { font-size: 16px; }
.msg-text :deep(h4) { font-size: 14px; font-weight: 700; margin: var(--kb-space-sm) 0; color: var(--kb-fg); font-family: var(--kb-font); }
.msg-text :deep(h5), .msg-text :deep(h6) { font-size: 13px; font-weight: 700; margin: var(--kb-space-sm) 0; color: var(--kb-fg-2); font-family: var(--kb-font); }
/* Assistant headings get a subtle gold left accent */
.msg.assistant .msg-text :deep(h1),
.msg.assistant .msg-text :deep(h2),
.msg.assistant .msg-text :deep(h3) {
  border-left: 3px solid var(--kb-gold);
  padding-left: 14px;
}
.msg-text :deep(p) { margin: var(--kb-space-sm) 0; }
.msg-text :deep(ul), .msg-text :deep(ol) { padding-left: 20px; margin: var(--kb-space-sm) 0; }
.msg-text :deep(li) { margin: 4px 0; }
/* GFM task lists */
.msg-text :deep(input[type="checkbox"]) { margin-right: 6px; transform: translateY(1px); }

/* Images — render inline content gracefully (responsive, rounded, captioned) */
.msg-text :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: var(--kb-radius);
  margin: var(--kb-space-sm) 0;
  box-shadow: var(--kb-shadow-sm);
  background: var(--kb-bg-subtle);
}
.msg-text :deep(em) { font-style: italic; color: var(--kb-fg-2); }
.msg-text :deep(del) { color: var(--kb-fg-mute); }
.msg-text :deep(mark) { background: var(--kb-amber-soft); color: var(--kb-fg); padding: 0 3px; border-radius: 3px; }
.msg-text :deep(kbd) {
  font-family: var(--kb-font-mono); font-size: 0.85em;
  background: var(--kb-bg-subtle); border: 1px solid var(--kb-border-strong);
  border-bottom-width: 2px; border-radius: 4px; padding: 1px 5px;
}

/* Code blocks — illuminated manuscript inset panel (gold-trimmed dark) */
.msg-text :deep(pre) {
  position: relative;
  background: linear-gradient(180deg, #1a1612 0%, #15110d 100%);
  color: #d5cfc6;
  padding: var(--kb-space) var(--kb-space-lg);
  padding-top: 30px;
  border-radius: var(--kb-radius);
  overflow-x: auto;
  font-family: var(--kb-font-mono);
  font-size: 12.5px; line-height: 1.6;
  margin: var(--kb-space) 0;
  border: 1px solid var(--kb-gold-deep);
  box-shadow:
    inset 0 1px 0 rgba(196, 154, 74, 0.12),
    0 4px 20px rgba(21, 17, 13, 0.3);
}
/* 语言标签角标 */
.msg-text :deep(pre.code-block.has-lang)::before {
  content: attr(data-lang);
  position: absolute; top: 8px; left: 14px;
  font-size: 10.5px; font-weight: 600; letter-spacing: 0.5px;
  text-transform: uppercase;
  color: rgba(200, 211, 224, 0.45);
  font-family: var(--kb-font-mono);
  pointer-events: none;
}
/* 复制按钮（hover 显示） */
.msg-text :deep(pre .code-copy-btn) {
  position: absolute; top: 6px; right: 6px;
  font-size: 11px; font-weight: 500;
  padding: 3px 9px; border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.06);
  color: rgba(220,228,238,0.85);
  cursor: pointer; opacity: 0;
  transition: all 0.18s var(--kb-ease);
}
.msg-text :deep(pre:hover .code-copy-btn),
.msg-text :deep(pre .code-copy-btn:focus) { opacity: 1; }
.msg-text :deep(pre .code-copy-btn:hover) {
  background: rgba(255,255,255,0.14);
  color: #fff;
  border-color: rgba(255,255,255,0.25);
}
.msg-text :deep(pre code) {
  background: transparent; color: inherit; padding: 0;
  font-family: inherit; font-size: inherit;
}
.msg-text :deep(code) {
  background: var(--kb-bg-subtle);
  color: var(--kb-primary);
  padding: 2px 6px; border-radius: 4px;
  font-family: var(--kb-font-mono); font-size: 0.88em;
  font-weight: 500;
}
.msg-text :deep(table) {
  border-collapse: collapse; margin: var(--kb-space-sm) 0;
  width: 100%; font-size: 13px;
}
.msg-text :deep(th) {
  background: var(--kb-bg-subtle);
  border: 1px solid var(--kb-border);
  padding: var(--kb-space-sm) var(--kb-space);
  font-weight: 600; text-align: left;
  color: var(--kb-fg-2);
}
.msg-text :deep(td) {
  border: 1px solid var(--kb-border);
  padding: var(--kb-space-sm) var(--kb-space);
  color: var(--kb-fg-2);
}
.msg-text :deep(blockquote) {
  border-left: 3px solid var(--kb-gold);
  padding-left: var(--kb-space);
  margin: var(--kb-space-sm) 0;
  color: var(--kb-fg-3);
  font-style: italic;
}
.msg-text :deep(strong) { color: var(--kb-fg); font-weight: 700; }
/* Ornamental horizontal rule — gold fleuron */
.msg-text :deep(hr) {
  border: none; text-align: center;
  margin: var(--kb-space-lg) 0 var(--kb-space);
  overflow: visible; height: 0;
}
.msg-text :deep(hr)::after {
  content: '❦';
  color: var(--kb-gold);
  font-size: 16px;
  opacity: 0.5;
}
.msg-text :deep(a) { color: var(--kb-primary); text-decoration: none; }
.msg-text :deep(a:hover) { text-decoration: underline; }

/* ── KaTeX math (server-side pre-rendered HTML) ── */
.msg-text :deep(.math-inline) { display: inline; }
.msg-text :deep(.math-inline .katex) { font-size: 1.1em; }
.msg-text :deep(.math-block) {
  display: block; overflow-x: auto; margin: 18px 0; padding: 12px 0;
  text-align: center; background: rgba(255,255,255,0.04); border-radius: 8px;
}
.msg-text :deep(.math-block .katex) { font-size: 1.2em; }
.msg-text :deep(.math-error) { background: var(--kb-rose-soft); padding: 4px 8px; border-radius: 4px; }

/* ── Mermaid diagrams ── */
.msg-text :deep(.mermaid),
.msg-text :deep(pre.mermaid),
.msg-text :deep(.mermaid-code-block),
.msg-text :deep(pre.mermaid-code-block) {
  text-align: center; margin: 18px 0; padding: 14px;
  background: var(--kb-bg); border-radius: 10px;
  border: 1px solid var(--kb-border);
  overflow-x: auto; position: relative;
}
.msg-text :deep(.mermaid-code-block code.language-mermaid) {
  background: transparent !important; border: none !important;
  color: var(--kb-fg-3); font-family: var(--kb-font-mono); font-size: 12.5px;
}
.msg-text :deep(.mermaid-rendered) {
  text-align: center; margin: 18px 0; padding: 16px;
  background: var(--kb-bg); border-radius: 10px;
  border: 1px solid var(--kb-border);
  overflow-x: auto;
  animation: kb-fade-in 0.35s var(--kb-ease-out);
}
.msg-text :deep(.mermaid-rendered svg) { max-width: 100%; height: auto; }
.msg-text :deep(.mermaid-error-badge) {
  position: absolute; top: 6px; right: 8px;
  font-size: 10.5px; color: var(--kb-rose);
  background: var(--kb-rose-soft);
  padding: 3px 9px; border-radius: 5px; z-index: 2;
  font-family: var(--kb-font); font-weight: 500;
}

/* ── Code block wrapper + language label ── */
.msg-text :deep(.code-block-wrapper) {
  position: relative; margin: 12px 0; border-radius: 10px; overflow: hidden;
  box-shadow: var(--kb-shadow-sm);
}
.msg-text :deep(.code-block-wrapper .code-lang-label) {
  position: absolute; top: 0; right: 0;
  font-family: var(--kb-font-mono); font-size: 10.5px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.08em;
  color: #c8d3e0; background: rgba(255,255,255,0.07);
  padding: 4px 12px; border-radius: 0 10px 0 7px;
  z-index: 2; user-select: none; pointer-events: none;
  backdrop-filter: blur(6px);
}
.msg-text :deep(.code-block-wrapper pre) { margin: 0; border-radius: 10px; }

/* ── Highlight.js token colors (chat dark code theme) ── */
.msg-text :deep(.hljs) { color: #e6e1dc; }
.msg-text :deep(.hljs-comment),
.msg-text :deep(.hljs-quote) { color: #7c7268; font-style: italic; }
.msg-text :deep(.hljs-keyword),
.msg-text :deep(.hljs-selector-tag),
.msg-text :deep(.hljs-type) { color: #e8907a; font-weight: 500; }
.msg-text :deep(.hljs-string),
.msg-text :deep(.hljs-addition) { color: #b5d97f; }
.msg-text :deep(.hljs-number),
.msg-text :deep(.hljs-literal) { color: #c8a3e6; }
.msg-text :deep(.hljs-title),
.msg-text :deep(.hljs-title.function_),
.msg-text :deep(.hljs-section),
.msg-text :deep(.hljs-name) { color: #8ccae8; }
.msg-text :deep(.hljs-attribute),
.msg-text :deep(.hljs-variable),
.msg-text :deep(.hljs-template-variable) { color: #e8c87a; }
.msg-text :deep(.hljs-built_in),
.msg-text :deep(.hljs-selector-class),
.msg-text :deep(.hljs-selector-id) { color: #e8c87a; }
.msg-text :deep(.hljs-regexp) { color: #f0a3a3; }
.msg-text :deep(.hljs-meta) { color: #8ccae8; font-weight: 500; }
.msg-text :deep(.hljs-tag) { color: #e8907a; }
.msg-text :deep(.hljs-doctag) { color: #e8907a; }
.msg-text :deep(.hljs-deletion) { color: #f0a3a3; }
.msg-text :deep(.hljs-emphasis) { font-style: italic; }
.msg-text :deep(.hljs-strong) { font-weight: 700; }
.msg-text :deep(.hljs-symbol),
.msg-text :deep(.hljs-bullet),
.msg-text :deep(.hljs-link) { color: #8ccae8; }
.msg-text :deep(.hljs-params) { color: #e6e1dc; }

/* ═══ Thinking ═══ */
.think-details {
  background: linear-gradient(135deg, var(--kb-gold-soft) 0%, transparent 100%);
  border: 1px solid var(--kb-gold-deep);
  border-left: 3px solid var(--kb-gold);
  border-radius: var(--kb-radius-sm);
  padding: var(--kb-space-sm) var(--kb-space);
  transition: all var(--kb-dur-fast) var(--kb-ease);
}
.think-details:hover { border-left-color: var(--kb-primary); }
.think-details summary {
  cursor: pointer; font-size: 12px; font-weight: 600;
  font-family: var(--kb-font-serif); font-style: italic;
  color: var(--kb-gold-deep);
  display: flex; align-items: center; gap: var(--kb-space-xs);
  user-select: none;
  letter-spacing: 0.02em;
}
.think-body {
  font-size: 12.5px; color: var(--kb-fg-3);
  white-space: pre-wrap;
  padding: var(--kb-space-sm) 0 0;
  border-top: 1px solid var(--kb-gold-deep);
  margin-top: var(--kb-space-sm);
  max-height: 320px; overflow-y: auto;
  line-height: 1.65;
  font-style: italic;
}

/* ═══ Tool cards — marginalia annotation style ═══ */
.tool-card { border-radius: var(--kb-radius-sm); }
.tool-head {
  display: flex; align-items: center; gap: var(--kb-space-sm);
  margin-bottom: 2px; flex-wrap: wrap;
}
.tool-badge {
  font-size: 11px; font-weight: 700; letter-spacing: 0.3px;
  padding: 3px 10px; border-radius: 4px;
  background: var(--kb-amber-soft); color: var(--kb-gold-deep);
  font-family: var(--kb-font-mono);
  border: 1px solid rgba(212, 175, 106, 0.3);
}
.tool-badge.mcp {
  background: rgba(124, 92, 255, 0.1); color: var(--kb-violet);
  border-color: rgba(124, 92, 255, 0.25);
}
.tool-preview {
  font-size: 11.5px; color: var(--kb-fg-3);
  font-family: var(--kb-font-mono);
  word-break: break-all; flex: 1; min-width: 0;
}
.tool-input, .tool-result-pre {
  background: var(--kb-bg-dark); color: #c8d3e0;
  padding: var(--kb-space-sm) var(--kb-space);
  border-radius: var(--kb-radius-sm);
  font-family: var(--kb-font-mono);
  font-size: 11.5px; line-height: 1.55;
  max-height: 240px; overflow: auto;
  margin: var(--kb-space-sm) 0 0;
  white-space: pre-wrap; word-break: break-word;
  border: 1px solid rgba(255,255,255,0.06);
}

/* ═══ Plan ═══ */
.plan-head {
  font-weight: 700; margin-bottom: var(--kb-space-sm);
  color: var(--kb-violet); font-size: 14px;
}
.plan-body { font-size: 13.5px; line-height: 1.65; color: var(--kb-fg-2); }

/* ═══ Todo ═══ */
.todo-head {
  font-weight: 700; margin-bottom: var(--kb-space-sm);
  font-size: 13px; color: var(--kb-amber);
}
.todo-item {
  display: flex; gap: var(--kb-space-sm);
  padding: 4px 0; font-size: 13.5px;
  align-items: center; color: var(--kb-fg-2);
}
.todo-item.completed { color: var(--kb-emerald); text-decoration: line-through; text-decoration-color: var(--kb-emerald); }
.todo-item.in_progress { color: var(--kb-primary); font-weight: 600; }
.todo-check { width: 18px; text-align: center; font-weight: 700; }

/* ═══ Ask user ═══ */
.ask-head {
  font-weight: 700; margin-bottom: var(--kb-space-xs);
  color: var(--kb-amber); font-size: 14px;
}
.ask-question { margin-bottom: var(--kb-space); font-size: 13.5px; color: var(--kb-fg-2); line-height: 1.6; }
.ask-options { display: flex; flex-direction: column; gap: var(--kb-space-sm); }
.ask-opt {
  text-align: left;
  padding: var(--kb-space-sm) var(--kb-space);
  border: 1px solid var(--kb-border-strong);
  border-radius: var(--kb-radius);
  background: var(--kb-bg-elevated);
  cursor: pointer;
  transition: all var(--kb-dur-fast) var(--kb-ease);
  display: flex; flex-direction: column; gap: 3px;
  color: var(--kb-fg-2);
}
.ask-opt:hover:not(:disabled) {
  border-color: var(--kb-amber);
  background: var(--kb-amber-soft);
  transform: translateY(-1px);
  box-shadow: var(--kb-shadow-sm);
}
.ask-opt:disabled { opacity: 0.5; cursor: default; }
.ask-answered { margin-top: var(--kb-space-sm); }

/* ═══ System details ═══ */
.sys-details {
  background: var(--kb-bg-subtle);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius-sm);
  padding: var(--kb-space-sm) var(--kb-space);
}
.sys-details summary {
  cursor: pointer; font-size: 12px; font-weight: 600;
  color: var(--kb-primary); user-select: none;
  display: flex; align-items: center; gap: var(--kb-space-xs);
}
.sys-body {
  font-size: 12px; padding: var(--kb-space-sm) 0 0;
  border-top: 1px solid var(--kb-border);
  margin-top: var(--kb-space-sm);
  color: var(--kb-fg-3); line-height: 1.6;
}

/* ═══ Result ═══ */
.result-card.err { border-top-color: var(--kb-rose); }
.result-card .msg-text :deep(table) { margin: 0; }
.result-card .msg-text :deep(th),
.result-card .msg-text :deep(td) { padding: 6px 12px; font-size: 12.5px; }

/* ═══ Error ═══ */
.err-card {
  color: var(--kb-rose);
  font-size: 13px;
  font-weight: 500;
}

/* ═══ Loading indicator ═══ */
.thinking-msg {
  color: var(--kb-fg-3); font-style: italic;
  display: flex; align-items: center; gap: var(--kb-space-sm);
  padding: var(--kb-space) var(--kb-space-lg);
  font-size: 13px;
}

/* ═══ Input area ═══ */
.input-area { position: relative; }
.slash-menu {
  position: absolute; bottom: 100%; left: 0; right: 0;
  max-height: 260px; overflow-y: auto;
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius);
  box-shadow: var(--kb-shadow-lg);
  margin-bottom: var(--kb-space-xs);
  z-index: 10;
}
.slash-menu-head {
  padding: var(--kb-space-sm) var(--kb-space);
  font-size: 11px; font-weight: 600;
  color: var(--kb-fg-mute);
  border-bottom: 1px solid var(--kb-border);
  display: flex; justify-content: space-between;
  position: sticky; top: 0;
  background: var(--kb-bg-elevated);
}
.slash-item {
  padding: 8px var(--kb-space); cursor: pointer;
  font-size: 13px;
  transition: background var(--kb-dur-fast) var(--kb-ease);
}
.slash-item:hover, .slash-item.active {
  background: var(--kb-primary-tint);
}
.slash-cmd {
  font-family: var(--kb-font-mono);
  color: var(--kb-primary); font-weight: 600;
}
.slash-desc {
  font-size: 11px; color: var(--kb-fg-mute);
  margin-left: auto;
  max-width: 50%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.input-bar {
  display: flex; gap: var(--kb-space-sm); align-items: flex-end;
  background: var(--kb-bg-elevated);
  border: 1.5px solid var(--kb-border);
  border-radius: 26px;                 /* ChatGPT 风格大圆角胶囊 */
  padding: 8px 8px 8px 14px;
  box-shadow: var(--kb-shadow-sm);
  transition: border-color var(--kb-dur-fast) var(--kb-ease), box-shadow var(--kb-dur-fast) var(--kb-ease);
}
.input-bar:focus-within {
  border-color: var(--kb-gold);
  box-shadow: var(--kb-shadow-sm), 0 0 0 4px var(--kb-gold-glow);
}
.input-bar :deep(.ant-input) {
  flex: 1; border: none; box-shadow: none; background: transparent;
  font-size: 15px; line-height: 1.5; resize: none; padding: 6px 4px;
}
.input-bar :deep(.ant-input:focus) { box-shadow: none; }
/* 输入栏内的图标按钮统一为圆形（仅附件/KB 这类纯图标按钮） */
.input-bar :deep(.ant-btn.att-btn),
.input-bar :deep(.ant-btn.kb-btn) {
  border-radius: 50%; width: 38px; height: 38px;
  min-width: 38px; padding: 0;
  display: inline-grid; place-items: center;
  flex-shrink: 0;
}
/* 主操作按钮（发送）做成突出的主色圆形 */
.input-bar :deep(.ant-btn-primary) {
  border-radius: 50%; width: 40px; height: 40px; min-width: 40px; padding: 0;
  display: inline-grid; place-items: center;
  box-shadow: 0 2px 12px var(--kb-gold-glow), 0 2px 6px var(--kb-primary-glow);
}
.input-bar :deep(.ant-btn-primary[disabled]) {
  box-shadow: none; opacity: 0.5;
}

/* ═══ Environment panel ═══ */
.env-item {
  padding: var(--kb-space-sm) var(--kb-space);
  border-bottom: 1px solid var(--kb-border);
  font-size: 13px;
  display: flex; align-items: center; gap: var(--kb-space-sm);
  transition: background var(--kb-dur-fast) var(--kb-ease);
}
.env-item.slash-env { cursor: pointer; }
.env-item.slash-env:hover { background: var(--kb-primary-tint); }

/* ═══ Permission dialog ═══ */
.perm-body { padding: 0 var(--kb-space-xs); }
.perm-hint { margin-bottom: var(--kb-space); font-size: 14px; color: var(--kb-fg); line-height: 1.6; }
.perm-input-block { margin: var(--kb-space-sm) 0; }
.perm-input {
  background: var(--kb-bg-dark); color: #c8d3e0;
  padding: var(--kb-space) var(--kb-space-lg);
  border-radius: var(--kb-radius-sm);
  font-family: var(--kb-font-mono);
  font-size: 12px; line-height: 1.55;
  max-height: 260px; overflow: auto;
  white-space: pre-wrap; word-break: break-word;
  margin: var(--kb-space-sm) 0 0;
  border: 1px solid rgba(255,255,255,0.06);
}

/* ═══ Scrollbar (gold-themed, illuminated manuscript) ═══ */
.messages::-webkit-scrollbar { width: 9px; }
.messages::-webkit-scrollbar-track {
  background: rgba(212, 175, 106, 0.06);
  border-radius: var(--kb-radius-pill);
}
.messages::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, var(--kb-gold-deep), var(--kb-gold));
  border-radius: var(--kb-radius-pill);
  border: 2px solid transparent; background-clip: content-box;
  box-shadow: 0 0 6px rgba(212, 175, 106, 0.2);
}
.messages::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, var(--kb-gold), var(--kb-gold-bright));
  background-clip: content-box;
}
.messages {
  scrollbar-width: thin;
  scrollbar-color: var(--kb-gold-deep) rgba(212, 175, 106, 0.08);
}

/* ═══ Workspace Manager ═══ */
.ws-manager-body { display: flex; flex-direction: column; gap: var(--kb-space-lg); }
.ws-manager-header { color: var(--kb-fg-2); font-size: 13px; line-height: 1.6; }
.ws-form { display: flex; gap: var(--kb-space-sm); align-items: center; flex-wrap: wrap; }
.ws-list { display: flex; flex-direction: column; gap: var(--kb-space-sm); max-height: 360px; overflow-y: auto; }
.ws-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: var(--kb-space) var(--kb-space-lg);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius);
  transition: all var(--kb-dur-fast) var(--kb-ease);
}
.ws-item:hover { border-color: var(--kb-primary-soft); background: var(--kb-primary-tint); }
.ws-item-info { flex: 1; cursor: pointer; min-width: 0; }
.ws-item-name { display: flex; align-items: center; gap: 6px; font-size: 14px; margin-bottom: 4px; }
.ws-item-path { font-size: 11.5px; color: var(--kb-fg-mute); font-family: var(--kb-font-mono); word-break: break-all; }
.ws-item-desc { font-size: 12px; color: var(--kb-fg-3); margin-top: 3px; }
.ws-item-meta { font-size: 11px; color: var(--kb-fg-mute); margin-top: 4px; }
.ws-item-actions { display: flex; gap: 6px; align-items: center; flex-shrink: 0; margin-left: var(--kb-space); }
.ws-empty { text-align: center; padding: 40px 20px; color: var(--kb-fg-3); }
.ws-empty p { margin: 6px 0; font-size: 14px; }

/* ═══ Attachment bar ═══ */
.att-bar {
  display: flex; flex-wrap: wrap; gap: var(--kb-space-sm);
  padding: var(--kb-space-sm) var(--kb-space);
  background: var(--kb-bg-subtle);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius);
  margin-bottom: var(--kb-space-sm);
}
.att-chip {
  display: flex; align-items: center; gap: var(--kb-space-sm);
  padding: 5px 10px;
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border-strong);
  border-radius: var(--kb-radius-sm);
  box-shadow: var(--kb-shadow-xs);
  transition: all var(--kb-dur-fast) var(--kb-ease);
  max-width: 280px;
}
.att-chip:hover { border-color: var(--kb-primary); }
.att-icon { font-size: 18px; flex-shrink: 0; }
.att-meta { display: flex; flex-direction: column; min-width: 0; flex: 1; }
.att-name {
  font-size: 12.5px; font-weight: 600; color: var(--kb-fg);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.att-type { font-size: 10.5px; color: var(--kb-fg-mute); }
.att-btn { flex-shrink: 0; }

/* ═══ KB-enhanced toggle & selector ═══ */
.kb-btn {
  flex-shrink: 0;
  position: relative;
  transition: all 0.2s ease;
  border-color: var(--kb-border);
  color: var(--kb-fg-3);
}
.kb-btn:hover {
  border-color: var(--kb-primary);
  color: var(--kb-primary);
}
.kb-btn.active {
  background: var(--kb-primary-tint);
  border-color: var(--kb-primary);
  color: var(--kb-primary);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
}
.kb-btn-dot {
  position: absolute;
  top: 3px;
  right: 3px;
  width: 6px;
  height: 6px;
  background: var(--kb-emerald);
  border-radius: 50%;
  animation: kb-pulse 1.8s ease-in-out infinite;
}
@keyframes kb-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.3); }
}

.kb-selector-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: var(--kb-primary-tint);
  border: 1px solid var(--kb-primary-soft);
  border-radius: var(--kb-radius);
  margin-bottom: 4px;
  animation: kb-fade-up 0.25s ease both;
}
.kb-selector-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--kb-primary);
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 4px;
}
.kb-hint {
  font-size: 11px;
  color: var(--kb-fg-mute);
  white-space: nowrap;
}
.kb-hint.selected {
  color: var(--kb-primary);
  font-weight: 500;
}

/* ═══ Tool catalog ═══ */
.cat-header {
  font-size: 11px; font-weight: 700; letter-spacing: 0.5px;
  text-transform: uppercase; color: var(--kb-fg-mute);
  margin: 12px 0 6px; padding-bottom: 4px;
  border-bottom: 1px solid var(--kb-border);
}
.tool-env { align-items: flex-start; }
.tool-icon { font-size: 16px; flex-shrink: 0; margin-top: 1px; }
.tool-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.tool-name {
  font-family: var(--kb-font-mono); font-size: 12.5px; font-weight: 600;
  color: var(--kb-primary);
}
.tool-desc { font-size: 11.5px; color: var(--kb-fg-3); line-height: 1.45; }

/* ═══ Skill catalog ═══ */
.skill-env { align-items: flex-start; cursor: pointer; }
.skill-env:hover { background: var(--kb-primary-tint); }
.skill-info { display: flex; flex-direction: column; gap: 4px; min-width: 0; flex: 1; }
.skill-desc { font-size: 11.5px; color: var(--kb-fg-3); line-height: 1.5; margin-top: 2px; }

/* ═══ Streaming typewriter rendering ═══ */
.streaming-msg {
  border-left: 3px solid var(--kb-gold) !important;
  position: relative;
}
.streaming-msg .msg-text::after {
  /* Make Markdown-rendered streaming text feel coherent */
  display: inline;
}
.stream-cursor {
  display: inline-block;
  width: 7px; height: 17px;
  background: linear-gradient(180deg, var(--kb-gold-bright), var(--kb-primary));
  margin-left: 2px;
  vertical-align: text-bottom;
  border-radius: 2px;
  animation: blink-cursor 0.9s steps(2) infinite;
  box-shadow: 0 0 8px var(--kb-gold-glow);
}
@keyframes blink-cursor {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0.3; }
}

/* ═══ Typing dot animation — gold ink drops ═══ */
.typing-msg {
  background: transparent;
}
.typing-dots {
  display: flex; gap: 6px; padding: 8px 0;
}
.typing-dots span {
  width: 7px; height: 7px; border-radius: 50%;
  background: linear-gradient(135deg, var(--kb-gold-bright), var(--kb-gold));
  animation: typing-bounce 1.3s ease-in-out infinite;
  box-shadow: 0 0 6px var(--kb-gold-glow);
}
.typing-dots span:nth-child(2) { animation-delay: 0.18s; }
.typing-dots span:nth-child(3) { animation-delay: 0.36s; }
@keyframes typing-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.45; }
  30% { transform: translateY(-7px); opacity: 1; }
}

/* ═══ Jump to latest button ═══ */
.jump-latest {
  position: sticky; bottom: 12px;
  margin: 0 auto;
  width: fit-content;
  display: flex; align-items: center; gap: 4px;
  padding: 8px 16px;
  background: var(--kb-primary);
  color: #fff;
  border-radius: var(--kb-radius-pill);
  box-shadow: var(--kb-shadow-lg);
  cursor: pointer;
  font-size: 13px; font-weight: 600;
  z-index: 20;
  transition: all var(--kb-dur-fast) var(--kb-ease);
  animation: kb-fade-up 0.25s var(--kb-ease) both;
}
.jump-latest:hover {
  transform: translateY(-2px);
  background: var(--kb-primary-hover);
  box-shadow: var(--kb-shadow-primary);
}
.jump-latest :deep(.anticon) { font-size: 14px; }
.jump-badge {
  background: var(--kb-rose);
  color: #fff;
  font-size: 10.5px; font-weight: 700;
  padding: 1px 7px;
  border-radius: var(--kb-radius-pill);
  min-width: 18px; text-align: center;
}
.jump-fade-enter-active, .jump-fade-leave-active {
  transition: all 0.25s var(--kb-ease);
}
.jump-fade-enter-from, .jump-fade-leave-to {
  opacity: 0; transform: translateY(10px);
}

/* Message cards entrance — gentle illuminated reveal */
.msg {
  animation: msg-in 0.45s var(--kb-ease-out) both;
}
@keyframes msg-in {
  from { opacity: 0; transform: translateY(12px); filter: blur(2px); }
  to { opacity: 1; transform: translateY(0); filter: blur(0); }
}
.streaming-msg { animation: none; } /* Streaming bubble should not re-enter */

/* ═══ History session entries (clickable whole row) ═══ */
.history-item { cursor: pointer; transition: background var(--kb-dur-fast) var(--kb-ease); }
.history-item:hover { background: var(--kb-primary-tint) !important; }
.history-item :deep(.ant-list-item-meta-title) { margin: 0 !important; }
.history-title { font-weight: 600; color: var(--kb-primary); }
.history-item :deep(.ant-list-item-extra) { margin-inline-start: 8px; }
.history-item :deep(.ant-list-item-action) { margin-inline-start: 8px; }
.history-item :deep(.ant-popconfirm) { /* Ensure delete button click bubble prevention */ }

/* ═══ Footer wrapper (fixed at bottom) ═══ */
/* ═══ Footer wrapper (own flex row — never overlaps messages) ═══ */
.chat-footer-wrapper {
  flex-shrink: 0;
  display: flex; flex-direction: column;
  gap: var(--kb-space-xs);
  padding-top: var(--kb-space-xs);
  border-top: 1px solid var(--kb-border);
  background: var(--kb-bg);
}

/* ═══ Quick Actions ═══ */
.quick-actions {
  display: flex; align-items: center; gap: 6px; flex-shrink: 0;
  padding: 4px 0;
}
.qa-label { font-size: 13px; flex-shrink: 0; margin-right: 2px; }
.qa-scroll { display: flex; gap: 5px; overflow-x: auto; flex: 1; }
.qa-pill {
  white-space: nowrap; cursor: pointer; font-size: 11.5px; font-weight: 500;
  padding: 3px 10px; border-radius: var(--kb-radius-pill);
  background: var(--kb-bg-subtle); border: 1px solid var(--kb-border);
  color: var(--kb-fg-2);
  transition: all var(--kb-dur-fast) var(--kb-ease);
  flex-shrink: 0; user-select: none;
}
.qa-pill:hover { border-color: var(--kb-gold); color: var(--kb-gold-deep); background: var(--kb-gold-soft); }

/* ═══ Message Queue Panel (production-grade) ═══ */
.queue-panel {
  flex-shrink: 0;
  background: var(--kb-amber-soft); border: 1px solid var(--kb-amber);
  border-radius: var(--kb-radius); padding: var(--kb-space-sm) var(--kb-space);
}
.queue-head {
  display: flex; align-items: center; gap: var(--kb-space-sm);
  font-size: 12px; font-weight: 700; color: var(--kb-amber);
  margin-bottom: var(--kb-space-sm);
}
.queue-head-actions {
  margin-left: auto;
  display: flex; align-items: center; gap: 2px;
}
.queue-item {
  display: flex; align-items: center; gap: var(--kb-space-sm);
  padding: 4px 0; font-size: 13px;
  border-bottom: 1px solid rgba(245,158,11,0.15);
}
.queue-item:last-child { border-bottom: none; }
.queue-item.sending {
  opacity: 0.7;
}
.queue-item.failed {
  border-left: 3px solid var(--kb-rose);
  padding-left: 8px;
  background: rgba(244, 63, 94, 0.05);
  border-radius: 0 var(--kb-radius-sm) var(--kb-radius-sm) 0;
}

/* Status dot */
.queue-status-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
  display: inline-block;
}
.queue-status-dot.pending { background: var(--kb-fg-mute); }
.queue-status-dot.sending {
  background: var(--kb-primary);
  animation: queue-pulse 1s ease-in-out infinite;
}
.queue-status-dot.sent { background: var(--kb-emerald); }
.queue-status-dot.failed { background: var(--kb-rose); }
@keyframes queue-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.7); }
}

.queue-idx { font-weight: 600; color: var(--kb-fg-mute); min-width: 20px; font-size: 11px; }
.queue-text { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--kb-fg-2); }
.queue-context {
  display: flex; gap: 3px; flex-shrink: 0;
}
.queue-tag { font-size: 10px !important; line-height: 16px !important; padding: 0 4px !important; }
.queue-error-icon { color: var(--kb-rose); font-size: 13px; flex-shrink: 0; cursor: help; }
.queue-actions { display: flex; gap: 2px; flex-shrink: 0; }

/* Paused banner */
.queue-paused-banner {
  margin-top: var(--kb-space-sm);
  padding: var(--kb-space-sm) var(--kb-space);
  background: var(--kb-bg-subtle);
  border: 1px dashed var(--kb-border);
  border-radius: var(--kb-radius-sm);
  font-size: 12px; color: var(--kb-fg-mute);
  text-align: center;
  display: flex; align-items: center; justify-content: center; gap: 6px;
}

/* ═══ Mobile responsive ═══ */
@media (max-width: 768px) {
  .claude-chat-page {
    padding: var(--kb-space-sm);
  }
  .chat-header { flex-direction: column; gap: var(--kb-space-sm); }
  .chat-header h2 { font-size: 17px; }
  .header-actions { width: 100%; justify-content: flex-end; }
  .toolbar { flex-direction: column; align-items: stretch; gap: var(--kb-space-xs); }
  .toolbar .workspace-selector { min-width: 0; flex-direction: column; }
  .toolbar :deep(.ant-select) { width: 100% !important; }
  .toolbar > .ant-input,
  .toolbar :deep(.ant-select) { max-width: 100%; }
  .messages { padding: var(--kb-space-sm); border-radius: var(--kb-radius); margin: var(--kb-space-sm) 0; }
  .msg { padding: var(--kb-space-sm); }

  /* Mobile input area adaptation */
  .input-bar { flex-wrap: wrap; }
  .input-bar .ant-btn.att-btn { order: -1; }
  .input-bar :deep(.ant-input),
  .input-bar :deep(textarea) { font-size: 16px; } /* Prevent iOS zoom */

  /* Attachment chip responsive */
  .att-chip { max-width: 100%; flex: 0 0 auto; }

  /* Smaller message text */
  .msg-text { font-size: 13.5px; }
  .msg-text :deep(pre) { font-size: 11px; max-height: 200px; }

  /* Full-screen tool panel on mobile */
  :deep(.ant-drawer-content-wrapper) { width: 100% !important; }
}

/* Tablet adaptation */
@media (min-width: 769px) and (max-width: 1024px) {
  .claude-chat-page { max-width: 100%; padding: var(--kb-space); }
  .toolbar .workspace-selector { min-width: 200px; }
}
</style>

<!-- ═══ 全局样式（非 scoped）：让书本 layout 的 .page-content 在渲染 claude-chat 时
     变成 flex 列容器并禁止自身滚动。这样 .claude-chat-page 用 flex:1 拉伸填满，
     绕过 .page-content 的 container-type 对子元素百分比高度的破坏。
     :has() 限定只在包含 claude-chat 时生效，不影响其他页面。 ═══ -->
<style>
.page-content:has(.claude-chat-page) {
  display: flex;
  flex-direction: column;
  overflow: hidden;   /* 外层不滚，滚动交给 .messages */
}
</style>

