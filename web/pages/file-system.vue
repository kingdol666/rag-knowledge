<template>
  <div class="file-system-page">
    <!-- Animated background -->
    <div class="ambient-bg">
      <div class="ambient-orb orb-1"></div>
      <div class="ambient-orb orb-2"></div>
      <div class="ambient-orb orb-3"></div>
      <div class="grid-overlay"></div>
    </div>

    <!-- Page header -->
    <header class="page-header">
      <div class="header-content">
        <div class="header-left">
          <div class="header-icon">
            <FolderOpenOutlined />
          </div>
          <div class="header-text">
            <h1 class="header-title">{{ $t('fs.title') }}</h1>
            <p class="header-subtitle">{{ $t('fs.subtitle') }}</p>
          </div>
        </div>
        <div class="header-actions">
          <a-button class="action-btn refresh-btn" @click="handleRefresh">
            <ReloadOutlined />
            <span>{{ $t('fs.refresh') }}</span>
          </a-button>
          <a-button type="primary" class="action-btn create-btn" @click="handleCreateRoot">
            <PlusOutlined />
            <span>{{ $t('fs.createRoot') }}</span>
          </a-button>
        </div>
      </div>
    </header>

    <!-- Main content area -->
    <main class="main-content">
      <div class="content-grid">
        <!-- Left file tree -->
        <aside class="sidebar-panel">
          <div class="panel-header">
            <div class="panel-title">
              <ApartmentOutlined class="panel-icon" />
              <span>{{ $t('fs.fileTree') }}</span>
            </div>
            <div class="panel-actions">
              <a-tooltip :title="isAllExpanded ? $t('fs.collapseAll') : $t('fs.expandAll')">
                <a-button type="text" size="small" class="icon-btn" @click="toggleExpandAll">
                  <ExpandOutlined v-if="!isAllExpanded" />
                  <ShrinkOutlined v-else />
                </a-button>
              </a-tooltip>
              <a-button type="primary" size="small" class="mini-create-btn" @click="handleCreateRoot">
                <PlusOutlined />
                {{ $t('fs.create') }}
              </a-button>
            </div>
          </div>

          <div class="panel-body tree-body">
            <a-spin :spinning="loading">
              <div v-if="treeData.length === 0" class="empty-state">
                <div class="empty-icon">
                  <FolderOpenOutlined />
                </div>
                <p class="empty-text">{{ $t('fs.empty') }}</p>
                <a-button type="primary" class="empty-action" @click="handleCreateRoot">
                  <PlusOutlined />
                  {{ $t('fs.createFirst') }}
                </a-button>
              </div>

              <a-tree v-else v-model:expandedKeys="expandedKeys" v-model:selectedKeys="selectedKeys"
                :tree-data="formattedTreeData" :show-icon="true" :block-node="true" class="custom-tree"
                @select="handleSelect" @expand="handleExpand">
                <template #icon="{ dataRef }">
                  <template v-if="dataRef.type === 'folder'">
                    <FolderOutlined v-if="!dataRef.expanded" class="folder-icon" />
                    <FolderOpenOutlined v-else class="folder-open-icon" />
                  </template>
                  <template v-else>
                    <FileTextOutlined class="file-icon" />
                  </template>
                </template>

                <template #title="{ dataRef }">
                  <div class="tree-node-wrapper">
                    <div class="tree-node-main">
                      <span class="node-name">{{ dataRef.title }}</span>
                      <span v-if="dataRef.type === 'folder' && (dataRef.childCount || dataRef.documentCount)"
                        class="node-badge">
                        {{ dataRef.childCount || 0 }} / {{ dataRef.documentCount || 0 }}
                      </span>
                      <span v-else-if="dataRef.type === 'file'" class="node-badge file-badge">
                        {{ dataRef.fileType || 'file' }}
                      </span>
                    </div>
                    <a-dropdown :trigger="['click']" @click.stop>
                      <a-button type="text" size="small" class="node-more-btn">
                        <EllipsisOutlined />
                      </a-button>
                      <template #overlay>
                        <a-menu class="dark-dropdown-menu">
                          <a-menu-item v-if="dataRef.type === 'folder'" @click="handleCreateChild(dataRef)">
                            <FolderAddOutlined />
                            <span>{{ $t('fs.newFolder') }}</span>
                          </a-menu-item>
                          <a-menu-item v-if="dataRef.type === 'folder'" @click="handleCreateFile(dataRef)">
                            <FileAddOutlined />
                            <span>{{ $t('fs.upload') }}</span>
                          </a-menu-item>
                          <a-menu-item v-if="dataRef.type === 'folder'" @click="handleBatchCreateFile(dataRef)">
                            <InboxOutlined />
                            <span>{{ $t('fs.batchUpload') }}</span>
                          </a-menu-item>
                          <a-menu-item v-if="dataRef.type === 'folder'" :disabled="parsing"
                            @click="handleParseDocuments(dataRef)">
                            <FileTextOutlined />
                            <span>{{ parsing ? $t('fs.parsing') : $t('fs.parse') }}</span>
                          </a-menu-item>
                          <a-menu-divider />
                          <a-menu-item @click="handleEdit(dataRef)">
                            <EditOutlined />
                            <span>{{ $t('fs.rename') }}</span>
                          </a-menu-item>
                          <a-menu-item danger @click="handleDelete(dataRef)">
                            <DeleteOutlined />
                            <span>{{ $t('fs.delete') }}</span>
                          </a-menu-item>
                        </a-menu>
                      </template>
                    </a-dropdown>
                  </div>
                </template>
              </a-tree>
            </a-spin>
          </div>

          <div class="panel-footer stats-footer">
            <div class="storage-path-info">
              <span class="storage-path-label">TREE_STORAGE_PATH</span>
              <code class="storage-path-code">{{ treeStoragePath }}</code>
            </div>
            <div class="stat-item">
              <div class="stat-icon folder-stat">
                <FolderOutlined />
              </div>
              <div class="stat-info">
                <span class="stat-value">{{ stats.folders }}</span>
                <span class="stat-label">{{ $t('fs.folders') }}</span>
              </div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <div class="stat-icon file-stat">
                <FileTextOutlined />
              </div>
              <div class="stat-info">
                <span class="stat-value">{{ stats.files }}</span>
                <span class="stat-label">{{ $t('fs.files') }}</span>
              </div>
            </div>
          </div>
        </aside>

        <!-- Right detail panel -->
        <section class="detail-panel">
          <div v-if="selectedNode" class="detail-content">
            <!-- Breadcrumb -->
            <nav class="breadcrumb-bar">
              <a-breadcrumb>
                <a-breadcrumb-item v-for="(node, index) in breadcrumbPath" :key="node.id">
                  <a-button v-if="index < breadcrumbPath.length - 1" type="link" size="small" class="breadcrumb-link"
                    @click="navigateToNode(node)">
                    <HomeOutlined v-if="!node.parentId" />
                    <FolderOutlined v-else />
                    <span>{{ node.name }}</span>
                  </a-button>
                  <span v-else class="breadcrumb-current">
                    <HomeOutlined v-if="!node.parentId" />
                    <FolderOutlined v-else-if="node.type === 'folder'" />
                    <FileOutlined v-else />
                    <span>{{ node.name }}</span>
                  </span>
                </a-breadcrumb-item>
              </a-breadcrumb>
            </nav>

            <!-- Detail card -->
            <div class="info-card">
              <div class="info-header">
                <div class="info-identity">
                  <div class="info-avatar" :class="selectedNode.type === 'folder' ? 'folder-avatar' : 'file-avatar'">
                    <FolderOpenOutlined v-if="selectedNode.type === 'folder'" />
                    <FileTextOutlined v-else />
                  </div>
                  <div class="info-titles">
                    <h2 class="info-name">{{ selectedNode.name }}</h2>
                    <p v-if="selectedNode.description" class="info-desc">{{ selectedNode.description }}</p>
                  </div>
                </div>
                <div class="info-actions">
                  <a-button type="text" class="icon-action" @click="handleEdit(selectedNode)">
                    <EditOutlined />
                  </a-button>
                  <a-button type="text" class="icon-action danger" @click="handleDelete(selectedNode)">
                    <DeleteOutlined />
                  </a-button>
                </div>
              </div>

              <div class="info-body">
                <div class="info-grid">
                  <div class="info-item">
                    <span class="info-label">{{ $t('fs.type') }}</span>
                    <a-tag :class="selectedNode.type === 'folder' ? 'tag-folder' : 'tag-file'">
                      {{ selectedNode.type === 'folder' ? $t('fs.folders') : $t('fs.files') }}
                    </a-tag>
                  </div>
                  <div class="info-item">
                    <span class="info-label">{{ $t('fs.path') }}</span>
                    <code class="info-code">{{ getFolderPath(selectedNode) }}</code>
                  </div>
                  <div class="info-item">
                    <span class="info-label">TREE_STORAGE_PATH</span>
                    <code class="info-code">{{ treeStoragePath }}</code>
                  </div>
                  <div v-if="selectedNode.type === 'folder'" class="info-item">
                    <span class="info-label">{{ $t('fs.subfolders') }}</span>
                    <span class="info-value">{{ selectedNode.childCount || 0 }}</span>
                  </div>
                  <div v-if="selectedNode.type === 'folder'" class="info-item">
                    <span class="info-label">{{ $t('fs.fileCount') }}</span>
                    <span class="info-value">{{ selectedNode.documentCount || 0 }}</span>
                  </div>
                  <div v-if="selectedNode.type === 'file'" class="info-item">
                    <span class="info-label">{{ $t('fs.fileTypeLabel') }}</span>
                    <span class="info-value">{{ selectedNode.fileType || 'unknown' }}</span>
                  </div>
                  <div v-if="selectedNode.type === 'file'" class="info-item">
                    <span class="info-label">{{ $t('fs.fileSizeLabel') }}</span>
                    <span class="info-value">{{ formatFileSize(selectedNode.fileSize || 0) }}</span>
                  </div>
                  <div class="info-item full-width">
                    <span class="info-label">{{ $t('fs.description') }}</span>
                    <span class="info-value">{{ selectedNode.description || $t('fs.none') }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">{{ $t('fs.created') }}</span>
                    <span class="info-value">{{ formatDate(selectedNode.createdAt) }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">{{ $t('fs.modified') }}</span>
                    <span class="info-value">{{ formatDate(selectedNode.updatedAt) }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- File preview -->
            <div v-if="selectedNode.type === 'file'" class="preview-card">
              <div class="preview-header">
                <div class="preview-title">
                  <FileTextOutlined />
                  <span>{{ $t('fs.preview') }}</span>
                </div>
                <div class="preview-actions">
                  <a-button type="text" size="small" class="preview-action"
                    @click="openFullscreenPreview(selectedNode)">
                    <FullscreenOutlined />
                    <span>{{ $t('fs.fullscreen') }}</span>
                  </a-button>
                  <a-button type="text" size="small" class="preview-action" @click="openInNewWindow(selectedNode)">
                    <ExportOutlined />
                    <span>{{ $t('fs.newWindow') }}</span>
                  </a-button>
                </div>
              </div>
              <div class="preview-body">
                <div v-if="previewLoading" class="preview-loading-state">
                  <a-spin :tip="$t('action.loading')" />
                </div>
                <div v-else class="preview-frame">
                  <!-- Image -->
                  <div v-if="getFilePreviewType(selectedNode) === 'image'" class="preview-image">
                    <img :src="`/api/preview/file?id=${selectedNode.id}`" :alt="selectedNode.name"
                      @click="openFullscreenPreview(selectedNode)" />
                  </div>
                  <!-- PDF -->
                  <div v-else-if="getFilePreviewType(selectedNode) === 'pdf'" class="preview-pdf">
                    <iframe :src="`/api/preview/file?id=${selectedNode.id}`" frameborder="0"></iframe>
                  </div>
                  <!-- Video -->
                  <div v-else-if="getFilePreviewType(selectedNode) === 'video'" class="preview-video">
                    <video controls>
                      <source :src="`/api/preview/file?id=${selectedNode.id}`" :type="selectedNode.mimeType">
                      {{ $t('fs.videoNotSupported') }}
                    </video>
                  </div>
                  <!-- Audio -->
                  <div v-else-if="getFilePreviewType(selectedNode) === 'audio'" class="preview-audio">
                    <audio controls>
                      <source :src="`/api/preview/file?id=${selectedNode.id}`" :type="selectedNode.mimeType">
                      {{ $t('fs.audioNotSupported') }}
                    </audio>
                  </div>
                  <!-- DOCX -->
                  <div v-else-if="getFilePreviewType(selectedNode) === 'docx'" class="preview-docx">
                    <iframe :src="`/api/preview/docx-preview?id=${selectedNode.id}`" frameborder="0"></iframe>
                  </div>
                  <!-- Markdown -->
                  <div v-else-if="getFilePreviewType(selectedNode) === 'markdown'" class="preview-markdown">
                    <iframe :src="`/api/preview/markdown-preview?id=${selectedNode.id}`" frameborder="0"></iframe>
                  </div>
                  <!-- Text/code -->
                  <div
                    v-else-if="previewContent && (getFilePreviewType(selectedNode) === 'text' || getFilePreviewType(selectedNode) === 'code')"
                    class="preview-text">
                    <pre>{{ previewContent }}</pre>
                  </div>
                  <!-- Office -->
                  <div v-else-if="getFilePreviewType(selectedNode) === 'office'" class="preview-office">
                    <div class="office-icon">
                      <FileWordOutlined v-if="selectedNode.fileType?.includes('doc')" />
                      <FileExcelOutlined v-else-if="selectedNode.fileType?.includes('xls')" />
                      <FilePptOutlined v-else-if="selectedNode.fileType?.includes('ppt')" />
                      <FileTextOutlined v-else />
                    </div>
                    <p class="office-label">{{ $t('fs.officeDoc') }}</p>
                    <p class="office-name">{{ selectedNode.name }}</p>
                    <div class="office-actions">
                      <a-button type="primary" @click="openInNewWindow(selectedNode)">
                        <ExportOutlined />
                        {{ $t('fs.viewOnline') }}
                      </a-button>
                      <a-button @click="downloadSelectedFile">
                        <DownloadOutlined />
                        {{ $t('action.download') }}
                      </a-button>
                    </div>
                  </div>
                  <!-- Other -->
                  <div v-else class="preview-other">
                    <FileTextOutlined class="other-icon" />
                    <p class="other-label">{{ $t('fs.noPreviewFallback') }}</p>
                    <p class="other-name">{{ selectedNode.name }}</p>
                    <a-button type="primary" @click="downloadSelectedFile">
                      <DownloadOutlined />
                      {{ $t('fs.downloadFile') }}
                    </a-button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Child content -->
            <div v-if="selectedNode.type === 'folder'" class="children-card">
              <div class="children-header">
                <div class="children-title">
                  <BlockOutlined />
                  <span>{{ $t('fs.children') }}</span>
                  <span class="children-count">({{ children.length }})</span>
                </div>
                <div class="children-actions">
                  <a-button type="primary" size="small" class="children-btn" @click="handleCreateChild(selectedNode)">
                    <FolderAddOutlined />
                    {{ $t('fs.create') }}
                  </a-button>
                  <a-button size="small" class="children-btn" @click="handleCreateFile(selectedNode)">
                    <FileAddOutlined />
                    {{ $t('fs.upload') }}
                  </a-button>
                  <a-button size="small" class="children-btn" @click="handleBatchCreateFile(selectedNode)">
                    <InboxOutlined />
                    {{ $t('fs.batchUpload') }}
                  </a-button>
                  <a-button type="primary" size="small" class="children-btn" :disabled="parsing"
                    @click="handleParseDocuments(selectedNode)">
                    <FileTextOutlined />
                    {{ parsing ? $t('fs.parsing') : $t('fs.parse') }}
                  </a-button>
                </div>
              </div>
              <div class="children-body">
                <a-spin :spinning="loading">
                  <div v-if="!children || children.length === 0" class="empty-children">
                    <div class="empty-children-icon">
                      <InboxOutlined />
                    </div>
                    <p class="empty-children-text">{{ $t('fs.emptyChildren') }}</p>
                    <div class="empty-children-actions">
                      <a-button type="primary" size="small" @click="handleCreateChild(selectedNode)">
                        <FolderAddOutlined />
                        {{ $t('fs.newFolder') }}
                      </a-button>
                      <a-button size="small" @click="handleCreateFile(selectedNode)">
                        <FileAddOutlined />
                        {{ $t('fs.uploadFile') }}
                      </a-button>
                    </div>
                  </div>
                  <div v-else class="children-grid">
                    <div v-for="child in children" :key="child.id" class="child-card"
                      @click="handleSelect([child.id], { node: { dataRef: child } })">
                      <div class="child-icon" :class="child.type === 'folder' ? 'child-folder' : 'child-file'">
                        <FolderOutlined v-if="child.type === 'folder'" />
                        <FileTextOutlined v-else />
                      </div>
                      <div class="child-info">
                        <span class="child-name">{{ child.name }}</span>
                        <span class="child-meta">{{ child.type === 'folder' ? $t('fs.folder') : (child.fileType || $t('fs.file')) }}</span>
                      </div>
                      <a-dropdown :trigger="['click']" @click.stop>
                        <a-button type="text" size="small" class="child-more">
                          <EllipsisOutlined />
                        </a-button>
                        <template #overlay>
                          <a-menu class="dark-dropdown-menu">
                            <a-menu-item v-if="child.type === 'folder'" @click="handleCreateChild(child)">
                              <FolderAddOutlined />
                              <span>{{ $t('fs.newFolder') }}</span>
                            </a-menu-item>
                            <a-menu-item v-if="child.type === 'folder'" @click="handleCreateFile(child)">
                              <FileAddOutlined />
                              <span>{{ $t('fs.upload') }}</span>
                            </a-menu-item>
                            <a-menu-item @click="handleEdit(child)">
                              <EditOutlined />
                              <span>{{ $t('fs.rename') }}</span>
                            </a-menu-item>
                            <a-menu-item danger @click="handleDelete(child)">
                              <DeleteOutlined />
                              <span>{{ $t('fs.delete') }}</span>
                            </a-menu-item>
                          </a-menu>
                        </template>
                      </a-dropdown>
                    </div>
                  </div>
                </a-spin>
              </div>
            </div>
          </div>

          <!-- Unselected state -->
          <div v-else class="empty-detail">
            <div class="empty-detail-visual">
              <div class="empty-orbit">
                <div class="orbit-center">
                  <FolderOpenOutlined />
                </div>
                <div class="orbit-ring ring-1"></div>
                <div class="orbit-ring ring-2"></div>
              </div>
            </div>
            <h3 class="empty-detail-title">{{ $t('fs.selectNode') }}</h3>
            <p class="empty-detail-desc">{{ $t('fs.selectNodeHint') }}</p>
          </div>
        </section>
      </div>
    </main>

    <!-- New folder dialog -->
    <a-modal v-model:open="showCreateFolderDialog" :title="$t('fs.newFolder')" class="dark-modal" :width="480"
      @cancel="closeCreateFolderDialog">
      <a-form :model="createFolderForm" layout="vertical">
        <a-form-item :label="$t('fs.name')" required>
          <a-input v-model:value="createFolderForm.name" :placeholder="$t('fs.namePlaceholder')" />
        </a-form-item>
        <a-form-item :label="$t('fs.description')">
          <a-textarea v-model:value="createFolderForm.description" :rows="3" :placeholder="$t('fs.descriptionPlaceholder')" />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-button @click="closeCreateFolderDialog">{{ $t('action.cancel') }}</a-button>
        <a-button type="primary" :loading="false" @click="handleSubmitCreateFolder">{{ $t('action.create') }}</a-button>
      </template>
    </a-modal>

    <!-- Edit dialog -->
    <a-modal v-model:open="showEditDialog" :title="$t('fs.rename')" class="dark-modal" :width="480" @cancel="closeEditDialog">
      <a-form :model="editForm" layout="vertical">
        <a-form-item :label="$t('fs.name')" required>
          <a-input v-model:value="editForm.name" :placeholder="$t('fs.renamePlaceholder')" />
        </a-form-item>
        <a-form-item v-if="editingNode?.type === 'folder'" :label="$t('fs.description')">
          <a-textarea v-model:value="editForm.description" :rows="3" :placeholder="$t('fs.descriptionPlaceholder')" />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-button @click="closeEditDialog">{{ $t('action.cancel') }}</a-button>
        <a-button type="primary" @click="handleSubmitEdit">{{ $t('action.save') }}</a-button>
      </template>
    </a-modal>

    <!-- {{ $t('fs.uploadFile') }} dialog -->
    <a-modal v-model:open="showUploadFileDialog" :title="$t('fs.uploadFile')" class="dark-modal" :width="520"
      @cancel="closeUploadFileDialog">
      <a-upload-dragger v-model:fileList="uploadFileList" :before-upload="beforeUploadFile" :multiple="false"
        class="dark-uploader">
        <p class="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p class="ant-upload-text">{{ $t('fs.uploadDragger') }}</p>
        <p class="ant-upload-hint">{{ $t('fs.uploadDraggerHint') }}</p>
      </a-upload-dragger>
      <a-form-item :label="$t('fs.description')" class="upload-desc" style="margin-top: 16px;">
        <a-textarea v-model:value="uploadDescription" :rows="2" :placeholder="$t('fs.uploadDescPlaceholder')" />
      </a-form-item>
      <template #footer>
        <a-button @click="closeUploadFileDialog">{{ $t('action.cancel') }}</a-button>
        <a-button type="primary" :loading="uploadingFile" @click="handleUploadFile">{{ $t('action.upload') }}</a-button>
      </template>
    </a-modal>

    <!-- {{ $t('fs.batchUpload') }}{{ $t('fs.upload') }} dialog -->
    <a-modal v-model:open="showBatchUploadDialog" :title="$t('fs.batchUpload')" class="dark-modal" :width="600"
      @cancel="closeBatchUploadDialog">
      <a-upload-dragger v-model:fileList="batchUploadFileList" :before-upload="beforeBatchUploadFile" :multiple="true"
        class="dark-uploader">
        <p class="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p class="ant-upload-text">{{ $t('fs.batchUploadDragger') }}</p>
        <p class="ant-upload-hint">{{ $t('fs.batchUploadHint') }}</p>
      </a-upload-dragger>
      <template #footer>
        <a-button @click="closeBatchUploadDialog">{{ $t('action.cancel') }}</a-button>
        <a-button type="primary" :loading="batchUploading" @click="handleBatchUpload">{{ $t('fs.startUpload') }}</a-button>
      </template>
    </a-modal>

    <!-- Parse document dialog -->
    <a-modal v-model:open="showParseDialog" :title="$t('fs.parseBtn')" class="dark-modal" :width="640" :footer="null"
      @cancel="closeParseDialog">
      <div class="parse-content">
        <a-upload-dragger v-model:fileList="customUploadFileList" :before-upload="beforeCustomUpload" :multiple="true"
          accept=".pdf" class="dark-uploader">
          <p class="ant-upload-drag-icon">
            <FileTextOutlined />
          </p>
          <p class="ant-upload-text">{{ $t('fs.parseDragger') }}</p>
          <p class="ant-upload-hint">{{ $t('fs.parseDraggerHint') }}</p>
        </a-upload-dragger>

        <div class="parse-options" style="margin-top: 16px;">
          <div class="parse-option-row">
            <label class="parse-option-label">{{ $t('fs.outputDir') }}</label>
            <a-input v-model:value="customOutputDir" :placeholder="$t('fs.outputDirPlaceholder')" />
          </div>
          <div class="parse-option-row">
            <a-checkbox v-model:checked="customUseOcr">{{ $t('fs.enableOcr') }}</a-checkbox>
          </div>
        </div>

        <div v-if="parsing" class="parse-progress">
          <a-progress :percent="Math.round((parseProgress.completed / parseProgress.total) * 100)" status="active" />
          <p class="parse-current">{{ parseProgress.currentFile }}</p>
        </div>

        <div class="parse-actions" style="margin-top: 16px; text-align: right;">
          <a-button @click="closeParseDialog">{{ $t('action.close') }}</a-button>
          <a-button type="primary" :loading="parsing" :disabled="customUploadFileList.length === 0"
            style="margin-left: 8px;" @click="startCustomParse">
            {{ $t('fs.startParse') }}
          </a-button>
        </div>
      </div>
    </a-modal>

    <!-- Fullscreen preview dialog -->
    <a-modal v-model:open="showFullscreenPreview" :title="fullscreenPreviewNode?.name" class="fullscreen-preview-modal"
      :width="'90vw'" :footer="null" @cancel="closeFullscreenPreview">
      <div class="fullscreen-content">
        <div v-if="fullscreenPreviewNode" class="fullscreen-frame">
          <img v-if="getFilePreviewType(fullscreenPreviewNode) === 'image'"
            :src="`/api/preview/file?id=${fullscreenPreviewNode.id}`" :alt="fullscreenPreviewNode.name"
            class="fullscreen-image" />
          <iframe v-else-if="getFilePreviewType(fullscreenPreviewNode) === 'pdf'"
            :src="`/api/preview/file?id=${fullscreenPreviewNode.id}`" class="fullscreen-iframe"></iframe>
          <iframe v-else-if="getFilePreviewType(fullscreenPreviewNode) === 'docx'"
            :src="`/api/preview/docx-preview?id=${fullscreenPreviewNode.id}`" class="fullscreen-iframe"></iframe>
          <iframe v-else-if="getFilePreviewType(fullscreenPreviewNode) === 'markdown'"
            :src="`/api/preview/markdown-preview?id=${fullscreenPreviewNode.id}`" class="fullscreen-iframe"></iframe>
          <video v-else-if="getFilePreviewType(fullscreenPreviewNode) === 'video'" controls class="fullscreen-video">
            <source :src="`/api/preview/file?id=${fullscreenPreviewNode.id}`" :type="fullscreenPreviewNode.mimeType">
          </video>
          <audio v-else-if="getFilePreviewType(fullscreenPreviewNode) === 'audio'" controls class="fullscreen-audio">
            <source :src="`/api/preview/file?id=${fullscreenPreviewNode.id}`" :type="fullscreenPreviewNode.mimeType">
          </audio>
          <pre
            v-else-if="previewContent && (getFilePreviewType(fullscreenPreviewNode) === 'text' || getFilePreviewType(fullscreenPreviewNode) === 'code')"
            class="fullscreen-text">{{ previewContent }}</pre>
          <div v-else class="fullscreen-fallback">
            <FileTextOutlined class="fallback-icon" />
            <p>{{ $t('fs.noFullscreenFallback') }}</p>
            <a-button type="primary" @click="downloadFile(fullscreenPreviewNode)">
              <DownloadOutlined />
              {{ $t('fs.downloadFile') }}
            </a-button>
          </div>
        </div>
      </div>
    </a-modal>
    <ParseTaskQueuePanel />

  </div>
</template>

<script setup lang="ts">
import { ref, computed, h, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  FolderOpenOutlined,
  ReloadOutlined,
  PlusOutlined,
  ExpandOutlined,
  ShrinkOutlined,
  FolderOutlined,
  FileTextOutlined,
  EllipsisOutlined,
  FolderAddOutlined,
  FileAddOutlined,
  InboxOutlined,
  EditOutlined,
  DeleteOutlined,
  HomeOutlined,
  FileOutlined,
  FullscreenOutlined,
  ExportOutlined,
  DownloadOutlined,
  FileWordOutlined,
  FileExcelOutlined,
  FilePptOutlined,
  BlockOutlined,
  ApartmentOutlined
} from '@ant-design/icons-vue'
import { Modal, message } from 'ant-design-vue'
import { useFileSystem } from '~/composables/useFileSystem'
import { useFilePreview } from '~/composables/useFilePreview'
import { useParseTaskQueue } from '~/composables/useParseTaskQueue'
import { useFileSystemUpload } from '~/composables/useFileSystemUpload'
import type { TreeNode } from '~/composables/useTreeFileSystem'

const { t } = useI18n()

const {
  treeData,
  loading,
  selectedNode,
  selectedKeys,
  expandedKeys,
  children,
  stats,
  fetchTree,
  fetchStats,
  fetchChildren,
  createFolder,
  updateFolder,
  updateFile,
  deleteNode,
  uploadFile,
  uploadFiles,
  downloadFile,
    saveParsedFiles,
    findNodeById,
    batchParseFilesVTStream,
    treeStoragePath
  } = useFileSystem()

const {
  previewContent,
  previewLoading,
  loadFilePreview,
  clearPreview,
  getFilePreviewType,
  openInNewWindow
} = useFilePreview()

const queue = useParseTaskQueue()

// Dialog state
const showCreateFolderDialog = ref(false)
const showEditDialog = ref(false)
const showParseDialog = ref(false)
const showFullscreenPreview = ref(false)

// Form data
const createParentId = ref<string | null>(null)
const createFolderForm = ref({ name: '', description: '', isKnowledgeBase: true })
const editingNode = ref<TreeNode | null>(null)
const editForm = ref({ name: '', description: '' })
const parsing = ref(false)
const parseProgress = ref({ completed: 0, total: 0, currentFile: '' })
const parseResults = ref<any[]>([])
const customUploadFileList = ref<any[]>([])
const customOutputDir = ref('')
const customUseOcr = ref(true)
const customParseDescriptions = ref<string[]>([])
const fullscreenPreviewNode = ref<TreeNode | null>(null)

// Breadcrumb path
const breadcrumbPath = computed(() => {
  if (!selectedNode.value) return []
  const path: TreeNode[] = []
  let current: TreeNode | null = selectedNode.value

  const findParent = (nodes: TreeNode[], targetId: string): TreeNode | null => {
    for (const node of nodes) {
      if (node.children) {
        for (const child of node.children) {
          if (child.id === targetId) return node
        }
        const found = findParent(node.children, targetId)
        if (found) return found
      }
    }
    return null
  }

  while (current) {
    path.unshift(current)
    const parent = findParent(treeData.value, current.id)
    current = parent || null
  }
  return path
})

// Format tree data
const formattedTreeData = computed(() => {
  const convert = (nodes: TreeNode[], depth: number = 0): any[] => {
    return nodes.map(node => ({
      key: node.id,
      title: node.name,
      ...node,
      depth,
      children: node.children ? convert(node.children, depth + 1) : undefined
    }))
  }
  return convert(treeData.value)
})

// Auto-refresh mechanism
let refreshTimer: ReturnType<typeof setInterval> | null = null
const isVisible = ref(true)

const handleVisibilityChange = () => {
  if (!document.hidden && !isVisible.value) {
    isVisible.value = true
    // Auto-refresh when page becomes visible again
    handleRefresh()
  } else {
    isVisible.value = !document.hidden
  }
}

onMounted(async () => {
  await handleRefresh()
  // Polling refresh every 30 seconds
  refreshTimer = setInterval(() => {
    if (!document.hidden) {
      fetchTree()
      fetchStats()
      if (selectedNode.value && selectedNode.value.type === 'folder') {
        fetchChildren(selectedNode.value.id)
      }
    }
  }, 30000)
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})

const handleRefresh = async () => {
  try {
    await fetchTree()
    await fetchStats()
    if (selectedNode.value && selectedNode.value.type === 'folder') {
      await fetchChildren(selectedNode.value.id)
    }
  } catch (error) {
    console.error('Refresh error:', error)
    message.error(t('fs.refreshFailed'))
  }
}

const {
  showUploadFileDialog,
  uploadFileList,
  uploadDescription,
  uploadingFile,
  showBatchUploadDialog,
  batchUploadFileList,
  batchUploading,
  handleCreateFile,
  handleBatchCreateFile,
  handleUploadFile,
  handleBatchUpload,
  beforeUploadFile,
  beforeBatchUploadFile,
  closeUploadFileDialog,
  closeBatchUploadDialog
} = useFileSystemUpload({
  createParentId,
  selectedNode,
  uploadFile,
  uploadFiles,
  fetchChildren,
  handleRefresh
})

const handleSelect = async (keys: string[], info: any) => {
  if (keys.length > 0) {
    const nodeId = keys[0]
    const nodeFromInfo = info?.node?.dataRef
    let node = nodeFromInfo || findNodeById(treeData.value, nodeId)

    if (node) {
      selectedNode.value = node
      selectedKeys.value = keys
      if (node.type === 'folder') {
        await fetchChildren(node.id)
      } else if (node.type === 'file') {
        await loadFilePreview(node)
      }
    }
  } else {
    selectedNode.value = null
    selectedKeys.value = []
    children.value = []
    clearPreview()
  }
}

const downloadSelectedFile = () => {
  if (selectedNode.value) {
    downloadFile(selectedNode.value)
  }
}

const handleExpand = (keys: string[]) => {
  expandedKeys.value = keys
}

const getAllFolderKeys = (nodes: any[]): string[] => {
  const keys: string[] = []
  for (const node of nodes) {
    if (node.type === 'folder') {
      keys.push(node.key)
      if (node.children && node.children.length > 0) {
        keys.push(...getAllFolderKeys(node.children))
      }
    }
  }
  return keys
}

const isAllExpanded = computed(() => {
  const allFolderKeys = getAllFolderKeys(formattedTreeData.value)
  if (allFolderKeys.length === 0) return false
  return allFolderKeys.every(key => expandedKeys.value.includes(key))
})

const toggleExpandAll = () => {
  if (isAllExpanded.value) {
    expandedKeys.value = []
  } else {
    expandedKeys.value = getAllFolderKeys(formattedTreeData.value)
  }
}

const handleCreateRoot = () => {
  createParentId.value = null
  createFolderForm.value = { name: '', description: '', isKnowledgeBase: true }
  showCreateFolderDialog.value = true
}

const handleCreateChild = (parent: TreeNode) => {
  createParentId.value = parent.id
  createFolderForm.value = { name: '', description: '', isKnowledgeBase: true }
  showCreateFolderDialog.value = true
}

const handleEdit = (node: TreeNode) => {
  editingNode.value = node
  editForm.value = {
    name: node.name,
    description: node.description || ''
  }
  showEditDialog.value = true
}

const handleDelete = async (node: TreeNode) => {
  const isFolder = node.type === 'folder'
  Modal.confirm({
    title: t('fs.deleteConfirm'),
    content: h('div', { style: 'color: var(--kb-fg-2);' }, t('fs.deleteConfirmText', { type: isFolder ? t('fs.folder') : t('fs.file'), name: node.name, extra: isFolder ? t('fs.deleteFolderExtra') : '' })),
    okText: t('fs.delete'),
    okType: 'danger',
    cancelText: t('action.cancel'),
    class: 'kb-confirm-modal',
    onOk: async () => {
      try {
        await deleteNode(node.id)
        message.success(t('fs.deleteSuccess'))
        await handleRefresh()

        if (selectedNode.value?.id === node.id) {
          selectedNode.value = null
          selectedKeys.value = []
          children.value = []
        } else if (selectedNode.value) {
          const currentChildren = await fetchChildren(selectedNode.value.id)
          children.value = currentChildren
        }
      } catch (error: any) {
        console.error('Delete error:', error)
        message.error(error.message || t('fs.deleteFailed'))
      }
    }
  })
}

const handleSubmitCreateFolder = async () => {
  if (!createFolderForm.value.name.trim()) {
    message.success(t('fs.nameRequired'))
    return
  }

  try {
    const response = await createFolder({
      name: createFolderForm.value.name,
      parentId: createParentId.value,
      description: createFolderForm.value.description,
      isKnowledgeBase: createFolderForm.value.isKnowledgeBase
    })

    if (!response || 'error' in response) {
      throw new Error(response?.error || t('fs.createFailed'))
    }

    const newFolder = response as { id: string; name: string; type: string }
    message.success(t('fs.createFolderSuccess'))

    closeCreateFolderDialog()
    await handleRefresh()
  } catch (error: any) {
    console.error('Create folder error:', error)
    message.error(error.message || t('fs.createFailed'))
  }
}

const handleSubmitEdit = async () => {
  if (!editForm.value.name.trim() || !editingNode.value) {
    message.error(t('fs.nameRequired'))
    return
  }

  try {
    if (editingNode.value.type === 'folder') {
      await updateFolder(editingNode.value.id, {
        name: editForm.value.name,
        description: editForm.value.description
      })
    } else {
      await updateFile(editingNode.value.id, {
        name: editForm.value.name
      })
    }
    message.success(t('fs.updateSuccess'))
    closeEditDialog()
    await handleRefresh()

    if (selectedNode.value?.id === editingNode.value.id) {
      const updated = findNodeById(treeData.value, editingNode.value.id)
      if (updated) {
        selectedNode.value = updated
      }
    }
  } catch (error: any) {
    console.error('Update error:', error)
    message.error(error.message || t('fs.renameFailed'))
  }
}

const closeCreateFolderDialog = () => {
  showCreateFolderDialog.value = false
  createParentId.value = null
  createFolderForm.value = { name: '', description: '', isKnowledgeBase: true }
}

const closeEditDialog = () => {
  showEditDialog.value = false
  editingNode.value = null
  editForm.value = { name: '', description: '' }
}

const handleParseDocuments = (folder: TreeNode) => {
  selectedNode.value = folder
  showParseDialog.value = true
  parseResults.value = []
  parseProgress.value = { completed: 0, total: 0, currentFile: '' }
  customUploadFileList.value = []
  customOutputDir.value = ''
  customUseOcr.value = true
  customParseDescriptions.value = []
}

const closeParseDialog = () => {
  showParseDialog.value = false
  if (!parsing.value) {
    parseResults.value = []
    parseProgress.value = { completed: 0, total: 0, currentFile: '' }
    customUploadFileList.value = []
    customOutputDir.value = ''
    customUseOcr.value = true
    customParseDescriptions.value = []
  }
}

const beforeCustomUpload = (file: any) => {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    message.error(t('fs.pdfOnlyError'))
    return false
  }
  return false
}

const startCustomParse = async () => {
  if (customUploadFileList.value.length === 0) {
    message.warning(t('fs.parseFileRequired'))
    return
  }

  const filesToParse: File[] = customUploadFileList.value
    .map((item: any) => item.originFileObj || item)
    .filter((file: any) => file instanceof File)

  if (filesToParse.length === 0) {
    message.error(t('fs.noValidPdf'))
    return
  }

  // Capture options into locals BEFORE closing the modal.
  const targetNodeId = selectedNode.value?.id
  const targetNodeName = selectedNode.value?.name
  const useOcr = customUseOcr.value
  const outputDir = customOutputDir.value || undefined
  const descriptions = [...customParseDescriptions.value]

  // Register in the task queue. addTask() auto-opens the panel.
  const queueTaskId = queue.addTask({
    fileNames: filesToParse.map((f: any) => f.name || "PDF"),
    parentId: targetNodeId,
    parentName: targetNodeName,
    useOcr,
    outputDir,
  })

  // Close the modal; the queue panel tracks progress.
  showParseDialog.value = false
  customUploadFileList.value = []
  customParseDescriptions.value = []
  customOutputDir.value = ""

  // Background: stream parse, save into KB, signal the queue.
  void (async () => {
    const stream = batchParseFilesVTStream(filesToParse, {
      parent_id: targetNodeId,
      output_dir: outputDir,
      use_ocr: useOcr,
    })

    stream.onProgress((data) => {
      queue.updateProgress(queueTaskId, {
        completed: data.current,
        total: data.total,
        currentFile: data.filename,
      })
    })

    const finalSummary = await new Promise<any>((resolve, reject) => {
      stream.onComplete((summary) => resolve(summary))
      stream.onError((error) => reject(new Error(error)))
    })

    if (finalSummary.failed > 0 && finalSummary.failed === finalSummary.total) {
      message.error(finalSummary.error || t('fs.parseFailed'))
      queue.failTask(queueTaskId, finalSummary.error || t('fs.parseFailed'))
      return
    }

    // success/fail counts read directly from finalSummary
    message.success(t('fs.parseResultMsg', { success: finalSummary.successful, failed: finalSummary.failed }))
    queue.markSaving(queueTaskId)

    let savedCount = 0
    if (targetNodeId && finalSummary.results?.length > 0) {
      try {
        const saveResult = await saveParsedFiles(
          targetNodeId,
          finalSummary.results as any[],
          descriptions,
        )
        savedCount = saveResult?.savedCount ?? 0
        if (saveResult.success)
          message.success(t('fs.savedToFolder', { count: savedCount }))
      } catch (saveError) {
        console.error("Save parsed files error:", saveError)
      }
      try {
        await fetchChildren(targetNodeId)
        await handleRefresh()
      } catch (refreshError) {
        console.error("Tree refresh error:", refreshError)
      }
    }
    // Normalize summary to match the Queue result shape.
    const queueSummary = {
      success: finalSummary.failed === 0,
      total_files: finalSummary.total || 0,
      successful_files: finalSummary.successful || 0,
      failed_files: finalSummary.failed || 0,
      results: finalSummary.results || [],
    }
    queue.completeTask(queueTaskId, queueSummary, savedCount)
  })().catch((error: any) => {
    console.error("Custom parse error:", error)
    message.error(t('fs.parseFailed') + `: ${error.message}`)
    queue.failTask(queueTaskId, error.message)
  })
}
const getFolderPath = (node: TreeNode | null): string => {
  if (!node) return ''
  const basePath = treeStoragePath.replace(/[\\/]+$/, '')
  const relativePath = node.path || node.name
  if (relativePath.includes(':') || relativePath.startsWith('/')) {
    return relativePath
  }
  return `${basePath}/${relativePath.replace(/\\/g, '/')}`
}

const formatDate = (dateStr: string | undefined) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const openFullscreenPreview = (node: TreeNode) => {
  fullscreenPreviewNode.value = node
  showFullscreenPreview.value = true
  if (node.type === 'file') {
    loadFilePreview(node)
  }
}

const closeFullscreenPreview = () => {
  showFullscreenPreview.value = false
  fullscreenPreviewNode.value = null
}

const navigateToNode = (node: TreeNode) => {
  handleSelect([node.id], { node: { dataRef: node } })
}
</script>

<style scoped>
/* ========== Base Layout ========== */
.file-system-page {
  min-height: 100vh;
  background: var(--kb-bg);
  position: relative;
  overflow-x: hidden;
}

/* ========== Animated background ========== */
.ambient-bg {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.ambient-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.25;
  animation: orbFloat 20s ease-in-out infinite;
}

.orb-1 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(37,99,235,0.2), transparent 70%);
  top: -200px;
  left: -200px;
  animation-delay: 0s;
}

