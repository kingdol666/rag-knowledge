<template>
  <div class="kb-manage-page">
    <!-- Page header -->
    <header class="page-header">
      <div class="header-content">
        <div class="header-left">
          <div class="header-icon">
            <DatabaseOutlined />
          </div>
          <div class="header-text">
            <h1 class="header-title">{{ $t('kb.title') }}</h1>
            <p class="header-subtitle">{{ $t('kb.subtitle') }}</p>
          </div>
        </div>
        <div class="header-actions">
          <a-button class="action-btn" @click="handleRefresh">
            <ReloadOutlined />
            <span>{{ $t('action.refresh') }}</span>
          </a-button>
          <a-button type="primary" class="action-btn" @click="showCreateDocDialog = true">
            <PlusOutlined />
            <span>{{ $t('kb.createDocTitle') }}</span>
          </a-button>
        </div>
      </div>
    </header>

    <main class="main-content">
      <div class="manage-layout">
        <!-- Left KB list -->
        <aside class="kb-list-panel">
          <div class="panel-header">
            <div class="panel-title">
              <AppstoreOutlined class="panel-icon" />
              <span>{{ $t('graph.kbs') }}</span>
            </div>
            <a-badge :count="catalog.length" :number-style="{ backgroundColor: 'var(--kb-primary)' }" />
          </div>
          <div class="panel-body">
            <a-spin :spinning="loading">
              <div v-if="catalog.length === 0 && !loading" class="empty-state">
                <a-empty :description="$t('kb.noKb')" />
              </div>
              <template v-for="kb in catalog" :key="kb.kbId">
                <!-- Top-level KB item -->
                <div
                  :class="['kb-item', { active: activeKb?.kbId === kb.kbId }]"
                  @click="selectKb(kb)"
                >
                  <div
                    class="kb-expand-btn"
                    @click="toggleKbExpand(kb, $event)"
                  >
                    <a-spin v-if="loadingSubKbs.has(kb.kbId)" size="small" />
                    <RightOutlined v-else-if="!expandedKbIds.has(kb.kbId)" class="expand-icon" />
                    <DownOutlined v-else class="expand-icon" />
                  </div>
                  <div class="kb-item-icon">
                    <DatabaseOutlined />
                  </div>
                  <div class="kb-item-body">
                    <div class="kb-item-name">{{ kb.name }}</div>
                    <div class="kb-item-desc">{{ kb.description || '无描述' }}</div>
                    <div class="kb-item-stat">
                      <FileTextOutlined />
                      <span>{{ kb.documentCount }} 篇</span>
                    </div>
                  </div>
                </div>
                <!-- Sub-KB list -->
                <div v-if="expandedKbIds.has(kb.kbId)" class="sub-kb-list">
                  <div
                    v-for="subKb in (subKbMap[kb.kbId] || [])"
                    :key="subKb.kbId"
                    :class="['kb-item sub-kb-item', { active: activeKb?.kbId === subKb.kbId }]"
                    @click="selectKb(subKb)"
                  >
                    <div class="sub-kb-indent"></div>
                    <div class="kb-item-icon sub-icon">
                      <FolderOutlined v-if="activeKb?.kbId !== subKb.kbId" />
                      <FolderOpenOutlined v-else />
                    </div>
                    <div class="kb-item-body">
                      <div class="kb-item-name">{{ subKb.name }}</div>
                      <div class="kb-item-stat">
                        <FileTextOutlined />
                        <span>{{ subKb.documentCount }} 篇</span>
                      </div>
                    </div>
                  </div>
                  <div v-if="(subKbMap[kb.kbId] || []).length === 0 && !loadingSubKbs.has(kb.kbId)" class="sub-kb-empty">
                    无子知识库
                  </div>
                </div>
              </template>
            </a-spin>
          </div>
        </aside>

        <!-- Right document management -->
        <section class="doc-panel">
          <div v-if="activeKb" class="doc-panel-content">
            <!-- Breadcrumb navigation -->
            <div class="doc-breadcrumb">
              <a-button type="link" size="small" @click="goTopLevel">
                <DatabaseOutlined />
                <span>全部知识库</span>
              </a-button>
              <template v-for="(histKb, hi) in kbNavHistory" :key="histKb.kbId">
                <span class="breadcrumb-sep">/</span>
                <a-button type="link" size="small" @click="navigateToKb(histKb)">{{ histKb.name }}</a-button>
              </template>
              <span class="breadcrumb-sep">/</span>
              <span class="breadcrumb-current">{{ activeKb.name }}</span>
            </div>

            <!-- Document list header -->
            <div class="doc-list-header">
              <div class="doc-list-title">
                <h2 class="doc-list-name">{{ activeKb.name }}</h2>
                <a-tag color="blue">{{ filteredDocs.length }} 篇文档</a-tag>
                <a-tag v-if="subKbList.length > 0" color="purple">{{ subKbList.length }} 个子库</a-tag>
              </div>
              <div class="doc-list-actions">
                <a-input-search
                  v-model:value="docFilter"
                  placeholder="搜索文档名..."
                  size="small"
                  style="width: 200px;"
                  allow-clear
                />
                <a-button type="primary" size="small" @click="showCreateDocDialog = true">
                  <PlusOutlined />
                  新建
                </a-button>
              </div>
            </div>

            <!-- Sub-KB card area -->
            <div v-if="subKbList.length > 0" class="sub-kb-section">
              <div class="section-title">
                <FolderOpenOutlined />
                <span>子知识库 ({{ subKbList.length }})</span>
              </div>
              <div class="sub-kb-grid">
                <div
                  v-for="subKb in subKbList"
                  :key="subKb.kbId"
                  class="sub-kb-card"
                  @click="openSubKb(subKb)"
                >
                  <div class="sub-kb-card-icon">
                    <FolderOutlined />
                  </div>
                  <div class="sub-kb-card-body">
                    <div class="sub-kb-card-name" :title="subKb.name">{{ subKb.name }}</div>
                    <div class="sub-kb-card-desc" :title="subKb.description">{{ subKb.description || '无描述' }}</div>
                    <div class="sub-kb-card-stat">
                      <FileTextOutlined />
                      <span>{{ subKb.documentCount }} 篇</span>
                    </div>
                  </div>
                  <div class="sub-kb-card-arrow">
                    <RightOutlined />
                  </div>
                </div>
              </div>
            </div>

            <!-- Document card area -->
            <div class="doc-table-wrapper">
              <a-spin :spinning="loading">
                <div v-if="filteredDocs.length === 0 && !loading" class="empty-state">
                  <a-empty description="暂无文档">
                    <a-button type="primary" @click="showCreateDocDialog = true">
                      <PlusOutlined /> 新建文档
                    </a-button>
                  </a-empty>
                </div>
                <div v-else class="doc-grid">
                  <div
                    v-for="doc in filteredDocs"
                    :key="doc.path"
                    class="doc-card"
                    @click="openDocPreview(doc)"
                  >
                    <div class="doc-card-header">
                      <div class="doc-card-icon">
                        <FileTextOutlined />
                      </div>
                      <div class="doc-card-info">
                        <div class="doc-card-name" :title="doc.name">{{ doc.name }}</div>
                        <div class="doc-card-desc" :title="doc.description">{{ doc.description || '无描述' }}</div>
                      </div>
                      <a-dropdown :trigger="['click']" @click.stop>
                        <a-button type="text" size="small" class="doc-more-btn">
                          <EllipsisOutlined />
                        </a-button>
                        <template #overlay>
                          <a-menu>
                            <a-menu-item @click="openEditMetaDialog(doc)">
                              <EditOutlined />
                              <span>编辑元数据</span>
                            </a-menu-item>
                            <a-menu-item @click="openEditContentDialog(doc)">
                              <FormOutlined />
                              <span>编辑内容</span>
                            </a-menu-item>
                            <a-menu-item @click="openTagsDialog(doc)">
                              <TagsOutlined />
                              <span>管理标签</span>
                            </a-menu-item>
                            <a-menu-item @click="openMoveDialog(doc)">
                              <DragOutlined />
                              <span>移动到其他库</span>
                            </a-menu-item>
                            <a-menu-divider />
                            <a-menu-item danger @click="handleDeleteDoc(doc)">
                              <DeleteOutlined />
                              <span>删除文档</span>
                            </a-menu-item>
                          </a-menu>
                        </template>
                      </a-dropdown>
                    </div>
                    <div class="doc-card-footer">
                      <a-tag v-if="doc.file_type" size="small" color="cyan">{{ doc.file_type }}</a-tag>
                      <div class="doc-tags">
                        <a-tag v-for="t in (doc.tags || []).slice(0, 3)" :key="t" size="small" color="green">{{ t }}</a-tag>
                        <span v-if="(doc.tags || []).length > 3" class="more-tags">+{{ (doc.tags || []).length - 3 }}</span>
                      </div>
                      <span v-if="doc.file_size" class="doc-size">{{ formatFileSize(doc.file_size) }}</span>
                    </div>
                  </div>
                </div>
              </a-spin>
            </div>
          </div>

          <!-- Unselected state -->
          <div v-else class="no-selection">
            <div class="no-sel-icon"><DatabaseOutlined /></div>
            <p class="no-sel-text">选择左侧知识库查看文档</p>
          </div>
        </section>
      </div>
    </main>

    <!-- New document dialog -->
    <a-modal v-model:open="showCreateDocDialog" title="新建文档" :width="640" @cancel="showCreateDocDialog = false">
      <a-form :model="createForm" layout="vertical">
        <a-form-item label="目标知识库" required>
          <a-select
            v-model:value="createForm.kbId"
            placeholder="选择知识库"
            :options="catalog.map(kb => ({ value: kb.kbId, label: kb.name }))"
          />
        </a-form-item>
        <a-form-item label="文档名称" required>
          <a-input v-model:value="createForm.name" placeholder="输入文档名称（自动添加 .md 后缀）" />
        </a-form-item>
        <a-form-item label="描述">
          <a-input v-model:value="createForm.description" placeholder="简要描述文档内容（可选）" />
        </a-form-item>
        <a-form-item label="文档内容">
          <a-textarea
            v-model:value="createForm.content"
            :rows="8"
            placeholder="输入 Markdown 内容..."
            class="content-editor"
          />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-button @click="showCreateDocDialog = false">取消</a-button>
        <a-button type="primary" :loading="submitting" @click="handleCreateDoc">创建</a-button>
      </template>
    </a-modal>

    <!-- Edit metadata dialog -->
    <a-modal v-model:open="showEditMetaDialog" title="编辑元数据" :width="520" @cancel="showEditMetaDialog = false">
      <a-form :model="editMetaForm" layout="vertical">
        <a-form-item label="文档名称" required>
          <a-input v-model:value="editMetaForm.name" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="editMetaForm.description" :rows="3" />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-button @click="showEditMetaDialog = false">取消</a-button>
        <a-button type="primary" :loading="submitting" @click="handleEditMeta">保存</a-button>
      </template>
    </a-modal>

    <!-- Edit content dialog -->
    <a-modal v-model:open="showEditContentDialog" title="编辑文档内容" :width="800" @cancel="showEditContentDialog = false">
      <div class="edit-content-wrapper">
        <a-spin :spinning="contentLoading">
          <a-textarea
            v-model:value="editContentValue"
            :rows="20"
            class="content-editor"
            placeholder="加载中..."
          />
        </a-spin>
      </div>
      <template #footer>
        <a-button @click="showEditContentDialog = false">取消</a-button>
        <a-button type="primary" :loading="submitting" @click="handleEditContent">保存内容</a-button>
      </template>
    </a-modal>

    <!-- Tag management dialog -->
    <a-modal v-model:open="showTagsDialog" title="管理标签" :width="520" @cancel="showTagsDialog = false">
      <div class="tags-dialog-content">
        <p class="tags-hint">为文档 <strong>{{ editingDoc?.name }}</strong> 管理标签</p>
        <div class="tags-current">
          <a-tag
            v-for="(tag, i) in editingTags"
            :key="i"
            closable
            color="green"
            @close="removeTag(i)"
          >{{ tag }}</a-tag>
          <span v-if="editingTags.length === 0" class="no-tags">暂无标签</span>
        </div>
        <a-divider />
        <div class="tags-add">
          <a-input
            v-model:value="newTagValue"
            placeholder="输入标签后回车添加"
            @press-enter="addTag"
          />
          <a-button type="primary" @click="addTag">添加</a-button>
        </div>
        <div v-if="allTags.length > 0" class="tags-suggest">
          <p class="tags-suggest-title">已有标签（点击添加）：</p>
          <div class="tags-suggest-list">
            <a-tag
              v-for="t in allTags.filter(t => !editingTags.includes(t))"
              :key="t"
              class="suggest-tag"
              @click="addSuggestedTag(t)"
            >+ {{ t }}</a-tag>
          </div>
        </div>
      </div>
      <template #footer>
        <a-button @click="showTagsDialog = false">取消</a-button>
        <a-button type="primary" :loading="submitting" @click="handleSaveTags">保存标签</a-button>
      </template>
    </a-modal>

    <!-- Move document dialog -->
    <a-modal v-model:open="showMoveDialog" title="移动文档" :width="480" @cancel="showMoveDialog = false">
      <div class="move-dialog-content">
        <p class="move-hint">将文档 <strong>{{ editingDoc?.name }}</strong> 移动到：</p>
        <a-select
          v-model:value="moveTargetKbId"
          placeholder="选择目标知识库"
          style="width: 100%;"
          :options="catalog.filter(kb => kb.kbId !== activeKb?.kbId).map(kb => ({ value: kb.kbId, label: kb.name }))"
        />
      </div>
      <template #footer>
        <a-button @click="showMoveDialog = false">取消</a-button>
        <a-button type="primary" :loading="submitting" @click="handleMoveDoc">移动</a-button>
      </template>
    </a-modal>

    <!-- Document preview drawer — format-aware rendering -->
    <a-drawer
      v-model:open="showPreviewDrawer"
      :title="previewDoc?.name || '文档预览'"
      placement="right"
      :width="drawerWidth"
      class="doc-preview-drawer"
    >
      <a-spin :spinning="previewLoading">
        <!-- Meta bar -->
        <div class="preview-meta-bar" v-if="previewDoc">
          <a-tag color="blue">{{ previewDoc.file_type }}</a-tag>
          <a-tag v-for="t in (previewDoc.tags || [])" :key="t" color="green">{{ t }}</a-tag>
          <span v-if="previewDoc.file_size" class="preview-size">{{ formatFileSize(previewDoc.file_size) }}</span>
          <a-button type="link" size="small" class="preview-fullscreen-btn" @click="openFullPreview">
            <ExpandOutlined /> 全屏
          </a-button>
        </div>

        <!-- MARKDOWN preview (server-side iframe with image-path rewriting) -->
        <div v-if="previewType === 'markdown' && previewDocId" class="preview-body preview-markdown">
          <iframe
            :src="`/api/preview/markdown-preview?id=${previewDocId}`"
            class="preview-iframe"
            frameborder="0"
            :title="previewDoc?.name"
          />
        </div>
        <!-- MARKDOWN fallback (client-side, no file ID available) -->
        <div v-else-if="previewType === 'markdown' && !previewDocId" class="preview-body preview-markdown-client">
          <div class="markdown-body" v-html="renderedMarkdown"></div>
          <div v-if="previewTruncated" class="preview-more">
            <a-button :loading="previewLoading" @click="loadMorePreview">加载更多</a-button>
          </div>
        </div>

        <!-- IMAGE preview -->
        <div v-else-if="previewType === 'image'" class="preview-body preview-image-wrapper">
          <img
            :src="`/api/preview/file?path=${encodeURIComponent(previewDoc?.path || '')}`"
            :alt="previewDoc?.name"
            class="preview-img"
            loading="lazy"
          />
        </div>

        <!-- PDF preview -->
        <div v-else-if="previewType === 'pdf'" class="preview-body preview-pdf-wrapper">
          <iframe
            :src="`/api/preview/file?path=${encodeURIComponent(previewDoc?.path || '')}`"
            class="preview-iframe"
            frameborder="0"
          />
        </div>

        <!-- TEXT / CODE preview -->
        <div v-else-if="previewType === 'text' || previewType === 'code'" class="preview-body preview-text">
          <pre><code :class="previewLanguage">{{ previewContent }}</code></pre>
          <div v-if="previewTruncated" class="preview-more">
            <a-button :loading="previewLoading" @click="loadMorePreview">
              <DownOutlined /> 加载更多
            </a-button>
          </div>
        </div>

        <!-- UNSUPPORTED format fallback -->
        <div v-else class="preview-body preview-unsupported">
          <div class="preview-unsupported-icon">
            <FileTextOutlined />
          </div>
          <p>{{ previewTypeLabel }} 格式暂不支持内嵌预览</p>
          <a-button type="primary" size="small" @click="openFullPreview">
            <ExportOutlined /> 在新窗口查看
          </a-button>
        </div>
      </a-spin>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { message, Modal } from 'ant-design-vue'
