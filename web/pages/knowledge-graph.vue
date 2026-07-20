<template>
  <div class="kg-page">
    <!-- Page header -->
    <header class="page-header">
      <div class="header-content">
        <div class="header-left">
          <div class="header-icon">
            <ShareAltOutlined />
          </div>
          <div class="header-text">
            <h1 class="header-title">{{ $t('settings.knowledgeGraph') }}</h1>
            <p class="header-subtitle">{{ $t('graph.subtitle') }}</p>
          </div>
        </div>
        <div class="header-actions">
          <a-button class="action-btn" @click="handleRefresh" :loading="graphLoading">
            <ReloadOutlined />
            <span>{{ $t('graph.refreshGraph') }}</span>
          </a-button>
          <a-button type="primary" class="action-btn" @click="handleRebuild" :loading="rebuilding">
            <BuildOutlined />
            <span>{{ $t('graph.rebuildGraph') }}</span>
          </a-button>
        </div>
      </div>
    </header>

    <main class="main-content">
      <!-- Stats cards -->
      <div class="stats-row" v-if="graphData.nodes.length > 0 || stats">
        <div class="stat-card">
          <div class="stat-card-icon kb-icon"><DatabaseOutlined /></div>
          <div class="stat-card-info">
            <span class="stat-card-value">{{ graphData.nodes.filter(n => n.type === 'kb').length }}</span>
            <span class="stat-card-label">{{ $t('graph.kbs') }}</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-card-icon doc-icon"><FileTextOutlined /></div>
          <div class="stat-card-info">
            <span class="stat-card-value">{{ graphData.nodes.filter(n => n.type === 'document').length }}</span>
            <span class="stat-card-label">{{ $t('graph.docs') }}</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-card-icon tag-icon"><TagOutlined /></div>
          <div class="stat-card-info">
            <span class="stat-card-value">{{ graphData.nodes.filter(n => n.type === 'tag').length }}</span>
            <span class="stat-card-label">{{ $t('graph.tags') }}</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-card-icon edge-icon"><ShareAltOutlined /></div>
          <div class="stat-card-info">
            <span class="stat-card-value">{{ graphData.edges.length }}</span>
            <span class="stat-card-label">{{ $t('graph.edges') }}</span>
          </div>
        </div>
      </div>

      <!-- Neo4j health status hint -->
      <div v-if="neo4jStatus === 'unavailable'" class="health-banner">
        <WarningOutlined />
        <span>{{ $t('graph.neo4jUnavailable') }}</span>
        <span class="health-hint">{{ $t('graph.neo4jHint') }}</span>
      </div>

      <!-- View mode switch -->
      <div class="view-tabs">
        <div
          v-for="tab in viewTabs"
          :key="tab.key"
          :class="['view-tab', { active: activeView === tab.key }]"
          @click="switchView(tab.key)"
        >
          <component :is="tab.icon" />
          <span>{{ tab.label }}</span>
        </div>
      </div>

      <!-- ============ Global graph view ============ -->
      <div v-show="activeView === 'full'" class="graph-layout">
        <div class="graph-canvas-wrapper">
          <div class="graph-toolbar">
            <a-tooltip title="放大"><a-button type="text" size="small" class="tool-btn" @click="zoomIn"><ZoomInOutlined /></a-button></a-tooltip>
            <a-tooltip title="缩小"><a-button type="text" size="small" class="tool-btn" @click="zoomOut"><ZoomOutOutlined /></a-button></a-tooltip>
            <a-tooltip title="重置视图"><a-button type="text" size="small" class="tool-btn" @click="resetView"><CompressOutlined /></a-button></a-tooltip>
            <a-divider type="vertical" />
            <a-tooltip title="自动适配"><a-button type="text" size="small" class="tool-btn" @click="fitView"><ExpandOutlined /></a-button></a-tooltip>
            <a-tooltip title="重新布局"><a-button type="text" size="small" class="tool-btn" @click="restartSimulation"><ReloadOutlined /></a-button></a-tooltip>
          </div>

          <div class="graph-legend">
            <div class="legend-item"><span class="legend-dot kb-dot"></span><span>{{ $t('graph.kbs') }}</span></div>
            <div class="legend-item"><span class="legend-dot doc-dot"></span><span>{{ $t('graph.docs') }}</span></div>
            <div class="legend-item"><span class="legend-dot tag-dot"></span><span>{{ $t('graph.tags') }}</span></div>
            <div class="legend-item"><span class="legend-line shared-line"></span><span>共享标签</span></div>
            <div class="legend-item"><span class="legend-line vector-line"></span><span>内容相似</span></div>
          </div>

          <div class="node-count-info" v-if="graphData.nodes.length > 0">
            <span>显示 {{ renderedNodes.length }} / {{ graphData.nodes.length }} 个节点</span>
          </div>

          <div class="svg-container" ref="svgContainerRef">
            <svg ref="svgRef" :width="canvasWidth" :height="canvasHeight" @mousedown="onCanvasMouseDown" @mousemove="onCanvasMouseMove" @mouseup="onCanvasMouseUp" @mouseleave="onCanvasMouseUp" @wheel.prevent="onWheel">
              <defs>
                <radialGradient id="kbGrad"><stop offset="0%" stop-color="#4f7cff" /><stop offset="100%" stop-color="#2563eb" /></radialGradient>
                <radialGradient id="docGrad"><stop offset="0%" stop-color="#22d3ee" /><stop offset="100%" stop-color="#06b6d4" /></radialGradient>
                <radialGradient id="tagGrad"><stop offset="0%" stop-color="#34d399" /><stop offset="100%" stop-color="#10b981" /></radialGradient>
                <radialGradient id="docGradHighlight"><stop offset="0%" stop-color="#fbbf24" /><stop offset="100%" stop-color="#f59e0b" /></radialGradient>
                <filter id="glow"><feGaussianBlur stdDeviation="3" result="coloredBlur" /><feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
              </defs>
              <g :transform="`translate(${panX},${panY}) scale(${zoom})`">
                <line v-for="(edge, i) in renderedEdges" :key="`edge-${i}`" :x1="edge.x1" :y1="edge.y1" :x2="edge.x2" :y2="edge.y2" :class="['graph-edge', { 'edge-highlight': isEdgeHighlighted(edge), 'edge-shared': edge.type === 'shared_tag' }]" :stroke="getEdgeColor(edge)" :stroke-width="isEdgeHighlighted(edge) ? 2.5 : 1" :stroke-opacity="isEdgeHighlighted(edge) ? 0.8 : 0.25" :stroke-dasharray="edge.type === 'shared_tag' ? '4,3' : 'none'" />
                <g v-for="node in renderedNodes" :key="node.id" :transform="`translate(${node.x},${node.y})`" class="graph-node-group" @click.stop="onNodeClick(node)" @mouseenter="onNodeHover(node)" @mouseleave="onNodeHover(null)" @mousedown.stop="onNodeDragStart($event, node)">
                  <circle v-if="selectedNode?.id === node.id" :r="getNodeRadius(node) + 8" fill="none" stroke="#2563eb" stroke-width="2" stroke-opacity="0.4" class="select-ring" />
                  <circle :r="getNodeRadius(node)" :fill="getNodeFill(node)" :class="['graph-node-circle', { 'node-hover': hoveredNode?.id === node.id }]" :filter="selectedNode?.id === node.id ? 'url(#glow)' : ''" />
                  <text :y="getNodeRadius(node) + 14" text-anchor="middle" class="graph-node-label" :font-size="node.type === 'kb' ? '12px' : '10px'" :font-weight="node.type === 'kb' ? '700' : '500'">{{ truncateLabel(node.label, node.type === 'kb' ? 16 : 12) }}</text>
                </g>
              </g>
            </svg>
            <div v-if="graphLoading" class="canvas-loading"><a-spin size="large" tip="构建知识图谱中..." /></div>
            <div v-if="!graphLoading && graphData.nodes.length === 0" class="canvas-empty">
              <div class="empty-icon"><ShareAltOutlined /></div>
              <p class="empty-text">暂无图谱数据</p>
              <a-button type="primary" @click="handleRebuild"><BuildOutlined /><span>构建图谱</span></a-button>
            </div>
          </div>
        </div>

        <aside class="detail-panel">
          <div class="filter-section">
            <a-input-search v-model:value="filterQuery" placeholder="过滤节点..." size="small" class="filter-input" allow-clear />
            <div class="filter-tags">
              <a-tag-checkable v-model:checked="showKbNodes" class="filter-tag kb-filter">{{ $t('graph.kbs') }}</a-tag-checkable>
              <a-tag-checkable v-model:checked="showDocNodes" class="filter-tag doc-filter">{{ $t('graph.docs') }}</a-tag-checkable>
              <a-tag-checkable v-model:checked="showTagNodes" class="filter-tag tag-filter">{{ $t('graph.tags') }}</a-tag-checkable>
            </div>
          </div>
          <NodeDetailPanel :node="selectedNode" :related-nodes="relatedNodes" :all-nodes="simNodes" @select="selectNode" />
        </aside>
      </div>

      <!-- ============ Document center view ============ -->
      <div v-show="activeView === 'doc-center'" class="doc-center-layout">
        <div class="doc-center-search">
          <a-input-search v-model:value="docSearchQuery" placeholder="输入文档名称或路径关键词搜索..." enter-button="搜索文档" size="large" @search="handleDocSearch" :loading="docSearching" />
          <div v-if="docSearchResults.length > 0" class="doc-search-results">
            <div v-for="doc in docSearchResults" :key="doc.doc_path || doc.path" class="doc-search-item" @click="loadDocumentGraph(doc.doc_path || doc.path)">
              <FileTextOutlined class="doc-search-icon" />
              <div class="doc-search-info">
                <div class="doc-search-name">{{ doc.doc_name || doc.name }}</div>
                <div class="doc-search-path">{{ doc.doc_path || doc.path }}</div>
              </div>
              <a-tag v-if="doc.kb_name" color="blue" size="small">{{ doc.kb_name }}</a-tag>
            </div>
          </div>
        </div>

        <div v-if="docCenterGraph.nodes.length > 0" class="graph-layout">
          <div class="graph-canvas-wrapper">
            <div class="graph-toolbar">
              <a-tooltip title="放大"><a-button type="text" size="small" class="tool-btn" @click="zoomIn"><ZoomInOutlined /></a-button></a-tooltip>
              <a-tooltip title="缩小"><a-button type="text" size="small" class="tool-btn" @click="zoomOut"><ZoomOutOutlined /></a-button></a-tooltip>
              <a-tooltip :title="$t('action.reset')"><a-button type="text" size="small" class="tool-btn" @click="resetView"><CompressOutlined /></a-button></a-tooltip>
              <a-divider type="vertical" />
              <a-tooltip title="自动适配"><a-button type="text" size="small" class="tool-btn" @click="fitView"><ExpandOutlined /></a-button></a-tooltip>
            </div>
            <div class="graph-legend">
              <div class="legend-item"><span class="legend-dot kb-dot"></span><span>{{ $t('graph.kbs') }}</span></div>
              <div class="legend-item"><span class="legend-dot doc-dot"></span><span>{{ $t('graph.docs') }}</span></div>
              <div class="legend-item"><span class="legend-dot tag-dot"></span><span>{{ $t('graph.tags') }}</span></div>
              <div class="legend-item"><span class="legend-dot center-dot"></span><span>中心文档</span></div>
            </div>
            <div class="svg-container" ref="docSvgContainerRef">
              <svg ref="docSvgRef" :width="canvasWidth" :height="canvasHeight" @mousedown="onCanvasMouseDown" @mousemove="onCanvasMouseMove" @mouseup="onCanvasMouseUp" @mouseleave="onCanvasMouseUp" @wheel.prevent="onWheel">
                <defs>
                  <radialGradient id="kbGrad2"><stop offset="0%" stop-color="#4f7cff" /><stop offset="100%" stop-color="#2563eb" /></radialGradient>
                  <radialGradient id="docGrad2"><stop offset="0%" stop-color="#22d3ee" /><stop offset="100%" stop-color="#06b6d4" /></radialGradient>
                  <radialGradient id="tagGrad2"><stop offset="0%" stop-color="#34d399" /><stop offset="100%" stop-color="#10b981" /></radialGradient>
                  <radialGradient id="centerGrad"><stop offset="0%" stop-color="#fbbf24" /><stop offset="100%" stop-color="#f59e0b" /></radialGradient>
                  <filter id="glow2"><feGaussianBlur stdDeviation="4" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
                </defs>
                <g :transform="`translate(${panX},${panY}) scale(${zoom})`">
                  <line v-for="(edge, i) in docCenterRenderedEdges" :key="`de-${i}`" :x1="edge.x1" :y1="edge.y1" :x2="edge.x2" :y2="edge.y2" :class="['graph-edge', { 'edge-shared': edge.type === 'shared_tag' || edge.type === 'vector_similar' }]" :stroke="getEdgeColor(edge)" :stroke-width="1.5" :stroke-opacity="0.4" :stroke-dasharray="edge.type === 'shared_tag' || edge.type === 'vector_similar' ? '5,3' : 'none'" />
                  <g v-for="node in docCenterRenderedNodes" :key="node.id" :transform="`translate(${node.x},${node.y})`" class="graph-node-group" @click.stop="onDocCenterNodeClick(node)" @mouseenter="onNodeHover(node)" @mouseleave="onNodeHover(null)">
                    <circle v-if="node.isCenter" :r="getNodeRadius(node) + 10" fill="none" stroke="#f59e0b" stroke-width="2" stroke-opacity="0.5" class="select-ring" />
                    <circle :r="getNodeRadius(node)" :fill="node.isCenter ? 'url(#centerGrad)' : getDocCenterNodeFill(node)" :class="['graph-node-circle', { 'node-hover': hoveredNode?.id === node.id }]" :filter="node.isCenter ? 'url(#glow2)' : ''" />
                    <text :y="getNodeRadius(node) + 14" text-anchor="middle" class="graph-node-label" :font-size="node.isCenter ? '13px' : node.type === 'kb' ? '12px' : '10px'" :font-weight="node.isCenter ? '800' : node.type === 'kb' ? '700' : '500'">{{ truncateLabel(node.label, node.isCenter ? 18 : node.type === 'kb' ? 16 : 12) }}</text>
                  </g>
                </g>
              </svg>
            </div>
          </div>
          <aside class="detail-panel">
            <NodeDetailPanel :node="docCenterSelectedNode" :related-nodes="docCenterRelatedNodes" :all-nodes="docCenterSimNodes" @select="selectDocCenterNode" />
          </aside>
        </div>
        <div v-else-if="!docSearching" class="doc-center-empty">
          <div class="empty-icon"><FileSearchOutlined /></div>
          <p class="empty-text">搜索并选择一个文档，查看其关联图谱</p>
          <p class="empty-hint">文档中心视图会展示该文档的KB归属、标签关联、跨KB连接</p>
        </div>
      </div>

      <!-- ============ Cross-KB analysis view ============ -->
      <div v-show="activeView === 'cross-kb'" class="cross-kb-layout">
        <div class="cross-kb-header">
          <h3 class="section-subtitle">跨知识库桥梁文档</h3>
          <p class="section-desc">通过共享标签或向量相似度关联到不同知识库的文档，是知识图谱中的关键桥梁节点</p>
        </div>
        <a-spin :spinning="crossKbLoading">
          <div v-if="crossKbDocs.length > 0" class="cross-kb-grid">
            <div v-for="doc in crossKbDocs" :key="doc.doc_path" class="cross-kb-card" @click="loadDocumentGraph(doc.doc_path)">
              <div class="cross-kb-card-header">
                <FileTextOutlined class="cross-kb-icon" />
                <div class="cross-kb-card-info">
                  <div class="cross-kb-card-name">{{ doc.doc_name }}</div>
                  <div class="cross-kb-card-path">{{ doc.doc_path }}</div>
                </div>
              </div>
              <div class="cross-kb-card-body">
                <div class="cross-kb-bridges">
                  <span class="bridge-label">桥接知识库:</span>
                  <a-tag v-for="kb in doc.bridging_kbs" :key="kb" color="blue" size="small">{{ kb }}</a-tag>
                </div>
                <div class="cross-kb-relation">
                  <span class="relation-badge" :class="`relation-${doc.relation_type}`">{{ doc.relation_type }}</span>
                  <span class="related-count">{{ doc.related_docs }} 篇关联文档</span>
                </div>
                <div class="cross-kb-tags" v-if="doc.tags && doc.tags.length">
                  <a-tag v-for="t in doc.tags.slice(0, 5)" :key="t" color="green" size="small">{{ t }}</a-tag>
                </div>
              </div>
            </div>
          </div>
          <div v-else-if="!crossKbLoading" class="cross-kb-empty">
            <div class="empty-icon"><SwapOutlined /></div>
            <p class="empty-text">暂无跨KB桥梁文档</p>
            <p class="empty-hint">跨KB分析需要Neo4j图谱数据库支持</p>
          </div>
        </a-spin>
      </div>

      <!-- ============ Path discovery view ============ -->
      <div v-show="activeView === 'path'" class="path-layout">
        <div class="path-header">
          <h3 class="section-subtitle">文档关联路径发现</h3>
          <p class="section-desc">选择两个文档，发现它们在知识图谱中的最短关联路径</p>
        </div>
        <div class="path-selector">
          <div class="path-input-group">
            <label class="path-label">起点文档</label>
            <a-input-search v-model:value="pathSearchA" placeholder="搜索起点文档..." @search="handlePathSearchA" size="default" />
            <div v-if="pathResultsA.length > 0" class="path-search-results">
              <div v-for="doc in pathResultsA" :key="doc.doc_path || doc.path" class="path-search-item" :class="{ selected: pathDocA === (doc.doc_path || doc.path) }" @click="selectPathDoc('A', doc)">
                <FileTextOutlined /> {{ doc.doc_name || doc.name || (doc.path || '').split(/[\\/]/).pop() }}
                <span class="path-search-path">{{ doc.doc_path || doc.path }}</span>
              </div>
            </div>
            <div v-if="pathDocA" class="path-selected">
              <CheckCircleOutlined /> 已选择: {{ pathDocA }}
            </div>
          </div>
          <div class="path-arrow">
            <ArrowRightOutlined />
          </div>
          <div class="path-input-group">
            <label class="path-label">终点文档</label>
            <a-input-search v-model:value="pathSearchB" placeholder="搜索终点文档..." @search="handlePathSearchB" size="default" />
            <div v-if="pathResultsB.length > 0" class="path-search-results">
              <div v-for="doc in pathResultsB" :key="doc.doc_path || doc.path" class="path-search-item" :class="{ selected: pathDocB === (doc.doc_path || doc.path) }" @click="selectPathDoc('B', doc)">
                <FileTextOutlined /> {{ doc.doc_name || doc.name || (doc.path || '').split(/[\\/]/).pop() }}
                <span class="path-search-path">{{ doc.doc_path || doc.path }}</span>
              </div>
            </div>
            <div v-if="pathDocB" class="path-selected">
              <CheckCircleOutlined /> 已选择: {{ pathDocB }}
            </div>
          </div>
        </div>
        <div class="path-action" v-if="pathDocA && pathDocB">
          <a-button type="primary" size="large" @click="findPath" :loading="pathFinding">
            <NodeIndexOutlined />
            <span>发现关联路径</span>
          </a-button>
        </div>
        <div v-if="pathResult" class="path-result">
          <div v-if="pathResult.found && pathResult.path && pathResult.path.length > 0" class="path-chain">
            <div class="path-chain-header">
              <CheckCircleOutlined class="path-found-icon" />
              <span>找到关联路径，共 {{ pathResult.length }} 步</span>
            </div>
            <div class="path-chain-list">
              <div v-for="(step, i) in pathResult.path" :key="i" class="path-step">
                <div class="path-step-num">{{ Number(i) + 1 }}</div>
                <div class="path-step-info">
                  <div class="path-step-name">{{ step.doc_name }}</div>
                  <div class="path-step-kb"><DatabaseOutlined /> {{ step.kb_name }}</div>
                </div>
                <ArrowRightOutlined v-if="Number(i) < pathResult.path.length - 1" class="path-step-arrow" />
              </div>
            </div>
          </div>
          <div v-else class="path-not-found">
            <CloseCircleOutlined />
            <span>未找到两个文档之间的关联路径（可能需要增加搜索深度或建立更多关联）</span>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, defineComponent, h } from 'vue'
