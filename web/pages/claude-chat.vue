<template>
  <div class="claude-chat-page">
    <!-- header -->
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
      <!-- Workspace selector (replaces raw cwd text input) -->
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
        <a-select-option v-for="m in PERMISSION_MODES" :key="m" :value="m">{{ PERMISSION_MODE_INFO[m].label }}</a-select-option>
      </a-select>
      <a-tooltip :title="PERMISSION_MODE_INFO[permissionMode].desc"><InfoCircleOutlined style="cursor:help" /></a-tooltip>
      <a-input v-model:value="model" placeholder="Model (leave empty for default)" style="width:160px" allow-clear />
      <!-- ⭐ Thinking depth control — full Claude Code modes -->
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

    <!-- meta -->
    <div v-if="(currentSessionId || initInfo.model) || bgSessions.length" class="meta-bar">
      <a-tag v-if="currentSessionId" color="green">active session {{ currentSessionId.slice(0, 12) }}…</a-tag>
      <a-tag v-if="initInfo.model" color="blue">{{ initInfo.model }}</a-tag>
      <a-tag v-for="m in initInfo.mcpServers" :key="m.name" :color="m.status === 'ready' ? 'green' : 'orange'">🔌 {{ m.name }} · {{ m.status }}</a-tag>
      <!-- Background sessions -->
      <template v-for="bg in bgSessions" :key="bg.id">
        <a-tooltip :title="'后台运行中: ' + bg.prompt.slice(0, 60) + '… — 点击切换回来'">
          <a-tag color="processing" style="cursor:pointer" @click="switchToBg(bg)">
            <SyncOutlined spin /> {{ bg.id.slice(0, 8) }}…
          </a-tag>
        </a-tooltip>
      </template>
    </div>

    <!-- Message list -->
    <div class="messages" ref="msgRef" @scroll="onMessagesScroll">
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

    <!-- ⭐ Quick Action Pills -->
    <div class="quick-actions" v-if="!streaming">
      <span class="qa-label">⚡</span>
      <div class="qa-scroll">
        <span v-for="act in QUICK_ACTIONS" :key="act.label" class="qa-pill" @click="queueAction(act)">
          {{ act.icon }} {{ act.label }}
        </span>
      </div>
    </div>

    <!-- ⭐ Message Queue Panel -->
    <div v-if="messageQueue.length" class="queue-panel">
      <div class="queue-head">
        <OrderedListOutlined /> 消息队列 ({{ messageQueue.length }})
        <a-button size="small" type="link" @click="clearQueue"><DeleteOutlined /> 清空</a-button>
      </div>
      <div v-for="(item, i) in messageQueue" :key="item.id" class="queue-item">
        <template v-if="item.status === 'editing'">
          <a-input v-model:value="queueEditText" size="small" style="flex:1" @keyup.enter="confirmEdit(item)" />
          <a-button size="small" type="primary" @click="confirmEdit(item)">✓</a-button>
          <a-button size="small" @click="cancelEdit(item)">✗</a-button>
        </template>
        <template v-else>
          <span class="queue-idx">{{ i + 1 }}.</span>
          <span class="queue-text">{{ item.text.slice(0, 60) }}{{ item.text.length > 60 ? '…' : '' }}</span>
          <span class="queue-actions">
            <a-tooltip title="编辑"><a-button size="small" type="text" @click="startEdit(item)"><EditOutlined /></a-button></a-tooltip>
            <a-tooltip title="删除"><a-button size="small" type="text" danger @click="removeFromQueue(item.id)"><DeleteOutlined /></a-button></a-tooltip>
            <a-tooltip title="立即发送"><a-button size="small" type="primary" ghost :disabled="streaming" @click="sendQueueItem(item)"><SendOutlined /></a-button></a-tooltip>
          </span>
        </template>
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
          <a-button class="att-btn" @click="triggerFilePicker" :disabled="streaming">
            <PaperClipOutlined />
          </a-button>
        </a-tooltip>

        <!-- KB-enhanced toggle -->
        <a-tooltip :title="kbEnhanced ? 'KB-enhanced ON (click to disable)' : 'KB-enhanced: answer from knowledge base'">
          <a-button
            class="kb-btn"
            :class="{ active: kbEnhanced }"
            @click="toggleKbEnhanced"
            :disabled="streaming"
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
          :placeholder="inputPlaceholder"
          :auto-size="{ minRows: 1, maxRows: 6 }"
          @keydown="onKeydown" :disabled="streaming"
        />
        <a-button type="primary" :loading="streaming" :disabled="!input.trim() && !attachments.length" @click="send">发送</a-button>
        <a-tooltip title="排队发送消息（当前对话结束后自动发出）">
          <a-button :disabled="!input.trim()" @click="addToQueue">➕ 队列</a-button>
        </a-tooltip>
        <a-button v-if="streaming" danger @click="abort">中断</a-button>
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
const msgRef = ref<HTMLElement | null>(null)
const inputRef = ref<any>(null)
const abortController = ref<AbortController | null>(null)
const processor = new MessageProcessor()