import {
  DatabaseOutlined, ReloadOutlined, PlusOutlined,
  AppstoreOutlined, FileTextOutlined, EllipsisOutlined,
  EditOutlined, FormOutlined, TagsOutlined, DragOutlined,
  DeleteOutlined, DownOutlined,
  RightOutlined, FolderOutlined, FolderOpenOutlined,
  ExpandOutlined, ExportOutlined,
} from '@ant-design/icons-vue'
import { useKbDocuments } from '~/composables/useKbDocuments'
import type { KbDoc } from '~/composables/useKbDocuments'
import type { KbCatalogEntry } from '~/composables/useKnowledgeSearch'
import { renderMarkdown } from '~/utils/markdown'
import { useMarkdownRenderer } from '~/composables/useMarkdownRenderer'
import 'katex/dist/katex.min.css'

const {
  loading, fetchCatalog, fetchSubCatalog, fetchDocuments, readDocument,
  createDocument, updateDocumentMeta, updateDocumentContent,
  deleteDocument, moveDocument, updateDocumentTags, fetchAllTags,
} = useKbDocuments()

// Data
const catalog = ref<KbCatalogEntry[]>([])
const activeKb = ref<KbCatalogEntry | null>(null)
const documents = ref<KbDoc[]>([])
const subKbList = ref<KbCatalogEntry[]>([])
const allTags = ref<string[]>([])
const docFilter = ref('')

