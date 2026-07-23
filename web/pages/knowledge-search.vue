<template>
  <div class="kb-search-page">
    <!-- Page header -->
    <header class="page-header">
      <div class="header-content">
        <div class="header-left">
          <div class="header-icon">
            <SearchOutlined />
          </div>
          <div class="header-text">
            <h1 class="header-title">{{ $t('search.title') }}</h1>
            <p class="header-subtitle">{{ $t('search.subtitle') }}</p>
          </div>
        </div>
        <div class="header-actions">
          <a-button class="action-btn" @click="handleReindex" :loading="reindexing">
            <SyncOutlined />
            <span>{{ $t('search.rebuildIndex') }}</span>
          </a-button>
        </div>
      </div>
    </header>

    <main class="main-content">
      <!-- Search area -->
      <div class="search-card">
        <!-- Search mode selection -->
        <div class="mode-bar">
          <div class="mode-label">{{ $t('search.strategy') }}:</div>
          <a-radio-group v-model:value="searchMode" button-style="solid" size="small">
            <a-radio-button value="two-stage">{{ $t('search.twoStage') }}</a-radio-button>
            <a-radio-button value="vector">{{ $t('search.vector') }}</a-radio-button>
            <a-radio-button value="keyword">{{ $t('search.keyword') }}</a-radio-button>
          </a-radio-group>
        </div>

        <!-- Search box -->
        <div class="search-row">
          <a-input-search
            v-model:value="searchQuery"
            :placeholder="$t('search.placeholder')"
            :enter-button="$t('search.searchBtn')"
            size="large"
            class="search-input"
            @search="handleSearch"
          />
        </div>

        <!-- Advanced options -->
        <div class="options-bar">
          <div class="option-group">
            <span class="option-label">{{ $t('search.kbScope') }}:</span>
            <a-select
              v-model:value="selectedKbId"
              style="width: 220px;"
              size="small"
              :placeholder="$t('search.allKbs')"
              allow-clear
              :options="kbOptions"
            />
          </div>
          <div class="option-group">
            <span class="option-label">{{ $t('search.topK') }}:</span>
            <a-input-number v-model:value="topK" :min="1" :max="50" size="small" style="width: 80px;" />
          </div>
          <div class="option-group" v-if="searchMode === 'two-stage'">
            <span class="option-label">{{ $t('search.bm25Recall') }}:</span>
            <a-input-number v-model:value="bm25TopK" :min="5" :max="100" size="small" style="width: 80px;" />
          </div>
          <div class="option-group" v-if="!selectedKbId && searchMode !== 'keyword'">
            <a-tooltip :title="$t('search.crossKbBalance')">
              <span class="option-label">{{ $t('search.crossKbBalance') }}:</span>
            </a-tooltip>
            <a-switch
              v-model:checked="balanceKbs"
              :checked-children="$t('search.on')"
              :un-checked-children="$t('search.off')"
              size="small"
            />
          </div>
        </div>

        <!-- Quick tag filter -->
        <div class="tag-bar" v-if="allTags.length > 0">
          <span class="tag-label">{{ $t('kb.tags') }}:</span>
          <div class="tag-list">
            <a-tag
              v-for="tag in allTags.slice(0, 15)"
              :key="tag"
              :class="['quick-tag', { active: selectedTag === tag }]"
              @click="toggleTagFilter(tag)"
            >{{ tag }}</a-tag>
          </div>
        </div>
      </div>

      <!-- Results area -->
      <a-spin :spinning="loading">
        <!-- Catalog view -->
        <div v-if="view === 'catalog'">
          <div v-if="catalog.length === 0 && !loading" class="empty-state">
            <a-empty :description="$t('kb.noKb')" />
          </div>
          <div v-else class="kb-grid">
            <div
              v-for="kb in catalog"
              :key="kb.kbId"
              class="kb-card"
              @click="openKb(kb)"
            >
              <div class="kb-card-icon">
                <DatabaseOutlined />
              </div>
              <div class="kb-card-body">
                <div class="kb-card-name">{{ kb.name }}</div>
                <div class="kb-card-desc">{{ kb.description || '无描述' }}</div>
                <div class="kb-card-stat">
                  <FileTextOutlined />
                  <span>{{ kb.documentCount }} {{ $t('kb.docs') }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- KB document list (with sub-KBs) -->
        <div v-else-if="view === 'kb-docs'">
          <!-- Breadcrumb navigation -->
          <div class="breadcrumb-bar">
            <a-button type="link" size="small" @click="goBackToCatalog">
              <DatabaseOutlined />
              <span>{{ $t('search.allKbs') }}</span>
            </a-button>
            <template v-for="(histKb, hi) in kbNavHistory" :key="histKb.kbId">
              <span class="breadcrumb-sep">/</span>
              <a-button type="link" size="small" @click="navigateToKb(histKb)">{{ histKb.name }}</a-button>
            </template>
            <span class="breadcrumb-sep">/</span>
            <span class="breadcrumb-current">{{ activeKb?.name }}</span>
          </div>

          <!-- Sub-KB cards -->
          <div v-if="subKbList.length > 0" class="sub-kb-section">
            <div class="section-title">
              <DatabaseOutlined />
              <span>子知识库 ({{ subKbList.length }})</span>
            </div>
            <div class="sub-kb-grid">
              <div
                v-for="subKb in subKbList"
                :key="subKb.kbId"
                class="sub-kb-card"
                @click="openKb(subKb)"
              >
                <div class="sub-kb-card-icon">
                  <DatabaseOutlined />
                </div>
                <div class="sub-kb-card-body">
                  <div class="sub-kb-card-name">{{ subKb.name }}</div>
                  <div class="sub-kb-card-desc">{{ subKb.description || '无描述' }}</div>
                  <div class="sub-kb-card-stat">
                    <FileTextOutlined />
                    <span>{{ subKb.documentCount }} 篇文档</span>
                  </div>
                </div>
                <div class="sub-kb-card-arrow">
                  <RightOutlined />
                </div>
              </div>
            </div>
          </div>

          <!-- Document list -->
          <div v-if="kbDocuments.length > 0" class="doc-section">
            <div class="section-title">
              <FileTextOutlined />
              <span>文档 ({{ kbDocuments.length }})</span>
            </div>
            <div class="doc-list">
              <div
                v-for="doc in kbDocuments"
                :key="doc.path"
                class="doc-item"
                @click="togglePreview(doc.path)"
              >
                <div class="doc-item-main">
                  <FileTextOutlined class="doc-icon" />
                  <div class="doc-info">
                    <div class="doc-name">{{ doc.name }}</div>
                    <div class="doc-desc">{{ doc.description || '无描述' }}</div>
                  </div>
                </div>
                <div class="doc-item-side">
                  <a-tag v-if="doc.file_type" color="cyan">{{ doc.file_type }}</a-tag>
                  <div class="doc-tags-mini" v-if="doc.tags && doc.tags.length">
                    <a-tag v-for="t in doc.tags.slice(0, 3)" :key="t" color="green" size="small">{{ t }}</a-tag>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Empty state -->
          <div v-if="subKbList.length === 0 && kbDocuments.length === 0 && !loading" class="empty-state">
            <a-empty :description="$t('kb.noDocs')" />
          </div>
        </div>

        <!-- Search results -->
        <div v-else-if="view === 'results'">
          <!-- Result stats + view switch -->
          <div class="results-summary" v-if="searchResults.length > 0">
            <div class="summary-left">
              <span class="summary-count">{{ $t('search.results') }}: {{ searchResults.length }}</span>
              <a-tag :color="modeColors[searchMode]">{{ modeLabels[searchMode] }}</a-tag>
              <span class="summary-time" v-if="searchDuration > 0">耗时 {{ searchDuration }}ms</span>
            </div>
            <div class="summary-right">
              <div class="results-tab-switcher">
                <div :class="['tab-btn', { active: resultsTab === 'list' }]" @click="resultsTab = 'list'">
                  <UnorderedListOutlined /><span>列表</span>
                </div>
                <div :class="['tab-btn', { active: resultsTab === 'graph' }]" @click="resultsTab = 'graph'">
                  <ShareAltOutlined /><span>关联图谱</span>
                </div>
              </div>
              <a-switch v-model:checked="autoVerifyContent" checked-children="内容验证" un-checked-children="关闭验证" size="small" />
            </div>
          </div>

          <div v-if="searchResults.length === 0 && !loading" class="empty-state">
            <a-empty :description="$t('search.noResults')" />
          </div>

          <!-- List view -->
          <div v-show="resultsTab === 'list'" class="results-list">
            <div
              v-for="(hit, index) in searchResults"
              :key="hit.path || hit.doc_id"
              class="result-card"
            >
              <div class="result-rank">#{{ index + 1 }}</div>
              <div class="result-body">
                <div class="result-header" @click="togglePreview(hit.path)">
                  <FileTextOutlined class="result-icon" />
                  <div class="result-info">
                    <div class="result-name">{{ hit.docName || hit.doc_name }}</div>
                    <div class="result-desc">{{ hit.description || '无描述' }}</div>
                  </div>
                </div>

                <!-- Content preview snippet -->
                <div v-if="hit.content_preview" class="result-preview">
                  {{ hit.content_preview }}
                </div>

                <!-- Score info -->
                <div class="result-scores">
                  <div class="score-group" v-if="hit.combined_score !== undefined">
                    <span class="score-label">综合</span>
                    <a-progress :percent="Math.round(hit.combined_score * 100)" :stroke-color="getScoreColor(hit.combined_score)" size="small" style="width: 120px;" />
                    <span class="score-value">{{ hit.combined_score.toFixed(4) }}</span>
                  </div>
                  <div class="score-group" v-if="hit.vector_score !== undefined && searchMode !== 'keyword'">
                    <span class="score-label">向量</span>
                    <a-progress :percent="Math.round(hit.vector_score * 100)" :stroke-color="getScoreColor(hit.vector_score)" size="small" style="width: 100px;" />
                    <span class="score-value">{{ hit.vector_score.toFixed(4) }}</span>
                  </div>
                  <div class="score-group" v-if="hit.bm25_score !== undefined && searchMode === 'two-stage'">
                    <span class="score-label">BM25</span>
                    <span class="score-value">{{ hit.bm25_score.toFixed(2) }}</span>
                  </div>
                  <div class="score-group" v-if="hit.score !== undefined && searchMode !== 'two-stage'">
                    <span class="score-label">得分</span>
                    <a-progress :percent="Math.round(hit.score * 100)" :stroke-color="getScoreColor(hit.score)" size="small" style="width: 100px;" />
                    <span class="score-value">{{ hit.score.toFixed(4) }}</span>
                  </div>
                </div>

                <!-- Metadata -->
                <div class="result-meta">
                  <a-tag color="purple">{{ hit.kbName || hit.kb_name }}</a-tag>
                  <a-tag v-for="t in (hit.tags || []).slice(0, 4)" :key="t" color="green" size="small">{{ t }}</a-tag>
                  <span v-if="hit.path" class="result-path" :title="hit.path">{{ hit.path }}</span>
                </div>

                <!-- Content verification status -->
                <div v-if="autoVerifyContent && verificationMap[hit.path || hit.doc_id]" class="verify-status">
                  <CheckCircleOutlined v-if="verificationMap[hit.path || hit.doc_id]?.relevant" class="verify-pass" />
                  <WarningOutlined v-else class="verify-warn" />
                  <span>{{ verificationMap[hit.path || hit.doc_id]?.reason }}</span>
                </div>

                <!-- Graph relation button -->
                <div class="result-actions" v-if="hit.path">
                  <a-button size="small" type="link" @click="viewDocInGraph(hit.path)">
                    <ShareAltOutlined />
                    <span>查看关联图谱</span>
                  </a-button>
                </div>
              </div>
            </div>
          </div>

          <!-- Relation graph view -->
          <div v-show="resultsTab === 'graph'" class="search-graph-view">
            <div class="search-graph-layout">
              <div class="search-graph-canvas" ref="searchGraphContainerRef">
                <div class="graph-toolbar">
                  <a-tooltip title="放大"><a-button type="text" size="small" class="tool-btn" @click="searchGraphZoom = Math.min(3, searchGraphZoom * 1.2)"><ZoomInOutlined /></a-button></a-tooltip>
                  <a-tooltip title="缩小"><a-button type="text" size="small" class="tool-btn" @click="searchGraphZoom = Math.max(0.2, searchGraphZoom * 0.8)"><ZoomOutOutlined /></a-button></a-tooltip>
                  <a-tooltip title="重置"><a-button type="text" size="small" class="tool-btn" @click="searchGraphZoom = 1; searchGraphPanX = 0; searchGraphPanY = 0"><CompressOutlined /></a-button></a-tooltip>
                </div>
                <div class="graph-legend">
                  <div class="legend-item"><span class="legend-dot kb-dot"></span><span>知识库</span></div>
                  <div class="legend-item"><span class="legend-dot doc-dot"></span><span>文档</span></div>
                  <div class="legend-item"><span class="legend-dot tag-dot"></span><span>标签</span></div>
                </div>
                <svg :width="searchGraphWidth" :height="searchGraphHeight" @mousedown="onSearchGraphMouseDown" @mousemove="onSearchGraphMouseMove" @mouseup="onSearchGraphMouseUp" @mouseleave="onSearchGraphMouseUp" @wheel.prevent="onSearchGraphWheel" style="cursor: grab;">
                  <defs>
                    <radialGradient id="sgKbGrad"><stop offset="0%" stop-color="#4f7cff" /><stop offset="100%" stop-color="#2563eb" /></radialGradient>
                    <radialGradient id="sgDocGrad"><stop offset="0%" stop-color="#22d3ee" /><stop offset="100%" stop-color="#06b6d4" /></radialGradient>
                    <radialGradient id="sgTagGrad"><stop offset="0%" stop-color="#34d399" /><stop offset="100%" stop-color="#10b981" /></radialGradient>
                    <filter id="sgGlow"><feGaussianBlur stdDeviation="3" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
                  </defs>
                  <g :transform="`translate(${searchGraphPanX},${searchGraphPanY}) scale(${searchGraphZoom})`">
                    <line v-for="(edge, i) in searchGraphRenderedEdges" :key="`sge-${i}`" :x1="edge.x1" :y1="edge.y1" :x2="edge.x2" :y2="edge.y2" :stroke="edge.type === 'shared_tag' ? '#f59e0b' : edge.type === 'belongs_to' ? '#2563eb' : '#10b981'" :stroke-width="isSearchEdgeHighlighted(edge) ? 2.5 : 1" :stroke-opacity="isSearchEdgeHighlighted(edge) ? 0.8 : 0.25" :stroke-dasharray="edge.type === 'shared_tag' ? '4,3' : 'none'" />
                    <g v-for="node in searchGraphNodes" :key="node.id" :transform="`translate(${node.x},${node.y})`" style="cursor: pointer;" @click.stop="searchGraphNodeSelected = node" @mouseenter="searchGraphNodeHovered = node" @mouseleave="searchGraphNodeHovered = null">
                      <circle v-if="searchGraphNodeSelected?.id === node.id" :r="getGraphNodeRadius(node) + 8" fill="none" stroke="#2563eb" stroke-width="2" stroke-opacity="0.4" class="select-ring" />
                      <circle :r="getGraphNodeRadius(node)" :fill="getGraphNodeFill(node)" :stroke="'#fff'" :stroke-width="2" :filter="searchGraphNodeSelected?.id === node.id ? 'url(#sgGlow)' : ''" />
                      <text :y="getGraphNodeRadius(node) + 14" text-anchor="middle" :font-size="node.type === 'kb' ? '12px' : '10px'" :font-weight="node.type === 'kb' ? '700' : '500'" fill="var(--kb-fg)" style="pointer-events: none; user-select: none;">{{ node.label.length > (node.type === 'kb' ? 16 : 12) ? node.label.slice(0, node.type === 'kb' ? 16 : 12) + '…' : node.label }}</text>
                    </g>
                  </g>
                </svg>
                <div v-if="searchGraphNodes.length === 0" class="graph-empty">
                  <ShareAltOutlined style="font-size: 32px; color: var(--kb-fg-mute);" />
                  <p style="margin-top: 12px; color: var(--kb-fg-3);">先执行搜索，再查看关联图谱</p>
                </div>
              </div>
              <!-- Graph node detail -->
              <aside class="search-graph-detail" v-if="searchGraphNodeSelected">
                <div class="sgd-header">
                  <div class="sgd-icon" :class="`icon-${searchGraphNodeSelected.type}`">
                    <DatabaseOutlined v-if="searchGraphNodeSelected.type === 'kb'" />
                    <FileTextOutlined v-else-if="searchGraphNodeSelected.type === 'document'" />
                    <TagOutlined v-else />
                  </div>
                  <div>
                    <h3 class="sgd-name">{{ searchGraphNodeSelected.label }}</h3>
                    <a-tag size="small" :class="`type-tag type-${searchGraphNodeSelected.type}`">{{ searchGraphNodeSelected.type === 'kb' ? '知识库' : searchGraphNodeSelected.type === 'document' ? '文档' : '标签' }}</a-tag>
                  </div>
                </div>
                <div v-if="searchGraphNodeSelected.description" class="sgd-desc">{{ searchGraphNodeSelected.description }}</div>
                <div v-if="searchGraphNodeSelected.kb_name" class="sgd-meta"><span class="meta-label">知识库</span><span>{{ searchGraphNodeSelected.kb_name }}</span></div>
                <div v-if="searchGraphNodeSelected.path" class="sgd-meta"><span class="meta-label">路径</span><span class="mono-path">{{ searchGraphNodeSelected.path }}</span></div>
                <div v-if="searchGraphNodeSelected.score !== undefined" class="sgd-meta"><span class="meta-label">检索得分</span><span>{{ searchGraphNodeSelected.score.toFixed(4) }}</span></div>
                <div v-if="searchGraphNodeSelected.tags && searchGraphNodeSelected.tags.length" class="sgd-meta">
                  <span class="meta-label">标签</span>
                  <div class="sgd-tags"><a-tag v-for="t in searchGraphNodeSelected.tags" :key="t" color="green" size="small">{{ t }}</a-tag></div>
                </div>
                <div class="sgd-related" v-if="searchGraphRelatedNodes.length > 0">
                  <div class="sgd-related-title"><ShareAltOutlined /> 关联节点 ({{ searchGraphRelatedNodes.length }})</div>
                  <div class="sgd-related-list">
                    <div v-for="rn in searchGraphRelatedNodes" :key="rn.id" class="sgd-related-item" @click="searchGraphNodeSelected = rn">
                      <div class="sgd-related-icon" :class="`icon-${rn.type}`">
                        <DatabaseOutlined v-if="rn.type === 'kb'" />
                        <FileTextOutlined v-else-if="rn.type === 'document'" />
                        <TagOutlined v-else />
                      </div>
                      <span>{{ rn.label }}</span>
                    </div>
                  </div>
                </div>
              </aside>
              <aside class="search-graph-detail search-graph-empty" v-else>
                <ShareAltOutlined style="font-size: 32px; color: var(--kb-primary); background: var(--kb-primary-soft); width: 64px; height: 64px; border-radius: 20px; display: grid; place-items: center;" />
                <p style="font-size: 15px; color: var(--kb-fg-2); font-weight: 600; margin: 16px 0 4px;">点击图谱节点查看详情</p>
                <p style="font-size: 13px; color: var(--kb-fg-mute); margin: 0;">文档、知识库、标签的关联关系一目了然</p>
              </aside>
            </div>
          </div>
        </div>
      </a-spin>

      <!-- Document preview drawer -->
      <a-drawer
        v-model:open="previewOpen"
        :title="previewTitle"
        placement="right"
        width="680"
      >
        <a-spin :spinning="previewLoading">
          <!-- Markdown rendering for .md files -->
          <div v-if="isPreviewMarkdown" class="preview-content preview-content-md">
            <div class="markdown-body" v-html="renderedPreview"></div>
          </div>
          <!-- Plain text / code for other files -->
          <div v-else class="preview-content">
            <pre>{{ previewContent }}</pre>
          </div>
          <div v-if="previewTruncated" class="preview-more">
            <a-button :loading="previewLoading" @click="loadMorePreview">
              <DownOutlined />
              <span>{{ $t('kb.loadMore') }}</span>
            </a-button>
          </div>
        </a-spin>
      </a-drawer>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import {
  SearchOutlined, DatabaseOutlined, FileTextOutlined,
  ArrowLeftOutlined, DownOutlined, SyncOutlined,
  CheckCircleOutlined, WarningOutlined,
  ShareAltOutlined, UnorderedListOutlined, TagOutlined,
  ZoomInOutlined, ZoomOutOutlined, CompressOutlined,
  RightOutlined,
} from '@ant-design/icons-vue'
import { useKbDocuments } from '~/composables/useKbDocuments'
import { useKbAdvancedSearch } from '~/composables/useKbAdvancedSearch'
import { useKbGraph } from '~/composables/useKbGraph'
import type { SearchMode } from '~/composables/useKbAdvancedSearch'
import type { GraphData, GraphNode } from '~/composables/useKbGraph'
import { renderMarkdown } from '~/utils/markdown'
import { useMarkdownRenderer } from '~/composables/useMarkdownRenderer'
import 'katex/dist/katex.min.css'

type View = 'catalog' | 'kb-docs' | 'results'

const docManager = useKbDocuments()
const advancedSearch = useKbAdvancedSearch()
const graphComposable = useKbGraph()

const loading = ref(false)
const reindexing = ref(false)
const resultsTab = ref<'list' | 'graph'>('list')

// KB navigation breadcrumb history
const kbNavHistory = ref<any[]>([])

// Graph related
const searchGraphData = ref<GraphData>({ nodes: [], edges: [] })
const searchGraphNodes = ref<any[]>([])
const searchGraphZoom = ref(1)
const searchGraphPanX = ref(0)
const searchGraphPanY = ref(0)
const searchGraphPanning = ref(false)
const searchGraphPanStart = ref({ x: 0, y: 0, px: 0, py: 0 })
const searchGraphNodeSelected = ref<any | null>(null)
const searchGraphNodeHovered = ref<any | null>(null)
const searchGraphSvgRef = ref<SVGSVGElement | null>(null)
const searchGraphContainerRef = ref<HTMLDivElement | null>(null)
const searchGraphWidth = ref(800)
const searchGraphHeight = ref(500)
let searchGraphAnimId: number | null = null

const view = ref<View>('catalog')
const searchQuery = ref('')
const searchMode = ref<SearchMode>('two-stage')
const selectedKbId = ref<string | undefined>(undefined)
const topK = ref(10)
const bm25TopK = ref(20)
const autoVerifyContent = ref(false)
const balanceKbs = ref(true)  // 默认开启跨库均衡，防大KB主导
const selectedTag = ref<string>('')
const searchDuration = ref(0)

const catalog = ref<any[]>([])
const allTags = ref<string[]>([])
const searchResults = ref<any[]>([])
const activeKb = ref<any | null>(null)
const kbDocuments = ref<any[]>([])
const subKbList = ref<any[]>([])
const verificationMap = ref<Record<string, { relevant: boolean; reason: string }>>({})

// Preview
const previewOpen = ref(false)
const previewTitle = ref('')
const previewContent = ref('')
const previewLoading = ref(false)
const previewTruncated = ref(false)
const previewPath = ref('')
const previewOffset = ref(0)

// ── Markdown preview rendering ──
/** Detect if the previewed file is a markdown document. */
const isPreviewMarkdown = computed(() => {
  const path = (previewPath.value || '').toLowerCase()
  return path.endsWith('.md') || path.endsWith('.markdown')
})

/** Rendered markdown HTML (with syntax highlighting + KaTeX math). */
const renderedPreview = computed(() => {
  if (!isPreviewMarkdown.value || !previewContent.value) return ''
  try {
    return renderMarkdown(previewContent.value)
  } catch {
    return previewContent.value
  }
})

// ── Mermaid diagram rendering ──
const { initMermaid } = useMarkdownRenderer()

function renderPreviewMermaid() {
  nextTick(async () => {
    await nextTick()
    const el = document.querySelector('.preview-content-md .markdown-body')
    if (!el) return
    try {
      await initMermaid(el as HTMLElement)
    } catch (err) {
      console.debug('Search preview mermaid init skipped:', err)
    }
  })
}

// Trigger mermaid rendering when markdown content changes
watch([renderedPreview, previewOpen], () => {
  if (previewOpen.value && isPreviewMarkdown.value) {
    renderPreviewMermaid()
  }
})

const modeLabels: Record<SearchMode, string> = {
  'two-stage': 'BM25 + 向量',
  'vector': '向量语义',
  'keyword': 'BM25 关键词',
}
const modeColors: Record<SearchMode, string> = {
  'two-stage': 'geekblue',
  'vector': 'purple',
  'keyword': 'orange',
}

const kbOptions = computed(() => catalog.value.map(kb => ({ value: kb.kbId, label: kb.name })))

const getScoreColor = (score: number): string => {
  if (score >= 0.75) return '#10b981'
  if (score >= 0.5) return '#2563eb'
  if (score >= 0.3) return '#f59e0b'
  return '#f43f5e'
}

const showCatalog = async () => {
  goBackToCatalog()
  if (catalog.value.length === 0) {
    catalog.value = await docManager.fetchCatalog()
  }
}

const toggleTagFilter = async (tag: string) => {
  if (selectedTag.value === tag) {
    selectedTag.value = ''
  } else {
    selectedTag.value = tag
    // Search by tag
    loading.value = true
    view.value = 'results'
    searchResults.value = await advancedSearch.searchByTag(tag, selectedKbId.value)
    loading.value = false
  }
}

const handleSearch = async () => {
  const q = searchQuery.value.trim()
  if (!q) {
    view.value = 'catalog'
    return
  }
  view.value = 'results'
  resultsTab.value = 'list'
  loading.value = true
  verificationMap.value = {}
  const startTime = Date.now()
  try {
    if (searchMode.value === 'vector') {
      searchResults.value = await advancedSearch.vectorSearch(q, {
        topK: topK.value,
        kbId: selectedKbId.value || '',
        balanceKbs: balanceKbs.value,
      })
    } else if (searchMode.value === 'two-stage') {
      searchResults.value = await advancedSearch.twoStageSearch(q, {
        topK: topK.value,
        kbId: selectedKbId.value || '',
        bm25TopK: bm25TopK.value,
        balanceKbs: balanceKbs.value,
      })
    } else {
      // keyword: use BM25 keyword search first
      try {
        const res = await $fetch<{ hits: any[] }>('/api/kb/search', {
          params: { query: q, top_k: topK.value },
        })
        searchResults.value = res.hits || []
      } catch {
        searchResults.value = []
      }
      // Fall back to tag matching if keyword search returns nothing
      if (searchResults.value.length === 0) {
        searchResults.value = await docManager.searchByTag(q, selectedKbId.value)
      }
    }
    searchDuration.value = Date.now() - startTime

    // Build search results relation graph
    searchGraphData.value = graphComposable.buildGraphFromSearchResults(searchResults.value)
    initSearchGraphSimulation()

    // Auto content verification
    if (autoVerifyContent.value && searchResults.value.length > 0) {
      await verifyResults(q)
    }
  } catch (err: any) {
    message.error(err.message || '检索失败')
  } finally {
    loading.value = false
  }
}

// -- Search results graph visualization --
const initSearchGraphSimulation = () => {
  const W = searchGraphWidth.value, H = searchGraphHeight.value
  searchGraphNodes.value = searchGraphData.value.nodes.map(n => ({
    ...n,
    x: W / 2 + (Math.random() - 0.5) * 250,
    y: H / 2 + (Math.random() - 0.5) * 250,
    vx: 0, vy: 0,
  }))
  startSearchGraphSim()
}
const startSearchGraphSim = () => {
  let tick = 0
  const maxTicks = 250
  const loop = () => {
    tick++
    stepSearchGraphSim()
    if (tick > maxTicks) return
    searchGraphAnimId = requestAnimationFrame(loop)
  }
  loop()
}
const stopSearchGraphSim = () => {
  if (searchGraphAnimId) { cancelAnimationFrame(searchGraphAnimId); searchGraphAnimId = null }
}
const stepSearchGraphSim = () => {
  const nodes = searchGraphNodes.value
  const edges = searchGraphData.value.edges
  if (nodes.length === 0) return
  const alpha = 0.3, repulsion = 500, linkDist = 70, linkStr = 0.1, centerStr = 0.02
  const W = searchGraphWidth.value, H = searchGraphHeight.value
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const dx = nodes[i].x - nodes[j].x, dy = nodes[i].y - nodes[j].y
      let d = Math.sqrt(dx*dx + dy*dy); if (d < 1) d = 1
      const f = repulsion / (d*d)
      nodes[i].vx += (dx/d)*f*alpha; nodes[i].vy += (dy/d)*f*alpha
      nodes[j].vx -= (dx/d)*f*alpha; nodes[j].vy -= (dy/d)*f*alpha
    }
  }
  const nodeMap = new Map(nodes.map(n => [n.id, n]))
  for (const e of edges) {
    const s = nodeMap.get(e.source), t = nodeMap.get(e.target)
    if (!s || !t) continue
    const dx = t.x - s.x, dy = t.y - s.y
    let d = Math.sqrt(dx*dx + dy*dy); if (d < 1) d = 1
    const f = (d - linkDist) * linkStr
    s.vx += (dx/d)*f*alpha; s.vy += (dy/d)*f*alpha
    t.vx -= (dx/d)*f*alpha; t.vy -= (dy/d)*f*alpha
  }
  for (const n of nodes) {
    n.vx += (W/2 - n.x) * centerStr * alpha
    n.vy += (H/2 - n.y) * centerStr * alpha
    n.vx *= 0.85; n.vy *= 0.85
    n.x += n.vx; n.y += n.vy
    n.x = Math.max(30, Math.min(W - 30, n.x))
    n.y = Math.max(30, Math.min(H - 30, n.y))
  }
}
const searchGraphRenderedEdges = computed(() =>
  searchGraphData.value.edges.map(e => {
    const s = searchGraphNodes.value.find(n => n.id === e.source)
    const t = searchGraphNodes.value.find(n => n.id === e.target)
    return { ...e, x1: s?.x || 0, y1: s?.y || 0, x2: t?.x || 0, y2: t?.y || 0 }
  })
)
const searchGraphRelatedNodes = computed(() => {
  if (!searchGraphNodeSelected.value) return []
  const ids = new Set<string>()
  for (const e of searchGraphData.value.edges) {
    if (e.source === searchGraphNodeSelected.value.id) ids.add(e.target)
    if (e.target === searchGraphNodeSelected.value.id) ids.add(e.source)
  }
  return searchGraphNodes.value.filter(n => ids.has(n.id))
})
const getGraphNodeRadius = (node: any): number => {
  if (node.type === 'kb') return 14 + Math.min((node.doc_count || 0) / 5, 10)
  if (node.type === 'document') return 8
  return 6
}
const getGraphNodeFill = (node: any): string => {
  if (node.type === 'kb') return 'url(#sgKbGrad)'
  if (node.type === 'document') return 'url(#sgDocGrad)'
  return 'url(#sgTagGrad)'
}
const isSearchEdgeHighlighted = (edge: any): boolean => {
  const active = searchGraphNodeSelected.value || searchGraphNodeHovered.value
  if (!active) return false
  return edge.source === active.id || edge.target === active.id
}
const onSearchGraphMouseDown = (e: MouseEvent) => {
  searchGraphPanning.value = true
  searchGraphPanStart.value = { x: e.clientX, y: e.clientY, px: searchGraphPanX.value, py: searchGraphPanY.value }
}
const onSearchGraphMouseMove = (e: MouseEvent) => {
  if (!searchGraphPanning.value) return
  searchGraphPanX.value = searchGraphPanStart.value.px + (e.clientX - searchGraphPanStart.value.x)
  searchGraphPanY.value = searchGraphPanStart.value.py + (e.clientY - searchGraphPanStart.value.y)
}
const onSearchGraphMouseUp = () => { searchGraphPanning.value = false }
const onSearchGraphWheel = (e: WheelEvent) => {
  const d = e.deltaY > 0 ? 0.9 : 1.1
  searchGraphZoom.value = Math.max(0.2, Math.min(3, searchGraphZoom.value * d))
}
const viewDocInGraph = (path: string) => {
  const node = searchGraphNodes.value.find(n => n.id === `doc:${path}`)
  if (node) {
    searchGraphNodeSelected.value = node
    resultsTab.value = 'graph'
  }
}