.orb-2 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(6,182,212,0.15), transparent 70%);
  bottom: -150px;
  right: -150px;
  animation-delay: -7s;
}

.orb-3 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(124,92,255,0.1), transparent 70%);
  top: 50%;
  left: 50%;
  animation-delay: -14s;
}

@keyframes orbFloat {

  0%,
  100% {
    transform: translate(0, 0) scale(1);
  }

  33% {
    transform: translate(30px, -30px) scale(1.1);
  }

  66% {
    transform: translate(-20px, 20px) scale(0.95);
  }
}

.grid-overlay {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(0, 0, 0, 0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 0, 0, 0.02) 1px, transparent 1px);
  background-size: 50px 50px;
  mask-image: radial-gradient(ellipse at center, black 30%, transparent 70%);
}

/* ========== Page Header ========== */
.page-header {
  position: relative;
  z-index: 10;
  padding: 24px 32px;
  border-bottom: 1px solid var(--kb-border);
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
}

.header-content {
  max-width: 1600px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--kb-primary), var(--kb-cyan));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  color: #fff;
}

.header-title {
  font-size: 22px;
  font-weight: 800;
  color: var(--kb-fg);
  margin: 0;
  line-height: 1.3;
}

.header-subtitle {
  font-size: 13px;
  color: var(--kb-fg-3);
  margin: 2px 0 0;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.action-btn {
  height: 38px;
  padding: 0 18px;
  border-radius: 10px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.3s ease;
}

.refresh-btn {
  background: var(--kb-bg-elevated) !important;
  border: 1px solid var(--kb-border) !important;
  color: var(--kb-fg-2) !important;
}

.refresh-btn:hover {
  background: var(--kb-primary-tint) !important;
  border-color: var(--kb-primary) !important;
  color: var(--kb-primary) !important;
  transform: translateY(-1px);
}

.create-btn {
  background: linear-gradient(135deg, var(--kb-primary), var(--kb-cyan)) !important;
  border: none !important;
  box-shadow: var(--kb-shadow-primary);
}

.create-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(139, 92, 246, 0.4);
}