// ⭐ Reasoning effort control
const reasoningEffort = ref<'auto' | 'low' | 'medium' | 'high' | 'xhigh' | 'max'>('auto')

// ⭐ Message queue
interface QueueItem { id: string; text: string; status: 'pending' | 'editing' | 'sent'; created_at: number }
const messageQueue = ref<QueueItem[]>([])
const queueEditText = ref('')
let queueIdCounter = 0

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
  messageQueue.value = []

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

// Auto-consumption: when streaming ends, pop queue
watch(streaming, (val) => {
  if (!val && messageQueue.value.length > 0) {
    const item = messageQueue.value.shift()!
    item.status = 'sent'
    messages.push({ kind: 'user', text: item.text, id: Date.now() })
    nextTick(() => sendRaw(item.text))
  }
})

function addToQueue() {
  const text = input.value.trim()
  if (!text) return
  messageQueue.value.push({ id: `q_${++queueIdCounter}`, text, status: 'pending', created_at: Date.now() })
  input.value = ''
  antMessage.success(`已加入队列 (${messageQueue.value.length})`)
}

function removeFromQueue(id: string) {
  messageQueue.value = messageQueue.value.filter(item => item.id !== id)
}

function clearQueue() {
  messageQueue.value = []
}

function startEdit(item: QueueItem) {
  item.status = 'editing'
  queueEditText.value = item.text
}

function confirmEdit(item: QueueItem) {
  if (queueEditText.value.trim()) {
    item.text = queueEditText.value.trim()
  }
  item.status = 'pending'
}

function cancelEdit(item: QueueItem) {
  item.status = 'pending'
  queueEditText.value = ''
}

function sendQueueItem(item: QueueItem) {
  messageQueue.value = messageQueue.value.filter(q => q.id !== item.id)
  messages.push({ kind: 'user', text: item.text, id: Date.now() })
  nextTick(() => sendRaw(item.text))
}

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

function onMessagesScroll() {
  const el = msgRef.value
  if (!el) return
  const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
  isAtBottom.value = distFromBottom < SCROLL_THRESHOLD
  // Reset unread count when back at bottom
  if (isAtBottom.value) unreadCount.value = 0
}