// Content verification: read doc content, judge relevance
const verifyResults = async (query: string) => {
  const queryLower = query.toLowerCase()
  const keywords = queryLower.split(/\s+/).filter(w => w.length > 1)

  for (const hit of searchResults.value.slice(0, 5)) {
    const path = hit.path || hit.doc_id
    if (!path) continue
    try {
      const res = await docManager.readDocument(path, { limit: 50, maxChars: 5000 })
      const content = (res.content || '').toLowerCase()
      const hasKeyword = keywords.some(kw => content.includes(kw))
      const hasContent = content.length > 100

      if (hasKeyword && hasContent) {
        verificationMap.value[path] = { relevant: true, reason: '内容包含关键词，验证通过' }
      } else if (hasContent) {
        verificationMap.value[path] = { relevant: true, reason: '内容充实，语义可能相关' }
      } else {
        verificationMap.value[path] = { relevant: false, reason: '内容过短或无关键词匹配' }
      }
    } catch {
      verificationMap.value[path] = { relevant: false, reason: '无法读取文档内容' }
    }
  }
}

/** Filter out sub-KB entries from document list (they appear as file_type='knowledge-base' in YAML). */
const filterRealDocs = (docs: any[]): any[] =>
  docs.filter(d => d.file_type !== 'knowledge-base' && !(d.metadata?.isKnowledgeBase))