import { message } from 'ant-design-vue'
import {
  ShareAltOutlined, ReloadOutlined, BuildOutlined,
  DatabaseOutlined, FileTextOutlined, TagOutlined,
  ZoomInOutlined, ZoomOutOutlined, CompressOutlined,
  WarningOutlined, ExpandOutlined,
  FileSearchOutlined, SwapOutlined, ArrowRightOutlined,
  NodeIndexOutlined, CheckCircleOutlined, CloseCircleOutlined,
} from '@ant-design/icons-vue'
import { useKbGraph } from '~/composables/useKbGraph'
import type { GraphNode, GraphEdge, GraphData, GraphStats } from '~/composables/useKbGraph'

// ——— composable ———
const {
  loading: graphLoading, error: graphError, buildLocalGraph,
  fetchStats, buildBackendGraph, checkHealth,
  searchGraph, getDocumentGraph, getCrossKbDocuments,
  findDocumentPaths,
} = useKbGraph()

// -- View mode --
type ViewMode = 'full' | 'doc-center' | 'cross-kb' | 'path'
const activeView = ref<ViewMode>('full')
const viewTabs = [
  { key: 'full' as ViewMode, label: '全局图谱', icon: ShareAltOutlined },
  { key: 'doc-center' as ViewMode, label: '文档中心', icon: FileSearchOutlined },
  { key: 'cross-kb' as ViewMode, label: '跨KB分析', icon: SwapOutlined },
  { key: 'path' as ViewMode, label: '路径发现', icon: NodeIndexOutlined },
]

