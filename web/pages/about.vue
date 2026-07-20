<template>
  <div class="about-page">
    <!-- Animated background -->
    <div class="animated-bg">
      <div class="gradient-orb orb-1"></div>
      <div class="gradient-orb orb-2"></div>
      <div class="gradient-orb orb-3"></div>
      <div class="particles-container">
        <div v-for="n in 30" :key="n" class="particle" :style="getParticleStyle(n)"></div>
      </div>
    </div>

    <!-- Main content area -->
    <div class="content-wrapper">
      <!-- Hero Section -->
      <section class="hero-section">
        <div class="hero-content">
          <div class="badge-wrapper">
            <a-tag class="glow-badge" color="purple">
              <InfoCircleOutlined />
              {{ $t('about.badge') }}
            </a-tag>
          </div>
          
          <h1 class="hero-title">
            <span class="title-line">
              <span class="gradient-text">{{ $t('about.heroTitle') }}</span>
            </span>
            <span class="title-line">
              <span class="outline-text">{{ $t('about.heroSub') }}</span>
            </span>
          </h1>
          
          <p class="hero-subtitle">
            {{ $t('about.heroDesc') }}
          </p>

          <div class="cta-buttons">
            <a-button 
              type="primary" 
              size="large" 
              class="primary-btn glow-effect"
              @click="navigateToFileSystem"
            >
              <FolderOpenOutlined />
              {{ $t('about.tryNow') }}
              <RightOutlined class="btn-icon" />
            </a-button>
            <a-button 
              size="large" 
              class="secondary-btn"
              @click="scrollToFeatures"
            >
              <ReadOutlined />
              {{ $t('about.learnTech') }}
            </a-button>
          </div>
        </div>

        <!-- 3D architecture display -->
        <div class="hero-visual">
          <div class="architecture-rings">
            <div class="ring ring-1">
              <div class="ring-content">
                <DatabaseOutlined />
                <span>{{ $t('about.dataLayer') }}</span>
              </div>
            </div>
            <div class="ring ring-2">
              <div class="ring-content">
                <ApiOutlined />
                <span>{{ $t('about.serviceLayer') }}</span>
              </div>
            </div>
            <div class="ring ring-3">
              <div class="ring-content">
                <DesktopOutlined />
                <span>{{ $t('about.presentationLayer') }}</span>
              </div>
            </div>
            <div class="center-core">
              <ThunderboltOutlined />
            </div>
          </div>
        </div>
      </section>

      <!-- System introduction -->
      <section id="features" class="intro-section">
        <div class="section-header">
          <h2 class="section-title">
            <span class="gradient-text">{{ $t('about.systemIntro') }}</span>
          </h2>
          <p class="section-desc">{{ $t('about.systemIntroDesc') }}</p>
        </div>

        <div class="intro-grid">
          <div class="intro-card main-intro">
            <div class="intro-icon-wrapper">
              <BulbOutlined class="intro-icon" />
            </div>
            <h3>{{ $t('about.whatIsRag') }}</h3>
            <p>{{ $t('about.ragDesc') }}</p>
            <div class="intro-highlight">
              <CheckCircleOutlined />
              <span>{{ $t('about.ragHighlight') }}</span>
            </div>
          </div>

          <div class="intro-card">
            <div class="intro-icon-wrapper blue">
              <SafetyCertificateOutlined class="intro-icon" />
            </div>
            <h3>{{ $t('about.enterpriseSecurity') }}</h3>
            <p>{{ $t('about.enterpriseSecurityDesc') }}</p>
          </div>

          <div class="intro-card">
            <div class="intro-icon-wrapper green">
              <RocketOutlined class="intro-icon" />
            </div>
            <h3>{{ $t('about.highPerfSearch') }}</h3>
            <p>{{ $t('about.highPerfSearchDesc') }}</p>
          </div>

          <div class="intro-card">
            <div class="intro-icon-wrapper orange">
              <TeamOutlined class="intro-icon" />
            </div>
            <h3>{{ $t('about.teamCollab') }}</h3>
            <p>{{ $t('about.teamCollabDesc') }}</p>
          </div>
        </div>
      </section>

      <!-- Core features details -->
      <section class="features-detail-section">
        <div class="section-header">
          <h2 class="section-title">
            <span class="gradient-text">{{ $t('about.featuresDetail') }}</span>
          </h2>
          <p class="section-desc">{{ $t('about.featuresDetailDesc') }}</p>
        </div>

        <div class="feature-list">
          <div 
            v-for="(feature, index) in detailedFeatures" 
            :key="index"
            class="feature-detail-item"
            :class="{ 'reverse': index % 2 === 1 }"
          >
            <div class="feature-visual">
              <div class="feature-icon-bg" :class="feature.colorClass">
                <component :is="feature.icon" class="feature-large-icon" />
              </div>
            </div>
            <div class="feature-content">
              <div class="feature-number">0{{ index + 1 }}</div>
              <h3 class="feature-name">{{ feature.title }}</h3>
              <p class="feature-description">{{ feature.description }}</p>
              <ul class="feature-points">
                <li v-for="(point, pIndex) in feature.points" :key="pIndex">
                  <CheckOutlined />
                  {{ point }}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <!-- Tech stack display -->
      <section class="tech-section">
        <div class="section-header">
          <h2 class="section-title">
            <span class="gradient-text">{{ $t('about.heroSub') }}</span>
          </h2>
          <p class="section-desc">{{ $t('about.techStackDesc') }}</p>
        </div>

        <div class="tech-architecture">
          <div class="tech-layer">
            <div class="layer-header">
              <DesktopOutlined />
              <h4>{{ $t('about.frontendLayer') }}</h4>
            </div>
            <div class="tech-cards">
              <div class="tech-card">
                <div class="tech-logo vue">Vue</div>
                <span>Vue 3</span>
                <small>{{ $t('about.progressiveFramework') }}</small>
              </div>
              <div class="tech-card">
                <div class="tech-logo nuxt">Nuxt</div>
                <span>Nuxt 3</span>
                <small>{{ $t('about.fullStackFramework') }}</small>
              </div>
              <div class="tech-card">
                <div class="tech-logo antd">AntD</div>
                <span>Ant Design Vue</span>
                <small>{{ $t('about.uiComponentLib') }}</small>
              </div>
              <div class="tech-card">
                <div class="tech-logo ts">TS</div>
                <span>TypeScript</span>
                <small>{{ $t('about.typeSafety') }}</small>
              </div>
            </div>
          </div>

          <div class="layer-connector">
            <SwapOutlined class="connector-icon" />
          </div>

          <div class="tech-layer">
            <div class="layer-header">
              <ApiOutlined />
              <h4>{{ $t('about.backendLayer') }}</h4>
            </div>
            <div class="tech-cards">
              <div class="tech-card">
                <div class="tech-logo python">Py</div>
                <span>Python</span>
                <small>{{ $t('about.coreLanguage') }}</small>
              </div>
              <div class="tech-card">
                <div class="tech-logo fastapi">Fast</div>
                <span>FastAPI</span>
                <small>{{ $t('about.highPerfApi') }}</small>
              </div>
              <div class="tech-card">
                <div class="tech-logo nitro">Nitro</div>
                <span>Nitro</span>
                <small>{{ $t('about.nuxtEngine') }}</small>
              </div>
            </div>
          </div>

          <div class="layer-connector">
            <SwapOutlined class="connector-icon" />
          </div>

          <div class="tech-layer">
            <div class="layer-header">
              <DatabaseOutlined />
              <h4>{{ $t('about.dataAiLayer') }}</h4>
            </div>
            <div class="tech-cards">
              <div class="tech-card">
                <div class="tech-logo ai">AI</div>
                <span>LLM</span>
                <small>{{ $t('about.largeLanguageModel') }}</small>
              </div>
              <div class="tech-card">
                <div class="tech-logo vector">Vec</div>
                <span>{{ $t('about.vectorDb') }}</span>
                <small>{{ $t('about.semanticSearch') }}</small>
              </div>
              <div class="tech-card">
                <div class="tech-logo yaml">YAML</div>
                <span>{{ $t('about.yamlMeta') }}</span>
                <small>{{ $t('about.knowledgeDesc') }}</small>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Use cases -->
      <section class="use-cases-section">
        <div class="section-header">
          <h2 class="section-title">
            <span class="gradient-text">{{ $t('about.useCases') }}</span>
          </h2>
          <p class="section-desc">{{ $t('about.useCasesDesc') }}</p>
        </div>

        <div class="use-cases-grid">
          <div class="use-case-card">
            <div class="use-case-icon">
              <BankOutlined />
            </div>
            <h4>{{ $t('about.useCaseEnterpriseKb') }}</h4>
            <p>{{ $t('about.useCaseEnterpriseKbDesc') }}</p>
          </div>
          <div class="use-case-card">
            <div class="use-case-icon">
              <CustomerServiceOutlined />
            </div>
            <h4>{{ $t('about.useCaseSmartService') }}</h4>
            <p>{{ $t('about.useCaseSmartServiceDesc') }}</p>
          </div>
          <div class="use-case-card">
            <div class="use-case-icon">
              <BookOutlined />
            </div>
            <h4>{{ $t('about.useCaseDocMgmt') }}</h4>
            <p>{{ $t('about.useCaseDocMgmtDesc') }}</p>
          </div>
          <div class="use-case-card">
            <div class="use-case-icon">
              <ProjectOutlined />
            </div>
            <h4>{{ $t('about.useCaseProjectKb') }}</h4>
            <p>{{ $t('about.useCaseProjectKbDesc') }}</p>
          </div>
        </div>
      </section>

      <!-- Contact us -->
      <section class="contact-section">
        <div class="contact-content">
          <div class="contact-info">
            <h2 class="contact-title">
              <span class="gradient-text">{{ $t('about.contact') }}</span>
            </h2>
            <p class="contact-desc">{{ $t('about.contactDesc') }}</p>
            
            <div class="contact-methods">
              <div class="contact-item">
                <div class="contact-icon">
                  <MailOutlined />
                </div>
                <div class="contact-detail">
                  <span class="contact-label">{{ $t('about.email') }}</span>
                  <span class="contact-value">support@ragkb.com</span>
                </div>
              </div>
              <div class="contact-item">
                <div class="contact-icon">
                  <GithubOutlined />
                </div>
                <div class="contact-detail">
                  <span class="contact-label">{{ $t('about.github') }}</span>
                  <span class="contact-value">github.com/rag-knowledge</span>
                </div>
              </div>
              <div class="contact-item">
                <div class="contact-icon">
                  <GlobalOutlined />
                </div>
                <div class="contact-detail">
                  <span class="contact-label">{{ $t('about.website') }}</span>
                  <span class="contact-value">www.ragkb.com</span>
                </div>
              </div>
            </div>
          </div>

          <div class="contact-form-wrapper">
            <a-card class="contact-form-card" :bordered="false">
              <a-form layout="vertical" :model="formState">
                <a-form-item :label="$t('about.formName')" name="name">
                  <a-input
                    v-model:value="formState.name"
                    :placeholder="$t('about.formNamePlaceholder')"
                    size="large"
                  />
                </a-form-item>
                <a-form-item :label="$t('about.formEmail')" name="email">
                  <a-input
                    v-model:value="formState.email"
                    :placeholder="$t('about.formEmailPlaceholder')"
                    size="large"
                  />
                </a-form-item>
                <a-form-item :label="$t('about.formMessage')" name="message">
                  <a-textarea
                    v-model:value="formState.message"
                    :placeholder="$t('about.formMessagePlaceholder')"
                    :rows="4"
                  />
                </a-form-item>
                <a-form-item>
                  <a-button 
                    type="primary" 
                    size="large"
                    block
                    class="submit-btn glow-effect"
                    @click="handleSubmit"
                  >
                    <SendOutlined />
                    {{ $t('about.formSubmit') }}
                  </a-button>
                </a-form-item>
              </a-form>
            </a-card>
          </div>
        </div>
      </section>

      <!-- Footer -->
      <footer class="about-footer">
        <div class="footer-content">
          <div class="footer-brand">
            <DatabaseOutlined class="brand-icon" />
            <span class="brand-text">RAG Knowledge Base</span>
          </div>
          <p class="footer-copyright">© 2026 RAG Knowledge Management System. All rights reserved.</p>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { message } from 'ant-design-vue'