const openKb = async (kb: any) => {
  // Push current KB to navigation history for breadcrumb
  if (activeKb.value) {
    kbNavHistory.value.push(activeKb.value)
  }
  activeKb.value = kb
  view.value = 'kb-docs'
  loading.value = true
  // Fetch both sub-KBs and documents in parallel
  const [subKbs, docs] = await Promise.all([
    docManager.fetchSubCatalog(kb.kbId),
    docManager.fetchDocuments(kb.kbId),
  ])
  subKbList.value = subKbs
  kbDocuments.value = filterRealDocs(docs)
  loading.value = false
}

const navigateToKb = async (kb: any) => {
  // Navigate to a KB from breadcrumb — truncate history
  const idx = kbNavHistory.value.findIndex(k => k.kbId === kb.kbId)
  if (idx !== -1) {
    kbNavHistory.value = kbNavHistory.value.slice(0, idx)
  }
  activeKb.value = kb
  view.value = 'kb-docs'
  loading.value = true
  const [subKbs, docs] = await Promise.all([
    docManager.fetchSubCatalog(kb.kbId),
    docManager.fetchDocuments(kb.kbId),
  ])
  subKbList.value = subKbs
  kbDocuments.value = filterRealDocs(docs)
  loading.value = false
}

const goBackToCatalog = () => {
  kbNavHistory.value = []
  activeKb.value = null
  subKbList.value = []
  kbDocuments.value = []
  view.value = 'catalog'
}