function scrollToBottom(behavior: ScrollBehavior = 'smooth') {
  nextTick(() => {
    const el = msgRef.value
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
    const el = msgRef.value
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

async function sendRaw(prompt: string, atts?: Attachment[]) {
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
      antMessage.error(e?.message || String(e))
      messages.push({ kind: 'error', text: e?.message || String(e), id: Date.now() })
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
  if ((!prompt && !atts.length) || streaming.value) return

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
      // Streaming → queue
      addToQueue()
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
  messageQueue.value = []
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

onMounted(() => {
  loadWorkspaces()
  loadSkillCatalog()
  loadKbCatalog()
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
 * Claude Chat — Using kb- design tokens (theme.css)
 * Message cards: semantic color background + subtle shadow instead of left-border cliche
 * ═══════════════════════════════════════════════════ */

.claude-chat-page {
  display: flex; flex-direction: column;
  height: calc(100vh - 80px);
  padding: var(--kb-space-lg);
  gap: var(--kb-space);
  max-width: 1100px; margin: 0 auto; width: 100%;
}

/* ── Header ── */
.chat-header { display: flex; justify-content: space-between; align-items: flex-start; flex-shrink: 0; }
.chat-header h2 { margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -0.3px; color: var(--kb-fg); }
.chat-header .hint { margin: 5px 0 0; color: var(--kb-fg-3); font-size: 12.5px; }
.chat-header .hint code {
  background: var(--kb-primary-soft); color: var(--kb-primary);
  padding: 1px 6px; border-radius: var(--kb-radius-sm);
  font-family: var(--kb-font-mono); font-size: 11px; font-weight: 600;
}
.header-actions { display: flex; gap: var(--kb-space-xs); flex-shrink: 0; }

/* ── Toolbar ── */
.toolbar {
  display: flex; gap: var(--kb-space-sm); align-items: center; flex-wrap: wrap; flex-shrink: 0;
  padding: var(--kb-space-sm) var(--kb-space);
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius);
  box-shadow: var(--kb-shadow-xs);
}
.toolbar > .ant-input { flex: 1; min-width: 260px; }
.workspace-selector { display: flex; gap: 6px; align-items: center; flex: 1; min-width: 320px; }
.ws-option { padding: 4px 0; }
.ws-option-main { display: flex; align-items: center; font-size: 13px; }
.ws-option-path { font-size: 11px; color: var(--kb-fg-mute); font-family: var(--kb-font-mono); margin-top: 2px; word-break: break-all; }
.ws-option-desc { font-size: 11px; color: var(--kb-fg-mute); margin-top: 1px; }
.meta-bar {
  display: flex; gap: var(--kb-space-xs); align-items: center; flex-wrap: wrap;
  padding: 2px 0; flex-shrink: 0;
}

/* ── Messages container ── */
.messages {
  flex: 1; overflow-y: auto;
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius-lg);
  padding: var(--kb-space-lg);
  box-shadow: var(--kb-shadow-sm);
  scroll-behavior: smooth;
}
.empty { text-align: center; padding: 80px 20px; }
.empty > p:first-child { font-size: 40px; margin-bottom: var(--kb-space); }
.empty p:nth-child(2) { color: var(--kb-fg-2); font-size: 16px; font-weight: 500; margin: 0 0 6px; }
.empty .muted { font-size: 12.5px; color: var(--kb-fg-mute); margin: 0; }
.empty code {
  background: var(--kb-primary-soft); color: var(--kb-primary);
  padding: 1px 6px; border-radius: var(--kb-radius-sm);
  font-family: var(--kb-font-mono); font-size: 11px; font-weight: 600;
}
.muted { color: var(--kb-fg-mute); font-size: 11px; }

/* ═══ Message cards ═══ */
.msg {
  margin-bottom: var(--kb-space);
  padding: var(--kb-space) var(--kb-space-lg);
  border-radius: var(--kb-radius);
  border: 1px solid var(--kb-border);
  box-shadow: var(--kb-shadow-xs);
  animation: kb-fade-up 0.3s var(--kb-ease) both;
}

/* User — Cobalt blue */
.msg.user {
  background: var(--kb-primary-tint);
  border-color: var(--kb-primary-soft);
}

/* Assistant — Emerald green */
.msg.assistant {
  background: var(--kb-bg-elevated);
  border-color: var(--kb-emerald-soft);
}

/* Thinking — No card, blended into background */
.msg.thinking {
  background: transparent; border: none; box-shadow: none; padding: 0;
  margin-bottom: var(--kb-space-sm);
}

/* Tool use / result — Amber, professional tool feel */
.msg.tool_use, .msg.tool_result {
  background: var(--kb-bg-subtle);
  border-color: var(--kb-border);
  padding: var(--kb-space-sm) var(--kb-space);
  border-radius: var(--kb-radius-sm);
  margin-bottom: var(--kb-space-sm);
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
  background: var(--kb-bg-elevated);
  border-color: var(--kb-violet);
  border-left: 4px solid var(--kb-violet);
}

/* Todo — Amber */
.msg.todo {
  background: var(--kb-amber-soft);
  border-color: var(--kb-amber);
}

/* Ask user — Interactive card */
.msg.ask_user {
  background: var(--kb-bg-elevated);
  border-color: var(--kb-amber);
  border-left: 4px solid var(--kb-amber);
}

/* System — Info Card */
.msg.system {
  background: var(--kb-bg-subtle);
  border-color: var(--kb-border);
  font-size: 12px;
  padding: var(--kb-space-sm) var(--kb-space);
}

/* Result — Completion summary */
.msg.result {
  background: var(--kb-bg-elevated);
  border-color: var(--kb-border-strong);
  border-top: 3px solid var(--kb-primary);
  border-radius: 0 0 var(--kb-radius) var(--kb-radius);
  margin-top: var(--kb-space);
}
.msg.result.err { border-top-color: var(--kb-rose); }

/* Error */
.msg.error {
  background: var(--kb-rose-soft);
  border-color: var(--kb-rose);
}

/* ── Message content ── */
.msg-head {
  font-size: 11px; font-weight: 700; letter-spacing: 0.3px;
  text-transform: uppercase;
  color: var(--kb-fg-mute);
  margin-bottom: var(--kb-space-sm);
  display: flex; align-items: center; gap: var(--kb-space-xs);
}
.msg.user .msg-head { color: var(--kb-primary); }
.msg.assistant .msg-head { color: var(--kb-emerald); }
.msg.tool_use .msg-head { color: var(--kb-amber); }

.msg-text {
  line-height: 1.7; word-break: break-word;
  color: var(--kb-fg); font-size: 14.5px;
  text-wrap: pretty;
}
.msg.user .msg-text { color: var(--kb-fg); }

/* ── Markdown rendering enhancements ── */
.msg-text :deep(h1),
.msg-text :deep(h2),
.msg-text :deep(h3) {
  font-weight: 700; letter-spacing: -0.2px; margin: var(--kb-space) 0 var(--kb-space-sm);
  color: var(--kb-fg);
}
.msg-text :deep(h1) { font-size: 20px; }
.msg-text :deep(h2) { font-size: 17px; }
.msg-text :deep(h3) { font-size: 15px; }
.msg-text :deep(h4) { font-size: 14px; font-weight: 700; margin: var(--kb-space-sm) 0; color: var(--kb-fg); }
.msg-text :deep(h5), .msg-text :deep(h6) { font-size: 13px; font-weight: 700; margin: var(--kb-space-sm) 0; color: var(--kb-fg-2); }
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

/* Code blocks -- dark IDE theme */
.msg-text :deep(pre) {
  background: var(--kb-bg-dark);
  color: #c8d3e0;
  padding: var(--kb-space) var(--kb-space-lg);
  border-radius: var(--kb-radius-sm);
  overflow-x: auto;
  font-family: var(--kb-font-mono);
  font-size: 12.5px; line-height: 1.6;
  margin: var(--kb-space-sm) 0;
  border: 1px solid rgba(255,255,255,0.06);
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
  border-left: 3px solid var(--kb-primary);
  padding-left: var(--kb-space);
  margin: var(--kb-space-sm) 0;
  color: var(--kb-fg-3);
}
.msg-text :deep(strong) { color: var(--kb-fg); font-weight: 700; }
.msg-text :deep(hr) { border: none; border-top: 1px solid var(--kb-border); margin: var(--kb-space) 0; }
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
  background: var(--kb-bg-subtle);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius-sm);
  padding: var(--kb-space-sm) var(--kb-space);
  transition: all var(--kb-dur-fast) var(--kb-ease);
}
.think-details:hover { border-color: var(--kb-border-strong); }
.think-details summary {
  cursor: pointer; font-size: 12px; font-weight: 600;
  color: var(--kb-fg-3);
  display: flex; align-items: center; gap: var(--kb-space-xs);
  user-select: none;
}
.think-body {
  font-size: 12.5px; color: var(--kb-fg-3);
  white-space: pre-wrap;
  padding: var(--kb-space-sm) 0 0;
  border-top: 1px solid var(--kb-border);
  margin-top: var(--kb-space-sm);
  max-height: 320px; overflow-y: auto;
  line-height: 1.6;
}

/* ═══ Tool cards ═══ */
.tool-card { border-radius: var(--kb-radius-sm); }
.tool-head {
  display: flex; align-items: center; gap: var(--kb-space-sm);
  margin-bottom: 2px; flex-wrap: wrap;
}
.tool-badge {
  font-size: 11.5px; font-weight: 700; letter-spacing: 0.2px;
  padding: 3px 10px; border-radius: var(--kb-radius-sm);
  background: var(--kb-amber-soft); color: var(--kb-amber);
  font-family: var(--kb-font-mono);
}
.tool-badge.mcp {
  background: rgba(124, 92, 255, 0.1); color: var(--kb-violet);
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
.input-area { position: relative; flex-shrink: 0; }
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
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius-lg);
  padding: var(--kb-space-sm);
  box-shadow: var(--kb-shadow-md);
  transition: border-color var(--kb-dur-fast) var(--kb-ease), box-shadow var(--kb-dur-fast) var(--kb-ease);
}
.input-bar:focus-within {
  border-color: var(--kb-primary);
  box-shadow: var(--kb-shadow-md), 0 0 0 3px rgba(37,99,235,0.08);
}
.input-bar :deep(.ant-input) {
  flex: 1; border: none; box-shadow: none; background: transparent;
  font-size: 14px; resize: none;
}
.input-bar :deep(.ant-input:focus) { box-shadow: none; }

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

/* ═══ Scrollbar (chat messages) ═══ */
.messages::-webkit-scrollbar { width: 8px; }
.messages::-webkit-scrollbar-track { background: transparent; }
.messages::-webkit-scrollbar-thumb {
  background: var(--kb-border-strong);
  border-radius: var(--kb-radius-pill);
  border: 2px solid transparent; background-clip: content-box;
}
.messages::-webkit-scrollbar-thumb:hover {
  background: var(--kb-fg-mute); background-clip: content-box;
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
  border-color: var(--kb-emerald) !important;
  border-left: 3px solid var(--kb-emerald);
  position: relative;
}
.streaming-msg .msg-text::after {
  /* Make Markdown-rendered streaming text feel coherent */
  display: inline;
}
.stream-cursor {
  display: inline-block;
  width: 8px; height: 18px;
  background: var(--kb-emerald);
  margin-left: 2px;
  vertical-align: text-bottom;
  border-radius: 1px;
  animation: blink-cursor 0.9s steps(2) infinite;
}
@keyframes blink-cursor {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* ═══ Typing dot animation (no streaming text) ═══ */
.typing-msg {
  background: var(--kb-bg-elevated);
  border-color: var(--kb-emerald-soft);
}
.typing-dots {
  display: flex; gap: 5px; padding: 6px 0;
}
.typing-dots span {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--kb-emerald);
  animation: typing-bounce 1.3s ease-in-out infinite;
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

/* Message cards entrance animation (overrides kb-fade-up, makes new messages livelier) */
.msg {
  animation: msg-in 0.35s var(--kb-ease) both;
}
@keyframes msg-in {
  from { opacity: 0; transform: translateY(10px) scale(0.99); }
  to { opacity: 1; transform: translateY(0) scale(1); }
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
.qa-pill:hover { border-color: var(--kb-primary); color: var(--kb-primary); background: var(--kb-primary-tint); }

/* ═══ Message Queue Panel ═══ */
.queue-panel {
  flex-shrink: 0;
  background: var(--kb-amber-soft); border: 1px solid var(--kb-amber);
  border-radius: var(--kb-radius); padding: var(--kb-space-sm) var(--kb-space);
  margin-bottom: var(--kb-space-sm);
}
.queue-head {
  display: flex; align-items: center; gap: var(--kb-space-sm);
  font-size: 12px; font-weight: 700; color: var(--kb-amber);
  margin-bottom: var(--kb-space-sm);
}
.queue-item {
  display: flex; align-items: center; gap: var(--kb-space-sm);
  padding: 4px 0; font-size: 13px;
  border-bottom: 1px solid rgba(245,158,11,0.15);
}
.queue-item:last-child { border-bottom: none; }
.queue-idx { font-weight: 600; color: var(--kb-fg-mute); min-width: 20px; }
.queue-text { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--kb-fg-2); }
.queue-actions { display: flex; gap: 2px; flex-shrink: 0; }

/* ═══ Mobile responsive ═══ */
@media (max-width: 768px) {
  .claude-chat-page {
    padding: var(--kb-space-sm);
    height: calc(100vh - 52px);
    gap: var(--kb-space-sm);
  }
  .chat-header { flex-direction: column; gap: var(--kb-space-sm); }
  .chat-header h2 { font-size: 17px; }
  .header-actions { width: 100%; justify-content: flex-end; }
  .toolbar { flex-direction: column; align-items: stretch; gap: var(--kb-space-xs); }
  .toolbar .workspace-selector { min-width: 0; flex-direction: column; }
  .toolbar :deep(.ant-select) { width: 100% !important; }
  .toolbar > .ant-input,
  .toolbar :deep(.ant-select) { max-width: 100%; }
  .messages { padding: var(--kb-space-sm); border-radius: var(--kb-radius); }
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

