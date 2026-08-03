<template>
  <div class="soul-page">
    <!-- Header -->
    <header class="page-header">
      <div class="header-content">
        <div class="header-left">
          <div class="header-icon"><RobotOutlined /></div>
          <div>
            <h1 class="page-title">SOUL 人格管理</h1>
            <p class="page-subtitle">人格生命周期 · 好奇心训练 · 检索增强问答 — 全部可视化触发</p>
          </div>
        </div>
        <div class="header-actions">
          <a-button type="primary" @click="openCreate">
            <PlusOutlined /> 创建人格
          </a-button>
          <a-button @click="loadAll" :loading="loadingList">
            <ReloadOutlined /> 刷新
          </a-button>
        </div>
      </div>
    </header>

    <!-- 人格卡片列表 -->
    <div v-if="souls.length === 0 && !loadingList" class="empty-state">
      <EmptyState icon="robot" title="暂无 SOUL 人格" desc="点击「创建人格」从模板初始化第一个灵魂" />
    </div>

    <div class="soul-grid">
      <div v-for="soul in souls" :key="soul.kb_id" class="soul-card" :class="{ 'is-training': soul._training }">
        <!-- 卡片头 -->
        <div class="card-head">
          <div class="soul-avatar">{{ soulAvatar(soul.name) }}</div>
          <div class="soul-id">
            <h3 class="soul-name">{{ soul.name }}</h3>
            <span class="soul-tag" :class="soul.is_template ? 'tag-template' : 'tag-active'">
              {{ soul.is_template ? '模板' : '人格' }}
            </span>
          </div>
          <a-dropdown>
            <a-button size="small" type="text"><MoreOutlined /></a-button>
            <template #overlay>
              <a-menu>
                <a-menu-item @click="openEdit(soul)"><SettingOutlined /> 配置</a-menu-item>
                <a-menu-item @click="openAsk(soul)"><MessageOutlined /> 人格问答</a-menu-item>
                <a-menu-item @click="openTrain(soul)"><ExperimentOutlined /> 训练</a-menu-item>
                <a-menu-item @click="reviewDrafts(soul)"><AuditOutlined /> 审批草稿</a-menu-item>
                <a-menu-item @click="doReflect(soul)"><SyncOutlined /> 反思</a-menu-item>
                <a-menu-item @click="doCheckpoint(soul)"><CameraOutlined /> 检查点</a-menu-item>
                <a-menu-item @click="doExport(soul)"><ExportOutlined /> 导出数据</a-menu-item>
                <a-menu-item v-if="!soul.is_template" danger @click="confirmDelete(soul)"><DeleteOutlined /> 删除人格</a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>

        <!-- 学习范围 -->
        <div class="card-scope">
          <span class="scope-label">学习范围</span>
          <div class="scope-tags">
            <a-tag v-for="s in soul.kb_scope || []" :key="s" color="blue">{{ s }}</a-tag>
            <a-tag v-if="!soul.kb_scope || soul.kb_scope.length === 0" color="orange">空(仅问答)</a-tag>
          </div>
        </div>
        <!-- 引擎与定时状态 -->
        <div class="card-scope">
          <span class="scope-label">引擎</span>
          <div class="scope-tags">
            <a-tag :color="(soul.meditation?.harness || 'omp') === 'claude' ? 'gold' : 'green'">{{ soul.meditation?.harness || 'omp' }}</a-tag>
            <a-tag v-if="soul.meditation?.model" color="cyan">{{ soul.meditation.model }}</a-tag>
            <a-tag v-if="soul.meditation?.enabled && soul.meditation?.meditation_mode === 'soul'" color="red">自动训练 {{ soul.meditation.interval_hours }}h × {{ soul.meditation.rounds_per_run }}轮</a-tag>
            <a-tag v-else color="default">未启用自动训练</a-tag>
          </div>
        </div>
        <div class="card-scope">
          <span class="scope-label">领域标签</span>
          <div class="scope-tags">
            <a-tag v-for="d in soul.domain_labels || []" :key="d" color="purple">{{ d }}</a-tag>
            <span v-if="!soul.domain_labels || soul.domain_labels.length === 0" class="muted">—</span>
          </div>
        </div>

        <!-- 摘要 -->
        <div class="card-summary" :title="soul.summary">{{ soul.summary || '暂无摘要' }}</div>

        <!-- 指标 -->
        <div class="card-metrics" v-if="soul._status">
          <div class="metric" v-if="soul._status.total_memories !== undefined">
            <span class="metric-val">{{ soul._status.total_memories }}</span><span class="metric-label">记忆</span>
          </div>
          <div class="metric" v-if="soul._status.drafts_pending_review !== undefined">
            <span class="metric-val" :class="{ warn: soul._status.drafts_pending_review > 0 }">{{ soul._status.drafts_pending_review }}</span><span class="metric-label">待审</span>
          </div>
          <div class="metric" v-if="soul._status.total_gaps !== undefined">
            <span class="metric-val">{{ soul._status.total_gaps }}</span><span class="metric-label">缺口</span>
          </div>
          <div class="metric" v-if="soul._status.mastery?.avg_score !== undefined">
            <span class="metric-val">{{ soul._status.mastery.avg_score.toFixed(1) }}</span><span class="metric-label">掌握分</span>
          </div>
          <div class="metric" v-if="soul._status.estimated_cost_usd !== undefined">
            <span class="metric-val" :class="{ warn: soul._status.estimated_cost_usd > 0.12 }">${{ soul._status.estimated_cost_usd.toFixed(2) }}</span><span class="metric-label">成本</span>
          </div>
          <div class="metric" v-if="soul._status.judge_divergence_count !== undefined">
            <span class="metric-val" :class="{ warn: soul._status.judge_divergence_count > 0 }">{{ soul._status.judge_divergence_count }}</span><span class="metric-label">分歧</span>
          </div>
        </div>

        <!-- 训练动画 -->
        <div v-if="soul._training" class="training-bar">
          <a-spin size="small" />
          <span>训练中… {{ soul._trainingMsg || '' }}</span>
        </div>

        <!-- 快速动作 -->
        <div class="card-actions">
          <a-button size="small" type="primary" ghost @click="openAsk(soul)"><MessageOutlined /> 提问</a-button>
          <a-button size="small" @click="openTrain(soul)"><ExperimentOutlined /> 训练</a-button>
          <a-button size="small" @click="reviewDrafts(soul)" :disabled="!(soul._status?.drafts_pending_review)"><AuditOutlined /> 审批({{ soul._status?.drafts_pending_review || 0 }})</a-button>
        </div>
      </div>
    </div>

    <!-- ═══════════ 创建人格 Modal ═══════════ -->
    <a-modal v-model:open="createOpen" title="创建新人格" :footer="null" width="620">
      <a-form layout="vertical">
        <a-form-item label="人格名称(soul- 前缀)">
          <a-input v-model:value="form.soul_name" placeholder="如 soul-材料学" />
        </a-form-item>
        <a-form-item label="学习范围 kb_scope(公开库,可多选;空=仅问答)">
          <a-checkbox v-model:value="form.allKb">全部知识库参与(默认, kb_scope=["*"])</a-checkbox>
          <a-select v-model:value="form.kb_scope" mode="multiple" placeholder="选择知识库" style="width:100%; margin-top:6px" :disabled="form.allKb">
            <a-select-option v-for="kb in kbCatalog" :key="kb.kb_id" :value="kb.kb_id">{{ kb.name }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="领域标签 domain_labels(路由匹配)">
          <a-select v-model:value="form.domain_labels" mode="tags" placeholder="如 材料科学 / 机器学习" style="width:100%" />
        </a-form-item>
        <a-form-item label="任务类型 supported_task_types">
          <a-select v-model:value="form.supported_task_types" mode="tags" placeholder="如 文献综述 / 技术选型" style="width:100%" />
        </a-form-item>
        <a-form-item :label="`训练 harness(默认 ${defaultHarness || 'omp'},可单独指定)`">
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
        <a-form-item label="人格">
          <a-input :value="editing.name" disabled />
        </a-form-item>
        <a-form-item label="学习范围">
          <a-select v-model:value="editForm.kb_scope" mode="multiple" style="width:100%">
            <a-select-option v-for="kb in kbCatalog" :key="kb.kb_id" :value="kb.kb_id">{{ kb.name }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="领域标签">
          <a-select v-model:value="editForm.domain_labels" mode="tags" style="width:100%" />
        </a-form-item>
        <a-form-item label="任务类型">
          <a-select v-model:value="editForm.supported_task_types" mode="tags" style="width:100%" />
        </a-form-item>
        <a-form-item label="路由权重(0=退出路由)">
          <a-slider v-model:value="editForm.route_weight" :min="0" :max="2" :step="0.1" />
        </a-form-item>
        <a-divider style="margin:8px 0">训练引擎(per-SOUL, 覆盖全局默认)</a-divider>
        <a-form-item label="harness(训练/冥想引擎)">
          <a-select v-model:value="editForm.harness" style="width:100%">
            <a-select-option value="omp">omp</a-select-option>
            <a-select-option value="claude">claude</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="模型(空=引擎默认)">
          <a-input v-model:value="editForm.model" placeholder="如 deepseek/deepseek-v4-flash" />
        </a-form-item>
        <a-divider style="margin:8px 0">自动训练(定时调度)</a-divider>
        <a-form-item label="启用定时自动训练">
          <a-switch v-model:value="editForm.autoTrainEnabled" />
        </a-form-item>
        <div class="ask-row">
          <a-form-item label="间隔(小时)">
            <a-input-number v-model:value="editForm.intervalHours" :min="1" :max="720" />
          </a-form-item>
          <a-form-item label="每轮固定轮数">
            <a-input-number v-model:value="editForm.roundsPerRun" :min="1" :max="20" />
          </a-form-item>
          <a-form-item label="每轮预算($)">
            <a-input-number v-model:value="editForm.maxBudgetUsd" :min="0.01" :max="2" :step="0.05" />
          </a-form-item>
        </div>
        <a-form-item label="每轮问题上限">
          <a-input-number v-model:value="editForm.maxQuestions" :min="1" :max="20" />
        </a-form-item>
        <div class="modal-actions">
          <a-button @click="editOpen = false">取消</a-button>
          <a-button type="primary" :loading="savingConfig" @click="doSaveConfig">保存</a-button>
        </div>
      </a-form>
    </a-modal>

    <!-- ═══════════ 训练 Modal ═══════════ -->
    <a-modal v-model:open="trainOpen" title="人格训练" :footer="null" width="680">
      <a-form layout="vertical" v-if="trainingSoul">
        <div class="train-target">
          <span class="train-label">目标人格</span>
          <a-tag color="purple">{{ trainingSoul.name }}</a-tag>
          <span class="train-hint">好奇心引擎: 自动生成四层问题(事实/概念/跨文档/挑战) → 检索自答 → 四维自评 → 蒸馏</span>
        </div>

        <!-- 模式: 单文档 / 全库 -->
        <a-radio-group v-model:value="trainMode" class="train-mode">
          <a-radio-button value="docs">指定文档</a-radio-button>
          <a-radio-button value="all">全库自举(增量)</a-radio-button>
        </a-radio-group>

        <template v-if="trainMode === 'docs'">
          <a-form-item label="学习文档(按 kb_scope 内文档, 可多选)">
            <a-select v-model:value="trainForm.doc_paths" mode="multiple" style="width:100%" placeholder="选择文档" :loading="loadingDocs">
              <a-select-option v-for="d in docOptions" :key="d.path" :value="d.path">{{ d.path }}</a-select-option>
            </a-select>
          </a-form-item>
          <div class="ask-row">
            <a-form-item label="每文档问题上限">
              <a-input-number v-model:value="trainForm.limit" :min="1" :max="10" />
            </a-form-item>
            <a-form-item label="固定训练轮数 rounds">
              <a-input-number v-model:value="trainForm.rounds" :min="1" :max="20" />
              <div class="train-hint">每轮独立预算, 学一批增量文档; 全部学完后自动停止</div>
            </a-form-item>
          </div>
        </template>
        <template v-else>
          <a-form-item label="单人格全库自举(空=所有人格)">
            <a-alert type="info" show-icon message="按 learned_hash 增量学习: 已学文档跳过,内容变更自动重学" />
          </a-form-item>
          <div class="ask-row">
            <a-form-item label="固定训练轮数 rounds">
              <a-input-number v-model:value="trainForm.rounds" :min="1" :max="20" />
              <div class="train-hint">每轮学一批增量文档(每轮≤30 次 LLM 调用), 直到轮数用完或全部学完</div>
            </a-form-item>
            <a-form-item label="每轮文档数上限">
              <a-input-number v-model:value="trainForm.maxDocs" :min="1" :max="50" />
            </a-form-item>
          </div>
          <a-checkbox v-model:value="trainForm.dry_run">仅估算(dry-run,不执行)</a-checkbox>
        </template>

        <div class="modal-actions">
          <a-button @click="trainOpen = false">取消</a-button>
          <a-button type="primary" :loading="training" @click="doTrain">开始训练</a-button>
        </div>
        <div v-if="trainResult" class="train-result">
          <h4>训练结果</h4>
          <pre>{{ trainResult }}</pre>
        </div>
      </a-form>
    </a-modal>

    <!-- ═══════════ 问答 Modal ═══════════ -->
    <a-modal v-model:open="askOpen" title="SOUL 人格问答(检索增强)" :footer="null" width="720">
      <div v-if="askSoul">
        <div class="ask-target">
          <span class="train-label">人格</span>
          <a-tag v-if="askSoul.name" color="purple">{{ askSoul.name }}</a-tag>
          <a-tag v-else color="green">自动路由(不指定)</a-tag>
          <span class="ask-hint">soul_kb_id 为空时按任务类型自动匹配最适人格</span>
        </div>
        <a-form layout="vertical">
          <a-form-item label="问题">
            <a-textarea v-model:value="askForm.query" :rows="3" placeholder="输入问题…" />
          </a-form-item>
          <div class="ask-row">
            <a-form-item label="任务类型 task_type">
              <a-input v-model:value="askForm.task_type" placeholder="如 文献综述" />
            </a-form-item>
            <a-form-item label="任务目标 task_goal">
              <a-input v-model:value="askForm.task_goal" placeholder="如 研究 / 教学" />
            </a-form-item>
          </div>
          <a-form-item label="临时背景 context_override(可选,仅本次生效)">
            <a-textarea v-model:value="askForm.context_override" :rows="2" placeholder="注入检索到的片段,人格基于此加工" />
          </a-form-item>
          <div class="ask-row">
            <a-button :loading="searchingKb" @click="doPreSearch"><SearchOutlined /> 先检索知识库(填充上下文)</a-button>
            <a-button type="primary" ghost :loading="asking" @click="doQdcvrAsk"><RobotOutlined /> 一键检索+人格回答</a-button>
            <span v-if="preSearchChunks.length" class="train-hint">已检索 {{ preSearchChunks.length }} 条片段(score≥0.35), 已注入 context_override</span>
          </div>
          <div v-if="preSearchChunks.length" class="pre-search-list">
            <div v-for="(c, i) in preSearchChunks" :key="i" class="cite-item">
              <span class="cite-path">{{ c.path }}</span>
              <span class="cite-score">{{ c.score?.toFixed?.(3) ?? c.score }}</span>
            </div>
          </div>
          <div class="modal-actions">
            <a-button @click="askOpen = false">关闭</a-button>
            <a-button type="primary" :loading="asking" @click="doAsk">提问</a-button>
          </div>
        </a-form>

        <!-- 回答展示 -->
        <div v-if="askResult" class="ask-result">
          <div class="result-head">
            <span class="result-label">回答</span>
            <a-tag v-if="askResult.selected_soul" color="green">路由: {{ soulName(askResult.selected_soul) }}</a-tag>
            <a-tag v-if="askResult.route_confidence !== undefined && askResult.route_confidence !== null" :color="askResult.route_confidence >= 0.6 ? 'green' : 'orange'">置信 {{ askResult.route_confidence }}</a-tag>
            <a-tag v-if="askResult.pas_score !== undefined && askResult.pas_score !== null" :color="askResult.pas_score >= 3 ? 'cyan' : 'red'">PAS {{ askResult.pas_score }}</a-tag>
          </div>
          <div class="answer-text">{{ askResult.answer }}</div>
          <div v-if="askResult.citations && askResult.citations.length" class="cite-list">
            <div class="cite-title">引用({{ askResult.citations.length }})</div>
            <div v-for="(c, i) in askResult.citations" :key="i" class="cite-item">
              <span class="cite-path">{{ c.path }}</span>
              <span class="cite-score">{{ c.score?.toFixed?.(3) ?? c.score }}</span>
            </div>
          </div>
        </div>
      </div>
    </a-modal>

    <!-- ═══════════ 草稿审批 Modal ═══════════ -->
    <a-modal v-model:open="reviewOpen" title="记忆草稿审批" :footer="null" width="760">
      <div v-if="reviewSoul">
        <div class="ask-target"><span class="train-label">人格</span><a-tag color="purple">{{ reviewSoul.name }}</a-tag></div>
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

    <!-- ═══════════ 操作反馈 Toast ═══════════ -->
    <div v-if="toast" class="soul-toast" :class="toastType">
      <span>{{ toast }}</span>
      <a-button size="small" type="text" @click="toast = ''">×</a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import {
  RobotOutlined, PlusOutlined, ReloadOutlined, MoreOutlined, SettingOutlined,
  MessageOutlined, ExperimentOutlined, AuditOutlined, SyncOutlined,
  CameraOutlined, ExportOutlined, DeleteOutlined, SearchOutlined,
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'

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

// 系统级设置(默认 harness)
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
const trainMode = ref<'docs' | 'all'>('docs')
const trainForm = ref({ doc_paths: [] as string[], limit: 6, dry_run: false, rounds: 1, maxDocs: 10 })
const trainResult = ref('')
const askSoul = ref<Soul | null>(null)
const askForm = ref({ query: '', task_type: '', task_goal: '', context_override: '' })
const askResult = ref<any>(null)
const reviewSoul = ref<Soul | null>(null)
const drafts = ref<any[]>([])
const draftColumns = [
  { title: '问题', dataIndex: 'question', key: 'question', ellipsis: true },
  { title: 'G/C/C/I', key: 'scores', width: 110 },
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
function showToast(msg: string, type: 'ok' | 'err' = 'ok') {
  toast.value = msg
  toastType.value = type
  setTimeout(() => { if (toast.value === msg) toast.value = '' }, 5000)
}

// ── 数据加载 ──
async function loadAll() {
  loadingList.value = true
  try {
    const list = await $fetch<any>('/api/soul/list')
    souls.value = (list || []).map((s: Soul) => ({ ...s }))
    await Promise.all(souls.value.map(async (s) => {
      try { s._status = await $fetch<any>(`/api/soul/status?soul_kb_id=${encodeURIComponent(s.kb_id)}`) } catch { /* noop */ }
    }))
    // 知识库目录(供 scope 选择)
    try {
      const cat = await $fetch<any>('/api/kb/catalog')
      kbCatalog.value = cat?.knowledgeBases || []
    } catch { /* noop */ }
    // SOUL 系统设置(默认 harness)
    try {
      soulSettings.value = await $fetch<any>('/api/soul/settings')
    } catch { /* noop */ }
  } catch (e: any) {
    showToast(`加载失败: ${e.message}`, 'err')
  } finally {
    loadingList.value = false
  }
}

// 加载某人格 scope 内的全部文档(供训练选择)
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

// ── CRUD ──
function openCreate() {
  form.value = { soul_name: '', kb_scope: [], domain_labels: [], supported_task_types: [], harness: '', allKb: true }
  createOpen.value = true
}
async function doCreate() {
  if (!form.value.soul_name.trim()) { message.warning('请输入人格名称'); return }
  creating.value = true
  try {
    // 经 kb-mcp 编排: 后端 /init 兼容;实际建库走 web kb create + bootstrap
    const kbName = form.value.soul_name.startsWith('soul-') ? form.value.soul_name : `soul-${form.value.soul_name}`
    const kb = await $fetch<any>('/api/kb/create', {
      method: 'POST',
      body: { name: kbName, description: `SOUL 人格 ${kbName}` },
    })
    const kbId = kb?.knowledgeBase?.id || kbName
    const kbScope = form.value.allKb ? ['*'] : (form.value.kb_scope || [])
    await $fetch<any>('/api/v1/soul/bootstrap', { baseURL: useRuntimeConfig().public.backendUrl as any || '', method: 'POST', body: {
      soul_kb_id: kbId,
      kb_scope: kbScope,
      domain_labels: form.value.domain_labels,
      supported_task_types: form.value.supported_task_types,
      harness: form.value.harness || '',
      model: '',
    } }).catch(() => { /* bootstrap 可能经 MCP;忽略 */ })
    createOpen.value = false
    showToast(`人格 ${kbName} 已创建`)
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
    // soul-config 层(scope/标签/任务/权重)
    await $fetch('/api/soul/config', { method: 'PUT', body: { soul_kb_id: editing.value.kb_id, ...editForm.value } })
    // meditation 层(harness/model/定时训练) — 合并语义,不丢 SOUL 字段
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
  modal.confirm({
    title: `删除人格 ${soul.name}?`,
    content: '将先自动保存检查点(快照保留),再删除人格库。此操作不可逆。',
    okType: 'danger',
    onOk: async () => {
      try {
        await $fetch('/api/soul/delete', { method: 'DELETE', body: { soul_kb_id: soul.kb_id } })
        showToast(`${soul.name} 已删除`)
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
  training.value = true
  trainResult.value = ''
  try {
    if (trainMode.value === 'docs') {
      if (!trainForm.value.doc_paths.length) { message.warning('请选择学习文档'); return }
      const res = await $fetch<any>('/api/soul/learn', {
        method: 'POST',
        body: {
          soul_kb_id: trainingSoul.value.kb_id, doc_paths: trainForm.value.doc_paths,
          limit: trainForm.value.limit, rounds: trainForm.value.rounds || 1,
        },
      })
      trainResult.value = JSON.stringify(res?.report || res, null, 2)
    } else {
      const res = await $fetch<any>('/api/soul/train-all', {
        method: 'POST',
        body: {
          soul_kb_id: trainingSoul.value.kb_id, max_docs: trainForm.value.maxDocs || 10,
          dry_run: trainForm.value.dry_run, rounds: trainForm.value.rounds || 1,
        },
      })
      trainResult.value = JSON.stringify(res?.report || res, null, 2)
    }
    showToast('训练完成')
    await loadAll()
  } catch (e: any) {
    trainResult.value = `训练失败: ${e.message}`
    showToast('训练失败', 'err')
  } finally {
    training.value = false
  }
}

// ── 问答 ──
function openAsk(soul?: Soul) {
  askSoul.value = soul || null  // null = 自动路由
  askForm.value = { query: '', task_type: '', task_goal: '', context_override: '' }
  askResult.value = null
  preSearchChunks.value = []
  askOpen.value = true
}
async function doPreSearch() {
  if (!askForm.value.query.trim()) { message.warning('请先输入问题再检索'); return }
  searchingKb.value = true
  try {
    // 检索范围: 显式人格时优先其 kb_scope(单库则限定该库, 多库/全库/自动路由则全库)
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
    // 一键 QDCVR+SOUL: 后端先检索(两阶段+阈值+去重)再注入人格合成
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
      // 浏览器 fetch 无 timeout 选项;Nitro 代理端已设 300s 超时
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
async function reviewDrafts(soul: Soul) {
  reviewSoul.value = soul
  drafts.value = []
  reviewOpen.value = true
  try {
    const res = await $fetch<any>('/api/soul/review', {
      method: 'POST', body: { soul_kb_id: soul.kb_id, action: 'list', draft_type: 'memory' },
    })
    drafts.value = res?.drafts || []
  } catch (e: any) {
    showToast(`加载草稿失败: ${e.message}`, 'err')
  }
}
async function approveDraft(id: string) {
  try {
    await $fetch('/api/soul/review', { method: 'POST', body: { soul_kb_id: reviewSoul.value!.kb_id, action: 'approve', draft_id: id } })
    showToast(`已批准 ${id}`)
    await reviewDrafts(reviewSoul.value!)
    await loadAll()
  } catch (e: any) { showToast(`批准失败: ${e.message}`, 'err') }
}
async function rejectDraft(id: string) {
  try {
    await $fetch('/api/soul/review', { method: 'POST', body: { soul_kb_id: reviewSoul.value!.kb_id, action: 'reject', draft_id: id } })
    showToast(`已驳回 ${id}`)
    await reviewDrafts(reviewSoul.value!)
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

onMounted(loadAll)
</script>

<style scoped>
.soul-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  color: var(--kb-ink);
}
.page-header .header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.header-icon {
  width: 44px; height: 44px; border-radius: 10px;
  background: linear-gradient(135deg, var(--kb-gold, #b8860b), var(--kb-copper, #a0522d));
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 22px;
}
.page-title { margin: 0; font-size: 22px; color: var(--kb-ink); }
.page-subtitle { margin: 2px 0 0; font-size: 13px; color: var(--kb-ink-dim); }
.header-actions { display: flex; gap: 8px; }

.soul-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}
.soul-card {
  background: var(--kb-surface);
  border: 1px solid var(--kb-border);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
  transition: transform .15s, box-shadow .15s;
}
.soul-card:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0,0,0,.1); }
.soul-card.is-training { border-color: var(--kb-gold, #b8860b); }

.card-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.soul-avatar {
  width: 38px; height: 38px; border-radius: 50%;
  background: linear-gradient(135deg, var(--kb-gold, #b8860b), var(--kb-copper, #a0522d));
  color: #fff; display: flex; align-items: center; justify-content: center;
  font-weight: 600; flex-shrink: 0;
}
.soul-id { flex: 1; display: flex; align-items: center; gap: 8px; }
.soul-name { margin: 0; font-size: 16px; }
.soul-tag { font-size: 11px; padding: 2px 8px; border-radius: 10px; }
.tag-active { background: rgba(82,196,26,.15); color: #52c41a; }
.tag-template { background: rgba(250,173,20,.15); color: #faad14; }

.card-scope { display: flex; align-items: flex-start; gap: 8px; margin-bottom: 6px; }
.scope-label { font-size: 12px; color: var(--kb-ink-dim); flex-shrink: 0; padding-top: 2px; }
.scope-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.muted { color: var(--kb-ink-dim); font-size: 12px; }

.card-summary {
  font-size: 12px; color: var(--kb-ink-dim);
  margin: 8px 0; line-height: 1.5;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}

.card-metrics { display: flex; gap: 14px; margin: 10px 0; padding: 10px 0; border-top: 1px dashed var(--kb-border); border-bottom: 1px dashed var(--kb-border); }
.metric { text-align: center; flex: 1; }
.metric-val { display: block; font-size: 18px; font-weight: 600; }
.metric-val.warn { color: #fa541c; }
.metric-label { font-size: 11px; color: var(--kb-ink-dim); }

.training-bar {
  display: flex; align-items: center; gap: 8px;
  background: rgba(184,134,11,.1); border-radius: 6px;
  padding: 6px 10px; font-size: 12px; margin-bottom: 10px;
}
.card-actions { display: flex; gap: 6px; }
.ml-4 { margin-left: 4px; }

.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
.train-target, .ask-target { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.train-label { font-size: 13px; color: var(--kb-ink-dim); }
.train-hint, .ask-hint { font-size: 12px; color: var(--kb-ink-dim); margin-left: 8px; }
.train-mode { margin-bottom: 14px; }
.ask-row { display: flex; gap: 12px; }
.ask-row .ant-form-item { flex: 1; }

.ask-result { margin-top: 16px; border-top: 1px solid var(--kb-border); padding-top: 12px; }
.result-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.result-label { font-weight: 600; }
.answer-text {
  white-space: pre-wrap; font-size: 13px; line-height: 1.7;
  background: var(--kb-surface-2); border-radius: 8px; padding: 12px;
  max-height: 300px; overflow-y: auto;
}
.cite-list { margin-top: 10px; }
.cite-title { font-size: 12px; color: var(--kb-ink-dim); margin-bottom: 6px; }
.cite-item { display: flex; justify-content: space-between; gap: 8px; font-size: 12px; padding: 3px 0; }
.cite-path { color: var(--kb-ink-dim); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cite-score { color: var(--kb-gold, #b8860b); flex-shrink: 0; }

.pre-search-list {
  margin-top: 8px;
  padding: 8px 10px;
  border: 1px dashed var(--kb-border, #d9d9d9);
  border-radius: 6px;
  max-height: 140px;
  overflow-y: auto;
  background: rgba(0, 0, 0, 0.02);
}
.train-hint { font-size: 12px; color: var(--kb-ink-dim, #888); margin-top: 2px; }
.card-scope { margin-top: 6px; }

.score-cell { display: inline-block; margin-right: 4px; background: rgba(82,196,26,.12); padding: 1px 5px; border-radius: 4px; font-size: 12px; }
.score-cell.low { background: rgba(245,34,45,.12); color: #f5222d; }

.train-result { margin-top: 12px; }
.train-result h4 { margin: 8px 0; font-size: 13px; }
.train-result pre {
  background: var(--kb-surface-2); border-radius: 8px; padding: 10px;
  font-size: 12px; max-height: 220px; overflow: auto; white-space: pre-wrap;
}

.soul-toast {
  position: fixed; bottom: 24px; right: 24px; z-index: 9999;
  padding: 10px 16px; border-radius: 8px; font-size: 13px;
  display: flex; align-items: center; gap: 10px; max-width: 420px;
  box-shadow: 0 4px 16px rgba(0,0,0,.2);
}
.soul-toast.ok { background: #f6ffed; border: 1px solid #b7eb8f; color: #389e0d; }
.soul-toast.err { background: #fff2f0; border: 1px solid #ffa39e; color: #cf1322; }

.empty-state { text-align: center; padding: 60px 0; color: var(--kb-ink-dim); }

:global([data-theme='dark']) .soul-toast.ok { background: #162312; border-color: #274916; color: #95de64; }
:global([data-theme='dark']) .soul-toast.err { background: #2a1215; border-color: #58181c; color: #ff7875; }
:global([data-theme='dark']) .answer-text { background: #161b22; }
:global([data-theme='dark']) .train-result pre { background: #161b22; }
</style>