const goBackOneLevel = async () => {
  if (kbNavHistory.value.length > 0) {
    const prevKb = kbNavHistory.value.pop()
    activeKb.value = prevKb
    view.value = 'kb-docs'
    loading.value = true
    const [subKbs, docs] = await Promise.all([
      docManager.fetchSubCatalog(prevKb.kbId),
      docManager.fetchDocuments(prevKb.kbId),
    ])
    subKbList.value = subKbs
    kbDocuments.value = filterRealDocs(docs)
    loading.value = false
  } else {
    goBackToCatalog()
  }
}

const togglePreview = async (path: string) => {
  if (previewOpen.value && previewPath.value === path) {
    previewOpen.value = false
    return
  }
  previewPath.value = path
  previewTitle.value = path.split(/[\\/]/).pop() || path
  previewOffset.value = 0
  previewContent.value = ''
  previewOpen.value = true
  await loadPreview()
}

const loadPreview = async () => {
  previewLoading.value = true
  try {
    const res = await docManager.readDocument(previewPath.value, {
      offset: previewOffset.value,
      limit: 200,
      maxChars: 30000,
    })
    previewContent.value += res.content
    previewTruncated.value = res.truncated
    previewOffset.value += 200
  } catch (err: any) {
    message.error(err?.message || '加载文档失败')
    previewOpen.value = false
  } finally {
    previewLoading.value = false
  }
}

