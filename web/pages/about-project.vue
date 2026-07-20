<template>
  <div class="about-project-page">
    <!-- Page header area -->
    <div class="page-header">
      <div class="header-icon">
        <ProjectOutlined />
      </div>
      <div class="header-content">
        <h1 class="page-title">{{ $t('aboutProject.title') }}</h1>
        <p class="page-subtitle">{{ $t('aboutProject.subtitle') }}</p>
      </div>
    </div>

    <!-- Project intro card -->
    <a-row :gutter="[24, 24]" class="content-row">
      <a-col :span="24">
        <a-card class="glass-card intro-card">
          <div class="intro-section">
            <h2 class="section-title">
              <InfoCircleOutlined />
              项目概述
            </h2>
            <p class="intro-text">
              RAG Knowledge Base 是一个基于检索增强生成（Retrieval-Augmented Generation, RAG）技术的智能知识管理系统。
              该系统旨在帮助用户高效地管理、检索和利用知识资源，通过结合大语言模型的生成能力与精准的知识检索技术，
              为用户提供智能问答、文档解析和知识发现服务。
            </p>
            <div class="tech-badges">
              <a-tag color="purple">Vue 3</a-tag>
              <a-tag color="blue">Nuxt 3</a-tag>
              <a-tag color="cyan">TypeScript</a-tag>
              <a-tag color="geekblue">Python</a-tag>
              <a-tag color="green">FastAPI</a-tag>
              <a-tag color="orange">RAG</a-tag>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- Core features -->
    <a-row :gutter="[24, 24]" class="content-row">
      <a-col :span="24">
        <h2 class="section-title-main">
          <AppstoreOutlined />
          Core features
        </h2>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="8" v-for="(feature, index) in features" :key="index">
        <a-card class="glass-card feature-card">
          <div class="feature-icon" :style="{ background: feature.gradient }">
            <component :is="feature.icon" />
          </div>
          <h3 class="feature-title">
            <component :is="feature.descIcon" class="feature-title-icon" />
            {{ feature.title }}
          </h3>
          <p class="feature-desc">{{ feature.description }}</p>
        </a-card>
      </a-col>
    </a-row>

    <!-- Technology architecture -->
    <a-row :gutter="[24, 24]" class="content-row">
      <a-col :span="24">
        <a-card class="glass-card architecture-card">
          <h2 class="section-title">
            <ClusterOutlined />
            Technology architecture
          </h2>
          <div class="architecture-content">
            <div class="arch-layer" v-for="(layer, index) in architecture" :key="index">
              <div class="layer-header">
                <div class="layer-icon" :style="{ background: layer.color }">
                  <component :is="layer.icon" />
                </div>
                <h3 class="layer-title">{{ layer.title }}</h3>
              </div>
              <p class="layer-desc">{{ layer.description }}</p>
              <div class="layer-techs">
                <a-tag v-for="(tech, idx) in layer.technologies" :key="idx" class="tech-tag">
                  <component :is="tech.icon" class="tech-icon" />
                  {{ tech.name }}
                </a-tag>
              </div>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- Project highlights -->
    <a-row :gutter="[24, 24]" class="content-row">
      <a-col :span="24">
        <a-card class="glass-card features-list-card">
          <h2 class="section-title">
            <StarOutlined />
            Project highlights
          </h2>
          <a-list class="features-list" :data-source="highlights" :split="false">
            <template #renderItem="{ item }">
              <a-list-item class="feature-list-item">
                <div class="feature-item">
                  <div class="feature-icon-wrapper" :style="{ background: item.color }">
                    <component :is="item.icon" class="feature-item-icon" />
                  </div>
                  <div class="feature-content">
                    <h4>{{ item.title }}</h4>
                    <p>{{ item.description }}</p>
                  </div>
                </div>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </a-col>
    </a-row>

    <!-- Getting started guide -->
    <a-row :gutter="[24, 24]" class="content-row">
      <a-col :span="24">
        <a-card class="glass-card guide-card">
          <h2 class="section-title">
            <ReadOutlined />
            快速开始
          </h2>
          <a-timeline class="guide-timeline">
            <a-timeline-item v-for="(step, index) in guideSteps" :key="index" :color="step.color">
              <div class="timeline-content">
                <h4>
                  <component :is="step.icon" class="timeline-icon" />
                  {{ step.title }}
                </h4>
                <p>{{ step.description }}</p>
              </div>
            </a-timeline-item>
          </a-timeline>
        </a-card>
      </a-col>
    </a-row>

    <!-- Contact information -->
    <a-row :gutter="[24, 24]" class="content-row">
      <a-col :span="24">
        <a-card class="glass-card contact-card">
          <h2 class="section-title">
            <TeamOutlined />
            Contact us
          </h2>
          <div class="contact-content">
            <p class="contact-text">
              如果您对项目有任何疑问、建议或合作意向，欢迎通过以下方式Contact us：
            </p>
            <div class="contact-links">
              <a-button type="primary" size="large" class="contact-btn">
                <GithubOutlined />
                GitHub 仓库
              </a-button>
              <a-button size="large" class="contact-btn">
                <MailOutlined />
                发送邮件
              </a-button>
              <a-button size="large" class="contact-btn">
                <BookOutlined />
                查看文档
              </a-button>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import {
  ProjectOutlined,
  InfoCircleOutlined,
  AppstoreOutlined,
  ClusterOutlined,
  StarOutlined,
  ReadOutlined,
  TeamOutlined,
  GithubOutlined,
  MailOutlined,
  BookOutlined,
  FolderOutlined,
  FileSearchOutlined,
  RobotOutlined,
  SafetyOutlined,
  ThunderboltOutlined,
  CloudOutlined,
  DatabaseOutlined,
  ApiOutlined,
  GlobalOutlined,
  CodeOutlined,
  BranchesOutlined,
  DeploymentUnitOutlined,
  FolderOpenOutlined,
  SearchOutlined,
  MessageOutlined,
  FileTextOutlined,
  SyncOutlined,
  CloudUploadOutlined,
  RocketOutlined,
  BulbOutlined,
  TranslationOutlined,
  HeartOutlined,
  AppstoreAddOutlined,
  LockOutlined,
  MobileOutlined
} from '@ant-design/icons-vue'

