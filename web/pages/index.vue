<template>
  <div class="landing-page">
    <!-- Animated background layer -->
    <div class="bg-layer">
      <div class="bg-orb orb-a"></div>
      <div class="bg-orb orb-b"></div>
      <div class="bg-orb orb-c"></div>
      <div class="bg-grain"></div>
    </div>

    <div class="page-inner">
      <!-- Hero -->
      <section class="hero">
        <div class="hero-badge">
          <ThunderboltOutlined /> AI 驱动的知识管理
        </div>

        <h1 class="hero-title">
          <span class="title-line"><span class="text-gradient">{{ $t('about.heroTitle') }}</span></span>
          <span class="title-line"><span class="text-serif">{{ $t('home.title2') }}</span></span>
        </h1>

        <p class="hero-sub">
          基于检索增强生成技术，打造智能化的企业级知识管理平台
        </p>

        <div class="hero-actions">
          <a-button type="primary" size="large" class="btn-primary" @click="navigateToFileSystem">
            <FolderOpenOutlined /> 进入文件系统 <RightOutlined class="btn-arrow" />
          </a-button>
          <a-button size="large" class="btn-secondary" @click="scrollToFeatures">
            <InfoCircleOutlined /> 了解更多
          </a-button>
        </div>

        <div class="hero-stats">
          <div class="stat-item">
            <span class="stat-val">{{ healthStats.storage.kb_count || '-' }}</span>
            <span class="stat-lbl">{{ $t('graph.kbs') }}</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-val">{{ healthStats.storage.doc_count || '-' }}</span>
            <span class="stat-lbl">{{ $t('home.docs') }}</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-val">{{ healthStats.vector.coverage_pct }}%</span>
            <span class="stat-lbl">{{ $t('home.coverage') }}</span>
          </div>
        </div>
      </section>

      <!-- Feature matrix -->
      <section class="features" ref="featuresRef">
        <h2 class="section-title">{{ $t('home.coreCapabilities') }}</h2>

        <div class="feature-grid">
          <div v-for="(f, i) in features" :key="i" class="feature-card" :style="{ '--idx': i }">
            <div class="feature-icon"> {{ f.icon }} </div>
            <h3>{{ f.title }}</h3>
            <p>{{ f.desc }}</p>
          </div>
        </div>
      </section>

      <!-- Quick links -->
      <section class="quick-links">
        <div class="ql-card" @click="navigateTo('/file-system')">
          <FolderOpenOutlined />
          <div>
            <strong>{{ $t('home.quickLinks.fileSystem.title') }}</strong>
            <span>{{ $t('home.quickLinks.fileSystem.desc') }}</span>
          </div>
          <RightOutlined class="ql-arrow" />
        </div>
        <div class="ql-card" @click="navigateTo('/knowledge-search')">
          <SearchOutlined />
          <div>
            <strong>{{ $t('search.title') }}</strong>
            <span>QDCVR 精准召回</span>
          </div>
          <RightOutlined class="ql-arrow" />
        </div>
        <div class="ql-card" @click="navigateTo('/claude-chat')">
          <RobotOutlined />
          <div>
            <strong>{{ $t('nav.claudeChat') }}</strong>
            <span>Agent SDK 流式交互</span>
          </div>
          <RightOutlined class="ql-arrow" />
        </div>
        <div class="ql-card" @click="navigateTo('/knowledge-graph')">
          <ShareAltOutlined />
          <div>
            <strong>{{ $t('settings.knowledgeGraph') }}</strong>
            <span>Neo4j 可视化导航</span>
          </div>
          <RightOutlined class="ql-arrow" />
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  RightOutlined, ThunderboltOutlined, FolderOpenOutlined,
  InfoCircleOutlined, SearchOutlined, RobotOutlined,
  ShareAltOutlined,
} from '@ant-design/icons-vue'

const router = useRouter()
const featuresRef = ref<HTMLElement>()