import {
  InfoCircleOutlined,
  FolderOpenOutlined,
  RightOutlined,
  ReadOutlined,
  DatabaseOutlined,
  ApiOutlined,
  DesktopOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  SafetyCertificateOutlined,
  RocketOutlined,
  TeamOutlined,
  CheckCircleOutlined,
  CheckOutlined,
  SwapOutlined,
  BankOutlined,
  CustomerServiceOutlined,
  BookOutlined,
  ProjectOutlined,
  MailOutlined,
  GithubOutlined,
  GlobalOutlined,
  SendOutlined,
  FileTextOutlined,
  SearchOutlined,
  RobotOutlined,
  CloudUploadOutlined,
  BranchesOutlined,
  SafetyOutlined
} from '@ant-design/icons-vue'

const { t } = useI18n()

// Detailed features list
const detailedFeatures = [
  {
    icon: FileTextOutlined,
    title: t('about.featureDocMgmt'),
    description: t('about.featureDocMgmtDesc'),
    colorClass: 'blue',
    points: [
      t('about.featureDocMgmtPt1'),
      t('about.featureDocMgmtPt2'),
      t('about.featureDocMgmtPt3'),
      t('about.featureDocMgmtPt4')
    ]
  },
  {
    icon: SearchOutlined,
    title: t('about.featureSearch'),
    description: t('about.featureSearchDesc'),
    colorClass: 'purple',
    points: [
      t('about.featureSearchPt1'),
      t('about.featureSearchPt2'),
      t('about.featureSearchPt3'),
      t('about.featureSearchPt4')
    ]
  },
  {
    icon: RobotOutlined,
    title: t('about.featureAiParse'),
    description: t('about.featureAiParseDesc'),
    colorClass: 'green',
    points: [
      t('about.featureAiParsePt1'),
      t('about.featureAiParsePt2'),
      t('about.featureAiParsePt3'),
      t('about.featureAiParsePt4')
    ]
  },
  {
    icon: CloudUploadOutlined,
    title: t('about.featureYamlMeta'),
    description: t('about.featureYamlMetaDesc'),
    colorClass: 'orange',
    points: [
      t('about.featureYamlMetaPt1'),
      t('about.featureYamlMetaPt2'),
      t('about.featureYamlMetaPt3'),
      t('about.featureYamlMetaPt4')
    ]
  },
  {
    icon: BranchesOutlined,
    title: t('about.featureRestApi'),
    description: t('about.featureRestApiDesc'),
    colorClass: 'cyan',
    points: [
      t('about.featureRestApiPt1'),
      t('about.featureRestApiPt2'),
      t('about.featureRestApiPt3'),
      t('about.featureRestApiPt4')
    ]
  },
  {
    icon: SafetyOutlined,
    title: t('about.featureEntSecurity'),
    description: t('about.featureEntSecurityDesc'),
    colorClass: 'red',
    points: [
      t('about.featureEntSecurityPt1'),
      t('about.featureEntSecurityPt2'),
      t('about.featureEntSecurityPt3'),
      t('about.featureEntSecurityPt4')
    ]
  }
]