const loadMorePreview = () => loadPreview()

const handleReindex = async () => {
  reindexing.value = true
  try {
    const res = await advancedSearch.reindex({ force: false })
    message.success(res.message || '索引重建成功')
  } catch (err: any) {
    message.error(err.message || '重建索引失败')
  } finally {
    reindexing.value = false
  }
}

onMounted(async () => {
  try {
    catalog.value = await docManager.fetchCatalog()
    allTags.value = await docManager.fetchAllTags()
  } catch (err: any) {
    message.error(err?.message || '初始化失败，请检查后端服务')
  }
  // Initialize search graph canvas size
  if (searchGraphContainerRef.value) {
    const rect = searchGraphContainerRef.value.getBoundingClientRect()
    searchGraphWidth.value = rect.width
    searchGraphHeight.value = Math.max(400, rect.height)
  }
})
onUnmounted(() => {
  stopSearchGraphSim()
})
</script>

<style scoped>
.kb-search-page { position: relative; min-height: calc(100vh - 110px); color: var(--kb-fg); animation: kb-fade-in 0.4s var(--kb-ease-out); }

/* Page header */
.page-header { margin-bottom: 24px; animation: kb-fade-up 0.5s var(--kb-ease-out) both; }
.header-content { display: flex; justify-content: space-between; align-items: center; }
.header-left { display: flex; align-items: center; gap: 16px; }
.header-icon { width: 54px; height: 54px; border-radius: 15px; display: grid; place-items: center; font-size: 25px; color: #fff; background: linear-gradient(135deg, var(--kb-primary), var(--kb-gold-deep)); box-shadow: var(--kb-shadow-primary); }
.header-text h1 { font-size: 26px; font-weight: 700; color: var(--kb-fg); margin: 0 0 3px; letter-spacing: -0.5px; font-family: var(--kb-font-serif); }
.header-text p { font-size: 14px; color: var(--kb-fg-3); margin: 0; }
.header-actions { display: flex; gap: 10px; }
.action-btn { height: 40px; padding: 0 18px; border-radius: 11px; font-size: 14px; display: flex; align-items: center; gap: 7px; }

/* Search Card */
.search-card { background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); border-radius: var(--kb-radius-lg); padding: 22px; box-shadow: var(--kb-shadow-md); margin-bottom: 24px; animation: kb-fade-up 0.55s 0.05s var(--kb-ease-out) both; }