const features = [
  { icon: '📄', title: '智能解析', desc: 'PDF/Word/Excel/PPT/图片 → Markdown，MinerU OCR 高精度' },
  { icon: '🔎', title: '精准检索', desc: 'QDCVR 六步检索 + 内容裁决，向量/CDI/经验三路召回' },
  { icon: '🧠', title: 'AI 对话', desc: '完整 Claude Code 客户端，流式 / 工具 / 技能 / 多模态' },
  { icon: '🌐', title: '知识图谱', desc: 'Neo4j 文档关系图谱，跨 KB 桥梁 + 路径发现' },
  { icon: '🏷️', title: '标签体系', desc: '结构化标签管理，自动归一化 + 黑名单过滤' },
  { icon: '📊', title: '经验复用', desc: '经验库 E0-E11 生命周期，检索优先 / 衰减 / 联动' },
]

function navigateToFileSystem() { router.push('/file-system') }
function navigateTo(path: string) { router.push(path) }

// ⭐ Real-time health stats
const healthStats = reactive({
  storage: { kb_count: 0, doc_count: 0, total_size_mb: 0 },
  vector: { indexed_docs: 0, total_docs: 0, coverage_pct: 0 },
  backend: { status: '' },
  neo4j: { available: false },
  status: 'loading',
})
onMounted(async () => {
  try {
    const d = await $fetch('/api/health/stats')
    Object.assign(healthStats, d)
  } catch { /* fallback to defaults */ }
})

function scrollToFeatures() {
  featuresRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
</script>

<style scoped>
.landing-page {
  position: relative;
  min-height: calc(100vh - 56px - 48px);
}

/* —— Animated background —— */
.bg-layer {
  position: fixed; inset: 0; z-index: 0;
  overflow: hidden; pointer-events: none;
}
.bg-orb {
  position: absolute; border-radius: 50%; filter: blur(80px);
  opacity: 0.15;
}
.orb-a {
  width: 500px; height: 500px;
  background: var(--kb-primary);
  top: -120px; right: -80px;
  animation: float-a 12s ease-in-out infinite;
}
.orb-b {
  width: 400px; height: 400px;
  background: var(--kb-cyan);
  bottom: -60px; left: -100px;
  animation: float-b 15s ease-in-out infinite;
}
.orb-c {
  width: 300px; height: 300px;
  background: var(--kb-amber);
  top: 50%; left: 60%;
  opacity: 0.08;
  animation: float-c 18s ease-in-out infinite;
}
.bg-grain {
  position: absolute; inset: 0;
  opacity: 0.025;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  background-size: 256px;
}

@keyframes float-a {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(40px, 30px) scale(1.05); }
  66% { transform: translate(-20px, -20px) scale(0.95); }
}
@keyframes float-b {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(-30px, 40px) scale(1.08); }
}
@keyframes float-c {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(50px, -30px) scale(1.1); }
  66% { transform: translate(-30px, 20px) scale(0.9); }
}

/* —— Content —— */
.page-inner {
  position: relative; z-index: 1;
  max-width: 960px; margin: 0 auto;
  padding: 60px 28px 80px;
}