// Core featuresData
const features = [
  {
    icon: FolderOutlined,
    title: '知识库管理',
    description: '支持多级文件夹结构，可创建、编辑、删除知识库，支持批量文件上传和解析',
    gradient: 'linear-gradient(135deg, #8b5cf6, #a78bfa)',
    descIcon: FolderOpenOutlined
  },
  {
    icon: FileSearchOutlined,
    title: '智能检索',
    description: '基于向量检索技术，支持语义搜索和关键词搜索，快速定位所需知识',
    gradient: 'linear-gradient(135deg, #3b82f6, #60a5fa)',
    descIcon: SearchOutlined
  },
  {
    icon: RobotOutlined,
    title: 'AI 问答',
    description: '集成大语言模型，基于检索到的知识进行智能问答，提供准确答案',
    gradient: 'linear-gradient(135deg, #10b981, #34d399)',
    descIcon: MessageOutlined
  },
  {
    icon: SafetyOutlined,
    title: '文档解析',
    description: '支持 PDF、Word、Markdown 等多种格式文档的自动解析和内容提取',
    gradient: 'linear-gradient(135deg, #f59e0b, #fbbf24)',
    descIcon: FileTextOutlined
  },
  {
    icon: ThunderboltOutlined,
    title: '实时处理',
    description: '支持实时文档解析进度显示，后台异步处理，不阻塞用户操作',
    gradient: 'linear-gradient(135deg, #ec4899, #f472b6)',
    descIcon: SyncOutlined
  },
  {
    icon: CloudOutlined,
    title: '云端同步',
    description: '支持知识库的导入导出，便于备份和跨环境迁移',
    gradient: 'linear-gradient(135deg, #06b6d4, #22d3ee)',
    descIcon: CloudUploadOutlined
  }
]