/* ========== Main Content ========== */
.main-content {
  position: relative;
  z-index: 5;
  padding: 24px 32px 32px;
}

.content-grid {
  max-width: 1600px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 20px;
}

/* ========== Sidebar Panel ========== */
.sidebar-panel {
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius-lg);
  box-shadow: var(--kb-shadow-md);
  display: flex;
  flex-direction: column;
  height: calc(100vh - 140px);
  position: sticky;
  top: 24px;
  overflow: hidden;
}

.panel-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--kb-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--kb-fg);
}

.panel-icon {
  color: var(--kb-primary);
  font-size: 16px;
}

.panel-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}

.icon-btn {
  width: 28px;
  height: 28px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--kb-fg-3) !important;
  border-radius: 6px;
}

.icon-btn:hover {
  background: var(--kb-primary-tint) !important;
  color: var(--kb-primary) !important;
}

.mini-create-btn {
  height: 28px;
  padding: 0 10px;
  font-size: 12px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.panel-body::-webkit-scrollbar {
  width: 4px;
}

.panel-body::-webkit-scrollbar-track {
  background: transparent;
}

.panel-body::-webkit-scrollbar-thumb {
  background: var(--kb-border-strong);
  border-radius: 2px;
}

/* ========== Empty State ========== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 20px;
  text-align: center;
}

.empty-icon {
  width: 64px;
  height: 64px;
  border-radius: 20px;
  background: var(--kb-primary-soft);
  border: 1px solid var(--kb-border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: var(--kb-primary);
  margin-bottom: 16px;
}

.empty-text {
  color: var(--kb-fg-3);
  font-size: 13px;
  margin-bottom: 16px;
}

.empty-action {
  height: 34px;
  padding: 0 16px;
  font-size: 13px;
  border-radius: 8px;
}

.folder-icon {
  color: var(--kb-amber) !important;
}

.folder-open-icon {
  color: var(--kb-amber) !important;
}

.file-icon {
  color: var(--kb-primary) !important;
}

.tree-node-wrapper {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding-right: 4px;
}

.tree-node-main {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.node-name {
  font-size: 13px;
  color: var(--kb-fg);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--kb-primary-soft);
  color: var(--kb-primary-hover);
  white-space: nowrap;
  flex-shrink: 0;
}

.node-badge.file-badge {
  background: var(--kb-cyan-soft);
  color: #0891b2;
}

.node-more-btn {
  width: 22px;
  height: 22px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--kb-fg-mute) !important;
  opacity: 0;
  transition: all 0.2s ease;
}

.custom-tree :deep(.ant-tree-treenode:hover) .node-more-btn {
  opacity: 1;
}

.node-more-btn:hover {
  background: var(--kb-primary-tint) !important;
  color: var(--kb-primary) !important;
}

/* ========== Stats Footer ========== */
.stats-footer {
  padding: 14px 20px;
  border-top: 1px solid var(--kb-border);
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  gap: 12px 16px;
}

.storage-path-info {
  width: 100%;
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid var(--kb-border);
  border-radius: 8px;
  background: var(--kb-bg-subtle);
}

.storage-path-label {
  display: block;
  margin-bottom: 6px;
  font-size: 10px;
  letter-spacing: 0;
  color: var(--kb-fg-3);
}

.storage-path-code {
  display: block;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 11px;
  line-height: 1.5;
  color: var(--kb-primary-hover);
  white-space: normal;
  overflow-wrap: anywhere;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

.stat-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.folder-stat {
  background: var(--kb-amber-soft);
  color: var(--kb-amber);
}

.file-stat {
  background: var(--kb-primary-soft);
  color: var(--kb-primary);
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--kb-fg);
  line-height: 1.2;
}

.stat-label {
  font-size: 11px;
  color: var(--kb-fg-3);
}

.stat-divider {
  width: 1px;
  height: 28px;
  background: var(--kb-border);
}

/* ========== Detail Panel ========== */
.detail-panel {
  min-height: calc(100vh - 140px);
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ========== Breadcrumb ========== */
.breadcrumb-bar {
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius);
  padding: 12px 20px;
}

.breadcrumb-bar :deep(.ant-breadcrumb) {
  color: var(--kb-fg-3);
}

.breadcrumb-bar :deep(.ant-breadcrumb-separator) {
  color: var(--kb-fg-mute);
}

.breadcrumb-link {
  color: var(--kb-fg-3) !important;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.2s;
}

.breadcrumb-link:hover {
  color: var(--kb-primary) !important;
  background: var(--kb-primary-tint);
}

.breadcrumb-current {
  color: var(--kb-fg);
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
}

/* ========== Info Card ========== */
.info-card {
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius-lg);
  overflow: hidden;
}