/* —— Hero —— */
.hero { text-align: center; margin-bottom: 80px; animation: kb-fade-up 0.6s var(--kb-ease) both; }
.hero-badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 16px; border-radius: var(--kb-radius-pill);
  font-size: 11.5px; font-weight: 600;
  letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--kb-gold-deep);
  background: linear-gradient(135deg, var(--kb-gold-soft), rgba(212, 175, 106, 0.15));
  border: 1px solid rgba(184, 148, 90, 0.4);
  margin-bottom: 28px;
  box-shadow: 0 1px 3px rgba(184, 148, 90, 0.15);
}
.hero-title { margin: 0 0 18px; line-height: 1.12; }
.title-line { display: block; }
.text-gradient {
  font-size: clamp(42px, 8.5vw, 68px);
  font-weight: 700;
  font-family: var(--kb-font-display);
  background: linear-gradient(135deg,
    var(--kb-gold-deep) 0%,
    var(--kb-gold) 20%,
    var(--kb-gold-bright) 40%,
    var(--kb-primary) 65%,
    #d67a3c 85%,
    var(--kb-gold-bright) 100%);
  background-size: 200% 200%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.02em;
  animation: kb-gold-shimmer 8s ease-in-out infinite;
  text-shadow: 0 2px 4px rgba(184, 148, 90, 0.08);
}
.text-serif {
  font-size: clamp(26px, 5vw, 40px);
  font-family: var(--kb-font-serif);
  color: var(--kb-fg-2);
  font-weight: 500;
  font-style: italic;
  letter-spacing: 0.01em;
}
.hero-sub {
  font-size: clamp(15px, 2vw, 17px);
  color: var(--kb-fg-3);
  max-width: 540px; margin: 0 auto 36px;
  line-height: 1.75;
  font-family: var(--kb-font-serif);
  font-size: clamp(16px, 2vw, 18.5px);
}
.hero-actions { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }
.btn-primary {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 11px 26px; font-size: 14px;
  font-weight: 600; letter-spacing: 0.02em;
  border-radius: var(--kb-radius-sm);
  background: linear-gradient(135deg, var(--kb-primary) 0%, #c95530 100%);
  border-color: var(--kb-primary);
  box-shadow: var(--kb-shadow-primary);
  transition: all var(--kb-dur) var(--kb-ease);
}
.btn-primary:hover {
  background: linear-gradient(135deg, var(--kb-primary-hover) 0%, #b84724 100%) !important;
  border-color: var(--kb-primary-hover) !important;
  transform: translateY(-2px);
  box-shadow: 0 14px 28px rgba(184,71,36,0.38) !important;
}
.btn-arrow { transition: transform var(--kb-dur-fast) var(--kb-ease); }
.btn-primary:hover .btn-arrow { transform: translateX(3px); }
.btn-secondary {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 11px 26px; font-size: 14px;
  border-radius: var(--kb-radius-sm);
  border: 1px solid var(--kb-gold);
  color: var(--kb-gold-deep);
  background: rgba(212, 175, 106, 0.06);
  transition: all var(--kb-dur) var(--kb-ease);
}
.btn-secondary:hover {
  border-color: var(--kb-gold-bright);
  color: var(--kb-gold-deep);
  background: rgba(212, 175, 106, 0.15);
  transform: translateY(-2px);
  box-shadow: var(--kb-shadow-gold);
}

/* —— Stats —— */
.hero-stats {
  display: flex; align-items: center; justify-content: center; gap: 0;
  margin-top: 44px; padding: 22px 36px;
  background:
    linear-gradient(135deg, var(--kb-bg-elevated) 0%, rgba(212, 175, 106, 0.06) 100%);
  border: 1px solid rgba(184, 148, 90, 0.3);
  border-radius: var(--kb-radius-lg);
  width: fit-content; margin-left: auto; margin-right: auto;
  box-shadow:
    var(--kb-shadow-md),
    inset 0 1px 0 rgba(255, 250, 235, 0.5);
  position: relative;
}
/* Gold corner accents on stats */
.hero-stats::before,
.hero-stats::after {
  content: '';
  position: absolute;
  width: 16px; height: 16px;
  border: 1.5px solid var(--kb-gold);
  opacity: 0.6;
}
.hero-stats::before {
  top: -1px; left: -1px;
  border-right: none; border-bottom: none;
  border-radius: var(--kb-radius-lg) 0 0 0;
}
.hero-stats::after {
  bottom: -1px; right: -1px;
  border-left: none; border-top: none;
  border-radius: 0 0 var(--kb-radius-lg) 0;
}
.stat-item { display: flex; flex-direction: column; align-items: center; padding: 0 26px; }
.stat-val {
  font-size: 28px; font-weight: 700;
  font-family: var(--kb-font-serif);
  color: var(--kb-gold-deep);
  line-height: 1.2;
  text-shadow: 0 1px 2px rgba(184, 148, 90, 0.15);
}
.stat-lbl {
  font-size: 11px; color: var(--kb-fg-3);
  font-weight: 600; letter-spacing: 0.06em;
  text-transform: uppercase;
}
.stat-divider { width: 1px; height: 38px; background: linear-gradient(180deg, transparent, var(--kb-gold), transparent); opacity: 0.4; }

/* —— Feature Matrix —— */
.features { margin-bottom: 60px; }
.section-title {
  font-size: 26px; font-weight: 600;
  text-align: center; margin: 0 0 36px;
  color: var(--kb-fg); letter-spacing: -0.3px;
  font-family: var(--kb-font-serif);
  font-style: italic;
  position: relative;
  display: inline-block;
  left: 50%; transform: translateX(-50%);
}
.section-title::before,
.section-title::after {
  content: '✦';
  color: var(--kb-gold);
  font-size: 0.6em;
  font-style: normal;
  vertical-align: middle;
  margin: 0 14px;
  opacity: 0.7;
}
.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}
.feature-card {
  padding: 26px 24px;
  background:
    linear-gradient(135deg, var(--kb-bg-elevated) 0%, rgba(212, 175, 106, 0.04) 100%);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius-lg);
  transition: all var(--kb-dur) var(--kb-ease);
  animation: kb-fade-up 0.5s var(--kb-ease) both;
  animation-delay: calc(var(--idx) * 0.07s);
  position: relative;
  overflow: hidden;
}
/* Subtle gold top-edge on hover */
.feature-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--kb-gold-bright), transparent);
  opacity: 0;
  transition: opacity var(--kb-dur) var(--kb-ease);
}
.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--kb-shadow-lg);
  border-color: var(--kb-gold);
  background: var(--kb-bg-elevated);
}
.feature-card:hover::before { opacity: 1; }
.feature-icon {
  font-size: 30px; margin-bottom: 14px;
  display: inline-block;
  filter: drop-shadow(0 2px 4px rgba(184, 148, 90, 0.2));
}
.feature-card h3 {
  font-size: 16px; font-weight: 700; margin: 0 0 8px;
  font-family: var(--kb-font-serif);
  color: var(--kb-fg); letter-spacing: -0.2px;
}
.feature-card p {
  font-size: 13px; color: var(--kb-fg-3); line-height: 1.65; margin: 0;
}