.mode-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.mode-label { font-size: 13px; font-weight: 600; color: var(--kb-fg-2); }

.search-row { margin-bottom: 16px; }
.search-row :deep(.ant-input-search-large .ant-input-affix-wrapper) { border-radius: 12px 0 0 12px; border-color: var(--kb-border-strong); height: 52px; }
.search-row :deep(.ant-input-search-large .ant-input-affix-wrapper:hover),
.search-row :deep(.ant-input-search-large .ant-input-affix-wrapper-focused) { border-color: var(--kb-gold); box-shadow: 0 0 0 3px rgba(212, 175, 106, 0.15); }
.search-row :deep(.ant-input-search-large .ant-btn) { height: 52px; border-radius: 0 12px 12px 0; font-weight: 600; }

.options-bar { display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 12px; }
.option-group { display: flex; align-items: center; gap: 8px; }
.option-label { font-size: 12px; color: var(--kb-fg-3); font-weight: 600; }

.tag-bar { display: flex; align-items: flex-start; gap: 8px; padding-top: 12px; border-top: 1px solid var(--kb-border); }
.tag-label { font-size: 12px; color: var(--kb-fg-3); font-weight: 600; flex-shrink: 0; margin-top: 4px; }
.tag-list { display: flex; flex-wrap: wrap; gap: 6px; }
.quick-tag { cursor: pointer; transition: all 0.2s; }
.quick-tag:hover { background: var(--kb-primary-soft); border-color: var(--kb-primary); }
.quick-tag.active { background: var(--kb-primary) !important; color: #fff !important; border-color: var(--kb-primary) !important; }

/* Result Statistics */
.results-summary { display: flex; justify-content: space-between; align-items: center; padding: 0 0 16px; }
.summary-left { display: flex; align-items: center; gap: 12px; }
.summary-count { font-size: 14px; font-weight: 700; color: var(--kb-fg); }
.summary-time { font-size: 12px; color: var(--kb-fg-mute); font-family: var(--kb-font-mono); }

/* KB Grid */
.kb-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 18px; }
.kb-card { display: flex; gap: 16px; padding: 22px; border-radius: var(--kb-radius-lg); background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); box-shadow: var(--kb-shadow-sm); cursor: pointer; transition: all var(--kb-dur) var(--kb-ease); animation: kb-fade-up 0.5s var(--kb-ease-out) both; }
.kb-card:hover { transform: translateY(-5px); box-shadow: var(--kb-shadow-lg); border-color: transparent; }
.kb-card-icon { flex-shrink: 0; width: 48px; height: 48px; border-radius: 13px; display: grid; place-items: center; font-size: 22px; color: #fff; background: linear-gradient(135deg, var(--kb-primary), var(--kb-gold-deep)); box-shadow: 0 2px 8px rgba(184, 71, 36, 0.2); }
.kb-card-body { flex: 1; min-width: 0; }
.kb-card-name { font-size: 16px; font-weight: 700; color: var(--kb-fg); margin-bottom: 5px; }
.kb-card-desc { font-size: 13px; color: var(--kb-fg-3); line-height: 1.55; margin-bottom: 12px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.kb-card-stat { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--kb-fg-3); background: var(--kb-bg-subtle); padding: 4px 10px; border-radius: 999px; }
.kb-card-stat :deep(.anticon) { color: var(--kb-primary); }

/* Breadcrumb */
.breadcrumb-bar { display: flex; align-items: center; gap: 8px; padding: 12px 18px; background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); border-radius: var(--kb-radius); margin-bottom: 16px; flex-wrap: wrap; }
.breadcrumb-bar :deep(.ant-btn-link) { color: var(--kb-primary); font-weight: 600; padding: 0; height: auto; }
.breadcrumb-sep { color: var(--kb-fg-mute); }
.breadcrumb-current { font-weight: 700; color: var(--kb-fg); }