.info-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px;
  border-bottom: 1px solid var(--kb-border);
}

.info-identity {
  display: flex;
  align-items: center;
  gap: 16px;
}

.info-avatar {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.info-avatar.folder-avatar {
  background: linear-gradient(135deg, var(--kb-primary-soft), var(--kb-cyan-soft));
  color: var(--kb-primary);
}

.info-avatar.file-avatar {
  background: linear-gradient(135deg, var(--kb-primary-soft), var(--kb-cyan-soft));
  color: var(--kb-cyan);
}

.info-titles {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-name {
  font-size: 20px;
  font-weight: 800;
  color: var(--kb-fg);
  margin: 0;
}

.info-desc {
  font-size: 13px;
  color: var(--kb-fg-3);
  margin: 0;
}

.info-actions {
  display: flex;
  gap: 8px;
}

.icon-action {
  color: var(--kb-fg-3);
  border-radius: 8px;
  transition: all 0.2s;
}

.icon-action:hover {
  color: var(--kb-primary);
  background: var(--kb-primary-tint);
}

.icon-action.danger:hover {
  color: var(--kb-rose);
  background: var(--kb-rose-soft);
}

.info-body {
  padding: 24px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-item.full-width {
  grid-column: span 2;
}

.info-label {
  font-size: 12px;
  color: var(--kb-fg-mute);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  font-size: 14px;
  color: var(--kb-fg);
}

.info-code {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px;
  color: var(--kb-primary-hover);
  background: var(--kb-primary-soft);
  padding: 6px 12px;
  border-radius: 6px;
  word-break: break-all;
}

.tag-folder {
  background: var(--kb-primary-soft) !important;
  border-color: rgba(37,99,235,0.2) !important;
  color: var(--kb-primary-hover) !important;
}

.tag-file {
  background: var(--kb-cyan-soft) !important;
  border-color: rgba(6,182,212,0.2) !important;
  color: #0891b2 !important;
}

/* ========== Preview Card ========== */
.preview-card {
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius-lg);
  overflow: hidden;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid var(--kb-border);
}

.preview-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--kb-fg);
  font-weight: 600;
}