// -- Global graph data --
const graphData = ref<GraphData>({ nodes: [], edges: [] })
const stats = ref<GraphStats | null>(null)
const selectedNode = ref<SimNode | null>(null)
const hoveredNode = ref<GraphNode | null>(null)
const rebuilding = ref(false)
const neo4jStatus = ref<'checking' | 'available' | 'unavailable'>('checking')

// ——— Physics simulation ———
interface SimNode extends GraphNode {
  x: number; y: number; vx: number; vy: number
  fx?: number | null; fy?: number | null
  isCenter?: boolean
}
const simNodes = ref<SimNode[]>([])
const simulationRunning = ref(false)
let animationId: number | null = null
const W = 800; const H = 600
const canvasWidth = ref(800); const canvasHeight = ref(600)

// ——— View transform ———
const zoom = ref(1); const panX = ref(0); const panY = ref(0)
const isPanning = ref(false)
const panStart = ref({ x: 0, y: 0, px: 0, py: 0 })

// ——— Drag ———
const draggingNode = ref<SimNode | null>(null)

// ——— Filter ———
const filterQuery = ref('')
const showKbNodes = ref(true)
const showDocNodes = ref(true)
const showTagNodes = ref(true)

// ——— refs ———
const svgRef = ref<SVGSVGElement | null>(null)
const svgContainerRef = ref<HTMLDivElement | null>(null)
const docSvgRef = ref<SVGSVGElement | null>(null)
const docSvgContainerRef = ref<HTMLDivElement | null>(null)

// ——— Document center view ———
const docSearchQuery = ref('')
const docSearching = ref(false)
const docSearchResults = ref<any[]>([])
const docCenterGraph = ref<GraphData>({ nodes: [], edges: [] })
const docCenterSimNodes = ref<SimNode[]>([])
const docCenterSelectedNode = ref<SimNode | null>(null)
const docCenterPath = ref<string>('')
let docCenterAnimId: number | null = null

// ——— Cross-KB analysis ———
const crossKbLoading = ref(false)
const crossKbDocs = ref<any[]>([])