/* —— Quick Links —— */
.quick-links {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}
.ql-card {
  display: flex; align-items: center; gap: 12px;
  padding: 16px 20px;
  background:
    linear-gradient(135deg, var(--kb-bg-elevated) 0%, rgba(212, 175, 106, 0.03) 100%);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius);
  cursor: pointer;
  transition: all var(--kb-dur) var(--kb-ease);
  animation: kb-fade-up 0.5s var(--kb-ease) both;
  position: relative;
  overflow: hidden;
}
.ql-card:nth-child(1) { animation-delay: 0.1s; }
.ql-card:nth-child(2) { animation-delay: 0.2s; }
.ql-card:nth-child(3) { animation-delay: 0.3s; }
.ql-card:nth-child(4) { animation-delay: 0.4s; }

.ql-card:hover {
  border-color: var(--kb-gold-bright);
  background:
    linear-gradient(135deg, var(--kb-gold-soft) 0%, rgba(212, 175, 106, 0.12) 100%);
  transform: translateY(-2px);
  box-shadow: var(--kb-shadow-md);
}
.ql-card :deep(.anticon):first-child {
  font-size: 20px; color: var(--kb-gold-deep); flex-shrink: 0;
  transition: color var(--kb-dur) var(--kb-ease);
}
.ql-card:hover :deep(.anticon):first-child { color: var(--kb-primary); }
.ql-card div { flex: 1; min-width: 0; }
.ql-card strong {
  display: block; font-size: 13.5px; font-weight: 600;
  font-family: var(--kb-font-serif);
  color: var(--kb-fg);
}
.ql-card span { font-size: 12px; color: var(--kb-fg-3); }
.ql-arrow { color: var(--kb-fg-mute); font-size: 12px; transition: transform var(--kb-dur-fast) var(--kb-ease), color var(--kb-dur-fast); }
.ql-card:hover .ql-arrow { transform: translateX(3px); color: var(--kb-gold-deep); }

@media (max-width: 640px) {
  .page-inner { padding: 40px 16px 60px; }
  .hero-stats { width: 100%; flex-direction: column; gap: 8px; }
  .stat-divider { display: none; }
  .feature-grid { grid-template-columns: 1fr; }
  .quick-links { grid-template-columns: 1fr; }
}
</style>