.preview-title :deep(.anticon) {
  color: var(--kb-primary);
}

.preview-actions {
  display: flex;
  gap: 8px;
}

.preview-action {
  color: var(--kb-fg-3);
  display: flex;
  align-items: center;
  gap: 4px;
}

.preview-action:hover {
  color: var(--kb-primary);
}

.preview-body {
  min-height: 300px;
}

.preview-loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

.preview-frame {
  display: flex;
  flex-direction: column;
}

.preview-image {
  display: flex;
  justify-content: center;
  padding: 24px;
}

.preview-image img {
  max-width: 100%;
  max-height: 500px;
  border-radius: 12px;
  cursor: pointer;
  transition: transform 0.3s;
}

.preview-image img:hover {
  transform: scale(1.02);
}

.preview-pdf iframe {
  width: 100%;
  height: 600px;
  border: none;
}

.preview-video {
  padding: 24px;
}

.preview-video video {
  width: 100%;
  max-height: 500px;
  border-radius: 12px;
  background: #000;
}

.preview-audio {
  padding: 24px;
  display: flex;
  justify-content: center;
}

.preview-audio audio {
  width: 100%;
  max-width: 500px;
}

.preview-docx iframe {
  width: 100%;
  height: 600px;
  border: none;
}

.preview-markdown iframe {
  width: 100%;
  height: 600px;
  border: none;
}