// ——— Path discovery ———
const pathSearchA = ref(''); const pathSearchB = ref('')
const pathResultsA = ref<any[]>([]); const pathResultsB = ref<any[]>([])
const pathDocA = ref(''); const pathDocB = ref('')
const pathFinding = ref(false)
const pathResult = ref<any | null>(null)

// -- NodeDetailPanel --
const NodeDetailPanel = defineComponent({
  props: {
    node: { type: Object as () => SimNode | null, default: null },
    relatedNodes: { type: Array as () => SimNode[], default: () => [] },
    allNodes: { type: Array as () => SimNode[], default: () => [] },
  },
  emits: ['select'],
  setup(props, { emit }) {
    return () => {
      if (!props.node) {
        return h('div', { class: 'no-selection' }, [
          h('div', { class: 'no-sel-icon' }, h(ShareAltOutlined)),
          h('p', { class: 'no-sel-text' }, '点击图谱节点查看详情'),
          h('p', { class: 'no-sel-hint' }, '支持拖拽、缩放、点击交互'),
        ])
      }
      const n = props.node
      const typeLabel = n.type === 'kb' ? '知识库' : n.type === 'document' ? '文档' : '标签'
      const typeIcon = n.type === 'kb' ? h(DatabaseOutlined) : n.type === 'document' ? h(FileTextOutlined) : h(TagOutlined)
      return h('div', { class: 'node-detail' }, [
        h('div', { class: 'detail-header' }, [
          h('div', { class: `detail-icon icon-${n.type}` }, typeIcon),
          h('div', { class: 'detail-titles' }, [
            h('h3', { class: 'detail-name' }, n.label),
            h('a-tag', { class: `type-tag type-${n.type}` }, typeLabel),
          ]),
        ]),
        n.description ? h('div', { class: 'detail-desc' }, n.description) : null,
        h('div', { class: 'detail-meta' }, [
          n.kb_name ? h('div', { class: 'meta-item' }, [
            h('span', { class: 'meta-label' }, '所属知识库'),
            h('span', { class: 'meta-value' }, n.kb_name),
          ]) : null,
          n.doc_count !== undefined ? h('div', { class: 'meta-item' }, [
            h('span', { class: 'meta-label' }, '文档数'),
            h('span', { class: 'meta-value' }, String(n.doc_count)),
          ]) : null,
          n.path ? h('div', { class: 'meta-item' }, [
            h('span', { class: 'meta-label' }, '路径'),
            h('span', { class: 'meta-value mono-path' }, n.path),
          ]) : null,
          n.score !== undefined ? h('div', { class: 'meta-item' }, [
            h('span', { class: 'meta-label' }, '得分'),
            h('span', { class: 'meta-value' }, n.score.toFixed(4)),
          ]) : null,
          n.tags && n.tags.length ? h('div', { class: 'meta-item' }, [
            h('span', { class: 'meta-label' }, '标签'),
            h('div', { class: 'meta-tags' }, n.tags.map((t: string) => h('a-tag', { key: t, color: 'green' }, t))),
          ]) : null,
        ]),
        h('div', { class: 'related-section' }, [
          h('div', { class: 'related-title' }, [
            h(ShareAltOutlined),
            h('span', `关联节点 (${props.relatedNodes.length})`),
          ]),
          h('div', { class: 'related-list' }, [
            ...props.relatedNodes.map(rn => h('div', {
              key: rn.id, class: 'related-item', onClick: () => emit('select', rn),
            }, [
              h('div', { class: `related-icon icon-${rn.type}` },
                rn.type === 'kb' ? h(DatabaseOutlined) : rn.type === 'document' ? h(FileTextOutlined) : h(TagOutlined)
              ),
              h('span', { class: 'related-name' }, rn.label),
              h('span', { class: 'related-type' }, rn.type === 'kb' ? '知识库' : rn.type === 'document' ? '文档' : '标签'),
            ])),
            props.relatedNodes.length === 0 ? h('div', { class: 'related-empty' }, '无关联节点') : null,
          ]),
        ]),
      ])
    }
  },
})

// -- Computed: filtered nodes --
const filteredNodes = computed(() => simNodes.value.filter(n => {
  if (n.type === 'kb' && !showKbNodes.value) return false
  if (n.type === 'document' && !showDocNodes.value) return false
  if (n.type === 'tag' && !showTagNodes.value) return false
  if (filterQuery.value) return n.label.toLowerCase().includes(filterQuery.value.toLowerCase())
  return true
}))
const filteredNodeIds = computed(() => new Set(filteredNodes.value.map(n => n.id)))
const renderedNodes = computed(() => filteredNodes.value)
const renderedEdges = computed(() => graphData.value.edges
  .filter(e => filteredNodeIds.value.has(e.source) && filteredNodeIds.value.has(e.target))
  .map(e => {
    const s = simNodes.value.find(n => n.id === e.source)
    const t = simNodes.value.find(n => n.id === e.target)
    return { ...e, x1: s?.x || 0, y1: s?.y || 0, x2: t?.x || 0, y2: t?.y || 0 }
  }))

const relatedNodes = computed(() => {
  if (!selectedNode.value) return []
  const ids = new Set<string>()
  for (const e of graphData.value.edges) {
    if (e.source === selectedNode.value.id) ids.add(e.target)
    if (e.target === selectedNode.value.id) ids.add(e.source)
  }
  return simNodes.value.filter(n => ids.has(n.id))
})

// -- Computed: central docs --
const docCenterRenderedNodes = computed(() => docCenterSimNodes.value)
const docCenterRenderedEdges = computed(() => docCenterGraph.value.edges.map(e => {
  const s = docCenterSimNodes.value.find(n => n.id === e.source)
  const t = docCenterSimNodes.value.find(n => n.id === e.target)
  return { ...e, x1: s?.x || 0, y1: s?.y || 0, x2: t?.x || 0, y2: t?.y || 0 }
}))
const docCenterRelatedNodes = computed(() => {
  if (!docCenterSelectedNode.value) return []
  const ids = new Set<string>()
  for (const e of docCenterGraph.value.edges) {
    if (e.source === docCenterSelectedNode.value.id) ids.add(e.target)
    if (e.target === docCenterSelectedNode.value.id) ids.add(e.source)
  }
  return docCenterSimNodes.value.filter(n => ids.has(n.id))
})

// ——— Methods ———
const getNodeRadius = (node: any): number => {
  if (node.isCenter) return 20
  if (node.type === 'kb') return 16 + Math.min((node.doc_count || 0) / 5, 12)
  if (node.type === 'document') return 8
  return 6
}
const getNodeFill = (node: any): string => {
  if (node.type === 'kb') return 'url(#kbGrad)'
  if (node.type === 'document') return 'url(#docGrad)'
  return 'url(#tagGrad)'
}
const getDocCenterNodeFill = (node: any): string => {
  if (node.isCenter) return 'url(#centerGrad)'
  if (node.type === 'kb') return 'url(#kbGrad2)'
  if (node.type === 'document') return 'url(#docGrad2)'
  return 'url(#tagGrad2)'
}
const truncateLabel = (label: string, maxLen: number): string => label.length <= maxLen ? label : label.slice(0, maxLen) + '…'
const getEdgeColor = (edge: any): string => {
  if (edge.type === 'belongs_to') return '#2563eb'
  if (edge.type === 'has_tag') return '#10b981'
  if (edge.type === 'shared_tag') return '#f59e0b'
  if (edge.type === 'vector_similar') return '#7c5cff'
  return '#9aa6bf'
}
const isEdgeHighlighted = (edge: any): boolean => {
  if (!selectedNode.value && !hoveredNode.value) return false
  const active = selectedNode.value || hoveredNode.value
  return edge.source === active?.id || edge.target === active?.id
}

