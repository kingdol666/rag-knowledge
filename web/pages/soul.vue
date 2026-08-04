<template>
  <div class="soul-studio">
    <!-- ═══ 顶栏 ═══ -->
    <header class="studio-header">
      <div class="header-left">
        <div class="header-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6">
            <circle cx="12" cy="12" r="8.2" />
            <path d="M12 3.8v16.4M3.8 12h16.4" opacity=".55" />
            <circle cx="12" cy="12" r="2.4" fill="currentColor" stroke="none" />
          </svg>
        </div>
        <div>
          <h1 class="page-title">SOUL · Persona Studio</h1>
          <p class="page-subtitle">人格生命周期监控 · 好奇心探索训练 · RL 强化进化 · 检索增强问答</p>
        </div>
      </div>
      <div class="header-actions">
        <span v-if="runningTasks" class="task-live">
          <i class="live-dot"></i>{{ runningTasks }} 个任务运行中
        </span>
        <button class="btn btn-ghost" @click="loadAll" :disabled="loadingList">
          <span class="btn-glyph">⟳</span> 刷新
        </button>
        <button class="btn btn-primary" @click="openCreate">
          <span class="btn-glyph">＋</span> 创建人格
        </button>
      </div>
    </header>

    <div class="studio-body">
      <!-- ═══ 左 rail: 人格清单 ═══ -->
      <aside class="persona-rail">
        <div class="rail-head">
          <span>人格清单</span>
          <span class="rail-count">{{ souls.length }}</span>
        </div>
        <div v-if="loadingList && !souls.length" class="rail-loading">载入中…</div>
        <div v-else-if="!souls.length" class="rail-empty">尚无人格，点击「创建人格」开始</div>
        <div
          v-for="soul in souls"
          :key="soul.kb_id"
          class="rail-item"
          :class="{ active: selected?.kb_id === soul.kb_id }"
          @click="selectSoul(soul)"
        >
          <div class="rail-item-top">
            <i
              class="state-light"
              :class="{
                training: soul._training,
                warn: !soul._training && (soul._status?.drafts_pending_review > 0),
                idle: !soul._training && !(soul._status?.drafts_pending_review > 0),
              }"
            ></i>
            <span class="rail-name">{{ soul.name }}</span>
            <span class="rail-mem">{{ soul._status?.total_memories ?? 0 }} 记忆</span>
          </div>
          <div class="rail-scope">{{ scopeDocs(soul).slice(0, 2).join(' · ') || (soul.kb_scope || []).join(' · ') || '仅问答' }}</div>
          <div class="rail-meta">
            <span class="pill pill-harness">{{ soul.meditation?.harness || 'omp' }}</span>
            <span v-if="soul.meditation?.enabled" class="pill pill-sched">定时 {{ soul.meditation.interval_hours }}h</span>
            <span v-if="soul._status?.drafts_pending_review" class="pill pill-warn">待审 {{ soul._status.drafts_pending_review }}</span>
            <span v-if="soul._status?.judge_divergence_count" class="pill pill-err">分歧 {{ soul._status.judge_divergence_count }}</span>
          </div>
        </div>
      </aside>

      <!-- ═══ 主区 ═══ -->
      <main class="studio-main">
        <template v-if="selected">
          <!-- 身份条 -->
          <section class="identity-bar">
            <div class="id-avatar">{{ soulAvatar(selected.name) }}</div>
            <div class="id-text">
              <div class="id-title">
                <h2>{{ selected.name }}</h2>
                <span v-if="selected.meditation?.enabled && selected.meditation?.meditation_mode === 'soul'" class="chip chip-red">自动训练 {{ selected.meditation.interval_hours }}h × {{ selected.meditation.rounds_per_run }}轮</span>
                <span v-if="selected._training" class="chip chip-amber">训练中</span>
              </div>
              <p class="id-summary">{{ selected.summary || '暂无摘要' }}</p>
              <div class="id-tags">
                <span class="tag-kb" v-for="s in selected.kb_scope || []" :key="s">{{ s }}</span>
                <span class="tag-dom" v-for="d in selected.domain_labels || []" :key="d">{{ d }}</span>
              </div>
            </div>
            <div class="id-actions">
              <button class="btn btn-primary btn-sm" @click="openAsk(selected)">提问</button>
              <button class="btn btn-copper btn-sm" @click="openTrain(selected)">训练</button>
              <button class="btn btn-ghost btn-sm" @click="reviewDrafts(selected)">审批<template v-if="selected._status?.drafts_pending_review"> {{ selected._status.drafts_pending_review }}</template></button>
              <button class="btn btn-ghost btn-sm" @click="openEdit(selected)">配置</button>
              <button class="btn btn-ghost btn-sm" @click="doReflect(selected)">反思</button>
              <button class="btn btn-ghost btn-sm" @click="doCheckpoint(selected)">检查点</button>
            </div>
          </section>

          <!-- 监控带 -->
          <section class="monitor-strip">
            <div class="metric-cell" v-for="m in metrics" :key="m.label">
              <span class="metric-val" :class="{ warn: m.warn }">{{ m.value }}</span>
              <span class="metric-label">{{ m.label }}</span>
            </div>
            <div class="metric-cell metric-reward" v-if="rewardRecords.length">
              <span class="metric-val">{{ lastReward }}</span>
              <span class="metric-label">RL reward</span>
            </div>
          </section>

          <div class="workspace">
            <!-- 训练控制台 -->
            <section class="console train-console">
              <div class="console-head">
                <h3>训练控制台</h3>
                <span class="console-sub">好奇心探索 · 评价驱动</span>
              </div>

              <!-- 未运行: 触发面板 -->
              <div v-if="trainTaskStatus !== 'running'" class="train-launch">
                <div class="mode-tabs">
                  <button class="mode-tab" :class="{ on: trainMode === 'docs' }" @click="trainMode = 'docs'">指定文档</button>
                  <button class="mode-tab" :class="{ on: trainMode === 'all' }" @click="trainMode = 'all'">全库自举</button>
                  <button class="mode-tab mode-rl" :class="{ on: trainMode === 'rl' }" @click="trainMode = 'rl'">RL 强化</button>
                </div>

                <template v-if="trainMode === 'docs'">
                  <label class="field">
                    <span class="field-label">学习文档（kb_scope 内）</span>
                    <select class="inp" v-model="trainForm.doc_paths" multiple size="5">
                      <option v-for="d in docOptions" :key="d.path" :value="d.path">{{ d.path }}</option>
                    </select>
                  </label>
                  <div class="field-row">
                    <label class="field"><span class="field-label">问题上限</span><input class="inp" type="number" v-model.number="trainForm.limit" min="1" max="10" /></label>
                    <label class="field"><span class="field-label">轮数 rounds</span><input class="inp" type="number" v-model.number="trainForm.rounds" min="1" max="20" /></label>
                  </div>
                </template>

                <template v-else-if="trainMode === 'all'">
                  <div class="field-row">
                    <label class="field"><span class="field-label">轮数 rounds</span><input class="inp" type="number" v-model.number="trainForm.rounds" min="1" max="20" /></label>
                    <label class="field"><span class="field-label">每轮文档上限</span><input class="inp" type="number" v-model.number="trainForm.maxDocs" min="1" max="50" /></label>
                  </div>
                  <label class="check"><input type="checkbox" v-model="trainForm.dry_run" /> 仅估算（dry-run，不执行）</label>
                </template>

                <template v-else>
                  <p class="rl-desc">
                    <b>RL 强化训练</b> — 每轮 = 好奇心探索（learn）→ 评价 Agent 四维打分（reward）→
                    低分维度生成认知草稿（策略更新）。草稿经审批后合并入人格定义，评价得分驱动结构文档持续优化。
                  </p>
                  <label class="field"><span class="field-label">RL 轮数 rounds</span><input class="inp" type="number" v-model.number="trainForm.rounds" min="1" max="10" /></label>
                </template>

                <div class="launch-row">
                  <button class="btn btn-copper" :disabled="training" @click="doTrain">
                    {{ training ? '提交中…' : (trainMode === 'rl' ? '启动 RL 强化训练' : '开始训练') }}
                  </button>
                  <span class="launch-hint">异步执行 · 提交即返回，实时追踪进度</span>
                </div>
              </div>

              <!-- 运行中 / 已完成: 监控 -->
              <div v-else class="train-monitor">
                <!-- 阶段时间线 -->
                <div class="phase-track" v-if="trainProgress">
                  <div class="phase" :class="{ on: phaseIdx('learn') >= 1, done: phaseIdx('learn') === 2 }">
                    <span class="phase-dot"></span><span class="phase-name">探索</span>
                    <span class="phase-note">{{ trainProgress.questions ?? 0 }} 问题</span>
                  </div>
                  <div class="phase-conn" :class="{ on: phaseIdx('reward') >= 1 }"></div>
                  <div class="phase" :class="{ on: phaseIdx('reward') >= 1, done: phaseIdx('reward') === 2 }">
                    <span class="phase-dot"></span><span class="phase-name">评价</span>
                    <span class="phase-note" v-if="trainProgress.reward !== undefined">reward {{ fmtNum(trainProgress.reward) }}</span>
                  </div>
                  <div class="phase-conn" :class="{ on: trainTaskStatus === 'done' }"></div>
                  <div class="phase" :class="{ on: (trainProgress.drafts_created ?? 0) > 0 || trainTaskStatus === 'done' }">
                    <span class="phase-dot"></span><span class="phase-name">策略更新</span>
                    <span class="phase-note">{{ trainProgress.drafts_created ?? 0 }} 认知草稿</span>
                  </div>
                </div>

                <div class="mon-line">
                  <span class="mon-label">进度</span>
                  <div class="bar"><i class="bar-fill" :style="{ width: trainPercent() + '%' }"></i></div>
                  <span class="mon-pct">{{ trainPercent() }}%</span>
                </div>
                <div class="mon-line" v-if="trainProgress">
                  <span class="mon-label">状态</span>
                  <span class="mon-text">
                    <template v-if="trainProgress.phase === 'scan'">扫描文档 {{ trainProgress.scanned }}/{{ trainProgress.total }} · 去重后 {{ trainProgress.unique_docs }}</template>
                    <template v-else-if="trainProgress.phase === 'learn'">学习轮 {{ trainProgress.round }}/{{ trainProgress.rounds }} · 问题 {{ trainProgress.questions }} · 记忆 {{ trainProgress.memories }} · 文档 {{ trainProgress.docs_processed }}<template v-if="trainProgress.learn_error"> · <span class="err">learn: {{ trainProgress.learn_error }}</span></template></template>
                    <template v-else-if="trainProgress.phase === 'reward'">第 {{ trainProgress.round }}/{{ trainProgress.rounds }} 轮 · 评价得分 <b>{{ fmtNum(trainProgress.reward) }}</b> · 认知草稿 {{ trainProgress.drafts_created }}</template>
                    <template v-else>执行中…</template>
                  </span>
                </div>

                <!-- 事件日志流 -->
                <div class="event-log">
                  <div class="log-head">事件流</div>
                  <div class="log-body" ref="logBody">
                    <div v-for="(ev, i) in eventLog" :key="i" class="log-line">
                      <span class="log-time">{{ ev.time }}</span>
                      <i class="log-dot" :class="ev.tone"></i>
                      <span class="log-text">{{ ev.text }}</span>
                    </div>
                  </div>
                </div>

                <div class="train-result-box" v-if="trainResult">
                  <div class="result-head2">
                    <span>训练结果</span>
                    <button class="btn btn-ghost btn-xs" @click="trainResult = ''">关闭</button>
                  </div>
                  <pre class="result-pre">{{ trainResult }}</pre>
                </div>
              </div>

              <!-- RL 进化曲线(常驻, 无论是否训练中) -->
              <div class="reward-curve" v-if="rewardRecords.length > 1">
                <div class="curve-head">
                  <span>RL 进化曲线</span>
                  <span class="curve-sub">{{ rewardRecords.length }} 轮 · 最新 {{ fmtNum(lastReward) }}</span>
                </div>
                <svg :viewBox="`0 0 320 96`" preserveAspectRatio="none" class="curve-svg">
                  <polyline
                    :points="curvePoints"
                    fill="none" stroke="var(--kb-primary, #b24422)" stroke-width="2"
                    vector-effect="non-scaling-stroke"
                  />
                  <circle v-for="(p, i) in curveDots" :key="i" :cx="p.x" :cy="p.y" r="2.6" fill="var(--kb-gold, #b8860b)" />
                </svg>
              </div>
              <div v-else-if="rewardRecords.length === 1" class="reward-curve">
                <div class="curve-head">
                  <span>RL 进化曲线</span>
                  <span class="curve-sub">已记录 1 轮 · reward {{ fmtNum(lastReward) }}（再训练一轮后绘制曲线）</span>
                </div>
              </div>
            </section>

            <!-- 人格定义查看器 -->
            <section class="console def-console">
              <div class="console-head">
                <h3>人格定义</h3>
                <span class="console-sub">
                  宪法层 · <template v-if="docEvolution > 0">RL 已进化 {{ docEvolution }} 行</template><template v-else>待进化</template>
                </span>
              </div>
              <div class="doc-tabs">
                <button
                  v-for="d in personaDocs"
                  :key="d.name"
                  class="doc-tab"
                  :class="{ on: activeDoc === d.name }"
                  @click="activeDoc = d.name"
                >{{ docShortName(d.name) }}</button>
              </div>
              <div class="doc-body" v-if="activeDocContent">
                <div class="doc-meta">
                  <span class="doc-updated">更新 {{ fmtTime(activeDocMeta.updated_at) }}</span>
                  <span class="doc-char">{{ activeDocContent.length }} 字符</span>
                </div>
                <div class="doc-scroll" ref="docScroll">
                  <template v-for="(line, i) in renderedDoc" :key="i">
                    <h4 v-if="isHeading(line)" class="doc-h">{{ line.replace(/^#+\s*/, '') }}</h4>
                    <div v-else-if="isBullet(line)" class="doc-bullet" :class="{ evolved: isEvolvedLine(line) }">
                      <span class="b-dot"></span><span>{{ line.replace(/^[-•*]\s*/, '') }}</span>
                      <span v-if="isEvolvedLine(line)" class="evolved-mark">RL</span>
                    </div>
                    <p v-else-if="line.trim()" class="doc-p" :class="{ evolved: isEvolvedLine(line) }">{{ line }}</p>
                  </template>
                </div>
              </div>
              <div v-else class="doc-empty">加载中…</div>
            </section>
          </div>
        </template>

        <!-- 未选择 -->
        <div v-else class="studio-empty">
          <div class="empty-symbol" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" stroke-width="1.3">
              <circle cx="12" cy="12" r="8.2" />
              <path d="M12 3.8v16.4M3.8 12h16.4" opacity=".5" />
            </svg>
          </div>
          <p class="empty-title">从左侧选择一个人格</p>
          <p class="empty-desc">或点击「创建人格」初始化一个 SOUL —— 补天蒸馏、好奇心训练、RL 强化与检索增强问答全部在此可视化。</p>
        </div>
      </main>
    </div>

    <!-- ═══ Toast ═══ -->
    <transition name="toast-fade">
      <div v-if="toast" class="soul-toast" :class="toastType">
        <span>{{ toast }}</span>
        <button class="toast-close" @click="toast = ''">×</button>
      </div>
    </transition>

    <!-- ═══════════ 创建人格 Modal ═══════════ -->
    <a-modal v-model:open="createOpen" title="创建新人格" :footer="null" width="620">
      <a-form layout="vertical">
        <a-form-item label="人格名称（soul- 前缀）">
          <a-input v-model:value="form.soul_name" placeholder="如 soul-材料学" />
        </a-form-item>
        <a-form-item label="学习范围 kb_scope（公开库，可多选；空=仅问答）">
          <a-checkbox v-model:value="form.allKb">全部知识库参与（默认，kb_scope=["*"]）</a-checkbox>
          <a-select v-model:value="form.kb_scope" mode="multiple" placeholder="选择知识库" style="width:100%; margin-top:6px" :disabled="form.allKb">
            <a-select-option v-for="kb in kbCatalog" :key="kb.kb_id" :value="kb.kb_id">{{ kb.name }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="领域标签 domain_labels（路由匹配）">
          <a-select v-model:value="form.domain_labels" mode="tags" placeholder="如 材料科学 / 机器学习" style="width:100%" />
        </a-form-item>
        <a-form-item label="任务类型 supported_task_types">
          <a-select v-model:value="form.supported_task_types" mode="tags" placeholder="如 文献综述 / 技术选型" style="width:100%" />
        </a-form-item>
        <a-form-item :label="`训练 harness（默认 ${defaultHarness || 'omp'}，可单独指定）`">
          <a-select v-model:value="form.harness" style="width:100%">
            <a-select-option value="">跟随全局默认 ({{ defaultHarness || 'omp' }})</a-select-option>
            <a-select-option value="omp">omp {{ harnessInstalled('omp') ? '(可用)' : '(未安装)' }}</a-select-option>
            <a-select-option value="claude">claude {{ harnessInstalled('claude') ? '(可用)' : '(需 ANTHROPIC_API_KEY)' }}</a-select-option>
          </a-select>
        </a-form-item>
        <div class="modal-actions">
          <a-button @click="createOpen = false">取消</a-button>
          <a-button type="primary" :loading="creating" @click="doCreate">创建</a-button>
        </div>
      </a-form>
    </a-modal>

    <!-- ═══════════ 配置 Modal ═══════════ -->
    <a-modal v-model:open="editOpen" title="人格配置" :footer="null" width="620">
      <a-form layout="vertical" v-if="editing">
        <a-form-item label="人格"><a-input :value="editing.name" disabled /></a-form-item>
        <a-form-item label="学习范围">
          <a-select v-model:value="editForm.kb_scope" mode="multiple" style="width:100%">
            <a-select-option v-for="kb in kbCatalog" :key="kb.kb_id" :value="kb.kb_id">{{ kb.name }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="领域标签"><a-select v-model:value="editForm.domain_labels" mode="tags" style="width:100%" /></a-form-item>
        <a-form-item label="任务类型"><a-select v-model:value="editForm.supported_task_types" mode="tags" style="width:100%" /></a-form-item>
        <a-form-item label="路由权重（0=退出路由）"><a-slider v-model:value="editForm.route_weight" :min="0" :max="2" :step="0.1" /></a-form-item>
        <a-divider style="margin:8px 0">训练引擎（per-SOUL，覆盖全局默认）</a-divider>
        <a-form-item label="harness">
          <a-select v-model:value="editForm.harness" style="width:100%">
            <a-select-option value="omp">omp</a-select-option>
            <a-select-option value="claude">claude</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="模型（空=引擎默认）"><a-input v-model:value="editForm.model" placeholder="如 deepseek/deepseek-v4-flash" /></a-form-item>
        <a-divider style="margin:8px 0">自动训练（定时调度）</a-divider>
        <a-form-item label="启用定时自动训练"><a-switch v-model:value="editForm.autoTrainEnabled" /></a-form-item>
        <div class="ask-row">
          <a-form-item label="间隔(小时)"><a-input-number v-model:value="editForm.intervalHours" :min="1" :max="720" /></a-form-item>
          <a-form-item label="每轮固定轮数"><a-input-number v-model:value="editForm.roundsPerRun" :min="1" :max="20" /></a-form-item>
          <a-form-item label="每轮预算($)"><a-input-number v-model:value="editForm.maxBudgetUsd" :min="0.01" :max="2" :step="0.05" /></a-form-item>
        </div>
        <a-form-item label="每轮问题上限"><a-input-number v-model:value="editForm.maxQuestions" :min="1" :max="20" /></a-form-item>
        <div class="modal-actions">
          <a-button @click="editOpen = false">取消</a-button>
          <a-button type="primary" :loading="savingConfig" @click="doSaveConfig">保存</a-button>
        </div>
      </a-form>
    </a-modal>

    <!-- ═══════════ 问答 Modal ═══════════ -->
    <a-modal v-model:open="askOpen" title="SOUL 人格问答（检索增强）" :footer="null" width="720">
      <div v-if="askSoul || true">
        <div class="ask-target">
          <span class="ask-target-label">目标</span>
          <a-tag v-if="askSoul?.name" color="purple">{{ askSoul.name }}</a-tag>
          <span v-else class="ask-route-hint">自动路由（按任务类型匹配最适人格）</span>
          <span class="ask-hint">soul_kb_id 为空时自动匹配；检索范围 = 人格 kb_scope</span>
        </div>
        <a-form layout="vertical">
          <a-form-item label="问题">
            <a-textarea v-model:value="askForm.query" :rows="3" placeholder="输入问题…" />
          </a-form-item>
          <div class="ask-row">
            <a-form-item label="任务类型"><a-input v-model:value="askForm.task_type" placeholder="如 文献综述" /></a-form-item>
            <a-form-item label="任务目标"><a-input v-model:value="askForm.task_goal" placeholder="如 研究 / 教学" /></a-form-item>
          </div>
          <a-form-item label="上下文注入 context_override（可选，来自预检索）">
            <a-textarea v-model:value="askForm.context_override" :rows="2" placeholder="注入检索到的片段，人格基于此加工" />
          </a-form-item>
        </a-form>
        <div class="ask-row">
          <a-button :loading="searchingKb" @click="doPreSearch">预检索知识库</a-button>
          <a-button type="primary" ghost :loading="asking" @click="doQdcvrAsk">一键检索+人格回答</a-button>
          <a-button type="primary" :loading="asking" @click="doAsk">提问</a-button>
        </div>
        <div v-if="preSearchChunks.length" class="pre-search-list">
          <div v-for="(c, i) in preSearchChunks.slice(0, 5)" :key="i" class="cite-item">
            <span class="cite-path">{{ c.doc_path }}</span>
            <span class="cite-score">{{ c.score?.toFixed?.(3) ?? c.score }}</span>
          </div>
        </div>
        <div v-if="askResult" class="ask-result">
          <div class="result-head">
            <span class="result-label">回答</span>
            <a-tag v-if="askResult.selected_soul" color="green">路由: {{ soulName(askResult.selected_soul) }}</a-tag>
            <a-tag v-if="askResult.pas_score !== undefined && askResult.pas_score !== null" :color="askResult.pas_score >= 3 ? 'cyan' : 'red'">PAS {{ askResult.pas_score }}</a-tag>
            <a-tag v-if="askResult.evidence_count !== undefined">证据 {{ askResult.evidence_count }}</a-tag>
          </div>
          <div class="answer-text">{{ askResult.answer }}</div>
          <div v-if="askResult.citations?.length" class="cite-list">
            <div class="cite-title">引用（{{ askResult.citations.length }}）</div>
            <div v-for="(c, i) in askResult.citations.slice(0, 8)" :key="i" class="cite-item">
              <span class="cite-path">{{ c.path }}</span>
              <span class="cite-score">{{ c.score?.toFixed?.(3) ?? c.score }}</span>
            </div>
          </div>
        </div>
        <div class="modal-actions">
          <a-button @click="askOpen = false">关闭</a-button>
        </div>
      </div>
    </a-modal>

    <!-- ═══════════ 审批 Modal ═══════════ -->
    <a-modal v-model:open="reviewOpen" title="草稿审批" :footer="null" width="780">
      <div v-if="reviewSoul">
        <div class="ask-target">
          <span class="ask-target-label">人格</span>
          <a-tag color="purple">{{ reviewSoul.name }}</a-tag>
          <a-radio-group v-model:value="reviewType" size="small" style="margin-left:12px">
            <a-radio-button value="memory" @click="reviewDrafts(reviewSoul, 'memory')">记忆草稿</a-radio-button>
            <a-radio-button value="cognition" @click="reviewDrafts(reviewSoul, 'cognition')">认知草稿 (RL)</a-radio-button>
          </a-radio-group>
          <a-button v-if="drafts.length > 1 && !reviewTaskStatus" size="small" type="primary" ghost style="margin-left:auto" @click="approveAllDrafts()">
            全部批准（{{ drafts.length }} 条，异步）
          </a-button>
        </div>
        <a-alert v-if="reviewTaskStatus === 'running'" type="info" show-icon style="margin-bottom:8px">
          <template #message>
            <div>审批执行中… {{ reviewProgress?.processed || 0 }}/{{ reviewProgress?.total || drafts.length }} 条（已批准 {{ reviewProgress?.approved || 0 }}）</div>
            <a-progress :percent="Math.round(((reviewProgress?.processed || 0) / (reviewProgress?.total || drafts.length || 1)) * 100)" size="small" />
          </template>
        </a-alert>
        <a-alert v-if="reviewTaskStatus === 'error'" type="error" show-icon :message="reviewError || '审批失败'" style="margin-bottom:8px" />
        <a-table
          :data-source="drafts"
          :columns="draftColumns"
          size="small"
          :pagination="false"
          :scroll="{ y: 360 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'scores'">
              <span class="score-cell" :class="{ low: (record.scores?.groundedness ?? 0) < 3 }">G{{ record.scores?.groundedness ?? '-' }}</span>
              <span class="score-cell">{{ record.scores?.completeness ?? '-' }}</span>
              <span class="score-cell">{{ record.scores?.coherence ?? '-' }}</span>
              <span class="score-cell">{{ record.scores?.info_gain ?? '-' }}</span>
              <span class="score-cell" v-if="record.scores?.reward !== undefined">R{{ record.scores.reward }}</span>
            </template>
            <template v-else-if="column.key === 'actions'">
              <a-button size="small" type="primary" @click="approveDraft(record.draft_id)">批准</a-button>
              <a-button size="small" danger class="ml-4" @click="rejectDraft(record.draft_id)">驳回</a-button>
            </template>
          </template>
        </a-table>
        <div class="modal-actions" style="margin-top:12px">
          <a-button @click="reviewOpen = false">关闭</a-button>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import {
  RobotOutlined, PlusOutlined, ReloadOutlined, MoreOutlined, SettingOutlined,
  MessageOutlined, ExperimentOutlined, AuditOutlined, SyncOutlined,
  CameraOutlined, ExportOutlined, DeleteOutlined, SearchOutlined,
} from '@ant-design/icons-vue'
import { message, Modal } from 'ant-design-vue'

// ── 类型 ──
interface Soul {
  kb_id: string
  name: string
  summary?: string
  kb_scope?: string[]
  domain_labels?: string[]
  supported_task_types?: string[]
  route_weight?: number
  is_template?: boolean
  meditation?: {
    harness?: string
    model?: string
    enabled?: boolean
    meditation_mode?: string
    interval_hours?: number
    rounds_per_run?: number
    max_questions_per_run?: number
    max_budget_usd?: number
  }
  _status?: any
  _training?: boolean
  _trainingMsg?: string
}

// ── 状态 ──
const souls = ref<Soul[]>([])
const kbCatalog = ref<any[]>([])
const loadingList = ref(false)
const creating = ref(false)
const savingConfig = ref(false)
const training = ref(false)
const asking = ref(false)
const searchingKb = ref(false)
const toast = ref('')
const toastType = ref<'ok' | 'err'>('ok')
const selected = ref<Soul | null>(null)
const runningTasks = ref(0)

// 系统级设置
const soulSettings = ref<any>(null)
const defaultHarness = computed(() => soulSettings.value?.default_harness || 'omp')
const docOptions = ref<{ path: string }[]>([])
const loadingDocs = ref(false)
const preSearchChunks = ref<any[]>([])

// Modals
const createOpen = ref(false)
const editOpen = ref(false)
const trainOpen = ref(false)
const askOpen = ref(false)
const reviewOpen = ref(false)

const form = ref({ soul_name: '', kb_scope: [] as string[], domain_labels: [] as string[], supported_task_types: [] as string[], harness: '', allKb: true })
const editing = ref<Soul | null>(null)
const editForm = ref({
  kb_scope: [] as string[], domain_labels: [] as string[], supported_task_types: [] as string[], route_weight: 1,
  harness: 'omp', model: '', autoTrainEnabled: false, intervalHours: 24, roundsPerRun: 1,
  maxBudgetUsd: 0.15, maxQuestions: 10,
})
const trainingSoul = ref<Soul | null>(null)
const trainMode = ref<'docs' | 'all' | 'rl'>('docs')
const trainForm = ref({ doc_paths: [] as string[], limit: 6, dry_run: false, rounds: 1, maxDocs: 10 })
const trainResult = ref('')
const trainTaskId = ref('')
const trainTaskStatus = ref('')
const trainProgress = ref<any>(null)
const trainError = ref('')
const reviewTaskId = ref('')
const reviewTaskStatus = ref('')
const reviewProgress = ref<any>(null)
const reviewError = ref('')
let trainPollTimer: any = null
let reviewPollTimer: any = null
let taskListTimer: any = null

// 事件日志流（训练监控）
const eventLog = ref<{ time: string; tone: string; text: string }[]>([])
const logBody = ref<HTMLElement | null>(null)

// 人格定义查看器
const personaDocs = ref<{ name: string; content: string; updated_at?: string }[]>([])
const activeDoc = ref('soul-definition.md')
const docEvolution = ref(0)
const evolutionLines = ref<string[]>([])

// RL 进化曲线
const rewardRecords = ref<any[]>([])

const askSoul = ref<Soul | null>(null)
const askForm = ref({ query: '', task_type: '', task_goal: '', context_override: '' })
const askResult = ref<any>(null)
const reviewSoul = ref<Soul | null>(null)
const drafts = ref<any[]>([])
const draftColumns = [
  { title: '问题', dataIndex: 'question', key: 'question', ellipsis: true },
  { title: 'G/C/C/I/R', key: 'scores', width: 150 },
  { title: '操作', key: 'actions', width: 130 },
]

// ── 工具 ──
function soulAvatar(name: string) {
  const m = name.match(/soul-([\u4e00-\u9fa5A-Za-z]+)/)
  return m ? m[1].slice(0, 2) : 'S'
}
function soulName(kbId: string) {
  return souls.value.find(s => s.kb_id === kbId)?.name || kbId.slice(0, 8)
}
function harnessInstalled(name: string): boolean {
  const h = soulSettings.value?.harnesses?.[name]
  return !!h?.installed
}
function scopeDocs(soul: Soul): string[] {
  const out: string[] = []
  for (const kb of kbCatalog.value) {
    if ((soul.kb_scope || []).includes(kb.kb_id) || (soul.kb_scope || []).includes(kb.name)) {
      out.push(kb.name)
    }
  }
  return out
}
function fmtNum(v: any): string {
  const n = Number(v)
  return Number.isFinite(n) ? n.toFixed(2) : String(v ?? '—')
}
function fmtTime(iso?: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
function showToast(msg: string, type: 'ok' | 'err' = 'ok') {
  toast.value = msg
  toastType.value = type
  setTimeout(() => { if (toast.value === msg) toast.value = '' }, 5000)
}
function pushLog(tone: string, text: string) {
  const now = new Date()
  const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`
  eventLog.value.push({ time, tone, text })
  if (eventLog.value.length > 200) eventLog.value.splice(0, eventLog.value.length - 200)
  nextTick(() => { if (logBody.value) logBody.value.scrollTop = logBody.value.scrollHeight })
}
function phaseIdx(phase: string): number {
  // 0=未开始 1=进行中 2=完成
  const p = trainProgress.value || {}
  if (trainTaskStatus.value === 'done') return 2
  if (p.phase === phase) return 1
  const order = ['learn', 'reward']
  if (order.indexOf(phase) >= 0 && order.indexOf(p.phase) > order.indexOf(phase)) return 2
  if (phase === 'reward' && p.phase === 'reward') return 1
  return p.phase === phase ? 1 : 0
}
function docShortName(name: string) {
  return name.replace(/\.md$/, '').replace(/-/g, ' ')
}
function isHeading(line: string) { return /^#{1,4}\s/.test(line) }
function isBullet(line: string) { return /^[-•*]\s/.test(line) }
function isEvolvedLine(line: string): boolean {
  const t = line.replace(/^[-•*]\s*/, '').trim()
  return evolutionLines.value.includes(t)
}

// ── 派生 ──
const metrics = computed(() => {
  const s = selected.value?._status
  if (!s) return []
  return [
    { label: '记忆', value: s.total_memories ?? 0 },
    { label: '待审', value: s.drafts_pending_review ?? 0, warn: s.drafts_pending_review > 0 },
    { label: '缺口', value: s.total_gaps ?? 0 },
    { label: '掌握分', value: s.mastery?.avg_score != null ? s.mastery.avg_score.toFixed(1) : '—' },
    { label: '成本', value: s.estimated_cost_usd != null ? `$${s.estimated_cost_usd.toFixed(2)}` : '—', warn: (s.estimated_cost_usd ?? 0) > 0.12 },
    { label: '分歧', value: s.judge_divergence_count ?? 0, warn: s.judge_divergence_count > 0 },
  ]
})
const lastReward = computed(() => {
  const r = rewardRecords.value[rewardRecords.value.length - 1]
  return r ? fmtNum(r.reward) : '—'
})
const activeDocMeta = computed(() => personaDocs.value.find(d => d.name === activeDoc.value) || {})
const activeDocContent = computed(() => activeDocMeta.value.content || '')
const renderedDoc = computed(() => activeDocContent.value.split('\n'))
const curvePoints = computed(() => {
  const n = rewardRecords.value.length
  if (n < 2) return ''
  const maxR = Math.max(...rewardRecords.value.map(r => Number(r.reward) || 0))
  const minR = Math.min(...rewardRecords.value.map(r => Number(r.reward) || 0))
  const span = Math.max(0.5, maxR - minR)
  return rewardRecords.value.map((r, i) => {
    const x = (i / (n - 1)) * 320
    const y = 88 - ((Number(r.reward) || 0) - minR) / span * 76
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
})
const curveDots = computed(() => {
  const n = rewardRecords.value.length
  if (n < 2) return []
  const maxR = Math.max(...rewardRecords.value.map(r => Number(r.reward) || 0))
  const minR = Math.min(...rewardRecords.value.map(r => Number(r.reward) || 0))
  const span = Math.max(0.5, maxR - minR)
  return rewardRecords.value.map((r, i) => ({
    x: (i / (n - 1)) * 320,
    y: 88 - ((Number(r.reward) || 0) - minR) / span * 76,
  }))
})

// ── 数据加载 ──
async function loadAll() {
  loadingList.value = true
  try {
    const list = await $fetch<any>('/api/soul/list')
    souls.value = (list || []).map((s: Soul) => ({ ...s }))
    await Promise.all(souls.value.map(async (s) => {
      try { s._status = await $fetch<any>(`/api/soul/status?soul_kb_id=${encodeURIComponent(s.kb_id)}`) } catch { /* noop */ }
    }))
    try {
      const cat = await $fetch<any>('/api/kb/catalog')
      kbCatalog.value = cat?.knowledgeBases || []
    } catch { /* noop */ }
    try {
      soulSettings.value = await $fetch<any>('/api/soul/settings')
    } catch { /* noop */ }
    // 默认选中第一个非模板人格
    if (!selected.value && souls.value.length) {
      selectSoul(souls.value.find(s => !s.is_template) || souls.value[0])
    } else if (selected.value) {
      const fresh = souls.value.find(s => s.kb_id === selected.value?.kb_id)
      if (fresh) selected.value = { ...fresh, _status: fresh._status, _training: selected.value._training }
    }
  } catch (e: any) {
    showToast(`加载失败: ${e.message}`, 'err')
  } finally {
    loadingList.value = false
  }
}

function selectSoul(soul: Soul) {
  selected.value = soul
  // 重置训练监控为该人格上下文
  trainResult.value = ''
  trainTaskStatus.value = ''
  trainProgress.value = null
  eventLog.value = []
  loadRewardHistory(soul)
  loadPersonaDocs(soul)
  loadScopeDocs(soul)
}

async function loadRewardHistory(soul: Soul) {
  try {
    const res = await $fetch<any>(`/api/soul/reward-history?soul_kb_id=${encodeURIComponent(soul.kb_id)}`)
    rewardRecords.value = res?.records || []
  } catch { rewardRecords.value = [] }
}
async function loadPersonaDocs(soul: Soul) {
  try {
    const res = await $fetch<any>(`/api/soul/persona-docs?soul_kb_id=${encodeURIComponent(soul.kb_id)}`)
    personaDocs.value = res?.docs || []
    docEvolution.value = res?.evolution_count ?? 0
    evolutionLines.value = res?.evolution_lines || []
    if (personaDocs.value.length && !personaDocs.value.some(d => d.name === activeDoc.value)) {
      activeDoc.value = personaDocs.value[0].name
    }
  } catch {
    personaDocs.value = []
    docEvolution.value = 0
    evolutionLines.value = []
  }
}
async function loadScopeDocs(soul: Soul) {
  loadingDocs.value = true
  docOptions.value = []
  try {
    const scope = (soul.kb_scope || []).filter((s: string) => s !== '*')
    const kbs = scope.length
      ? kbCatalog.value.filter((kb: any) => scope.includes(kb.kb_id) || scope.includes(kb.name))
      : kbCatalog.value
    const paths = new Set<string>()
    await Promise.all(kbs.map(async (kb: any) => {
      try {
        const res = await $fetch<any>(`/api/kb/documents?kb_id=${encodeURIComponent(kb.kb_id)}`)
        for (const d of (res?.documents || [])) {
          if (d.path && (d.file_type === 'md' || d.path.endsWith('.md'))) paths.add(d.path)
        }
      } catch { /* noop */ }
    }))
    docOptions.value = [...paths].sort().map(p => ({ path: p }))
  } finally {
    loadingDocs.value = false
  }
}

// 全局任务列表监控（顶栏运行中计数）
async function pollTaskList() {
  try {
    const res = await $fetch<any>('/api/soul/tasks?status=running')
    const arr = res?.tasks || []
    runningTasks.value = arr.length
    // 训练中的人格状态灯
    for (const t of arr) {
      const kbId = t.meta?.soul_kb_id
      if (kbId) {
        const s = souls.value.find(x => x.kb_id === kbId)
        if (s) { s._training = true; s._trainingMsg = `${t.kind} · ${t.elapsed_seconds ?? 0}s` }
      }
    }
  } catch { /* noop */ }
}

// ── CRUD ──
function openCreate() {
  form.value = { soul_name: '', kb_scope: [], domain_labels: [], supported_task_types: [], harness: '', allKb: true }
  createOpen.value = true
}
async function doCreate() {
  if (!form.value.soul_name.trim()) { message.warning('请输入人格名称'); return }
  creating.value = true
  try {
    const kbName = form.value.soul_name.startsWith('soul-') ? form.value.soul_name : `soul-${form.value.soul_name}`
    const kbScope = form.value.allKb ? ['*'] : (form.value.kb_scope || [])
    const r = await $fetch<any>('/api/soul/init', {
      method: 'POST',
      body: {
        name: kbName,
        description: `SOUL 人格 ${kbName}`,
        kb_scope: kbScope,
        domain_labels: form.value.domain_labels,
        supported_task_types: form.value.supported_task_types,
        harness: form.value.harness || '',
      },
    })
    const docsOk = (r?.docs_created || []).filter((d: any) => d.ok).length
    if (docsOk < 4) {
      showToast(`人格已创建但仅 ${docsOk}/4 人格文档写入，请检查模板库 soul-template`, 'err')
    } else {
      showToast(`人格 ${kbName} 已创建（4 文档 + 索引完成）`)
    }
    createOpen.value = false
    await loadAll()
  } catch (e: any) {
    showToast(`创建失败: ${e.message}`, 'err')
  } finally {
    creating.value = false
  }
}
function openEdit(soul: Soul) {
  editing.value = soul
  const med = soul.meditation || {}
  editForm.value = {
    kb_scope: soul.kb_scope || [],
    domain_labels: soul.domain_labels || [],
    supported_task_types: soul.supported_task_types || [],
    route_weight: soul.route_weight ?? 1,
    harness: med.harness || 'omp',
    model: med.model || '',
    autoTrainEnabled: !!med.enabled && med.meditation_mode === 'soul',
    intervalHours: med.interval_hours || 24,
    roundsPerRun: med.rounds_per_run || 1,
    maxBudgetUsd: med.max_budget_usd || 0.15,
    maxQuestions: med.max_questions_per_run || 10,
  }
  editOpen.value = true
}
async function doSaveConfig() {
  if (!editing.value) return
  savingConfig.value = true
  try {
    await $fetch('/api/soul/config', { method: 'PUT', body: { soul_kb_id: editing.value.kb_id, ...editForm.value } })
    await $fetch('/api/kb/meditation', { method: 'PUT', body: {
      kb_id: editing.value.kb_id,
      config: {
        harness: editForm.value.harness,
        model: editForm.value.model,
        enabled: editForm.value.autoTrainEnabled,
        meditation_mode: 'soul',
        interval_hours: editForm.value.intervalHours,
        rounds_per_run: editForm.value.roundsPerRun,
        max_budget_usd: editForm.value.maxBudgetUsd,
        max_questions_per_run: editForm.value.maxQuestions,
      },
    } })
    editOpen.value = false
    showToast('配置已保存')
    await loadAll()
  } catch (e: any) {
    showToast(`保存失败: ${e.message}`, 'err')
  } finally {
    savingConfig.value = false
  }
}
function confirmDelete(soul: Soul) {
  Modal.confirm({
    title: `删除人格 ${soul.name}?`,
    content: '将先自动保存检查点（快照保留），再删除人格库。此操作不可逆。',
    okType: 'danger',
    onOk: async () => {
      try {
        await $fetch('/api/soul/delete', { method: 'DELETE', body: { soul_kb_id: soul.kb_id } })
        showToast(`${soul.name} 已删除`)
        if (selected.value?.kb_id === soul.kb_id) selected.value = null
        await loadAll()
      } catch (e: any) { showToast(`删除失败: ${e.message}`, 'err') }
    },
  })
}

// ── 训练 ──
function openTrain(soul: Soul) {
  trainingSoul.value = soul
  trainMode.value = 'docs'
  trainForm.value = { doc_paths: [], limit: 6, dry_run: false, rounds: 1, maxDocs: 10 }
  trainResult.value = ''
  preSearchChunks.value = []
  trainOpen.value = true
  loadScopeDocs(soul)
}
async function doTrain() {
  if (!trainingSoul.value) return
  if (trainMode.value === 'docs' && !trainForm.value.doc_paths.length) { message.warning('请选择学习文档'); return }
  training.value = true
  trainResult.value = ''
  trainTaskId.value = ''
  trainTaskStatus.value = 'running'
  trainProgress.value = null
  trainError.value = ''
  eventLog.value = []
  pushLog('info', `提交${trainMode.value === 'rl' ? ' RL 强化' : ''}训练任务 → ${trainingSoul.value.name}`)
  clearInterval(trainPollTimer)
  try {
    let res: any
    if (trainMode.value === 'rl') {
      res = await $fetch<any>('/api/soul/train-rl', {
        method: 'POST',
        body: { soul_kb_id: trainingSoul.value.kb_id, rounds: trainForm.value.rounds || 1 },
      })
    } else if (trainMode.value === 'docs') {
      res = await $fetch<any>('/api/soul/learn', {
        method: 'POST',
        body: {
          soul_kb_id: trainingSoul.value.kb_id, doc_paths: trainForm.value.doc_paths,
          limit: trainForm.value.limit, rounds: trainForm.value.rounds || 1,
        },
      })
    } else {
      res = await $fetch<any>('/api/soul/train-all', {
        method: 'POST',
        body: {
          soul_kb_id: trainingSoul.value.kb_id, max_docs: trainForm.value.maxDocs || 10,
          dry_run: trainForm.value.dry_run, rounds: trainForm.value.rounds || 1,
        },
      })
    }
    if (trainForm.value.dry_run) {
      trainResult.value = JSON.stringify(res?.report || res, null, 2)
      training.value = false
      trainTaskStatus.value = ''
      return
    }
    const taskId = res?.task_id
    if (taskId) {
      trainTaskId.value = taskId
      pushLog('ok', `任务已提交 task=${taskId.slice(0, 8)} · 异步执行中`)
      pollTrainTask(taskId)
    } else {
      trainResult.value = JSON.stringify(res?.report || res, null, 2)
      training.value = false
      trainTaskStatus.value = ''
      showToast('训练完成')
      await loadAll()
    }
  } catch (e: any) {
    trainResult.value = `训练失败: ${e.message}`
    trainTaskStatus.value = 'error'
    pushLog('err', `提交失败: ${e.message}`)
    showToast('训练失败', 'err')
    training.value = false
  }
}

function pollTrainTask(taskId: string) {
  let lastProgress = ''
  clearInterval(trainPollTimer)
  trainPollTimer = setInterval(async () => {
    try {
      const st: any = await $fetch(`/api/soul/tasks/${taskId}`)
      trainTaskStatus.value = st.status
      const p = st.progress || null
      // 进度变化 → 事件流
      const sig = JSON.stringify(p)
      if (p && sig !== lastProgress) {
        lastProgress = sig
        if (p.phase === 'learn') {
          pushLog('info', `探索轮 ${p.round ?? 1}/${p.rounds ?? 1} · 问题 ${p.questions ?? 0} · 记忆 ${p.memories ?? 0} · 文档 ${p.docs_processed ?? 0}`)
        } else if (p.phase === 'reward') {
          pushLog('reward', `评价得分 ${fmtNum(p.reward)} · 生成认知草稿 ${p.drafts_created ?? 0} 条`)
        } else if (p.phase === 'scan') {
          pushLog('info', `扫描文档 ${p.scanned}/${p.total} · 去重后 ${p.unique_docs}`)
        } else if (p.processed !== undefined) {
          pushLog('info', `审批 ${p.processed}/${p.total} · 批准 ${p.approved ?? 0}`)
        }
      }
      trainProgress.value = p
      trainError.value = st.error || ''
      if (st.status === 'done') {
        clearInterval(trainPollTimer)
        const rep = st.result?.report || st.result
        trainResult.value = JSON.stringify(rep, null, 2)
        trainTaskStatus.value = 'done'
        training.value = false
        const rounds = rep?.per_round || []
        if (rounds.length) {
          for (const r of rounds) {
            pushLog('ok', `第 ${r.round} 轮完成 · reward ${fmtNum(r.reward)} · 认知草稿 ${r.cognition_drafts_created?.length ?? 0}`)
          }
        }
        pushLog('ok', '训练完成')
        showToast('训练完成')
        await loadAll()
        if (selected.value) { loadRewardHistory(selected.value); loadPersonaDocs(selected.value) }
      } else if (st.status === 'error') {
        clearInterval(trainPollTimer)
        trainResult.value = `训练失败: ${st.error || 'unknown'}`
        trainTaskStatus.value = 'error'
        training.value = false
        pushLog('err', `失败: ${st.error || 'unknown'}`)
        showToast('训练失败', 'err')
      }
    } catch { /* 轮询失败不中断 */ }
  }, 4000)
}

function trainPercent() {
  const p = trainProgress.value
  if (!p) return 0
  if (p.phase === 'scan') return Math.min(90, Math.round((p.scanned / (p.total || 1)) * 90))
  const rounds = p.rounds || 1
  if (rounds > 1 && p.round) return Math.min(99, Math.round((p.round / rounds) * 100))
  return Math.min(95, (p.docs_processed || 0) * 10 + (p.questions || 0) * 3)
}

// ── 问答 ──
function openAsk(soul?: Soul) {
  askSoul.value = soul || null
  askForm.value = { query: '', task_type: '', task_goal: '', context_override: '' }
  askResult.value = null
  preSearchChunks.value = []
  askOpen.value = true
}
async function doPreSearch() {
  if (!askForm.value.query.trim()) { message.warning('请先输入问题再检索'); return }
  searchingKb.value = true
  try {
    let kbId = ''
    const scope = (askSoul.value?.kb_scope || []).filter((s: string) => s !== '*')
    if (askSoul.value && scope.length === 1) {
      const hit = kbCatalog.value.find((kb: any) => kb.kb_id === scope[0] || kb.name === scope[0])
      kbId = hit?.kb_id || scope[0]
    }
    const res = await $fetch<any>('/api/soul/pre-search', {
      method: 'POST',
      body: { query: askForm.value.query, kb_id: kbId, top_k: 5 },
    })
    if (res?.success && res.chunks?.length) {
      preSearchChunks.value = res.chunks
      askForm.value.context_override = res.context_override
      showToast(`已检索 ${res.chunks.length} 条片段并注入上下文`)
    } else {
      preSearchChunks.value = []
      askForm.value.context_override = ''
      showToast('知识库未检索到相关片段(将诚实降级)', 'err')
    }
  } catch (e: any) {
    showToast(`检索失败: ${e.message}`, 'err')
  } finally {
    searchingKb.value = false
  }
}
async function doQdcvrAsk() {
  if (!askForm.value.query.trim()) { message.warning('请输入问题'); return }
  asking.value = true
  askResult.value = null
  try {
    let kbId = ''
    const scope = (askSoul.value?.kb_scope || []).filter((s: string) => s !== '*')
    if (askSoul.value && scope.length === 1) {
      const hit = kbCatalog.value.find((kb: any) => kb.kb_id === scope[0] || kb.name === scope[0])
      kbId = hit?.kb_id || scope[0]
    }
    const res = await $fetch<any>('/api/soul/qdcvr-ask', {
      method: 'POST',
      body: {
        query: askForm.value.query,
        soul_kb_id: askSoul.value?.kb_id || '',
        task_type: askForm.value.task_type,
        task_goal: askForm.value.task_goal,
        top_k: 5,
      },
    })
    if (res?.success === false) {
      askResult.value = { answer: `错误: ${res.error} ${res.detail || ''}` }
    } else {
      askResult.value = res
      const ev = (res as any)?.evidence_count ?? (res?.citations?.length ?? 0)
      showToast(`已检索 ${ev} 条证据并人格化回答`)
    }
  } catch (e: any) {
    askResult.value = { answer: `检索+回答失败: ${e.message}` }
  } finally {
    asking.value = false
  }
}
async function doAsk() {
  if (!askForm.value.query.trim()) { message.warning('请输入问题'); return }
  asking.value = true
  askResult.value = null
  try {
    const res = await $fetch<any>('/api/soul/ask', {
      method: 'POST',
      body: {
        query: askForm.value.query,
        soul_kb_id: askSoul.value?.kb_id || '',
        task_type: askForm.value.task_type,
        task_goal: askForm.value.task_goal,
        context_override: askForm.value.context_override,
      },
    })
    if (res?.success === false) {
      askResult.value = { answer: `错误: ${res.error} ${res.detail || ''}` }
    } else {
      askResult.value = res
    }
  } catch (e: any) {
    askResult.value = { answer: `问答失败: ${e.message}` }
  } finally {
    asking.value = false
  }
}

// ── 草稿审批 ──
const reviewType = ref<'memory' | 'cognition'>('memory')
async function reviewDrafts(soul: Soul, type: 'memory' | 'cognition' = 'memory') {
  reviewSoul.value = soul
  reviewType.value = type
  drafts.value = []
  reviewOpen.value = true
  try {
    const res = await $fetch<any>('/api/soul/review', {
      method: 'POST', body: { soul_kb_id: soul.kb_id, action: 'list', draft_type: type },
    })
    drafts.value = res?.drafts || []
  } catch (e: any) {
    showToast(`加载草稿失败: ${e.message}`, 'err')
  }
}
async function approveDraft(id: string) {
  try {
    await $fetch('/api/soul/review', { method: 'POST', body: { soul_kb_id: reviewSoul.value!.kb_id, action: 'approve', draft_id: id, draft_type: reviewType.value } })
    showToast(`已批准 ${id}`)
    await reviewDrafts(reviewSoul.value!, reviewType.value)
    await loadAll()
    if (selected.value && reviewType.value === 'cognition') loadPersonaDocs(selected.value)
  } catch (e: any) { showToast(`批准失败: ${e.message}`, 'err') }
}
async function approveAllDrafts() {
  if (!reviewSoul.value || !drafts.value.length) return
  const ids = drafts.value.map((d: any) => d.draft_id)
  reviewTaskId.value = ''
  reviewTaskStatus.value = 'running'
  reviewProgress.value = null
  reviewError.value = ''
  clearInterval(reviewPollTimer)
  try {
    const res: any = await $fetch('/api/soul/review', {
      method: 'POST',
      body: { soul_kb_id: reviewSoul.value.kb_id, action: 'approve', draft_ids: ids, draft_type: reviewType.value },
    })
    const taskId = res?.task_id
    if (!taskId) {
      showToast(`已批准 ${res?.approved?.length || 0} 条`)
      await reviewDrafts(reviewSoul.value!)
      await loadAll()
      reviewTaskStatus.value = ''
      if (selected.value && reviewType.value === 'cognition') loadPersonaDocs(selected.value)
      return
    }
    reviewTaskId.value = taskId
    pollReviewTask(taskId)
  } catch (e: any) {
    reviewTaskStatus.value = 'error'
    reviewError.value = e.message
    showToast(`批量批准失败: ${e.message}`, 'err')
  }
}
function pollReviewTask(taskId: string) {
  clearInterval(reviewPollTimer)
  reviewPollTimer = setInterval(async () => {
    try {
      const st: any = await $fetch(`/api/soul/tasks/${taskId}`)
      reviewTaskStatus.value = st.status
      reviewProgress.value = st.progress || null
      reviewError.value = st.error || ''
      if (st.status === 'done') {
        clearInterval(reviewPollTimer)
        showToast(`审批完成: ${st.result?.approved?.length || st.result?.results?.length || 0} 条`)
        await reviewDrafts(reviewSoul.value!)
        await loadAll()
        reviewTaskStatus.value = ''
        if (selected.value && reviewType.value === 'cognition') loadPersonaDocs(selected.value)
      } else if (st.status === 'error') {
        clearInterval(reviewPollTimer)
        reviewTaskStatus.value = 'error'
        reviewError.value = st.error || 'unknown'
        showToast(`审批失败: ${st.error || 'unknown'}`, 'err')
      }
    } catch { /* noop */ }
  }, 3000)
}
async function rejectDraft(id: string) {
  try {
    await $fetch('/api/soul/review', { method: 'POST', body: { soul_kb_id: reviewSoul.value!.kb_id, action: 'reject', draft_id: id, draft_type: reviewType.value } })
    showToast(`已驳回 ${id}`)
    await reviewDrafts(reviewSoul.value!, reviewType.value)
  } catch (e: any) { showToast(`驳回失败: ${e.message}`, 'err') }
}

// ── 其他动作 ──
async function doReflect(soul: Soul) {
  try {
    const res = await $fetch<any>('/api/soul/reflect', { method: 'POST', body: { soul_kb_id: soul.kb_id } })
    showToast(`反思完成: ${res?.drift_detected ? '检测到漂移' : '无漂移'} · ${res?.report_path || ''}`)
  } catch (e: any) { showToast(`反思失败: ${e.message}`, 'err') }
}
async function doCheckpoint(soul: Soul) {
  try {
    const res = await $fetch<any>('/api/soul/checkpoint', { method: 'POST', body: { soul_kb_id: soul.kb_id } })
    showToast(`检查点已保存: ${res?.checkpoint_id?.slice(0, 8) || ''}`)
  } catch (e: any) { showToast(`检查点失败: ${e.message}`, 'err') }
}
async function doExport(soul: Soul) {
  try {
    const res = await $fetch<any>('/api/soul/export', { method: 'POST', body: { soul_kb_id: soul.kb_id, min_score: 3.0 } })
    showToast(`导出完成: ${res?.record_count || 0} 条 → ${res?.export_path || ''}`)
  } catch (e: any) { showToast(`导出失败: ${e.message}`, 'err') }
}

onMounted(() => {
  loadAll()
  taskListTimer = setInterval(pollTaskList, 8000)
})
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════════
   SOUL Persona Studio — 继承项目设计系统 (theme.css 变量)
   暖象牙学者风 · 铜金强调 · JetBrains Mono 数据 · 克制阴影
   ═══════════════════════════════════════════════════════════════ */
.soul-studio {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  padding: 20px 24px 40px;
  max-width: 1560px;
  margin: 0 auto;
  gap: 18px;
}

/* ── 顶栏 ── */
.studio-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--kb-border);
}
.header-left { display: flex; align-items: center; gap: 14px; }
.header-mark {
  width: 42px; height: 42px; border-radius: 8px;
  background: var(--kb-bg-dark);
  color: var(--kb-gold-bright);
  display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--kb-border-strong);
}
.page-title { margin: 0; font-size: 21px; font-weight: 650; letter-spacing: .01em; color: var(--kb-fg); }
.page-subtitle { margin: 2px 0 0; font-size: 12.5px; color: var(--kb-fg-3); }
.header-actions { display: flex; align-items: center; gap: 10px; }
.task-live {
  font-family: 'JetBrains Mono', monospace; font-size: 12px;
  color: var(--kb-primary); display: inline-flex; align-items: center; gap: 6px;
  background: var(--kb-primary-tint); border: 1px solid var(--kb-border);
  padding: 4px 10px; border-radius: 6px;
}
.live-dot {
  width: 7px; height: 7px; border-radius: 50%; background: var(--kb-primary);
  animation: breathe 1.6s ease-in-out infinite;
}
@keyframes breathe { 0%, 100% { opacity: .35; } 50% { opacity: 1; } }

/* ── 按钮体系 ── */
.btn {
  font: inherit; font-size: 13px; cursor: pointer;
  padding: 7px 14px; border-radius: 6px;
  border: 1px solid var(--kb-border-strong);
  background: var(--kb-bg-elevated); color: var(--kb-fg);
  transition: border-color .15s, background .15s, transform .06s, box-shadow .15s;
  display: inline-flex; align-items: center; gap: 6px;
}
.btn:hover { border-color: var(--kb-primary); background: var(--kb-primary-tint); }
.btn:active { transform: translateY(1px); }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.btn-primary { background: var(--kb-bg-dark); color: var(--kb-gold-bright); border-color: var(--kb-bg-dark); }
.btn-primary:hover { background: #241f18; color: var(--kb-gold); }
.btn-copper { background: var(--kb-primary); color: #fff; border-color: var(--kb-primary); }
.btn-copper:hover { background: var(--kb-primary-hover); border-color: var(--kb-primary-hover); }
.btn-ghost { background: transparent; }
.btn-sm { padding: 5px 11px; font-size: 12.5px; }
.btn-xs { padding: 3px 8px; font-size: 11.5px; }
.btn-glyph { font-size: 13px; line-height: 1; }

/* ── 主体布局 ── */
.studio-body {
  display: grid;
  grid-template-columns: 288px 1fr;
  gap: 18px;
  align-items: start;
}

/* ── 左 rail ── */
.persona-rail {
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border);
  border-radius: 8px;
  overflow: hidden;
  position: sticky; top: 16px;
  max-height: calc(100vh - 120px);
  display: flex; flex-direction: column;
}
.rail-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 11px 14px; font-size: 12.5px; font-weight: 600;
  color: var(--kb-fg-3); letter-spacing: .04em;
  border-bottom: 1px solid var(--kb-border);
  text-transform: uppercase;
}
.rail-count {
  font-family: 'JetBrains Mono', monospace; font-size: 11px;
  background: var(--kb-gold-soft); color: var(--kb-gold-deep);
  padding: 1px 7px; border-radius: 10px;
}
.rail-loading, .rail-empty { padding: 22px 14px; font-size: 12.5px; color: var(--kb-fg-3); text-align: center; }
.rail-items { overflow-y: auto; }
.rail-item {
  padding: 11px 14px;
  border-bottom: 1px solid var(--kb-border);
  cursor: pointer;
  transition: background .15s;
  border-left: 2px solid transparent;
}
.rail-item:hover { background: var(--kb-bg-subtle); }
.rail-item.active {
  background: var(--kb-gold-soft);
  border-left-color: var(--kb-gold);
}
.rail-item-top { display: flex; align-items: center; gap: 8px; }
.state-light { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.state-light.idle { background: var(--kb-emerald); opacity: .75; }
.state-light.warn { background: var(--kb-gold); animation: breathe 2s infinite; }
.state-light.training { background: var(--kb-primary); animation: breathe 1.2s infinite; }
.rail-name { font-size: 13.5px; font-weight: 600; color: var(--kb-fg); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rail-mem { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--kb-fg-3); }
.rail-scope {
  font-size: 11.5px; color: var(--kb-fg-3); margin: 4px 0 6px 16px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.rail-meta { display: flex; gap: 5px; flex-wrap: wrap; margin-left: 16px; }
.pill {
  font-size: 10.5px; padding: 1px 7px; border-radius: 9px;
  border: 1px solid var(--kb-border);
  color: var(--kb-fg-3); background: var(--kb-bg-subtle);
}
.pill-harness { color: var(--kb-gold-deep); border-color: var(--kb-gold); }
.pill-sched { color: var(--kb-primary); border-color: var(--kb-primary); }
.pill-warn { color: var(--kb-gold-deep); background: var(--kb-gold-soft); border-color: var(--kb-gold); }
.pill-err { color: #b0442a; border-color: #d99a86; background: var(--kb-primary-soft); }

/* ── 主区 ── */
.studio-main { min-width: 0; display: flex; flex-direction: column; gap: 14px; }

/* 身份条 */
.identity-bar {
  display: flex; align-items: flex-start; gap: 16px;
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border);
  border-radius: 8px;
  padding: 16px 18px;
}
.id-avatar {
  width: 46px; height: 46px; border-radius: 8px; flex-shrink: 0;
  background: var(--kb-bg-dark);
  color: var(--kb-gold-bright);
  border: 1px solid var(--kb-border-strong);
  display: flex; align-items: center; justify-content: center;
  font-weight: 650; font-size: 16px;
}
.id-text { flex: 1; min-width: 0; }
.id-title { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.id-title h2 { margin: 0; font-size: 19px; font-weight: 650; }
.id-summary {
  margin: 5px 0 0; font-size: 12.5px; line-height: 1.55;
  color: var(--kb-fg-3);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.id-tags { display: flex; gap: 5px; flex-wrap: wrap; margin-top: 8px; }
.tag-kb, .tag-dom { font-size: 11px; padding: 1px 8px; border-radius: 4px; }
.tag-kb { background: var(--kb-cyan-soft); color: var(--kb-cyan); }
.tag-dom { background: var(--kb-gold-soft); color: var(--kb-gold-deep); }
.id-actions { display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }
.chip { font-size: 10.5px; padding: 2px 9px; border-radius: 9px; }
.chip-red { background: var(--kb-primary-soft); color: var(--kb-primary); border: 1px solid #e3b3a4; }
.chip-amber { background: var(--kb-gold-soft); color: var(--kb-gold-deep); border: 1px solid var(--kb-gold); animation: breathe 2s infinite; }

/* 监控带 */
.monitor-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 1px;
  background: var(--kb-border);
  border: 1px solid var(--kb-border);
  border-radius: 8px;
  overflow: hidden;
}
.metric-cell {
  background: var(--kb-bg-elevated);
  padding: 10px 14px;
  text-align: center;
}
.metric-val {
  display: block; font-family: 'JetBrains Mono', monospace;
  font-size: 19px; font-weight: 600; color: var(--kb-fg);
}
.metric-val.warn { color: var(--kb-primary); }
.metric-label { font-size: 10.5px; color: var(--kb-fg-3); letter-spacing: .05em; text-transform: uppercase; }
.metric-reward .metric-val { color: var(--kb-gold-deep); }

/* 工作区双栏 */
.workspace {
  display: grid;
  grid-template-columns: minmax(420px, 1.05fr) minmax(360px, .95fr);
  gap: 14px;
  align-items: start;
}
@media (max-width: 1180px) { .workspace { grid-template-columns: 1fr; } }
@media (max-width: 900px) { .studio-body { grid-template-columns: 1fr; } .persona-rail { position: static; max-height: 280px; } }

.console {
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border);
  border-radius: 8px;
  overflow: hidden;
}
.console-head {
  display: flex; align-items: baseline; gap: 10px;
  padding: 11px 16px;
  border-bottom: 1px solid var(--kb-border);
}
.console-head h3 { margin: 0; font-size: 14px; font-weight: 650; }
.console-sub { font-size: 11px; color: var(--kb-fg-3); margin-left: auto; }

/* 训练触发面板 */
.train-launch { padding: 16px; display: flex; flex-direction: column; gap: 13px; }
.mode-tabs { display: flex; gap: 4px; background: var(--kb-bg-subtle); padding: 4px; border-radius: 7px; width: fit-content; }
.mode-tab {
  font: inherit; font-size: 12.5px; cursor: pointer;
  padding: 5px 14px; border-radius: 5px;
  border: none; background: transparent; color: var(--kb-fg-3);
  transition: background .15s, color .15s;
}
.mode-tab:hover { color: var(--kb-fg); }
.mode-tab.on { background: var(--kb-bg-elevated); color: var(--kb-fg); font-weight: 600; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.mode-rl.on { color: var(--kb-primary); }
.field { display: flex; flex-direction: column; gap: 5px; flex: 1; min-width: 0; }
.field-row { display: flex; gap: 12px; }
.field-label { font-size: 11.5px; color: var(--kb-fg-3); }
.inp {
  font: inherit; font-size: 13px;
  padding: 6px 10px; border-radius: 6px;
  border: 1px solid var(--kb-border-strong);
  background: var(--kb-bg-subtle); color: var(--kb-fg);
  transition: border-color .15s;
}
.inp:focus { outline: none; border-color: var(--kb-primary); }
select.inp[multiple] { min-height: 110px; }
.check { font-size: 12.5px; color: var(--kb-fg-3); display: flex; gap: 6px; align-items: center; cursor: pointer; }
.rl-desc {
  font-size: 12.5px; line-height: 1.65; color: var(--kb-fg-3);
  margin: 0; padding: 10px 12px;
  background: var(--kb-gold-soft); border: 1px solid var(--kb-gold);
  border-radius: 6px;
}
.rl-desc b { color: var(--kb-gold-deep); }
.launch-row { display: flex; align-items: center; gap: 12px; margin-top: 2px; }
.launch-hint { font-size: 11.5px; color: var(--kb-fg-3); }

/* 训练监控 */
.train-monitor { padding: 16px; display: flex; flex-direction: column; gap: 14px; }
.phase-track { display: flex; align-items: flex-start; }
.phase { display: flex; flex-direction: column; gap: 3px; min-width: 76px; }
.phase-dot {
  width: 11px; height: 11px; border-radius: 50%;
  border: 2px solid var(--kb-border-strong);
  background: var(--kb-bg-elevated);
  transition: background .3s, border-color .3s;
}
.phase.on .phase-dot { border-color: var(--kb-primary); background: var(--kb-primary); box-shadow: 0 0 0 3px var(--kb-primary-glow); }
.phase.done .phase-dot { border-color: var(--kb-emerald); background: var(--kb-emerald); }
.phase-name { font-size: 12px; font-weight: 600; color: var(--kb-fg); }
.phase-note { font-size: 10.5px; color: var(--kb-fg-3); font-family: 'JetBrains Mono', monospace; }
.phase-conn { flex: 1; height: 2px; margin-top: 4.5px; background: var(--kb-border); transition: background .3s; }
.phase-conn.on { background: var(--kb-primary); }
.mon-line { display: flex; align-items: center; gap: 12px; }
.mon-label { font-size: 11.5px; color: var(--kb-fg-3); width: 42px; flex-shrink: 0; }
.bar { flex: 1; height: 7px; border-radius: 4px; background: var(--kb-bg-subtle); border: 1px solid var(--kb-border); overflow: hidden; }
.bar-fill {
  display: block; height: 100%; border-radius: 4px;
  background: linear-gradient(90deg, var(--kb-gold), var(--kb-primary));
  transition: width .6s ease;
  position: relative;
}
.bar-fill::after {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.35), transparent);
  animation: shimmer 1.8s infinite;
}
@keyframes shimmer { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }
.mon-pct { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--kb-fg-3); width: 40px; text-align: right; }
.mon-text { font-size: 12.5px; color: var(--kb-fg); line-height: 1.5; }
.mon-text .err { color: var(--kb-primary); }

/* RL 曲线 */
.reward-curve {
  border: 1px solid var(--kb-border);
  border-radius: 6px;
  padding: 10px 12px 6px;
  background: var(--kb-bg-subtle);
}
.curve-head { display: flex; justify-content: space-between; font-size: 11.5px; color: var(--kb-fg-3); margin-bottom: 4px; }
.curve-sub { font-family: 'JetBrains Mono', monospace; }
.curve-svg { width: 100%; height: 76px; display: block; }

/* 事件流 */
.event-log { border: 1px solid var(--kb-border); border-radius: 6px; overflow: hidden; }
.log-head {
  font-size: 11px; letter-spacing: .05em; text-transform: uppercase;
  color: var(--kb-fg-3); padding: 7px 12px;
  border-bottom: 1px solid var(--kb-border); background: var(--kb-bg-subtle);
}
.log-body { max-height: 170px; overflow-y: auto; padding: 6px 0; font-family: 'JetBrains Mono', monospace; }
.log-line { display: flex; align-items: center; gap: 8px; padding: 3px 12px; font-size: 11.5px; }
.log-time { color: var(--kb-fg-3); flex-shrink: 0; }
.log-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.log-dot.info { background: var(--kb-cyan); }
.log-dot.ok { background: var(--kb-emerald); }
.log-dot.reward { background: var(--kb-gold); }
.log-dot.err { background: var(--kb-primary); }
.log-text { color: var(--kb-fg-2); }

.train-result-box { border: 1px solid var(--kb-border); border-radius: 6px; overflow: hidden; }
.result-head2 {
  display: flex; justify-content: space-between; align-items: center;
  padding: 7px 12px; font-size: 12px; font-weight: 600;
  border-bottom: 1px solid var(--kb-border); background: var(--kb-bg-subtle);
}
.result-pre {
  margin: 0; padding: 12px; font-size: 11.5px; line-height: 1.5;
  max-height: 220px; overflow: auto; white-space: pre-wrap;
  font-family: 'JetBrains Mono', monospace; color: var(--kb-fg-2);
}

/* 人格定义查看器 */
.def-console { display: flex; flex-direction: column; min-height: 460px; }
.doc-tabs { display: flex; gap: 2px; padding: 9px 12px 0; border-bottom: 1px solid var(--kb-border); overflow-x: auto; }
.doc-tab {
  font: inherit; font-size: 11.5px; cursor: pointer;
  padding: 6px 11px; border: none; background: transparent;
  color: var(--kb-fg-3); border-bottom: 2px solid transparent;
  white-space: nowrap;
}
.doc-tab:hover { color: var(--kb-fg); }
.doc-tab.on { color: var(--kb-primary); border-bottom-color: var(--kb-primary); font-weight: 600; }
.doc-body { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.doc-meta {
  display: flex; justify-content: space-between; gap: 10px;
  font-family: 'JetBrains Mono', monospace; font-size: 10.5px;
  color: var(--kb-fg-3); padding: 7px 14px;
  border-bottom: 1px dashed var(--kb-border);
}
.doc-scroll { padding: 10px 14px 18px; overflow-y: auto; max-height: 520px; }
.doc-h {
  margin: 14px 0 7px; font-size: 13px; font-weight: 650; color: var(--kb-fg);
  padding-bottom: 4px; border-bottom: 1px solid var(--kb-border);
}
.doc-h:first-child { margin-top: 4px; }
.doc-bullet { display: flex; align-items: flex-start; gap: 7px; padding: 2.5px 0; font-size: 12.5px; line-height: 1.55; color: var(--kb-fg-2); }
.b-dot { width: 4px; height: 4px; border-radius: 50%; background: var(--kb-border-strong); margin-top: 7px; flex-shrink: 0; }
.doc-p { margin: 4px 0; font-size: 12.5px; line-height: 1.6; color: var(--kb-fg-2); }
.doc-bullet.evolved, .doc-p.evolved {
  background: var(--kb-gold-soft);
  border-radius: 3px;
  padding-left: 4px;
  outline: 1px solid var(--kb-gold);
}
.evolved-mark {
  font-size: 9px; font-weight: 700; letter-spacing: .05em;
  color: var(--kb-gold-deep); border: 1px solid var(--kb-gold);
  border-radius: 3px; padding: 0 3px; margin-left: 2px; flex-shrink: 0;
  font-family: 'JetBrains Mono', monospace;
}
.doc-empty { padding: 30px; text-align: center; font-size: 12.5px; color: var(--kb-fg-3); }

/* 空态 */
.studio-empty {
  min-height: 420px; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 8px;
  border: 1px dashed var(--kb-border-strong); border-radius: 8px;
  background: var(--kb-bg-elevated);
  text-align: center; padding: 40px;
}
.empty-symbol { color: var(--kb-gold); opacity: .75; }
.empty-title { margin: 6px 0 0; font-size: 16px; font-weight: 600; color: var(--kb-fg); }
.empty-desc { margin: 4px 0 0; font-size: 12.5px; color: var(--kb-fg-3); max-width: 420px; line-height: 1.6; }

/* Toast */
.soul-toast {
  position: fixed; bottom: 26px; right: 26px; z-index: 9999;
  padding: 11px 16px; border-radius: 7px; font-size: 13px;
  display: flex; align-items: center; gap: 12px; max-width: 440px;
  box-shadow: 0 6px 22px rgba(42, 31, 21, .22);
  border: 1px solid;
}
.soul-toast.ok { background: var(--kb-emerald-soft); border-color: var(--kb-emerald); color: #2c4a2c; }
.soul-toast.err { background: var(--kb-primary-soft); border-color: var(--kb-primary); color: var(--kb-primary); }
.toast-close { border: none; background: none; font-size: 15px; cursor: pointer; opacity: .6; color: inherit; }
.toast-fade-enter-active, .toast-fade-leave-active { transition: opacity .25s, transform .25s; }
.toast-fade-enter-from, .toast-fade-leave-to { opacity: 0; transform: translateY(8px); }

/* 复用旧类(模态内) */
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
.ask-target { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.ask-target-label { font-size: 13px; color: var(--kb-fg-3); }
.ask-route-hint { font-size: 12.5px; color: var(--kb-gold-deep); background: var(--kb-gold-soft); padding: 2px 9px; border-radius: 9px; }
.ask-hint { font-size: 12px; color: var(--kb-fg-3); margin-left: 8px; }
.ask-row { display: flex; gap: 12px; }
.ask-row .ant-form-item { flex: 1; }
.ask-result { margin-top: 16px; border-top: 1px solid var(--kb-border); padding-top: 12px; }
.result-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.result-label { font-weight: 600; }
.answer-text {
  white-space: pre-wrap; font-size: 13px; line-height: 1.7;
  background: var(--kb-bg-subtle); border: 1px solid var(--kb-border);
  border-radius: 6px; padding: 12px;
  max-height: 320px; overflow-y: auto;
}
.cite-list { margin-top: 10px; }
.cite-title { font-size: 12px; color: var(--kb-fg-3); margin-bottom: 6px; }
.cite-item { display: flex; justify-content: space-between; gap: 8px; font-size: 12px; padding: 3px 0; }
.cite-path { color: var(--kb-fg-3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cite-score { color: var(--kb-gold-deep); flex-shrink: 0; font-family: 'JetBrains Mono', monospace; }
.pre-search-list {
  margin-top: 8px; padding: 8px 10px;
  border: 1px dashed var(--kb-border-strong); border-radius: 6px;
  max-height: 140px; overflow-y: auto;
  background: var(--kb-bg-subtle);
}
.score-cell {
  display: inline-block; margin-right: 4px;
  background: var(--kb-emerald-soft); color: var(--kb-emerald);
  padding: 1px 5px; border-radius: 4px; font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
}
.score-cell.low { background: var(--kb-primary-soft); color: var(--kb-primary); }
.ml-4 { margin-left: 4px; }

:global([data-theme='dark']) .btn-primary { background: var(--kb-gold); color: #1a1612; }
:global([data-theme='dark']) .btn-primary:hover { background: var(--kb-gold-bright); }
:global([data-theme='dark']) .soul-toast.ok { background: #162312; border-color: #274916; color: #95de64; }
:global([data-theme='dark']) .soul-toast.err { background: #2a1215; border-color: #58181c; color: #ff7875; }
</style>