.preview-text {
  padding: 24px;
}

.preview-text pre {
  background: var(--kb-bg-subtle);
  border: 1px solid var(--kb-border);
  border-radius: 12px;
  padding: 20px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: var(--kb-fg);
  overflow-x: auto;
  max-height: 600px;
  overflow-y: auto;
}

.preview-office {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 24px;
  text-align: center;
}

.office-icon {
  font-size: 64px;
  color: var(--kb-primary);
  margin-bottom: 16px;
}

.office-label {
  font-size: 18px;
  font-weight: 700;
  color: var(--kb-fg);
  margin-bottom: 8px;
}

.office-name {
  font-size: 14px;
  color: var(--kb-fg-3);
  margin-bottom: 24px;
}

.office-actions {
  display: flex;
  gap: 12px;
}

.preview-other {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 24px;
  text-align: center;
}

.other-icon {
  font-size: 64px;
  color: var(--kb-fg-mute);
  margin-bottom: 16px;
}

.other-label {
  font-size: 16px;
  color: var(--kb-fg-3);
  margin-bottom: 8px;
}

.other-name {
  font-size: 14px;
  color: var(--kb-fg-mute);
  margin-bottom: 24px;
}

/* ========== Child Content Card ========== */
.children-card {
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius-lg);
  overflow: hidden;
}