// ——— Physics simulation ———
const initSimulation = () => {
  const nodes = graphData.value.nodes
  const maxNodes = 200
  const limited = nodes.length > maxNodes ? nodes.slice(0, maxNodes) : nodes
  const validIds = new Set(limited.map(n => n.id))
  const limitedEdges = graphData.value.edges.filter(e => validIds.has(e.source) && validIds.has(e.target))
  if (limited.length < nodes.length) {
    graphData.value = { nodes: limited, edges: limitedEdges }
    message.info(`节点数量较多，仅显示前 ${maxNodes} 个节点`)
  }
  simNodes.value = limited.map(n => ({ ...n, x: W / 2 + (Math.random() - 0.5) * 300, y: H / 2 + (Math.random() - 0.5) * 300, vx: 0, vy: 0, fx: null, fy: null }))
  startSimulation()
}
const startSimulation = () => {
  if (simulationRunning.value) return
  simulationRunning.value = true
  let tick = 0
  const maxTicks = 300
  const loop = () => {
    if (!simulationRunning.value) return
    tick++
    stepSimulation(simNodes.value, graphData.value.edges)
    if (tick > maxTicks) { simulationRunning.value = false; return }
    animationId = requestAnimationFrame(loop)
  }
  loop()
}
const stopSimulation = () => {
  simulationRunning.value = false
  if (animationId) { cancelAnimationFrame(animationId); animationId = null }
}
const stepSimulation = (nodes: SimNode[], edges: GraphEdge[]) => {
  if (nodes.length === 0) return
  const alpha = 0.3, repulsion = 600, linkDistance = 80, linkStrength = 0.1, centerStrength = 0.02
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const dx = nodes[i].x - nodes[j].x, dy = nodes[i].y - nodes[j].y
      let dist = Math.sqrt(dx * dx + dy * dy); if (dist < 1) dist = 1
      const force = repulsion / (dist * dist)
      const fx = (dx / dist) * force, fy = (dy / dist) * force
      nodes[i].vx += fx * alpha; nodes[i].vy += fy * alpha
      nodes[j].vx -= fx * alpha; nodes[j].vy -= fy * alpha
    }
  }
  const nodeMap = new Map(nodes.map(n => [n.id, n]))
  for (const edge of edges) {
    const s = nodeMap.get(edge.source), t = nodeMap.get(edge.target)
    if (!s || !t) continue
    const dx = t.x - s.x, dy = t.y - s.y
    let dist = Math.sqrt(dx * dx + dy * dy); if (dist < 1) dist = 1
    const force = (dist - linkDistance) * linkStrength
    const fx = (dx / dist) * force, fy = (dy / dist) * force
    s.vx += fx * alpha; s.vy += fy * alpha
    t.vx -= fx * alpha; t.vy -= fy * alpha
  }
  for (const node of nodes) {
    node.vx += (W / 2 - node.x) * centerStrength * alpha
    node.vy += (H / 2 - node.y) * centerStrength * alpha
  }
  for (const node of nodes) {
    if (node.fx !== null && node.fx !== undefined) node.x = node.fx
    else { node.vx *= 0.85; node.x += node.vx }
    if (node.fy !== null && node.fy !== undefined) node.y = node.fy
    else { node.vy *= 0.85; node.y += node.vy }
    node.x = Math.max(30, Math.min(W - 30, node.x))
    node.y = Math.max(30, Math.min(H - 30, node.y))
  }
}
const restartSimulation = () => {
  for (const n of simNodes.value) { n.vx = (Math.random() - 0.5) * 10; n.vy = (Math.random() - 0.5) * 10 }
  if (!simulationRunning.value) startSimulation()
}

// ——— Document center simulation ———
const startDocCenterSimulation = () => {
  let tick = 0
  const maxTicks = 300
  const loop = () => {
    tick++
    stepSimulation(docCenterSimNodes.value, docCenterGraph.value.edges)
    if (tick > maxTicks) return
    docCenterAnimId = requestAnimationFrame(loop)
  }
  loop()
}
const stopDocCenterSimulation = () => {
  if (docCenterAnimId) { cancelAnimationFrame(docCenterAnimId); docCenterAnimId = null }
}

// -- Interaction --
const onNodeClick = (node: any) => { selectedNode.value = node }
const onDocCenterNodeClick = (node: any) => { docCenterSelectedNode.value = node }
const onNodeHover = (node: GraphNode | null) => { hoveredNode.value = node }
const selectNode = (node: GraphNode) => {
  selectedNode.value = node as SimNode
  const sn = simNodes.value.find(n => n.id === node.id)
  if (sn) { panX.value = canvasWidth.value / 2 - sn.x * zoom.value; panY.value = canvasHeight.value / 2 - sn.y * zoom.value }
}
const selectDocCenterNode = (node: GraphNode) => {
  docCenterSelectedNode.value = node as SimNode
  const sn = docCenterSimNodes.value.find(n => n.id === node.id)
  if (sn) { panX.value = canvasWidth.value / 2 - sn.x * zoom.value; panY.value = canvasHeight.value / 2 - sn.y * zoom.value }
}

// ——— Drag ———
const onNodeDragStart = (e: MouseEvent, node: SimNode) => {
  draggingNode.value = node
  node.fx = node.x; node.fy = node.y
}
const onCanvasMouseDown = (e: MouseEvent) => {
  if (draggingNode.value) return
  isPanning.value = true
  panStart.value = { x: e.clientX, y: e.clientY, px: panX.value, py: panY.value }
}
const onCanvasMouseMove = (e: MouseEvent) => {
  if (draggingNode.value) {
    const dx = (e.clientX - panStart.value.x) / zoom.value
    const dy = (e.clientY - panStart.value.y) / zoom.value
    draggingNode.value.fx = (draggingNode.value.x + dx) as any
    draggingNode.value.fy = (draggingNode.value.y + dy) as any
    draggingNode.value.x += dx
    draggingNode.value.y += dy
    panStart.value.x = e.clientX
    panStart.value.y = e.clientY
    return
  }
  if (!isPanning.value) return
  panX.value = panStart.value.px + (e.clientX - panStart.value.x)
  panY.value = panStart.value.py + (e.clientY - panStart.value.y)
}
const onCanvasMouseUp = () => {
  isPanning.value = false
  if (draggingNode.value) {
    draggingNode.value.fx = null; draggingNode.value.fy = null
    draggingNode.value = null
  }
}
const onWheel = (e: WheelEvent) => {
  const delta = e.deltaY > 0 ? 0.9 : 1.1
  zoom.value = Math.max(0.2, Math.min(3, zoom.value * delta))
}
const zoomIn = () => { zoom.value = Math.min(3, zoom.value * 1.2) }
const zoomOut = () => { zoom.value = Math.max(0.2, zoom.value * 0.8) }
const resetView = () => { zoom.value = 1; panX.value = 0; panY.value = 0 }
const fitView = () => {
  const nodes = activeView.value === 'full' ? simNodes.value : docCenterSimNodes.value
  if (nodes.length === 0) return
  const xs = nodes.map(n => n.x), ys = nodes.map(n => n.y)
  const minX = Math.min(...xs), maxX = Math.max(...xs)
  const minY = Math.min(...ys), maxY = Math.max(...ys)
  const w = maxX - minX + 100, h = maxY - minY + 100
  const scale = Math.min(canvasWidth.value / w, canvasHeight.value / h, 2)
  zoom.value = Math.max(0.3, scale)
  panX.value = (canvasWidth.value - (minX + maxX) * zoom.value) / 2
  panY.value = (canvasHeight.value - (minY + maxY) * zoom.value) / 2
}

// -- View switching --
const switchView = (view: ViewMode) => {
  activeView.value = view
  resetView()
  if (view === 'cross-kb' && crossKbDocs.value.length === 0) {
    loadCrossKbDocs()
  }
}