// Technology architectureData
const architecture = [
  {
    icon: GlobalOutlined,
    title: '前端层',
    description: '基于 Vue 3 + Nuxt 3 构建的现代化用户界面，采用 TypeScript 开发',
    color: 'linear-gradient(135deg, #8b5cf6, #a78bfa)',
    technologies: [
      { name: 'Vue 3', icon: 'CodeOutlined' },
      { name: 'Nuxt 3', icon: 'RocketOutlined' },
      { name: 'TypeScript', icon: 'FileTextOutlined' },
      { name: 'Ant Design Vue', icon: 'AppstoreOutlined' },
      { name: 'Pinia', icon: 'DatabaseOutlined' }
    ]
  },
  {
    icon: ApiOutlined,
    title: 'API 层',
    description: '基于 Python FastAPI 构建的高性能 RESTful API 服务',
    color: 'linear-gradient(135deg, #3b82f6, #60a5fa)',
    technologies: [
      { name: 'Python', icon: 'CodeOutlined' },
      { name: 'FastAPI', icon: 'ThunderboltOutlined' },
      { name: 'Uvicorn', icon: 'RocketOutlined' },
      { name: 'Pydantic', icon: 'SafetyOutlined' }
    ]
  },
  {
    icon: DatabaseOutlined,
    title: '数据层',
    description: '支持多种数据存储方案，包括向量数据库和关系型数据库',
    color: 'linear-gradient(135deg, #10b981, #34d399)',
    technologies: [
      { name: 'ChromaDB', icon: DeploymentUnitOutlined },
      { name: 'PostgreSQL', icon: DatabaseOutlined },
      { name: 'Redis', icon: ThunderboltOutlined },
      { name: 'MinIO', icon: CloudOutlined }
    ]
  },
  {
    icon: CodeOutlined,
    title: 'AI 层',
    description: '集成大语言模型和嵌入模型，提供智能问答和知识检索能力',
    color: 'linear-gradient(135deg, #f59e0b, #fbbf24)',
    technologies: [
      { name: 'OpenAI', icon: RobotOutlined },
      { name: 'Ollama', icon: BulbOutlined },
      { name: 'LangChain', icon: BranchesOutlined },
      { name: 'Sentence Transformers', icon: TranslationOutlined }
    ]
  }
]

// Project highlightsData
const highlights = [
  {
    icon: HeartOutlined,
    title: '开源免费',
    description: '项目完全开源，基于 MIT 协议，可自由使用和二次开发',
    color: 'linear-gradient(135deg, #8b5cf6, #a78bfa)'
  },
  {
    icon: RocketOutlined,
    title: '易于部署',
    description: '提供 Docker 部署方案，支持一键启动，降低部署门槛',
    color: 'linear-gradient(135deg, #3b82f6, #60a5fa)'
  },
  {
    icon: AppstoreAddOutlined,
    title: '高度可扩展',
    description: '模块化架构设计，支持自定义组件和插件扩展',
    color: 'linear-gradient(135deg, #10b981, #34d399)'
  },
  {
    icon: LockOutlined,
    title: '安全可靠',
    description: '支持用户认证和权限管理，保障数据安全',
    color: 'linear-gradient(135deg, #f59e0b, #fbbf24)'
  },
  {
    icon: MobileOutlined,
    title: '响应式设计',
    description: '适配多种屏幕尺寸，支持桌面端和移动端访问',
    color: 'linear-gradient(135deg, #ec4899, #f472b6)'
  }
]

// Quick start steps
const guideSteps = [
  {
    icon: FolderOutlined,
    title: '创建知识库',
    description: '在文件系统中创建您的第一个知识库文件夹',
    color: '#8b5cf6'
  },
  {
    icon: CloudUploadOutlined,
    title: '上传文档',
    description: '将 PDF、Word 或 Markdown 文档上传到知识库中',
    color: '#3b82f6'
  },
  {
    icon: FileTextOutlined,
    title: '解析文档',
    description: '系统自动解析文档内容，提取文本和元数据',
    color: '#10b981'
  },
  {
    icon: SearchOutlined,
    title: '开始检索',
    description: '使用搜索功能或 AI 问答，快速获取所需知识',
    color: '#f59e0b'
  }
]
</script>

<style scoped>
/* Project info page — light industrial theme */
.about-project-page { color: var(--kb-fg); animation: kb-fade-in 0.4s var(--kb-ease-out); min-height: calc(100vh - 110px); }