const formState = reactive({
  name: '',
  email: '',
  message: '',
})

// Particle animation styles
const getParticleStyle = (n: number) => {
  const size = Math.random() * 3 + 1
  const left = Math.random() * 100
  const delay = Math.random() * 15
  const duration = Math.random() * 15 + 10
  
  return {
    width: `${size}px`,
    height: `${size}px`,
    left: `${left}%`,
    animationDelay: `${delay}s`,
    animationDuration: `${duration}s`
  }
}

// Navigate to file system
const navigateToFileSystem = () => {
  navigateTo('/file-system')
}

// Scroll to features section
const scrollToFeatures = () => {
  const element = document.getElementById('features')
  if (element) {
    element.scrollIntoView({ behavior: 'smooth' })
  }
}

const handleSubmit = () => {
  if (!formState.name || !formState.email || !formState.message) {
    message.warning(t('about.formValidationWarning'))
    return
  }
  message.success(t('about.formSubmitSuccess'))
  formState.name = ''
  formState.email = ''
  formState.message = ''
}
</script>

<style scoped>
/* About page — light industrial theme */
.about-page { min-height: calc(100vh - 62px); color: var(--kb-fg); background: var(--kb-bg); position: relative; overflow-x: hidden; margin: -26px; }

/* Animated Background: keep warm orbs but tuned lighter */
.animated-bg { position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }
.gradient-orb { position: absolute; border-radius: 50%; filter: blur(90px); opacity: 0.5; animation: kb-float 18s ease-in-out infinite; }
.orb-1 { width: 480px; height: 480px; background: radial-gradient(circle, rgba(37,99,235,0.16), transparent 70%); top: -160px; right: -100px; }
.orb-2 { width: 420px; height: 420px; background: radial-gradient(circle, rgba(6,182,212,0.14), transparent 70%); bottom: -140px; left: -80px; animation-delay: -6s; }
.orb-3 { display: none; }
.particles-container { display: none; }