// Left panel expand state
const expandedKbIds = ref<Set<string>>(new Set())
const subKbMap = ref<Record<string, KbCatalogEntry[]>>({})
const loadingSubKbs = ref<Set<string>>(new Set())

// Breadcrumb navigation history
const kbNavHistory = ref<KbCatalogEntry[]>([])

// Dialog state
const showCreateDocDialog = ref(false)
const showEditMetaDialog = ref(false)
const showEditContentDialog = ref(false)
const showTagsDialog = ref(false)
const showMoveDialog = ref(false)
const showPreviewDrawer = ref(false)
const submitting = ref(false)
const contentLoading = ref(false)

// Form
const createForm = ref({ kbId: '', name: '', description: '', content: '' })
const editMetaForm = ref({ name: '', description: '' })
const editContentValue = ref('')
const editingDoc = ref<KbDoc | null>(null)
const editingTags = ref<string[]>([])
const newTagValue = ref('')
const moveTargetKbId = ref('')

// Preview
const previewDoc = ref<KbDoc | null>(null)
const previewContent = ref('')
const previewLoading = ref(false)
const previewTruncated = ref(false)
const previewOffset = ref(0)

// ── Preview type detection ──────────────────────────────────
/** Detect the preview rendering mode from a document's file_type / extension. */
function detectPreviewType(doc: KbDoc): string {
  const type = (doc.file_type || '').toLowerCase()
  const name = (doc.name || '').toLowerCase()
  const ext = name.includes('.') ? name.split('.').pop()! : ''

  // Images
  if (/^(jpg|jpeg|png|gif|webp|svg|bmp|ico)$/.test(type) ||
      /^(jpg|jpeg|png|gif|webp|svg|bmp|ico)$/.test(ext)) return 'image'
  // PDF
  if (type === 'pdf' || ext === 'pdf') return 'pdf'
  // Markdown
  if (/^(md|markdown)$/.test(type) || /^(md|markdown)$/.test(ext)) return 'markdown'
  // Code files
  if (/^(js|ts|jsx|tsx|py|java|go|rs|c|cpp|h|css|vue|sh|bat|sql|rb|php|swift)$/.test(ext)) return 'code'
  // Office documents
  if (/^(docx?|xlsx?|pptx?)$/.test(type) || /^(docx?|xlsx?|pptx?)$/.test(ext)) return 'unsupported'

  return 'text'  // default: treat as text
}