// ——— Document center view ———
const handleDocSearch = async () => {
  const q = docSearchQuery.value.trim()
  if (!q) return
  docSearching.value = true
  try {
    const res = await searchGraph(q, 'documents', { limit: 20 })
    docSearchResults.value = res.documents || []
    if (docSearchResults.value.length === 0) message.info('未找到匹配文档')
  } catch { message.error('搜索失败') }
  finally { docSearching.value = false }
}
const loadDocumentGraph = async (docPath: string) => {
  docCenterPath.value = docPath
  try {
    const data = await getDocumentGraph(docPath)
    // Mark center node
    const centerId = `doc:${docPath}`
    const nodes = data.nodes.map(n => ({ ...n, isCenter: n.id === centerId || n.path === docPath }))
    // Also check if the node exists with different ID format
    if (!nodes.some(n => n.isCenter)) {
      const docNode = nodes.find(n => n.type === 'document' && n.path === docPath)
      if (docNode) docNode.isCenter = true
    }
    docCenterGraph.value = { nodes, edges: data.edges }
    docCenterSimNodes.value = nodes.map(n => ({
      ...n,
      x: W / 2 + (Math.random() - 0.5) * 200,
      y: H / 2 + (Math.random() - 0.5) * 200,
      vx: 0, vy: 0, fx: null, fy: null,
    }))
    docCenterSelectedNode.value = docCenterSimNodes.value.find(n => n.isCenter) || null
    stopDocCenterSimulation()
    startDocCenterSimulation()
    // Switch to doc-center view if not already
    if (activeView.value !== 'doc-center') activeView.value = 'doc-center'
    message.success(`已加载文档关联图谱: ${docPath.split(/[\\/]/).pop()}`)
  } catch { message.error('加载文档图谱失败') }
}

// ——— Cross-KB analysis ———
const loadCrossKbDocs = async () => {
  crossKbLoading.value = true
  try {
    crossKbDocs.value = await getCrossKbDocuments(50)
  } catch {
    message.warning('跨KB分析需要Neo4j支持，当前不可用')
    crossKbDocs.value = []
  }
  finally { crossKbLoading.value = false }
}

// ——— Path discovery ———
const handlePathSearchA = async () => {
  const q = pathSearchA.value.trim(); if (!q) return
  try {
    const res = await searchGraph(q, 'documents', { limit: 10 })
    pathResultsA.value = res.documents || []
  } catch { pathResultsA.value = [] }
}
const handlePathSearchB = async () => {
  const q = pathSearchB.value.trim(); if (!q) return
  try {
    const res = await searchGraph(q, 'documents', { limit: 10 })
    pathResultsB.value = res.documents || []
  } catch { pathResultsB.value = [] }
}
const selectPathDoc = (which: 'A' | 'B', doc: any) => {
  if (which === 'A') { pathDocA.value = doc.doc_path || doc.path; pathResultsA.value = [] }
  else { pathDocB.value = doc.doc_path || doc.path; pathResultsB.value = [] }
}
const findPath = async () => {
  if (!pathDocA.value || !pathDocB.value) return
  pathFinding.value = true
  pathResult.value = null
  try {
    pathResult.value = await findDocumentPaths(pathDocA.value, pathDocB.value, 4)
    if (pathResult.value && !pathResult.value.found) {
      message.info('未找到关联路径，尝试增加搜索深度或选择其他文档')
    }
  } catch { message.error('路径查找失败') }
  finally { pathFinding.value = false }
}

// -- Data loading --
const loadGraph = async () => {
  graphLoading.value = true
  try {
    const health = await checkHealth()
    neo4jStatus.value = health.healthy ? 'available' : 'unavailable'
    const data = await buildLocalGraph()
    graphData.value = data
    initSimulation()
    try { stats.value = await fetchStats() } catch {}
  } catch (err: any) { message.error(err.message || '加载图谱失败') }
  finally { graphLoading.value = false }
}
const handleRefresh = () => { loadGraph(); message.info('正在刷新图谱...') }
const handleRebuild = async () => {
  rebuilding.value = true
  try {
    const result = await buildBackendGraph(true, true)
    if (result?.success !== false) {
      const r = result?.result || {}
      const p2 = r?.phase2_vector_similarity || {}
      const p3 = r?.phase3_kb_relations || {}
      message.success(`图谱重建成功！\n文档: ${r?.phase1_metadata?.docs_processed || 0}篇\n向量关联: ${p2.total_edges || 0}条 (跨库${p2.cross_kb_edges || 0}条)\nKB间关联: ${p3.total_kb_pairs || 0}对`, 8)
      await loadGraph()
    } else { message.warning('后端图谱构建返回异常，已重新加载本地图谱'); await loadGraph() }
  } catch (err: any) { message.warning(err.message || '后端图谱构建失败，已重新加载本地图谱'); await loadGraph() }
  finally { rebuilding.value = false }
}

// -- Canvas resize --
const updateCanvasSize = () => {
  const ref = activeView.value === 'full' ? svgContainerRef.value : docSvgContainerRef.value || svgContainerRef.value
  if (ref) {
    const rect = ref.getBoundingClientRect()
    canvasWidth.value = rect.width
    canvasHeight.value = rect.height
  }
}

// ——— Lifecycle ———
onMounted(async () => {
  updateCanvasSize()
  window.addEventListener('resize', updateCanvasSize)
  await loadGraph()
})
onUnmounted(() => {
  stopSimulation()
  stopDocCenterSimulation()
  window.removeEventListener('resize', updateCanvasSize)
})
</script>

<style scoped>
.kg-page { position: relative; min-height: calc(100vh - 110px); color: var(--kb-fg); animation: kb-fade-in 0.4s var(--kb-ease-out); }