/* Section Title */
.section-title { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 700; color: var(--kb-fg); margin-bottom: 14px; }
.section-title :deep(.anticon) { color: var(--kb-primary); }

/* Sub-KB Area */
.sub-kb-section { margin-bottom: 28px; }
.sub-kb-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
.sub-kb-card { display: flex; align-items: center; gap: 14px; padding: 18px; border-radius: var(--kb-radius-lg); background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); box-shadow: var(--kb-shadow-sm); cursor: pointer; transition: all var(--kb-dur) var(--kb-ease); }
.sub-kb-card:hover { transform: translateY(-3px); box-shadow: var(--kb-shadow-md); border-color: var(--kb-gold); }
.sub-kb-card-icon { flex-shrink: 0; width: 42px; height: 42px; border-radius: 11px; display: grid; place-items: center; font-size: 20px; color: #fff; background: linear-gradient(135deg, var(--kb-primary), var(--kb-gold-deep)); }
.sub-kb-card-body { flex: 1; min-width: 0; }
.sub-kb-card-name { font-size: 15px; font-weight: 700; color: var(--kb-fg); margin-bottom: 4px; }
.sub-kb-card-desc { font-size: 12.5px; color: var(--kb-fg-3); line-height: 1.5; margin-bottom: 8px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.sub-kb-card-stat { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; color: var(--kb-fg-3); background: var(--kb-bg-subtle); padding: 3px 9px; border-radius: 999px; }
.sub-kb-card-stat :deep(.anticon) { color: var(--kb-primary); font-size: 11px; }
.sub-kb-card-arrow { flex-shrink: 0; color: var(--kb-fg-mute); font-size: 14px; transition: transform 0.2s; }
.sub-kb-card:hover .sub-kb-card-arrow { transform: translateX(4px); color: var(--kb-primary); }

/* Document Area */
.doc-section { }

/* Document List */
.doc-list { display: flex; flex-direction: column; gap: 12px; }
.doc-item { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 16px 20px; background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); border-radius: var(--kb-radius); box-shadow: var(--kb-shadow-xs); cursor: pointer; transition: all var(--kb-dur-fast) var(--kb-ease); }
.doc-item:hover { border-color: var(--kb-gold); box-shadow: var(--kb-shadow-md); transform: translateX(4px); }
.doc-item-main { display: flex; align-items: center; gap: 14px; flex: 1; min-width: 0; }
.doc-icon { font-size: 22px; color: var(--kb-primary); flex-shrink: 0; }
.doc-info { min-width: 0; }
.doc-name { font-size: 15px; font-weight: 600; color: var(--kb-fg); margin-bottom: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.doc-desc { font-size: 13px; color: var(--kb-fg-3); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.doc-item-side { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.doc-tags-mini { display: flex; gap: 4px; }

/* Search Result Cards */
.results-list { display: flex; flex-direction: column; gap: 16px; }
.result-card { display: flex; gap: 16px; padding: 20px; background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); border-radius: var(--kb-radius-lg); box-shadow: var(--kb-shadow-sm); transition: all 0.25s; animation: kb-fade-up 0.4s var(--kb-ease-out) both; }
.result-card:hover { border-color: var(--kb-gold); box-shadow: var(--kb-shadow-lg); transform: translateY(-2px); }
.result-rank { width: 36px; height: 36px; border-radius: 10px; display: grid; place-items: center; font-size: 14px; font-weight: 800; color: var(--kb-primary); background: var(--kb-primary-soft); flex-shrink: 0; }
.result-body { flex: 1; min-width: 0; }
.result-header { display: flex; align-items: flex-start; gap: 12px; cursor: pointer; }
.result-icon { font-size: 20px; color: var(--kb-gold-deep); flex-shrink: 0; margin-top: 2px; }
.result-info { flex: 1; min-width: 0; }
.result-name { font-size: 15px; font-weight: 700; color: var(--kb-fg); margin-bottom: 4px; }
.result-desc { font-size: 13px; color: var(--kb-fg-3); line-height: 1.5; }
.result-preview { margin-top: 12px; padding: 10px 14px; background: var(--kb-bg-subtle); border-radius: var(--kb-radius-sm); font-size: 12.5px; color: var(--kb-fg-2); line-height: 1.6; border-left: 3px solid var(--kb-gold); display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }

.result-scores { display: flex; gap: 20px; flex-wrap: wrap; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--kb-border); }
.score-group { display: flex; align-items: center; gap: 6px; }
.score-label { font-size: 11px; color: var(--kb-fg-mute); font-weight: 600; text-transform: uppercase; }
.score-value { font-size: 12px; color: var(--kb-fg-2); font-family: var(--kb-font-mono); font-weight: 600; }

.result-meta { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-top: 10px; }
.result-path { font-size: 11px; color: var(--kb-fg-mute); font-family: var(--kb-font-mono); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 300px; }

.verify-status { display: flex; align-items: center; gap: 6px; margin-top: 10px; padding: 8px 12px; border-radius: var(--kb-radius-sm); font-size: 12px; }
.verify-pass { color: var(--kb-emerald); }
.verify-warn { color: var(--kb-amber); }
.verify-status:has(.verify-pass) { background: var(--kb-emerald-soft); }
.verify-status:has(.verify-warn) { background: var(--kb-amber-soft); }

/* Empty State */
.empty-state { padding: 70px 20px; text-align: center; }
.empty-state :deep(.ant-empty-description) { color: var(--kb-fg-3); }

/* Preview Drawer */
.preview-content { background: var(--kb-bg-subtle); border: 1px solid var(--kb-border); border-radius: var(--kb-radius); padding: 18px; }
.preview-content pre { margin: 0; white-space: pre-wrap; word-break: break-word; font-family: var(--kb-font-mono); font-size: 13px; line-height: 1.7; color: var(--kb-fg-2); }
.preview-content-md { background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); border-radius: var(--kb-radius); padding: 20px 24px; }
.preview-more { text-align: center; margin-top: 16px; }

/* Result Area Right Actions */
.summary-right { display: flex; align-items: center; gap: 14px; }

/* View Switcher */
.results-tab-switcher { display: flex; gap: 4px; padding: 3px; background: var(--kb-bg-subtle); border-radius: var(--kb-radius-sm); }
.tab-btn { display: flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 6px; font-size: 13px; font-weight: 600; color: var(--kb-fg-3); cursor: pointer; transition: all 0.25s var(--kb-ease); }
.tab-btn:hover { color: var(--kb-fg); background: var(--kb-bg-elevated); }
.tab-btn.active { background: var(--kb-bg-elevated); color: var(--kb-primary); box-shadow: var(--kb-shadow-xs); }
.tab-btn :deep(.anticon) { font-size: 14px; }

/* ============ Search Results Relation Graph View ============ */
.search-graph-view { animation: kb-fade-in 0.3s var(--kb-ease-out); }
.search-graph-layout { display: grid; grid-template-columns: 1fr 320px; gap: 16px; }

.search-graph-canvas { position: relative; background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); border-radius: var(--kb-radius-lg); box-shadow: var(--kb-shadow-md); overflow: hidden; min-height: 500px; height: calc(100vh - 340px); }
.search-graph-canvas svg { display: block; cursor: grab; }
.search-graph-canvas svg:active { cursor: grabbing; }