const previewType = computed(() => previewDoc.value ? detectPreviewType(previewDoc.value) : 'unknown')
const previewDocId = computed(() => previewDoc.value?.doc_id || '')
const previewTypeLabel = computed(() => {
  const map: Record<string,string> = {markdown:'Markdown',image:'图片',pdf:'PDF',code:'代码',text:'文本',unsupported:'此',unknown:'此'}
  return map[previewType.value] || '此'
})

/** Client-side markdown renderer (fallback when doc has no tree-fs file ID).
 *  Uses the shared engine with KaTeX math + GFM. */
const renderedMarkdown = computed(() => {
  if (previewType.value !== 'markdown') return ''
  let md = previewContent.value || ''
  if (!md) return ''
  try {
    // Rewrite KB-relative image paths → file-preview endpoint
    const mdRelDir = (previewDoc.value?.path || '')
      .replace(/\\/g, '/')
      .split('/')
      .slice(0, -1)
      .join('/')
    md = md.replace(
      /!\[([^\]]*)\]\(([^)]+)\)/g,
      (_, alt, src) => {
        const cleaned = src.trim()
        if (/^(https?:|data:|\/api\/)/.test(cleaned)) return `![${alt}](${cleaned})`
        const resolved = mdRelDir ? `${mdRelDir}/${cleaned}`.replace(/\/+/g, '/') : cleaned
        return `![${alt}](/api/preview/file?path=${encodeURIComponent(resolved)})`
      },
    )
    return renderMarkdown(md)
  } catch {
    return md
  }
})

const previewLanguage = computed(() => {
  const ext = (previewDoc.value?.name || '').split('.').pop()?.toLowerCase() || ''
  return ext ? `language-${ext}` : ''
})

const drawerWidth = computed(() =>
  typeof window !== 'undefined' && window.innerWidth < 640 ? '100%' : 780,
)

// ── Preview actions ──────────────────────────────────────
const openFullPreview = () => {
  if (!previewDoc.value) return
  const path = encodeURIComponent(previewDoc.value.path || '')
  if (previewType.value === 'markdown' && previewDocId.value) {
    window.open(`/api/preview/markdown-preview?id=${previewDocId.value}`, '_blank')
  } else {
    window.open(`/api/preview/file?path=${path}`, '_blank')
  }
}

/** Filter out sub-KB entries from document list (they appear as file_type='knowledge-base' in YAML). */
const realDocuments = computed(() =>
  documents.value.filter(d =>
    d.file_type !== 'knowledge-base' && !(d as any).metadata?.isKnowledgeBase
  )
)

// computed
const filteredDocs = computed(() => {
  if (!docFilter.value) return realDocuments.value
  const q = docFilter.value.toLowerCase()
  return realDocuments.value.filter(d =>
    d.name.toLowerCase().includes(q) ||
    (d.description || '').toLowerCase().includes(q)
  )
})

// Methods
const loadCatalog = async () => {
  try {
    catalog.value = await fetchCatalog()
    allTags.value = await fetchAllTags()
  } catch (err: any) {
    antMessage.error(err?.message || '加载知识库目录失败')
  }
}

/** Toggle expand/collapse of a KB in the left panel to reveal sub-KBs. */
const toggleKbExpand = async (kb: KbCatalogEntry, event?: Event) => {
  event?.stopPropagation()
  if (expandedKbIds.value.has(kb.kbId)) {
    expandedKbIds.value.delete(kb.kbId)
  } else {
    expandedKbIds.value.add(kb.kbId)
    if (!subKbMap.value[kb.kbId]) {
      loadingSubKbs.value.add(kb.kbId)
      try {
        subKbMap.value[kb.kbId] = await fetchSubCatalog(kb.kbId)
      } catch {
        subKbMap.value[kb.kbId] = []
      } finally {
        loadingSubKbs.value.delete(kb.kbId)
      }
    }
  }
}

const selectKb = async (kb: KbCatalogEntry) => {
  activeKb.value = kb
  loading.value = true
  try {
    const [subKbs, docs] = await Promise.all([
      fetchSubCatalog(kb.kbId),
      fetchDocuments(kb.kbId),
    ])
    subKbList.value = subKbs
    documents.value = docs
  } catch (err: any) {
    antMessage.error(err?.message || '加载知识库失败')
  } finally {
    loading.value = false
  }
}