.page-header { display: flex; align-items: center; gap: 18px; padding: 28px 32px; margin-bottom: 24px; border-radius: var(--kb-radius-xl); background: radial-gradient(700px 320px at 90% 0%, rgba(6,182,212,0.16), transparent 60%), radial-gradient(600px 300px at 0% 100%, rgba(37,99,235,0.18), transparent 62%), linear-gradient(135deg, #0d1424, #13234a); animation: kb-fade-up 0.5s var(--kb-ease-out) both; position: relative; overflow: hidden; }
.page-header::before { content: ''; position: absolute; inset: 0; background-image: linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px); background-size: 48px 48px; mask-image: radial-gradient(circle at 50% 50%, #000, transparent 80%); pointer-events: none; }
.header-icon { width: 60px; height: 60px; border-radius: 16px; display: grid; place-items: center; font-size: 28px; color: #fff; background: linear-gradient(135deg, var(--kb-primary), var(--kb-cyan)); box-shadow: 0 10px 26px rgba(37,99,235,0.4); }
.header-content h1 { font-size: 28px; font-weight: 800; color: #fff; margin: 0 0 4px; letter-spacing: -0.6px; }
.header-content p { font-size: 14.5px; color: #aab6d4; margin: 0; }

.content-row { margin-bottom: 8px !important; }

/* glass-card: light card style */
:deep(.glass-card) { background: var(--kb-bg-elevated) !important; border: 1px solid var(--kb-border) !important; border-radius: var(--kb-radius-lg) !important; box-shadow: var(--kb-shadow-sm); }
:deep(.glass-card .ant-card-body) { padding: 26px; }
:deep(.glass-card:hover) { box-shadow: var(--kb-shadow-md); }

.intro-card { animation: kb-fade-up 0.5s 0.05s var(--kb-ease-out) both; }
.intro-section .section-title { font-size: 21px; font-weight: 800; color: var(--kb-fg); margin-bottom: 14px; display: flex; align-items: center; gap: 9px; }
.intro-section .section-title :deep(.anticon) { color: var(--kb-primary); }
.intro-text { font-size: 15px; line-height: 1.85; color: var(--kb-fg-2); margin-bottom: 18px; }
.tech-badges { display: flex; flex-wrap: wrap; gap: 8px; }

.section-title-main { font-size: 22px; font-weight: 800; color: var(--kb-fg); margin: 30px 0 18px; display: flex; align-items: center; gap: 10px; padding-left: 4px; }
.section-title-main :deep(.anticon) { color: var(--kb-primary); }

.feature-card { transition: all var(--kb-dur) var(--kb-ease); animation: kb-fade-up 0.5s var(--kb-ease-out) both; }
.feature-card:hover { transform: translateY(-5px); box-shadow: var(--kb-shadow-lg) !important; }
.feature-icon { width: 50px; height: 50px; border-radius: 14px; display: grid; place-items: center; font-size: 23px; color: #fff; margin-bottom: 14px; box-shadow: var(--kb-shadow-sm); }
.feature-title { font-size: 16.5px; font-weight: 700; color: var(--kb-fg); margin-bottom: 8px; display: flex; align-items: center; gap: 7px; }
.feature-title-icon { font-size: 15px; color: var(--kb-primary); }
.feature-desc { font-size: 13.5px; line-height: 1.65; color: var(--kb-fg-3); }

.architecture-card { animation: kb-fade-up 0.5s 0.1s var(--kb-ease-out) both; }
.architecture-card .section-title { font-size: 21px; font-weight: 800; color: var(--kb-fg); margin-bottom: 22px; display: flex; align-items: center; gap: 9px; }
.architecture-card .section-title :deep(.anticon) { color: var(--kb-primary); }
.architecture-content { display: flex; flex-direction: column; gap: 18px; }
.arch-layer { padding: 20px; border-radius: var(--kb-radius); background: var(--kb-bg); border: 1px solid var(--kb-border); transition: all var(--kb-dur) var(--kb-ease); }
.arch-layer:hover { border-color: var(--kb-border-strong); box-shadow: var(--kb-shadow-sm); transform: translateX(4px); }
.layer-header { display: flex; align-items: center; gap: 14px; margin-bottom: 10px; }
.layer-icon { width: 44px; height: 44px; border-radius: 12px; display: grid; place-items: center; font-size: 21px; color: #fff; }
.layer-title { font-size: 17px; font-weight: 700; color: var(--kb-fg); margin: 0; }
.layer-desc { font-size: 14px; color: var(--kb-fg-3); line-height: 1.6; margin: 0 0 14px; }
.layer-techs { display: flex; flex-wrap: wrap; gap: 8px; }
.tech-tag { display: inline-flex; align-items: center; gap: 6px; background: var(--kb-bg-elevated) !important; border: 1px solid var(--kb-border) !important; color: var(--kb-fg-2) !important; border-radius: 999px !important; font-size: 12.5px; font-weight: 600; padding: 3px 11px; margin: 0; }
.tech-icon { font-size: 13px; color: var(--kb-primary); }

.features-list-card { animation: kb-fade-up 0.5s 0.15s var(--kb-ease-out) both; }
.features-list-card .section-title { font-size: 21px; font-weight: 800; color: var(--kb-fg); margin-bottom: 18px; display: flex; align-items: center; gap: 9px; }
.features-list-card .section-title :deep(.anticon) { color: var(--kb-primary); }
:deep(.features-list .ant-list-item) { border-bottom: 1px solid var(--kb-border) !important; padding: 16px 0 !important; }
.feature-item { display: flex; align-items: flex-start; gap: 14px; width: 100%; }
.feature-icon-wrapper { width: 42px; height: 42px; border-radius: 12px; display: grid; place-items: center; font-size: 19px; color: #fff; flex-shrink: 0; }
.feature-content { flex: 1; }
.feature-content h4 { font-size: 15.5px; font-weight: 700; color: var(--kb-fg); margin: 2px 0 5px; }
.feature-content p { font-size: 13.5px; color: var(--kb-fg-3); line-height: 1.55; margin: 0; }

.guide-card { animation: kb-fade-up 0.5s 0.2s var(--kb-ease-out) both; }
.guide-card .section-title { font-size: 21px; font-weight: 800; color: var(--kb-fg); margin-bottom: 20px; display: flex; align-items: center; gap: 9px; }
.guide-card .section-title :deep(.anticon) { color: var(--kb-primary); }
:deep(.guide-timeline .ant-timeline-item-head) { background: var(--kb-primary); border-color: var(--kb-primary); }
:deep(.guide-timeline .ant-timeline-item-tail) { border-inline-start: 2px solid var(--kb-border); }
.timeline-content { padding: 14px 18px; border-radius: var(--kb-radius); background: var(--kb-bg); border: 1px solid var(--kb-border); transition: all var(--kb-dur-fast) var(--kb-ease); }
.timeline-content:hover { border-color: var(--kb-border-strong); box-shadow: var(--kb-shadow-sm); transform: translateX(4px); }
.timeline-content h4 { font-size: 15px; font-weight: 700; color: var(--kb-fg); margin: 0 0 5px; display: flex; align-items: center; gap: 7px; }
.timeline-content h4 :deep(.anticon) { color: var(--kb-primary); }
.timeline-content p { font-size: 13.5px; color: var(--kb-fg-3); margin: 0; line-height: 1.6; }

.contact-card { animation: kb-fade-up 0.5s 0.25s var(--kb-ease-out) both; }
.contact-card .section-title { font-size: 21px; font-weight: 800; color: var(--kb-fg); margin-bottom: 16px; display: flex; align-items: center; gap: 9px; }
.contact-card .section-title :deep(.anticon) { color: var(--kb-primary); }
.contact-text { font-size: 15px; line-height: 1.7; color: var(--kb-fg-2); margin-bottom: 22px; }
.contact-links { display: flex; gap: 12px; flex-wrap: wrap; }
.contact-btn { height: 46px; border-radius: 12px; font-weight: 600; display: inline-flex; align-items: center; gap: 8px; transition: all var(--kb-dur) var(--kb-ease); }
.contact-btn:hover { transform: translateY(-2px); box-shadow: var(--kb-shadow-md); }
</style>