/* Toolbar (reuses knowledge-graph page style) */
.graph-toolbar { position: absolute; top: 12px; right: 12px; z-index: 10; display: flex; align-items: center; gap: 4px; padding: 5px 8px; background: rgba(255,255,255,0.92); backdrop-filter: blur(10px); border: 1px solid var(--kb-border); border-radius: 10px; box-shadow: var(--kb-shadow-sm); }
.tool-btn { width: 30px; height: 30px; display: grid; place-items: center; color: var(--kb-fg-3); border-radius: 6px; transition: all 0.2s; }
.tool-btn:hover { background: var(--kb-primary-tint); color: var(--kb-primary); }

/* Legend */
.graph-legend { position: absolute; bottom: 12px; left: 12px; z-index: 10; display: flex; gap: 12px; padding: 7px 14px; background: rgba(255,255,255,0.92); backdrop-filter: blur(10px); border: 1px solid var(--kb-border); border-radius: 10px; box-shadow: var(--kb-shadow-sm); }
.legend-item { display: flex; align-items: center; gap: 5px; font-size: 11.5px; color: var(--kb-fg-2); font-weight: 600; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; }
.kb-dot { background: linear-gradient(135deg, #4f7cff, #2563eb); }
.doc-dot { background: linear-gradient(135deg, #22d3ee, #06b6d4); }
.tag-dot { background: linear-gradient(135deg, #34d399, #10b981); }

/* Graph Empty State */
.graph-empty { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; }

/* SVG node animation */
.select-ring { animation: kb-pulse-ring 1.5s ease-out infinite; }

/* ============ Search Graph Detail Panel ============ */
.search-graph-detail { background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); border-radius: var(--kb-radius-lg); box-shadow: var(--kb-shadow-md); padding: 18px; overflow-y: auto; max-height: calc(100vh - 340px); display: flex; flex-direction: column; gap: 14px; animation: kb-fade-up 0.3s var(--kb-ease-out); }
.search-graph-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; gap: 0; }

.sgd-header { display: flex; align-items: center; gap: 12px; }
.sgd-icon { width: 44px; height: 44px; border-radius: 12px; display: grid; place-items: center; font-size: 20px; color: #fff; flex-shrink: 0; }
.sgd-icon.icon-kb { background: linear-gradient(135deg, var(--kb-primary), #4f7cff); }
.sgd-icon.icon-document { background: linear-gradient(135deg, var(--kb-cyan), #22d3ee); }
.sgd-icon.icon-tag { background: linear-gradient(135deg, var(--kb-emerald), #34d399); }
.sgd-name { font-size: 16px; font-weight: 700; color: var(--kb-fg); margin: 0 0 4px; word-break: break-word; }
.type-tag { font-size: 11px !important; }
.type-kb { background: var(--kb-primary-soft) !important; color: var(--kb-primary-hover) !important; border-color: transparent !important; }
.type-document { background: var(--kb-cyan-soft) !important; color: #0891b2 !important; border-color: transparent !important; }
.type-tag { background: var(--kb-emerald-soft) !important; color: #059669 !important; border-color: transparent !important; }

.sgd-desc { font-size: 13px; color: var(--kb-fg-3); line-height: 1.6; padding: 10px 12px; background: var(--kb-bg-subtle); border-radius: var(--kb-radius-sm); }
.sgd-meta { display: flex; flex-direction: column; gap: 4px; }
.sgd-meta .meta-label { font-size: 11px; color: var(--kb-fg-mute); text-transform: uppercase; letter-spacing: 0.4px; font-weight: 600; }
.sgd-meta span:last-child { font-size: 13px; color: var(--kb-fg); font-weight: 500; }
.mono-path { font-family: var(--kb-font-mono); font-size: 12px; word-break: break-all; }
.sgd-tags { display: flex; flex-wrap: wrap; gap: 4px; }

.sgd-related { border-top: 1px solid var(--kb-border); padding-top: 14px; display: flex; flex-direction: column; gap: 10px; }
.sgd-related-title { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700; color: var(--kb-fg); }
.sgd-related-title :deep(.anticon) { color: var(--kb-primary); }
.sgd-related-list { display: flex; flex-direction: column; gap: 6px; max-height: 240px; overflow-y: auto; }
.sgd-related-item { display: flex; align-items: center; gap: 10px; padding: 8px 10px; background: var(--kb-bg-subtle); border-radius: var(--kb-radius-sm); cursor: pointer; transition: all 0.2s; }
.sgd-related-item:hover { background: var(--kb-primary-tint); }
.sgd-related-icon { width: 26px; height: 26px; border-radius: 7px; display: grid; place-items: center; font-size: 12px; color: #fff; flex-shrink: 0; }
.sgd-related-icon.icon-kb { background: linear-gradient(135deg, var(--kb-primary), #4f7cff); }
.sgd-related-icon.icon-document { background: linear-gradient(135deg, var(--kb-cyan), #22d3ee); }
.sgd-related-icon.icon-tag { background: linear-gradient(135deg, var(--kb-emerald), #34d399); }
.sgd-related-item span { font-size: 12.5px; color: var(--kb-fg); font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* Graph Result Action Buttons */
.result-actions { margin-top: 10px; }
.result-actions :deep(.ant-btn-link) { padding: 0; height: auto; font-size: 12.5px; }

/* Responsive */
@media (max-width: 768px) {
  .options-bar { flex-direction: column; gap: 12px; }
  .result-scores { gap: 12px; }
  .search-graph-layout { grid-template-columns: 1fr; }
  .search-graph-canvas { min-height: 400px; height: 400px; }
  .search-graph-detail { max-height: 300px; }
  .results-summary { flex-direction: column; gap: 12px; align-items: flex-start; }
  .summary-right { flex-direction: column; gap: 8px; align-items: flex-start; }
}
</style>