/** Navigate into a sub-KB — push current KB to history for breadcrumb. */
const openSubKb = async (kb: KbCatalogEntry) => {
  if (activeKb.value) {
    kbNavHistory.value.push(activeKb.value)
  }
  await selectKb(kb)
}

/** Navigate to a KB from the breadcrumb. */
const navigateToKb = async (kb: KbCatalogEntry) => {
  const idx = kbNavHistory.value.findIndex(k => k.kbId === kb.kbId)
  if (idx !== -1) {
    kbNavHistory.value = kbNavHistory.value.slice(0, idx)
  }
  await selectKb(kb)
}

/** Go back to top-level (clear breadcrumb). */
const goTopLevel = () => {
  kbNavHistory.value = []
  activeKb.value = null
  subKbList.value = []
  documents.value = []
}

const handleRefresh = async () => {
  // Clear sub-KB cache so refresh fetches fresh data
  subKbMap.value = {}
  expandedKbIds.value = new Set()
  await loadCatalog()
  if (activeKb.value) {
    await selectKb(activeKb.value)
  }
  message.success('已刷新')
}

const formatFileSize = (bytes: number): string => {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// New document
const handleCreateDoc = async () => {
  if (!createForm.value.kbId) { message.error('请选择知识库'); return }
  if (!createForm.value.name.trim()) { message.error('请输入文档名称'); return }
  submitting.value = true
  try {
    await createDocument(
      createForm.value.kbId,
      createForm.value.name.trim(),
      createForm.value.content || '# ' + createForm.value.name.trim(),
      createForm.value.description.trim()
    )
    message.success('文档创建成功')
    showCreateDocDialog.value = false
    createForm.value = { kbId: '', name: '', description: '', content: '' }
    await handleRefresh()
  } catch (err: any) {
    message.error(err.message || '创建失败')
  } finally {
    submitting.value = false
  }
}

// Edit metadata
const openEditMetaDialog = (doc: KbDoc) => {
  editingDoc.value = doc
  editMetaForm.value = { name: doc.name, description: doc.description || '' }
  showEditMetaDialog.value = true
}

const handleEditMeta = async () => {
  if (!editingDoc.value || !activeKb.value) return
  submitting.value = true
  try {
    await updateDocumentMeta(activeKb.value.kbId, editingDoc.value.path, {
      name: editMetaForm.value.name,
      description: editMetaForm.value.description,
    })
    message.success('元数据已更新')
    showEditMetaDialog.value = false
    await selectKb(activeKb.value)
  } catch (err: any) {
    message.error(err.message || '更新失败')
  } finally {
    submitting.value = false
  }
}

// Edit content
const openEditContentDialog = async (doc: KbDoc) => {
  editingDoc.value = doc
  showEditContentDialog.value = true
  contentLoading.value = true
  editContentValue.value = ''
  try {
    const res = await readDocument(doc.path, { limit: 500, maxChars: 100000 })
    editContentValue.value = res.content
  } catch (err: any) {
    message.error('加载内容失败')
  } finally {
    contentLoading.value = false
  }
}

const handleEditContent = async () => {
  if (!editingDoc.value || !activeKb.value) return
  submitting.value = true
  try {
    await updateDocumentContent(activeKb.value.kbId, editingDoc.value.path, editContentValue.value)
    message.success('内容已保存')
    showEditContentDialog.value = false
  } catch (err: any) {
    message.error(err.message || '保存失败')
  } finally {
    submitting.value = false
  }
}

// Tag management
const openTagsDialog = (doc: KbDoc) => {
  editingDoc.value = doc
  editingTags.value = [...(doc.tags || [])]
  newTagValue.value = ''
  showTagsDialog.value = true
}

const addTag = () => {
  const tag = newTagValue.value.trim()
  if (!tag) return
  if (editingTags.value.includes(tag)) { message.warning('标签已存在'); return }
  editingTags.value.push(tag)
  newTagValue.value = ''
}

const addSuggestedTag = (tag: string) => {
  if (!editingTags.value.includes(tag)) {
    editingTags.value.push(tag)
  }
}

const removeTag = (index: number) => {
  editingTags.value.splice(index, 1)
}

const handleSaveTags = async () => {
  if (!editingDoc.value || !activeKb.value) return
  submitting.value = true
  try {
    await updateDocumentTags(activeKb.value.kbId, editingDoc.value.path, editingTags.value)
    message.success('标签已保存')
    showTagsDialog.value = false
    await selectKb(activeKb.value)
    allTags.value = await fetchAllTags()
  } catch (err: any) {
    message.error(err.message || '保存标签失败')
  } finally {
    submitting.value = false
  }
}

// Move document
const openMoveDialog = (doc: KbDoc) => {
  editingDoc.value = doc
  moveTargetKbId.value = ''
  showMoveDialog.value = true
}

const handleMoveDoc = async () => {
  if (!editingDoc.value) return
  if (!moveTargetKbId.value) { message.error('请选择目标知识库'); return }
  submitting.value = true
  try {
    await moveDocument(editingDoc.value.path, moveTargetKbId.value)
    message.success('文档移动成功')
    showMoveDialog.value = false
    await handleRefresh()
  } catch (err: any) {
    message.error(err.message || '移动失败')
  } finally {
    submitting.value = false
  }
}

// Delete document
const handleDeleteDoc = (doc: KbDoc) => {
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除文档 "${doc.name}" 吗？此操作不可撤销。`,
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      if (!activeKb.value) return
      try {
        await deleteDocument(activeKb.value.kbId, doc.path)
        message.success('文档已删除')
        await selectKb(activeKb.value)
      } catch (err: any) {
        message.error(err.message || '删除失败')
      }
    },
  })
}

// Preview
const openDocPreview = async (doc: KbDoc) => {
  previewDoc.value = doc
  previewContent.value = ''
  previewOffset.value = 0
  previewTruncated.value = false
  showPreviewDrawer.value = true

  const type = detectPreviewType(doc)
  // Image, PDF, and markdown-with-file-ID render via iframe/img — no content fetch needed
  if (type === 'image' || type === 'pdf' || (type === 'markdown' && doc.doc_id)) {
    previewLoading.value = false
    return
  }
  await loadPreview()
}

const loadPreview = async () => {
  if (!previewDoc.value) return
  previewLoading.value = true
  try {
    const res = await readDocument(previewDoc.value.path, {
      offset: previewOffset.value,
      limit: 200,
      maxChars: 30000,
    })
    previewContent.value += res.content
    previewTruncated.value = res.truncated
    previewOffset.value += 200
  } catch (err: any) {
    message.error('加载预览失败')
  } finally {
    previewLoading.value = false
  }
}

const loadMorePreview = () => loadPreview()

// ── Mermaid diagram rendering for client-side markdown preview ──
const { initMermaid } = useMarkdownRenderer()

/** Scan the preview drawer for Mermaid blocks and render them. */
function renderPreviewMermaid() {
  nextTick(async () => {
    // Wait for the drawer DOM to be ready
    await nextTick()
    const drawer = document.querySelector('.doc-preview-drawer .ant-drawer-body')
    if (!drawer) return
    // Only process client-side rendered markdown (not the iframe)
    const clientMd = drawer.querySelector('.preview-markdown-client .markdown-body')
    if (!clientMd) return
    try {
      await initMermaid(clientMd as HTMLElement)
    } catch (err) {
      console.debug('Preview mermaid init skipped:', err)
    }
  })
}

// Trigger mermaid rendering when client-side markdown content changes
watch(renderedMarkdown, () => {
  if (previewType.value === 'markdown' && !previewDocId.value) {
    renderPreviewMermaid()
  }
})
// Also trigger when preview content loads more
watch(previewContent, () => {
  if (previewType.value === 'markdown' && !previewDocId.value) {
    renderPreviewMermaid()
  }
})

// Auto-select first KB
watch(catalog, (newCatalog) => {
  if (newCatalog.length > 0 && !activeKb.value) {
    selectKb(newCatalog[0])
  }
})

// KbDoc may carry metadata field (from YAML)
interface KbDocWithMeta extends KbDoc {
  metadata?: Record<string, any>
}

onMounted(async () => {
  await loadCatalog()
})
</script>

<style scoped>
.kb-manage-page { position: relative; min-height: calc(100vh - 110px); color: var(--kb-fg); animation: kb-fade-in 0.4s var(--kb-ease-out); }

/* Page header */
.page-header { margin-bottom: 24px; animation: kb-fade-up 0.5s var(--kb-ease-out) both; }
.header-content { display: flex; justify-content: space-between; align-items: center; }
.header-left { display: flex; align-items: center; gap: 16px; }
.header-icon { width: 54px; height: 54px; border-radius: 15px; display: grid; place-items: center; font-size: 25px; color: #fff; background: linear-gradient(135deg, var(--kb-primary), var(--kb-gold-deep)); box-shadow: var(--kb-shadow-primary); }
.header-text h1 { font-size: 26px; font-weight: 800; color: var(--kb-fg); margin: 0 0 3px; letter-spacing: -0.5px; font-family: var(--kb-font-serif); }
.header-text p { font-size: 14px; color: var(--kb-fg-3); margin: 0; }
.header-actions { display: flex; gap: 10px; }
.action-btn { height: 40px; padding: 0 18px; border-radius: 11px; font-size: 14px; display: flex; align-items: center; gap: 7px; }

/* Layout */
.manage-layout { display: grid; grid-template-columns: 300px 1fr; gap: 20px; }

/* KB List Panel */
.kb-list-panel { background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); border-radius: var(--kb-radius-lg); box-shadow: var(--kb-shadow-md); display: flex; flex-direction: column; max-height: calc(100vh - 160px); overflow: hidden; }
.panel-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 18px; border-bottom: 1px solid var(--kb-border); }
.panel-title { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 700; color: var(--kb-fg); }
.panel-icon { color: var(--kb-primary); font-size: 16px; }
.panel-body { flex: 1; overflow-y: auto; padding: 10px; }

.kb-item { display: flex; gap: 12px; padding: 12px; border-radius: var(--kb-radius); cursor: pointer; transition: all 0.2s; margin-bottom: 6px; border: 1px solid transparent; align-items: flex-start; }
.kb-item:hover { background: var(--kb-gold-soft); border-color: var(--kb-border); }
.kb-item.active { background: linear-gradient(135deg, var(--kb-primary-soft), rgba(212, 175, 106, 0.12)); border-color: var(--kb-gold); box-shadow: inset 3px 0 0 var(--kb-primary); }

/* Expand/Collapse Button */
.kb-expand-btn { width: 20px; height: 20px; display: grid; place-items: center; flex-shrink: 0; cursor: pointer; border-radius: 4px; transition: all 0.2s; margin-top: 10px; }
.kb-expand-btn:hover { background: var(--kb-primary-tint); }
.expand-icon { font-size: 10px; color: var(--kb-fg-3); transition: transform 0.2s; }

/* Sub-KB List */
.sub-kb-list { margin-left: 16px; padding-left: 8px; border-left: 2px solid var(--kb-border); margin-bottom: 4px; }
.sub-kb-item { padding: 8px 12px; margin-bottom: 4px; }
.sub-kb-indent { width: 4px; flex-shrink: 0; }
.sub-icon { width: 32px; height: 32px; font-size: 14px; border-radius: 9px; background: linear-gradient(135deg, var(--kb-amber), #f59e0b); }
.sub-kb-empty { font-size: 12px; color: var(--kb-fg-mute); padding: 8px 12px; font-style: italic; }
.kb-item-icon { width: 40px; height: 40px; border-radius: 11px; display: grid; place-items: center; font-size: 18px; color: #fff; background: linear-gradient(135deg, var(--kb-primary), var(--kb-gold-deep)); flex-shrink: 0; box-shadow: 0 2px 6px rgba(184, 71, 36, 0.2); }
.kb-item-body { flex: 1; min-width: 0; }
.kb-item-name { font-size: 14px; font-weight: 700; color: var(--kb-fg); margin-bottom: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.kb-item-desc { font-size: 12px; color: var(--kb-fg-3); line-height: 1.4; margin-bottom: 6px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.kb-item-stat { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; color: var(--kb-fg-3); background: var(--kb-bg-subtle); padding: 2px 8px; border-radius: 999px; }
.kb-item-stat :deep(.anticon) { color: var(--kb-primary); }

/* Document Panel */
.doc-panel { background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); border-radius: var(--kb-radius-lg); box-shadow: var(--kb-shadow-md); min-height: calc(100vh - 160px); }
.doc-panel-content { display: flex; flex-direction: column; height: 100%; }

/* Breadcrumb */
.doc-breadcrumb { display: flex; align-items: center; gap: 6px; padding: 10px 22px; border-bottom: 1px solid var(--kb-border); flex-wrap: wrap; }
.doc-breadcrumb :deep(.ant-btn-link) { color: var(--kb-primary); font-weight: 600; padding: 0; height: auto; font-size: 13px; }
.breadcrumb-sep { color: var(--kb-fg-mute); font-size: 12px; }
.breadcrumb-current { font-weight: 700; color: var(--kb-fg); font-size: 13px; }

/* Section Title */
.section-title { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 700; color: var(--kb-fg); margin-bottom: 12px; }
.section-title :deep(.anticon) { color: var(--kb-amber); }

/* Sub-KB Card Area */
.sub-kb-section { padding: 16px 22px 4px; }
.sub-kb-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
.sub-kb-card { display: flex; align-items: center; gap: 12px; padding: 14px; border-radius: var(--kb-radius); background: var(--kb-bg); border: 1px solid var(--kb-border); cursor: pointer; transition: all 0.2s; }
.sub-kb-card:hover { border-color: var(--kb-gold); box-shadow: var(--kb-shadow-md); transform: translateY(-2px); }
.sub-kb-card-icon { width: 38px; height: 38px; border-radius: 10px; display: grid; place-items: center; font-size: 17px; color: #fff; background: linear-gradient(135deg, var(--kb-amber), #f59e0b); flex-shrink: 0; }
.sub-kb-card-body { flex: 1; min-width: 0; }
.sub-kb-card-name { font-size: 13px; font-weight: 700; color: var(--kb-fg); margin-bottom: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sub-kb-card-desc { font-size: 11px; color: var(--kb-fg-3); line-height: 1.4; margin-bottom: 5px; display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden; }
.sub-kb-card-stat { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; color: var(--kb-fg-3); background: var(--kb-bg-subtle); padding: 2px 7px; border-radius: 999px; }
.sub-kb-card-stat :deep(.anticon) { color: var(--kb-primary); font-size: 10px; }
.sub-kb-card-arrow { flex-shrink: 0; color: var(--kb-fg-mute); font-size: 12px; transition: transform 0.2s; }
.sub-kb-card:hover .sub-kb-card-arrow { transform: translateX(3px); color: var(--kb-primary); }
.doc-list-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 22px; border-bottom: 1px solid var(--kb-border); }
.doc-list-title { display: flex; align-items: center; gap: 10px; }
.doc-list-name { font-size: 22px; font-weight: 700; color: var(--kb-fg); margin: 0; font-family: var(--kb-font-serif); letter-spacing: -0.2px; }
.doc-list-actions { display: flex; gap: 10px; align-items: center; }

.doc-table-wrapper { flex: 1; padding: 18px 22px; overflow-y: auto; }

/* Document Grid */
.doc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.doc-card { background: linear-gradient(135deg, var(--kb-bg-elevated) 0%, var(--kb-bg) 100%); border: 1px solid var(--kb-border); border-radius: var(--kb-radius); padding: 16px; cursor: pointer; transition: all 0.25s var(--kb-ease); display: flex; flex-direction: column; gap: 12px; position: relative; overflow: hidden; }
.doc-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent, var(--kb-gold-bright), transparent); opacity: 0; transition: opacity 0.25s; }
.doc-card:hover { border-color: var(--kb-gold); box-shadow: var(--kb-shadow-lg); transform: translateY(-3px); }
.doc-card:hover::before { opacity: 1; }
.doc-card-header { display: flex; align-items: flex-start; gap: 12px; }
.doc-card-icon { width: 40px; height: 40px; border-radius: 11px; display: grid; place-items: center; font-size: 18px; color: #fff; background: linear-gradient(135deg, var(--kb-gold-deep), var(--kb-gold)); flex-shrink: 0; box-shadow: 0 2px 6px rgba(184, 148, 90, 0.25); }
.doc-card-info { flex: 1; min-width: 0; }
.doc-card-name { font-size: 14px; font-weight: 700; color: var(--kb-fg); margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.doc-card-desc { font-size: 12px; color: var(--kb-fg-3); line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.doc-more-btn { color: var(--kb-fg-3); }
.doc-more-btn:hover { color: var(--kb-primary); }
.doc-card-footer { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.doc-tags { display: flex; gap: 4px; flex-wrap: wrap; }
.more-tags { font-size: 11px; color: var(--kb-fg-mute); }
.doc-size { font-size: 11px; color: var(--kb-fg-mute); margin-left: auto; font-family: var(--kb-font-mono); }

/* Empty State */
.empty-state { padding: 60px 20px; text-align: center; }
.no-selection { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 400px; text-align: center; }
.no-sel-icon { width: 64px; height: 64px; border-radius: 20px; display: grid; place-items: center; font-size: 28px; color: var(--kb-primary); background: var(--kb-primary-soft); margin-bottom: 16px; }
.no-sel-text { font-size: 15px; color: var(--kb-fg-3); margin: 0; }

/* Editor */
.content-editor :deep(textarea) { font-family: var(--kb-font-mono); font-size: 13px; line-height: 1.6; }
.edit-content-wrapper { min-height: 400px; }

/* Tag Dialog */
.tags-dialog-content { }
.tags-hint { font-size: 14px; color: var(--kb-fg-2); margin-bottom: 16px; }
.tags-current { display: flex; flex-wrap: wrap; gap: 8px; min-height: 40px; align-items: center; }
.no-tags { color: var(--kb-fg-mute); font-size: 13px; }
.tags-add { display: flex; gap: 8px; }
.tags-suggest { margin-top: 16px; }
.tags-suggest-title { font-size: 13px; color: var(--kb-fg-3); margin-bottom: 8px; }
.tags-suggest-list { display: flex; flex-wrap: wrap; gap: 6px; }
.suggest-tag { cursor: pointer; transition: all 0.2s; }
.suggest-tag:hover { background: var(--kb-emerald-soft); border-color: var(--kb-emerald); }

/* Move Dialog */
.move-dialog-content { }
.move-hint { font-size: 14px; color: var(--kb-fg-2); margin-bottom: 16px; }

/* ═══ Preview Drawer — format-aware styles ═══ */
.doc-preview-drawer :deep(.ant-drawer-body) { padding: 0; display: flex; flex-direction: column; }
.preview-meta-bar {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding: 12px 20px; border-bottom: 1px solid var(--kb-border);
  background: var(--kb-bg-subtle);
}
.preview-size { font-size: 11px; color: var(--kb-fg-mute); font-family: var(--kb-font-mono); }
.preview-fullscreen-btn { margin-left: auto; }
.preview-body { padding: 0; flex: 1; min-height: 0; display: flex; flex-direction: column; }

/* Markdown server-side iframe */
.preview-markdown { flex: 1; min-height: 0; display: flex; }
.preview-iframe { width: 100%; flex: 1; min-height: 500px; border: none; }

/* Markdown client-side rendering (when no tree-fs file ID) */
.preview-markdown-client { padding: 20px 24px; overflow-y: auto; flex: 1; }
.preview-markdown-client .markdown-body {
  font-size: 14.5px; line-height: 1.75; color: var(--kb-fg-2);
}
.preview-markdown-client .markdown-body h1,
.preview-markdown-client .markdown-body h2,
.preview-markdown-client .markdown-body h3 {
  font-weight: 700; color: var(--kb-fg); margin: 20px 0 10px;
}
.preview-markdown-client .markdown-body h1 { font-size: 1.6em; border-bottom: 1px solid var(--kb-border); padding-bottom: 8px; }
.preview-markdown-client .markdown-body h2 { font-size: 1.35em; }
.preview-markdown-client .markdown-body h3 { font-size: 1.15em; }
.preview-markdown-client .markdown-body p { margin: 10px 0; }
.preview-markdown-client .markdown-body img { max-width: 100%; border-radius: 8px; margin: 8px 0; box-shadow: var(--kb-shadow-sm); }
.preview-markdown-client .markdown-body code {
  background: var(--kb-bg-subtle); padding: 2px 6px; border-radius: 4px;
  font-family: var(--kb-font-mono); font-size: 0.88em; color: var(--kb-primary);
}
.preview-markdown-client .markdown-body pre {
  background: var(--kb-bg-dark); color: #c8d3e0; padding: 16px; border-radius: 8px;
  overflow-x: auto; font-size: 13px; line-height: 1.6;
}
.preview-markdown-client .markdown-body pre code { background: transparent; padding: 0; color: inherit; }
.preview-markdown-client .markdown-body table { border-collapse: collapse; width: 100%; margin: 12px 0; }
.preview-markdown-client .markdown-body th,
.preview-markdown-client .markdown-body td { border: 1px solid var(--kb-border); padding: 8px 12px; font-size: 13px; }
.preview-markdown-client .markdown-body th { background: var(--kb-bg-subtle); font-weight: 600; }
.preview-markdown-client .markdown-body blockquote {
  border-left: 3px solid var(--kb-primary); padding-left: 14px; margin: 12px 0;
  color: var(--kb-fg-3);
}
.preview-markdown-client .markdown-body a { color: var(--kb-primary); }
.preview-markdown-client .markdown-body ul, .preview-markdown-client .markdown-body ol { padding-left: 22px; margin: 8px 0; }
.preview-markdown-client .markdown-body li { margin: 4px 0; }

/* KaTeX math in knowledge-base drawer */
.preview-markdown-client .markdown-body .math-inline { display: inline; }
.preview-markdown-client .markdown-body .math-inline .katex { font-size: 1.08em; }
.preview-markdown-client .markdown-body .math-block { display: block; overflow-x: auto; margin: 20px 0; padding: 14px 0; text-align: center; background: rgba(255,255,255,0.04); border-radius: 10px; border: 1px solid var(--kb-border); }
.preview-markdown-client .markdown-body .math-block .katex { font-size: 1.22em; }
.preview-markdown-client .markdown-body .math-error { background: var(--kb-rose-soft); padding: 4px 10px; border-radius: 4px; font-size: 0.9em; }

/* Mermaid diagrams in knowledge-base drawer */
.preview-markdown-client .markdown-body .mermaid,
.preview-markdown-client .markdown-body pre.mermaid,
.preview-markdown-client .markdown-body pre > code.language-mermaid {
  text-align: center; margin: 20px 0; padding: 16px;
  background: rgba(0,0,0,0.02); border-radius: 10px;
  border: 1px solid var(--kb-border); overflow-x: auto;
}

/* Image preview */
.preview-image-wrapper { display: flex; align-items: center; justify-content: center; min-height: 400px; padding: 16px; background: var(--kb-bg); }
.preview-img { max-width: 100%; max-height: 75vh; object-fit: contain; border-radius: 8px; box-shadow: var(--kb-shadow-lg); background: var(--kb-bg-subtle); }

/* PDF preview */
.preview-pdf-wrapper { flex: 1; min-height: 0; display: flex; }
.preview-pdf-wrapper .preview-iframe { min-height: 75vh; }

/* Text / code preview */
.preview-text { flex: 1; overflow: hidden; }
.preview-text pre {
  margin: 0; padding: 18px 22px; white-space: pre-wrap; word-break: break-word;
  font-family: var(--kb-font-mono); font-size: 13px; line-height: 1.7;
  color: var(--kb-fg-2); background: var(--kb-bg-elevated); min-height: 300px;
  overflow-y: auto; flex: 1;
}
.preview-text code { font-family: inherit; font-size: inherit; color: inherit; }

/* Unsupported format */
.preview-unsupported { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 320px; padding: 40px 20px; text-align: center; }
.preview-unsupported-icon { font-size: 48px; color: var(--kb-fg-mute); margin-bottom: 14px; }
.preview-unsupported p { font-size: 14px; color: var(--kb-fg-3); margin-bottom: 16px; }

.preview-more { text-align: center; margin-top: 14px; padding-bottom: 8px; }

/* Drawer responsive */
@media (max-width: 640px) {
  .doc-preview-drawer :deep(.ant-drawer-content-wrapper) { width: 100% !important; }
  .preview-meta-bar { padding: 10px 14px; }
  .preview-markdown-client { padding: 14px 16px; }
  .preview-text pre { padding: 14px 16px; font-size: 12px; }
}

/* Responsive layout */
@media (max-width: 992px) {
  .manage-layout { grid-template-columns: 1fr; }
  .kb-list-panel { max-height: 300px; }
}
@media (max-width: 768px) {
  .doc-grid { grid-template-columns: 1fr; }
  .doc-list-header { flex-direction: column; gap: 12px; align-items: flex-start; }
}
</style>