.children-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid var(--kb-border);
}

.children-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--kb-fg);
  font-weight: 600;
}

.children-title :deep(.anticon) {
  color: var(--kb-primary);
}

.children-count {
  color: var(--kb-fg-mute);
  font-weight: 400;
}

.children-actions {
  display: flex;
  gap: 8px;
}

.children-btn {
  display: flex;
  align-items: center;
  gap: 4px;
}

.children-body {
  padding: 24px;
}

.empty-children {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
}

.empty-children-icon {
  font-size: 48px;
  color: var(--kb-fg-mute);
  margin-bottom: 16px;
}

.empty-children-text {
  font-size: 14px;
  color: var(--kb-fg-3);
  margin-bottom: 16px;
}

.empty-children-actions {
  display: flex;
  gap: 12px;
}

.children-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.child-card {
  background: var(--kb-bg);
  border: 1px solid var(--kb-border);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.child-card:hover {
  background: var(--kb-primary-tint);
  border-color: rgba(37,99,235,0.3);
  transform: translateY(-2px);
}

.child-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.child-icon.child-folder {
  background: linear-gradient(135deg, var(--kb-primary-soft), var(--kb-cyan-soft));
  color: var(--kb-primary);
}

.child-icon.child-file {
  background: linear-gradient(135deg, var(--kb-cyan-soft), var(--kb-emerald-soft));
  color: var(--kb-cyan);
}

.child-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.child-name {
  font-size: 14px;
  color: var(--kb-fg);
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.child-meta {
  font-size: 12px;
  color: var(--kb-fg-mute);
}

.child-more {
  position: absolute;
  top: 8px;
  right: 8px;
  color: var(--kb-fg-mute);
}

.child-more:hover {
  color: var(--kb-primary);
}

/* ========== Unselected State ========== */
.empty-detail {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 140px);
  text-align: center;
}

.empty-detail-visual {
  position: relative;
  width: 200px;
  height: 200px;
  margin-bottom: 32px;
}

.empty-orbit {
  position: relative;
  width: 100%;
  height: 100%;
}

.orbit-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, var(--kb-primary-soft), var(--kb-cyan-soft));
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  color: var(--kb-primary);
}

.orbit-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  border: 1px solid rgba(37,99,235,0.15);
  border-radius: 50%;
  transform: translate(-50%, -50%);
}

.orbit-ring.ring-1 {
  width: 140px;
  height: 140px;
  animation: orbitSpin 8s linear infinite;
}