.content-wrapper { position: relative; z-index: 1; }

/* —— Hero —— */
.hero-section { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 40px; min-height: 86vh; padding: 80px 6vw; background: radial-gradient(1000px 560px at 80% 12%, rgba(6,182,212,0.22), transparent 60%), radial-gradient(900px 540px at 10% 85%, rgba(37,99,235,0.28), transparent 62%), linear-gradient(160deg, #0b1226, #0d1424 55%, #0a1a33); overflow: hidden; }
.hero-section::before { content: ''; position: absolute; inset: 0; background-image: linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px); background-size: 56px 56px; mask-image: radial-gradient(circle at 50% 40%, #000, transparent 78%); pointer-events: none; }
.hero-content { position: relative; z-index: 2; max-width: 620px; animation: kb-fade-up 0.7s var(--kb-ease-out) both; }

.glow-badge { display: inline-flex; align-items: center; gap: 7px; padding: 7px 14px; border-radius: 999px; font-size: 13px; font-weight: 600; background: rgba(124,92,255,0.16); border: 1px solid rgba(167,139,250,0.35); color: #d8ccff !important; backdrop-filter: blur(6px); }
.glow-badge :deep(.anticon) { color: var(--kb-violet); }

.hero-title { margin: 22px 0 18px; font-size: clamp(40px, 5.4vw, 66px); font-weight: 800; line-height: 1.06; letter-spacing: -1.2px; }
.title-line { display: block; }
.gradient-text { background: linear-gradient(100deg, #fff 0%, #bcd4ff 40%, var(--kb-cyan) 100%); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.outline-text { color: transparent; -webkit-text-stroke: 1.4px rgba(180,205,255,0.5); }
.hero-subtitle { font-size: clamp(16px, 1.4vw, 19px); line-height: 1.7; color: #aab6d4; max-width: 520px; margin-bottom: 32px; }
.cta-buttons { display: flex; gap: 14px; flex-wrap: wrap; }
.primary-btn { height: 50px; padding: 0 26px; border-radius: 13px; font-size: 15.5px; font-weight: 600; background: linear-gradient(135deg, var(--kb-primary), #4f7cff) !important; border: none !important; box-shadow: var(--kb-shadow-primary) !important; display: inline-flex; align-items: center; gap: 9px; transition: transform var(--kb-dur) var(--kb-ease), box-shadow var(--kb-dur) var(--kb-ease) !important; }
.primary-btn:hover { transform: translateY(-2px); box-shadow: var(--kb-shadow-primary-lg) !important; }
.btn-icon { transition: transform var(--kb-dur) var(--kb-ease); }
.primary-btn:hover .btn-icon { transform: translateX(3px); }
.secondary-btn { height: 50px; padding: 0 24px; border-radius: 13px; font-size: 15.5px; font-weight: 600; background: rgba(255,255,255,0.06) !important; border: 1px solid rgba(255,255,255,0.16) !important; color: #d6e0f5 !important; display: inline-flex; align-items: center; gap: 9px; transition: all var(--kb-dur) var(--kb-ease) !important; backdrop-filter: blur(6px); }
.secondary-btn:hover { background: rgba(255,255,255,0.12) !important; border-color: rgba(255,255,255,0.3) !important; transform: translateY(-2px); }

/* Architecture ring visual */
.hero-visual { position: relative; flex: 1; min-width: 320px; height: 440px; animation: kb-fade-in 1s 0.2s both; }
.architecture-rings { position: absolute; inset: 0; display: grid; place-items: center; }
.ring { position: absolute; border-radius: 50%; display: grid; place-items: start center; border: 1px solid rgba(120,160,240,0.22); }
.ring-1 { width: 360px; height: 360px; animation: kb-spin-slow 50s linear infinite; }
.ring-2 { width: 260px; height: 260px; animation: kb-spin-slow 36s linear infinite reverse; border-style: dashed; }
.ring-3 { width: 160px; height: 160px; animation: kb-spin-slow 24s linear infinite; }
.ring-content { display: flex; flex-direction: column; align-items: center; gap: 6px; margin-top: -22px; color: #cfe0ff; font-size: 12.5px; font-weight: 600; }
.ring-content :deep(.anticon) { font-size: 20px; color: var(--kb-cyan); }
.center-core { position: absolute; width: 70px; height: 70px; border-radius: 50%; display: grid; place-items: center; font-size: 30px; color: #fff; background: linear-gradient(135deg, var(--kb-primary), var(--kb-cyan)); box-shadow: 0 0 40px rgba(37,99,235,0.6); }

/* -- Section common -- */
.section-header { text-align: center; max-width: 640px; margin: 0 auto 52px; }
.section-title { font-size: clamp(28px, 3.4vw, 40px); font-weight: 800; letter-spacing: -0.8px; margin-bottom: 12px; color: var(--kb-fg); }
.section-title .gradient-text { background: linear-gradient(100deg, var(--kb-primary), var(--kb-cyan)); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.section-desc { font-size: 16px; color: var(--kb-fg-3); line-height: 1.6; }

/* —— System introduction —— */
.intro-section { padding: 88px 6vw; }
.intro-grid { display: grid; grid-template-columns: 1.4fr 1fr 1fr 1fr; gap: 22px; max-width: 1240px; margin: 0 auto; }
.intro-card { padding: 30px 26px; border-radius: var(--kb-radius-lg); background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); box-shadow: var(--kb-shadow-sm); transition: all var(--kb-dur) var(--kb-ease); animation: kb-fade-up 0.5s var(--kb-ease-out) both; }
.intro-card:hover { transform: translateY(-5px); box-shadow: var(--kb-shadow-lg); }
.main-intro { grid-row: span 2; background: linear-gradient(160deg, var(--kb-bg-elevated), var(--kb-primary-tint)); border-color: rgba(37,99,235,0.18); }
.main-intro .intro-icon { font-size: 30px; color: var(--kb-primary); margin-bottom: 16px; }
.main-intro h3 { font-size: 22px; font-weight: 800; color: var(--kb-fg); margin-bottom: 12px; }
.intro-highlight { padding: 16px 18px; border-radius: var(--kb-radius); background: var(--kb-primary-soft); border-inline-start: 3px solid var(--kb-primary); margin-top: 16px; font-size: 14px; line-height: 1.65; color: var(--kb-fg-2); }
.intro-icon-wrapper { width: 46px; height: 46px; border-radius: 13px; display: grid; place-items: center; font-size: 21px; margin-bottom: 14px; color: #fff; }
.intro-icon-wrapper.blue { background: linear-gradient(135deg, var(--kb-primary), #4f7cff); }
.intro-icon-wrapper.green { background: linear-gradient(135deg, var(--kb-emerald), #34d399); }
.intro-icon-wrapper.orange { background: linear-gradient(135deg, var(--kb-amber), #fbbf24); }
.intro-card h3 { font-size: 17px; font-weight: 700; color: var(--kb-fg); margin-bottom: 8px; }
.intro-card p { font-size: 13.5px; line-height: 1.6; color: var(--kb-fg-3); }

/* —— Core features details —— */
.features-detail-section { padding: 56px 6vw 88px; background: var(--kb-bg-elevated); border-block: 1px solid var(--kb-border); }
.feature-list { max-width: 1100px; margin: 0 auto; display: flex; flex-direction: column; gap: 32px; }
.feature-detail-item { display: flex; align-items: center; gap: 44px; animation: kb-fade-up 0.6s var(--kb-ease-out) both; }
.feature-detail-item.reverse { flex-direction: row-reverse; }
.feature-visual { flex-shrink: 0; }
.feature-icon-bg { width: 120px; height: 120px; border-radius: 28px; display: grid; place-items: center; color: #fff; box-shadow: var(--kb-shadow-lg); }
.feature-icon-bg.blue { background: linear-gradient(135deg, var(--kb-primary), var(--kb-cyan)); }
.feature-icon-bg.violet { background: linear-gradient(135deg, var(--kb-violet), #a78bfa); }
.feature-icon-bg.emerald { background: linear-gradient(135deg, var(--kb-emerald), #34d399); }
.feature-icon-bg.amber { background: linear-gradient(135deg, var(--kb-amber), #fbbf24); }
.feature-large-icon { font-size: 52px; }
.feature-content { flex: 1; }
.feature-number { font-size: 13px; font-weight: 700; color: var(--kb-primary); font-family: var(--kb-font-mono); letter-spacing: 1px; margin-bottom: 8px; }
.feature-name { font-size: 24px; font-weight: 800; color: var(--kb-fg); margin-bottom: 12px; letter-spacing: -0.4px; }
.feature-description { font-size: 15px; line-height: 1.75; color: var(--kb-fg-3); margin-bottom: 18px; }
.feature-points { list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.feature-points li { display: flex; align-items: center; gap: 9px; font-size: 13.5px; color: var(--kb-fg-2); }
.feature-points li::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: var(--kb-cyan); flex-shrink: 0; }

/* —— Technology architecture —— */
.tech-section { padding: 88px 6vw; }
.tech-architecture { max-width: 1000px; margin: 0 auto; display: flex; flex-direction: column; gap: 0; }
.tech-layer { padding: 26px; border-radius: var(--kb-radius-lg); background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); box-shadow: var(--kb-shadow-sm); animation: kb-fade-up 0.5s var(--kb-ease-out) both; }
.layer-header { display: flex; align-items: center; gap: 14px; margin-bottom: 20px; }
.layer-header h3 { font-size: 19px; font-weight: 700; color: var(--kb-fg); margin: 0; }
.layer-header :deep(.anticon) { font-size: 22px; color: var(--kb-primary); }
.tech-cards { display: flex; gap: 16px; flex-wrap: wrap; }
.tech-card { display: flex; align-items: center; gap: 12px; padding: 12px 18px; border-radius: var(--kb-radius); background: var(--kb-bg); border: 1px solid var(--kb-border); transition: all var(--kb-dur-fast) var(--kb-ease); }
.tech-card:hover { transform: translateY(-3px); box-shadow: var(--kb-shadow-sm); }
.tech-logo { width: 42px; height: 42px; border-radius: 11px; display: grid; place-items: center; font-size: 14px; font-weight: 800; color: #fff; }
.tech-logo.vue { background: #42b883; }
.tech-logo.nuxt { background: #00dc82; }
.tech-logo.antd { background: var(--kb-primary); }
.tech-logo.ts { background: #3178c6; }
.tech-logo.python { background: #3776ab; }
.tech-logo.fastapi { background: #009688; }
.tech-card h4 { font-size: 15px; font-weight: 700; color: var(--kb-fg); margin: 0 0 2px; }
.tech-card p { font-size: 12.5px; color: var(--kb-fg-3); margin: 0; }
.layer-connector { display: flex; justify-content: center; padding: 14px 0; color: var(--kb-fg-mute); }
.connector-icon { font-size: 22px; transform: rotate(90deg); }

/* -- Use cases -- */
.use-cases-section { padding: 0 6vw 88px; }
.use-cases-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 22px; max-width: 1240px; margin: 0 auto; }
.use-case-card { padding: 28px 24px; border-radius: var(--kb-radius-lg); background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); box-shadow: var(--kb-shadow-sm); transition: all var(--kb-dur) var(--kb-ease); animation: kb-fade-up 0.5s var(--kb-ease-out) both; }
.use-case-card:hover { transform: translateY(-5px); box-shadow: var(--kb-shadow-lg); }
.use-case-icon { width: 48px; height: 48px; border-radius: 13px; display: grid; place-items: center; font-size: 22px; color: #fff; background: linear-gradient(135deg, var(--kb-primary), var(--kb-cyan)); margin-bottom: 16px; }

/* -- Contact -- */
.contact-section { padding: 0 6vw 88px; }
.contact-form-card { max-width: 1000px; margin: 0 auto; padding: 48px; border-radius: var(--kb-radius-xl); background: radial-gradient(700px 340px at 80% 0%, rgba(6,182,212,0.16), transparent 60%), linear-gradient(135deg, #0d1424, #13234a); overflow: hidden; }
.contact-content { display: flex; gap: 48px; align-items: center; }
.contact-info { flex: 1; }
.contact-title { font-size: 30px; font-weight: 800; color: #fff; margin-bottom: 12px; letter-spacing: -0.6px; }
.contact-desc { font-size: 15.5px; line-height: 1.7; color: #aab6d4; margin-bottom: 26px; }
.contact-methods { display: flex; flex-direction: column; gap: 16px; }
.contact-item { display: flex; align-items: center; gap: 14px; }
.contact-icon { width: 44px; height: 44px; border-radius: 12px; display: grid; place-items: center; font-size: 19px; color: var(--kb-cyan); background: rgba(6,182,212,0.14); border: 1px solid rgba(6,182,212,0.25); }
.contact-label { font-size: 12px; color: #8b97b3; }
.contact-value { font-size: 15px; font-weight: 600; color: #e6ecfa; }
.submit-btn { height: 50px; border-radius: 13px; font-weight: 600; background: linear-gradient(135deg, var(--kb-primary), #4f7cff) !important; border: none !important; box-shadow: var(--kb-shadow-primary) !important; }

/* -- Footer -- */
.about-footer { padding: 40px 6vw; text-align: center; background: var(--kb-bg-dark); color: #6b7794; }
.brand-icon { width: 38px; height: 38px; border-radius: 11px; display: inline-grid; place-items: center; font-size: 19px; color: #fff; background: linear-gradient(135deg, var(--kb-primary), var(--kb-cyan)); vertical-align: middle; margin-right: 10px; }
.brand-text { font-size: 17px; font-weight: 800; color: #fff; vertical-align: middle; }
.footer-copyright { margin-top: 14px; font-size: 13px; }

/* -- Responsive -- */
@media (max-width: 980px) {
  .intro-grid { grid-template-columns: 1fr 1fr; }
  .main-intro { grid-row: span 1; grid-column: span 2; }
  .use-cases-grid { grid-template-columns: 1fr; }
  .feature-detail-item, .feature-detail-item.reverse { flex-direction: column; text-align: center; gap: 24px; }
  .feature-points { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .hero-section { flex-direction: column; text-align: center; }
  .hero-visual { display: none; }
  .cta-buttons { justify-content: center; }
  .intro-grid { grid-template-columns: 1fr; }
  .main-intro { grid-column: span 1; }
  .contact-content { flex-direction: column; }
  .contact-form-card { padding: 30px; }
}
</style>