/* Page header */
.page-header { margin-bottom: 20px; animation: kb-fade-up 0.5s var(--kb-ease-out) both; }
.header-content { display: flex; justify-content: space-between; align-items: center; }
.header-left { display: flex; align-items: center; gap: 16px; }
.header-icon { width: 54px; height: 54px; border-radius: 15px; display: grid; place-items: center; font-size: 25px; color: #fff; background: linear-gradient(135deg, var(--kb-primary), var(--kb-gold-deep)); box-shadow: var(--kb-shadow-primary); }
.header-text h1 { font-size: 26px; font-weight: 700; color: var(--kb-fg); margin: 0 0 3px; letter-spacing: -0.5px; font-family: var(--kb-font-serif); }
.header-text p { font-size: 14px; color: var(--kb-fg-3); margin: 0; }
.header-actions { display: flex; gap: 10px; }
.action-btn { height: 40px; padding: 0 18px; border-radius: 11px; font-size: 14px; display: flex; align-items: center; gap: 7px; }

/* Health Hint */
.health-banner { display: flex; align-items: center; gap: 8px; padding: 10px 18px; background: var(--kb-amber-soft); border: 1px solid rgba(245,158,11,0.3); border-radius: var(--kb-radius); margin-bottom: 16px; font-size: 13px; color: #92400e; }
.health-banner :deep(.anticon) { color: var(--kb-amber); font-size: 16px; }
.health-hint { color: #b45309; margin-left: auto; }

/* View Tabs */
.view-tabs { display: flex; gap: 4px; margin-bottom: 20px; padding: 4px; background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); border-radius: var(--kb-radius); box-shadow: var(--kb-shadow-xs); }
.view-tab { display: flex; align-items: center; gap: 8px; padding: 8px 18px; border-radius: var(--kb-radius-sm); font-size: 14px; font-weight: 600; color: var(--kb-fg-3); cursor: pointer; transition: all 0.25s var(--kb-ease); }
.view-tab:hover { background: var(--kb-bg-subtle); color: var(--kb-fg-2); }
.view-tab.active { background: linear-gradient(135deg, var(--kb-primary), #4f7cff); color: #fff; box-shadow: var(--kb-shadow-primary); }
.view-tab :deep(.anticon) { font-size: 16px; }

/* Stats Row */
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
.stat-card { display: flex; align-items: center; gap: 14px; padding: 18px 22px; background: linear-gradient(135deg, var(--kb-bg-elevated) 0%, rgba(212, 175, 106, 0.04) 100%); border: 1px solid var(--kb-border); border-radius: var(--kb-radius-lg); box-shadow: var(--kb-shadow-sm); animation: kb-fade-up 0.5s var(--kb-ease-out) both; transition: all 0.25s var(--kb-ease); position: relative; overflow: hidden; }
.stat-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent, var(--kb-gold-bright), transparent); opacity: 0; transition: opacity 0.25s; }
.stat-card:hover { transform: translateY(-3px); box-shadow: var(--kb-shadow-md); border-color: var(--kb-gold); }
.stat-card:hover::before { opacity: 1; }
.stat-card-icon { width: 46px; height: 46px; border-radius: 12px; display: grid; place-items: center; font-size: 21px; color: #fff; }
.kb-icon { background: linear-gradient(135deg, var(--kb-primary), var(--kb-gold-deep)); }
.doc-icon { background: linear-gradient(135deg, var(--kb-cyan), #22d3ee); }
.tag-icon { background: linear-gradient(135deg, var(--kb-emerald), #34d399); }
.edge-icon { background: linear-gradient(135deg, var(--kb-violet), #a78bfa); }
.stat-card-info { display: flex; flex-direction: column; }
.stat-card-value { font-size: 28px; font-weight: 700; color: var(--kb-fg); line-height: 1.1; font-feature-settings: 'tnum'; font-family: var(--kb-font-serif); }
.stat-card-label { font-size: 11px; color: var(--kb-fg-3); margin-top: 3px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }

/* Graph Layout */
.graph-layout { display: grid; grid-template-columns: 1fr 340px; gap: 20px; }

/* Canvas */
.graph-canvas-wrapper { position: relative; background: linear-gradient(135deg, var(--kb-bg-elevated), var(--kb-bg-subtle)); border: 1px solid var(--kb-border); border-radius: var(--kb-radius-lg); box-shadow: var(--kb-shadow-md); overflow: hidden; min-height: 600px; }
.svg-container { position: relative; width: 100%; height: 600px; cursor: grab; }
.svg-container:active { cursor: grabbing; }
.svg-container svg { display: block; }

/* Toolbar */
.graph-toolbar { position: absolute; top: 14px; right: 14px; z-index: 10; display: flex; align-items: center; gap: 4px; padding: 6px 10px; background: rgba(255,255,255,0.92); backdrop-filter: blur(10px); border: 1px solid var(--kb-border); border-radius: 11px; box-shadow: var(--kb-shadow-sm); }
.tool-btn { width: 32px; height: 32px; display: grid; place-items: center; color: var(--kb-fg-3); }
.tool-btn:hover { background: var(--kb-primary-tint); color: var(--kb-primary); }

/* Legend */
.graph-legend { position: absolute; bottom: 14px; left: 14px; z-index: 10; display: flex; gap: 14px; padding: 8px 16px; background: rgba(255,255,255,0.92); backdrop-filter: blur(10px); border: 1px solid var(--kb-border); border-radius: 11px; box-shadow: var(--kb-shadow-sm); }
.legend-item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--kb-fg-2); font-weight: 600; }
.legend-dot { width: 12px; height: 12px; border-radius: 50%; }
.kb-dot { background: linear-gradient(135deg, #4f7cff, #2563eb); }
.doc-dot { background: linear-gradient(135deg, #22d3ee, #06b6d4); }
.tag-dot { background: linear-gradient(135deg, #34d399, #10b981); }
.center-dot { background: linear-gradient(135deg, #fbbf24, #f59e0b); }
.legend-line { width: 20px; height: 2px; background: #f59e0b; border-radius: 2px; }
.shared-line { background: repeating-linear-gradient(90deg, #f59e0b, #f59e0b 4px, transparent 4px, transparent 7px); }
.vector-line { background: repeating-linear-gradient(90deg, #7c5cff, #7c5cff 4px, transparent 4px, transparent 7px); }

/* Node Count */
.node-count-info { position: absolute; top: 14px; left: 14px; z-index: 10; padding: 4px 12px; background: rgba(255,255,255,0.92); backdrop-filter: blur(10px); border: 1px solid var(--kb-border); border-radius: 999px; font-size: 11px; color: var(--kb-fg-3); font-weight: 600; }

/* SVG Nodes/Edges */
.graph-edge { transition: stroke-opacity 0.2s, stroke-width 0.2s; }
.edge-shared { stroke-dasharray: 4,3; }
.graph-node-group { cursor: pointer; }
.graph-node-circle { stroke: #fff; stroke-width: 2; transition: r 0.2s; }
.node-hover { stroke-width: 3; }
.select-ring { animation: kb-pulse-ring 1.5s ease-out infinite; }
.graph-node-label { fill: var(--kb-fg); pointer-events: none; user-select: none; }

/* Loading/Empty */
.canvas-loading, .canvas-empty { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; background: rgba(255,255,255,0.85); backdrop-filter: blur(6px); z-index: 5; }
.empty-icon { width: 64px; height: 64px; border-radius: 20px; display: grid; place-items: center; font-size: 28px; color: var(--kb-primary); background: var(--kb-primary-soft); }
.empty-text { font-size: 16px; color: var(--kb-fg-3); margin: 0; }
.empty-hint { font-size: 13px; color: var(--kb-fg-mute); margin: 4px 0 0; }

/* Detail Panel */
.detail-panel { background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); border-radius: var(--kb-radius-lg); box-shadow: var(--kb-shadow-md); display: flex; flex-direction: column; max-height: calc(100vh - 280px); overflow: hidden; }
.filter-section { padding: 16px; border-bottom: 1px solid var(--kb-border); }
.filter-input { margin-bottom: 12px; }
.filter-tags { display: flex; gap: 8px; flex-wrap: wrap; }
.filter-tag { font-size: 12px; padding: 2px 10px; border-radius: 999px; }
.kb-filter :deep(.ant-tag-checkable-checked) { background: var(--kb-primary) !important; color: #fff !important; border-color: var(--kb-primary) !important; }
.doc-filter :deep(.ant-tag-checkable-checked) { background: var(--kb-cyan) !important; color: #fff !important; border-color: var(--kb-cyan) !important; }
.tag-filter :deep(.ant-tag-checkable-checked) { background: var(--kb-emerald) !important; color: #fff !important; border-color: var(--kb-emerald) !important; }

/* Node Detail */
.node-detail { padding: 18px; overflow-y: auto; flex: 1; }
.detail-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.detail-icon { width: 48px; height: 48px; border-radius: 13px; display: grid; place-items: center; font-size: 22px; color: #fff; flex-shrink: 0; }
.icon-kb { background: linear-gradient(135deg, var(--kb-primary), #4f7cff); }
.icon-document { background: linear-gradient(135deg, var(--kb-cyan), #22d3ee); }
.icon-tag { background: linear-gradient(135deg, var(--kb-emerald), #34d399); }
.detail-titles { flex: 1; min-width: 0; }
.detail-name { font-size: 17px; font-weight: 700; color: var(--kb-fg); margin: 0 0 4px; word-break: break-word; }
.type-tag { font-size: 11px; }
.type-kb { background: var(--kb-primary-soft) !important; color: var(--kb-primary-hover) !important; border-color: transparent !important; }
.type-document { background: var(--kb-cyan-soft) !important; color: #0891b2 !important; border-color: transparent !important; }
.type-tag { background: var(--kb-emerald-soft) !important; color: #059669 !important; border-color: transparent !important; }
.detail-desc { font-size: 13px; color: var(--kb-fg-3); line-height: 1.6; margin-bottom: 16px; padding: 12px; background: var(--kb-bg-subtle); border-radius: var(--kb-radius); }
.detail-meta { display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px; }
.meta-item { display: flex; flex-direction: column; gap: 4px; }
.meta-label { font-size: 11px; color: var(--kb-fg-mute); text-transform: uppercase; letter-spacing: 0.4px; }
.meta-value { font-size: 14px; color: var(--kb-fg); font-weight: 500; }
.mono-path { font-family: var(--kb-font-mono); font-size: 12px; word-break: break-all; }
.meta-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.related-section { border-top: 1px solid var(--kb-border); padding-top: 16px; }
.related-title { display: flex; align-items: center; gap: 6px; font-size: 14px; font-weight: 700; color: var(--kb-fg); margin-bottom: 12px; }
.related-title :deep(.anticon) { color: var(--kb-primary); }
.related-list { display: flex; flex-direction: column; gap: 8px; max-height: 300px; overflow-y: auto; }
.related-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: var(--kb-bg-subtle); border-radius: var(--kb-radius-sm); cursor: pointer; transition: all 0.2s; }
.related-item:hover { background: var(--kb-primary-tint); }
.related-icon { width: 28px; height: 28px; border-radius: 8px; display: grid; place-items: center; font-size: 13px; color: #fff; flex-shrink: 0; }
.related-name { flex: 1; font-size: 13px; color: var(--kb-fg); font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.related-type { font-size: 11px; color: var(--kb-fg-mute); }
.related-empty { text-align: center; padding: 20px; font-size: 13px; color: var(--kb-fg-mute); }

/* Unselected */
.no-selection { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px 20px; text-align: center; }
.no-sel-icon { width: 64px; height: 64px; border-radius: 20px; display: grid; place-items: center; font-size: 28px; color: var(--kb-primary); background: var(--kb-primary-soft); margin-bottom: 16px; }
.no-sel-text { font-size: 15px; color: var(--kb-fg-2); font-weight: 600; margin: 0 0 6px; }
.no-sel-hint { font-size: 13px; color: var(--kb-fg-mute); margin: 0; }

/* ============ Document Center View ============ */
.doc-center-layout { display: flex; flex-direction: column; gap: 20px; }
.doc-center-search { max-width: 800px; margin: 0 auto; width: 100%; }
.doc-center-search :deep(.ant-input-search-large .ant-input-affix-wrapper) { border-radius: 12px 0 0 12px; height: 52px; }
.doc-center-search :deep(.ant-input-search-large .ant-btn) { height: 52px; border-radius: 0 12px 12px 0; }
.doc-search-results { margin-top: 12px; background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); border-radius: var(--kb-radius-lg); box-shadow: var(--kb-shadow-md); max-height: 320px; overflow-y: auto; }
.doc-search-item { display: flex; align-items: center; gap: 12px; padding: 12px 18px; cursor: pointer; transition: all 0.2s; border-bottom: 1px solid var(--kb-border); }
.doc-search-item:last-child { border-bottom: none; }
.doc-search-item:hover { background: var(--kb-primary-tint); }
.doc-search-icon { font-size: 18px; color: var(--kb-cyan); flex-shrink: 0; }
.doc-search-info { flex: 1; min-width: 0; }
.doc-search-name { font-size: 14px; font-weight: 600; color: var(--kb-fg); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.doc-search-path { font-size: 12px; color: var(--kb-fg-mute); font-family: var(--kb-font-mono); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.doc-center-empty { padding: 60px 20px; text-align: center; }

/* ============ Cross-KB Analysis View ============ */
.cross-kb-layout { display: flex; flex-direction: column; gap: 20px; }
.cross-kb-header { text-align: center; margin-bottom: 8px; }
.section-subtitle { font-size: 20px; font-weight: 800; color: var(--kb-fg); margin: 0 0 8px; }
.section-desc { font-size: 14px; color: var(--kb-fg-3); margin: 0; }
.cross-kb-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; }
.cross-kb-card { padding: 20px; background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); border-radius: var(--kb-radius-lg); box-shadow: var(--kb-shadow-sm); cursor: pointer; transition: all 0.25s var(--kb-ease); animation: kb-fade-up 0.4s var(--kb-ease-out) both; }
.cross-kb-card:hover { transform: translateY(-4px); box-shadow: var(--kb-shadow-lg); border-color: var(--kb-gold); }
.cross-kb-card-header { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.cross-kb-icon { font-size: 24px; color: var(--kb-primary); flex-shrink: 0; }
.cross-kb-card-info { flex: 1; min-width: 0; }
.cross-kb-card-name { font-size: 15px; font-weight: 700; color: var(--kb-fg); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cross-kb-card-path { font-size: 11px; color: var(--kb-fg-mute); font-family: var(--kb-font-mono); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cross-kb-card-body { display: flex; flex-direction: column; gap: 10px; }
.cross-kb-bridges { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.bridge-label { font-size: 12px; color: var(--kb-fg-3); font-weight: 600; }
.cross-kb-relation { display: flex; align-items: center; gap: 10px; }
.relation-badge { padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; }
.relation-shared_tag { background: var(--kb-amber-soft); color: #92400e; }
.relation-vector_similar { background: #ede9fe; color: #6d28d9; }
.relation-agent_judged { background: var(--kb-primary-soft); color: var(--kb-primary-hover); }
.related-count { font-size: 12px; color: var(--kb-fg-3); }
.cross-kb-tags { display: flex; gap: 4px; flex-wrap: wrap; }
.cross-kb-empty { padding: 60px 20px; text-align: center; }

/* ============ Path Discovery View ============ */
.path-layout { display: flex; flex-direction: column; gap: 24px; max-width: 900px; margin: 0 auto; width: 100%; }
.path-header { text-align: center; }
.path-selector { display: flex; align-items: flex-start; gap: 20px; }
.path-input-group { flex: 1; }
.path-label { display: block; font-size: 13px; font-weight: 700; color: var(--kb-fg-2); margin-bottom: 8px; }
.path-arrow { margin-top: 36px; font-size: 24px; color: var(--kb-fg-mute); flex-shrink: 0; }
.path-search-results { margin-top: 8px; background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); border-radius: var(--kb-radius); box-shadow: var(--kb-shadow-md); max-height: 240px; overflow-y: auto; }
.path-search-item { display: flex; align-items: center; gap: 8px; padding: 10px 14px; cursor: pointer; font-size: 13px; color: var(--kb-fg); transition: all 0.2s; border-bottom: 1px solid var(--kb-border); }
.path-search-item:last-child { border-bottom: none; }
.path-search-item:hover { background: var(--kb-primary-tint); }
.path-search-item.selected { background: var(--kb-primary-soft); color: var(--kb-primary-hover); font-weight: 600; }
.path-search-path { font-size: 11px; color: var(--kb-fg-mute); font-family: var(--kb-font-mono); margin-left: auto; }
.path-selected { display: flex; align-items: center; gap: 6px; margin-top: 8px; padding: 8px 12px; background: var(--kb-emerald-soft); border-radius: var(--kb-radius-sm); font-size: 13px; color: #059669; }
.path-selected :deep(.anticon) { color: var(--kb-emerald); }
.path-action { text-align: center; }
.path-result { }
.path-chain { background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); border-radius: var(--kb-radius-lg); box-shadow: var(--kb-shadow-md); padding: 24px; }
.path-chain-header { display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: 700; color: var(--kb-emerald); margin-bottom: 20px; }
.path-found-icon { font-size: 22px; }
.path-chain-list { display: flex; flex-direction: column; gap: 0; }
.path-step { display: flex; align-items: center; gap: 14px; padding: 14px 0; position: relative; }
.path-step:not(:last-child)::after { content: ''; position: absolute; left: 19px; top: 48px; width: 2px; height: calc(100% - 34px); background: linear-gradient(var(--kb-primary), var(--kb-border)); }
.path-step-num { width: 38px; height: 38px; border-radius: 11px; display: grid; place-items: center; font-size: 15px; font-weight: 800; color: #fff; background: linear-gradient(135deg, var(--kb-primary), #4f7cff); flex-shrink: 0; z-index: 1; box-shadow: var(--kb-shadow-primary); }
.path-step-info { flex: 1; }
.path-step-name { font-size: 15px; font-weight: 600; color: var(--kb-fg); margin-bottom: 3px; }
.path-step-kb { display: flex; align-items: center; gap: 4px; font-size: 12px; color: var(--kb-fg-3); }
.path-step-kb :deep(.anticon) { font-size: 11px; }
.path-step-arrow { font-size: 18px; color: var(--kb-fg-mute); flex-shrink: 0; }
.path-not-found { display: flex; align-items: center; gap: 8px; padding: 24px; background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); border-radius: var(--kb-radius-lg); font-size: 14px; color: var(--kb-fg-3); }
.path-not-found :deep(.anticon) { color: var(--kb-rose); font-size: 20px; }

/* Responsive */
@media (max-width: 1100px) {
  .graph-layout { grid-template-columns: 1fr; }
  .detail-panel { max-height: 400px; }
  .stats-row { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
  .header-content { flex-direction: column; gap: 16px; }
  .view-tabs { flex-wrap: wrap; }
  .path-selector { flex-direction: column; }
  .path-arrow { display: none; }
  .cross-kb-grid { grid-template-columns: 1fr; }
}
</style>