.orbit-ring.ring-2 {
  width: 180px;
  height: 180px;
  animation: orbitSpin 12s linear infinite reverse;
}

@keyframes orbitSpin {
  from {
    transform: translate(-50%, -50%) rotate(0deg);
  }

  to {
    transform: translate(-50%, -50%) rotate(360deg);
  }
}

.empty-detail-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--kb-fg);
  margin-bottom: 8px;
}

.empty-detail-desc {
  font-size: 14px;
  color: var(--kb-fg-3);
}

/* ========== Dialog Styles ========== */
.dark-modal :deep(.ant-modal-content) {
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border);
  border-radius: 20px;
}

.dark-modal :deep(.ant-modal-header) {
  background: transparent;
  border-bottom: 1px solid var(--kb-border);
  border-radius: 20px 20px 0 0;
}

.dark-modal :deep(.ant-modal-title) {
  color: var(--kb-fg);
}

.dark-modal :deep(.ant-modal-body) {
  background: transparent;
}

.dark-modal :deep(.ant-modal-footer) {
  border-top: 1px solid var(--kb-border);
}

.dark-modal :deep(.ant-form-item-label > label) {
  color: var(--kb-fg-2);
}

.dark-modal :deep(.ant-input),
.dark-modal :deep(.ant-input-textarea) {
  background: var(--kb-bg);
  border-color: var(--kb-border-strong);
  color: var(--kb-fg);
}

.dark-modal :deep(.ant-input:focus),
.dark-modal :deep(.ant-input-focused) {
  border-color: var(--kb-primary);
  box-shadow: 0 0 0 2px rgba(37,99,235,0.12);
}

.dark-modal :deep(.ant-input::placeholder) {
  color: var(--kb-fg-mute);
}

/* ========== {{ $t('fs.upload') }} Component ========== */
.dark-uploader {
  background: var(--kb-bg-subtle);
  border-color: var(--kb-border-strong);
}

.dark-uploader:hover {
  border-color: var(--kb-primary);
}

.dark-uploader :deep(.ant-upload-drag-icon) {
  color: var(--kb-primary);
}

.dark-uploader :deep(.ant-upload-text) {
  color: var(--kb-fg);
}

.dark-uploader :deep(.ant-upload-hint) {
  color: var(--kb-fg-3);
}

.upload-desc :deep(.ant-form-item-control-input) {
  margin-top: 8px;
}

/* ========== Parse Options ========== */
.parse-option-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.parse-option-row:last-child {
  margin-bottom: 0;
}

.parse-option-label {
  font-size: 14px;
  color: var(--kb-fg-3);
  min-width: 80px;
}

.parse-option-row .ant-input {
  background: var(--kb-bg);
  border-color: var(--kb-border-strong);
  color: var(--kb-fg);
}

.parse-option-row .ant-input:focus {
  border-color: var(--kb-primary);
  box-shadow: 0 0 0 2px rgba(37,99,235,0.12);
}

.parse-option-row .ant-input::placeholder {
  color: var(--kb-fg-mute);
}

/* ========== Parse Progress ========== */
.parse-progress {
  margin-top: 16px;
  padding: 16px;
  background: var(--kb-primary-soft);
  border-radius: 12px;
}

.parse-current {
  margin-top: 8px;
  font-size: 13px;
  color: var(--kb-fg-3);
  text-align: center;
}

/* ========== Fullscreen Preview ========== */
.fullscreen-preview-modal :deep(.ant-modal-content) {
  background: var(--kb-bg-elevated);
  border: none;
  border-radius: 20px;
}

.fullscreen-preview-modal :deep(.ant-modal-header) {
  background: transparent;
  border-bottom: 1px solid var(--kb-border);
}

.fullscreen-preview-modal :deep(.ant-modal-title) {
  color: var(--kb-fg);
}

.fullscreen-content {
  height: 80vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.fullscreen-frame {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.fullscreen-image {
  max-width: 100%;
  max-height: 80vh;
  border-radius: 12px;
}

.fullscreen-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.fullscreen-video,
.fullscreen-audio {
  max-width: 100%;
}

.fullscreen-text {
  width: 100%;
  height: 100%;
  overflow: auto;
  padding: 24px;
}

.fullscreen-text pre {
  background: var(--kb-bg-subtle);
  border: 1px solid var(--kb-border);
  border-radius: 12px;
  padding: 20px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 14px;
  line-height: 1.6;
  color: var(--kb-fg);
  white-space: pre-wrap;
  word-break: break-word;
}

.fullscreen-fallback {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.fallback-icon {
  font-size: 64px;
  color: var(--kb-fg-mute);
}

.fullscreen-fallback p {
  color: var(--kb-fg-3);
}

/* ========== Dark Dropdown Menu ========== */
.dark-dropdown-menu {
  background: var(--kb-bg-elevated) !important;
  border: 1px solid var(--kb-border) !important;
  border-radius: 12px !important;
  box-shadow: var(--kb-shadow-lg) !important;
}

.dark-dropdown-menu :deep(.ant-dropdown-menu-item) {
  color: var(--kb-fg-2) !important;
}

.dark-dropdown-menu :deep(.ant-dropdown-menu-item:hover) {
  background: var(--kb-primary-tint) !important;
  color: var(--kb-primary) !important;
}

.dark-dropdown-menu :deep(.ant-dropdown-menu-item-danger:hover) {
  background: var(--kb-rose-soft) !important;
  color: var(--kb-rose) !important;
}

.dark-dropdown-menu :deep(.ant-dropdown-menu-item-divider) {
  background: var(--kb-border);
}

.dark-dropdown-menu :deep(.anticon) {
  color: inherit;
}

/* ========== Confirm Dialog ========== */
.kb-confirm-modal :deep(.ant-modal-content) {
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border);
  border-radius: 20px;
}

.kb-confirm-modal :deep(.ant-modal-title) {
  color: var(--kb-fg);
}

.kb-confirm-modal :deep(.ant-modal-body) {
  color: var(--kb-fg-2);
}

/* ========== Responsive Design ========== */
@media (max-width: 1200px) {
  .content-grid {
    grid-template-columns: 320px 1fr;
  }
}

@media (max-width: 992px) {
  .content-grid {
    grid-template-columns: 280px 1fr;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }

  .info-item.full-width {
    grid-column: span 1;
  }
}

@media (max-width: 768px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .sidebar-panel {
    max-height: 400px;
  }

  .page-header-content {
    flex-direction: column;
    gap: 16px;
  }

  .header-actions {
    justify-content: flex-start;
  }

  .children-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 576px) {
  .page-header {
    padding: 16px;
  }

  .header-title {
    font-size: 18px;
  }

  .header-subtitle {
    font-size: 12px;
  }

  .header-icon {
    width: 40px;
    height: 40px;
    font-size: 20px;
  }

  .action-btn span {
    display: none;
  }

  .mini-create-btn span {
    display: none;
  }
}
</style>

<style>
/* Global styles — ensure custom-tree styles apply */
.custom-tree .ant-tree-node-content-wrapper.ant-tree-node-selected {
  background-color: var(--kb-primary-soft) !important;
}

.custom-tree .ant-tree-node-content-wrapper.ant-tree-node-selected:hover {
  background-color: var(--kb-primary-soft) !important;
}

.custom-tree .ant-tree-checkbox+span.ant-tree-node-selected {
  background-color: var(--kb-primary-soft) !important;
}

.custom-tree .ant-tree-checkbox+span.ant-tree-node-selected:hover {
  background-color: var(--kb-primary-soft) !important;
}

.custom-tree .ant-tree-node-selected {
  background: transparent !important;
}

.custom-tree .ant-tree-treenode {
  padding: 2px 0;
  color: var(--kb-fg-2) !important;
  transition: all 0.2s ease;
  border-radius: 8px;
}

.custom-tree .ant-tree-treenode:hover {
  background-color: var(--kb-primary-tint);
}

/* Smooth transition on selected node hover */
.custom-tree .ant-tree-treenode {
  transition: background-color 0.2s var(--kb-ease), transform 0.2s var(--kb-ease);
}

.custom-tree .ant-tree-switcher {
  color: var(--kb-fg-mute) !important;
}
</style>
