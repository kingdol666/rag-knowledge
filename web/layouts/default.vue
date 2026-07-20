<template>
  <div class="library-shell">
    <!-- Cinematic video background (fills the space around the book) -->
    <video
      class="library-bg-video"
      :class="{ 'is-ready': videoReady }"
      autoplay
      muted
      loop
      playsinline
      preload="auto"
      aria-hidden="true"
      @canplay="videoReady = true"
    >
      <source src="/videos/bg.mp4" type="video/mp4" />
    </video>
    <!-- Dimming + vignette overlay so the paper book reads clearly -->
    <div class="library-bg-overlay"></div>

    <!-- Ambient library atmosphere -->
    <div class="library-atmosphere">
      <div class="shelf-shadow shelf-top"></div>
      <div class="shelf-shadow shelf-left"></div>
      <div class="shelf-shadow shelf-right"></div>
      <div class="dust-mote" v-for="i in 12" :key="i" :style="dustStyle(i)"></div>
    </div>

    <!-- The Open Book -->
    <div class="book-stage" ref="bookStage">
      <div class="book-container" :class="{ 'is-turning': isTurning, 'is-mobile': isMobile }">
        <!-- Book cover background shadow -->
        <div class="book-cover-shadow"></div>

        <!-- LEFT PAGE — Navigation / Table of Contents (becomes a drawer on mobile) -->
        <div class="book-page page-left" :class="{ 'drawer-open': mobileMenuOpen }" ref="leftPage">
          <!-- Page texture -->
          <div class="page-texture"></div>

          <!-- Bookmark ribbon -->
          <div class="bookmark-ribbon" :style="{ top: bookmarkTop + 'px' }">
            <div class="ribbon-fold"></div>
          </div>

          <!-- Left page header -->
          <div class="page-left-header">
            <div class="book-plate">
              <div class="plate-ornament top-ornament">❦</div>
              <img src="/images/logo.svg" alt="RAG Knowledge Platform" class="plate-logo" />
              <span class="plate-text">RAG Knowledge</span>
              <div class="plate-ornament bottom-ornament">❦</div>
            </div>
          </div>

          <!-- Table of Contents -->
          <nav class="book-toc">
            <div class="toc-heading">
              <span class="toc-label">Contents</span>
              <span class="toc-divider"></span>
            </div>

            <div
              v-for="(item, idx) in navItems"
              :key="item.path"
              :class="['toc-item', { active: isActive(item.path) }]"
              :style="{ '--item-delay': idx * 0.04 + 's' }"
              @click="navigateToPage(item)"
            >
              <span class="toc-number">{{ String(idx + 1).padStart(2, '0') }}</span>
              <component :is="item.icon" class="toc-icon" />
              <span class="toc-title">{{ item.label }}</span>
              <span class="toc-dots"></span>
              <span class="toc-page-num">{{ item.pageNum || String(idx + 1).padStart(2, '0') }}</span>
            </div>
          </nav>

          <!-- Left page footer -->
          <div class="page-left-footer">
            <div class="footer-ornament">⚘</div>
            <span class="footer-text">RAG Knowledge Platform v2.0</span>
          </div>

          <!-- Page curl shadow (right edge of left page) -->
          <div class="page-curl page-curl-left"></div>
        </div>

        <!-- SPINE -->
        <div class="book-spine">
          <div class="spine-groove" v-for="i in 5" :key="i"></div>
          <div class="spine-label">RAG·KB</div>
        </div>

        <!-- RIGHT PAGE — Content Area -->
        <div class="book-page page-right" ref="rightPage">
          <!-- Page texture -->
          <div class="page-texture"></div>

          <!-- Right page header bar -->
          <div class="page-right-header">
            <div class="page-running-head">
              <span class="running-title">{{ currentPageTitle }}</span>
              <span class="running-dot">·</span>
              <span class="running-chapter">{{ currentChapter }}</span>
            </div>
            <div class="header-actions-mini">
              <button class="mini-btn mobile-menu-btn" @click="toggleMobileMenu" title="目录 / Contents">
                <MenuOutlined />
              </button>
              <button class="mini-btn" @click="toggleFullscreen" :title="isFullscreen ? 'Exit fullscreen' : 'Fullscreen'">
                <ExpandOutlined v-if="!isFullscreen" />
                <CompressOutlined v-else />
              </button>
              <LangSwitcher />
            </div>
          </div>

          <!-- Page turn animation wrapper -->
          <div class="page-turn-stage" ref="turnStage">
            <Transition :name="turnDirection" @before-enter="onTurnStart" @after-enter="onTurnEnd">
              <div class="page-content" :key="route.fullPath">
                <slot />
              </div>
            </Transition>
          </div>

          <!-- Right page footer — page number -->
          <div class="page-right-footer">
            <span class="page-number">{{ currentPageNum }}</span>
            <span class="page-decor">— ✦ —</span>
          </div>

          <!-- Page curl shadow (left edge of right page) -->
          <div class="page-curl page-curl-right"></div>
        </div>

        <!-- Stacked page edges (visual depth) -->
        <div class="page-stack page-stack-bottom"></div>
        <div class="page-stack page-stack-bottom2"></div>
      </div>
    </div>

    <!-- Page turn navigation arrows (desktop) -->
    <Transition name="nav-arrow-fade">
      <button v-if="prevPage" class="nav-arrow nav-prev" @click="goToPrev" :title="prevPage.label">
        <LeftOutlined />
      </button>
    </Transition>
    <Transition name="nav-arrow-fade">
      <button v-if="nextPage" class="nav-arrow nav-next" @click="goToNext" :title="nextPage.label">
        <RightOutlined />
      </button>
    </Transition>

    <!-- Mobile drawer backdrop -->
    <Transition name="backdrop-fade">
      <div v-if="mobileMenuOpen" class="mobile-drawer-backdrop" @click="closeMobileMenu"></div>
    </Transition>

    <!-- Mobile bottom navigation (single-page prev/next) -->
    <div class="mobile-bottom-nav">
      <button class="mob-nav-btn" @click="goToPrev" :disabled="!prevPage" :title="prevPage ? prevPage.label : ''">
        <LeftOutlined />
      </button>
      <span class="mob-page-indicator">
        <span class="mob-page-num">{{ currentPageNum }}</span>
        <span class="mob-page-sep">/</span>
        <span class="mob-page-total">{{ String(navItems.length).padStart(2, '0') }}</span>
      </span>
      <button class="mob-nav-btn" @click="goToNext" :disabled="!nextPage" :title="nextPage ? nextPage.label : ''">
        <RightOutlined />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  HomeOutlined, FolderOpenOutlined, DatabaseOutlined,
  SearchOutlined, ShareAltOutlined, RobotOutlined,
  SettingOutlined, QuestionCircleOutlined,
  ExpandOutlined, CompressOutlined, LeftOutlined, RightOutlined,
  MenuOutlined,
} from '@ant-design/icons-vue'

const route = useRoute()
const router = useRouter()

// ── Navigation items ───────────────────────────────────────
const navItems = computed(() => [
  { path: '/',              label: 'Home',             icon: HomeOutlined,         pageNum: '01', chapter: 'Front Matter' },
  { path: '/file-system',   label: 'File System',      icon: FolderOpenOutlined,   pageNum: '02', chapter: 'Repository' },
  { path: '/knowledge-base',label: 'Knowledge Base',   icon: DatabaseOutlined,     pageNum: '03', chapter: 'Collections' },
  { path: '/knowledge-search', label: 'KB Search',     icon: SearchOutlined,       pageNum: '04', chapter: 'Retrieval' },
  { path: '/knowledge-graph',  label: 'Graph Explorer',icon: ShareAltOutlined,     pageNum: '05', chapter: 'Relations' },
  { path: '/claude-chat',   label: 'Claude Chat',      icon: RobotOutlined,        pageNum: '06', chapter: 'Assistant' },
  { path: '/settings',      label: 'Settings',         icon: SettingOutlined,      pageNum: '07', chapter: 'Configuration' },
  { path: '/about',         label: 'About',            icon: QuestionCircleOutlined, pageNum: '08', chapter: 'Appendix' },
])

// ── State ───────────────────────────────────────────────────
const isTurning = ref(false)
const turnDirection = ref('turn-forward')
const lastRouteIdx = ref(0)
const isFullscreen = ref(false)
const isMobile = ref(false)
const mobileMenuOpen = ref(false)
const videoReady = ref(false)
const bookStage = ref<HTMLElement | null>(null)
const leftPage = ref<HTMLElement | null>(null)
const rightPage = ref<HTMLElement | null>(null)
const turnStage = ref<HTMLElement | null>(null)

// ── Computed ────────────────────────────────────────────────
const currentIdx = computed(() => {
  const idx = navItems.value.findIndex(item => isActive(item.path))
  return idx >= 0 ? idx : 0
})

const currentPageTitle = computed(() => {
  const item = navItems.value[currentIdx.value]
  return item?.label || 'Home'
})

const currentChapter = computed(() => {
  const item = navItems.value[currentIdx.value]
  return item?.chapter || 'Front Matter'
})

const currentPageNum = computed(() => {
  return String(currentIdx.value + 1).padStart(2, '0')
})

const prevPage = computed(() => {
  if (currentIdx.value <= 0) return null
  return navItems.value[currentIdx.value - 1]
})

const nextPage = computed(() => {
  if (currentIdx.value >= navItems.value.length - 1) return null
  return navItems.value[currentIdx.value + 1]
})

const bookmarkTop = computed(() => {
  // Position bookmark at the active TOC item (tuned for the enlarged left page)
  return 168 + currentIdx.value * 55
})

// ── Methods ─────────────────────────────────────────────────
function isActive(path: string): boolean {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

async function navigateToPage(item: { path: string; disabled?: boolean }) {
  if (item.disabled || isTurning.value) return
  if (isActive(item.path)) {
    closeMobileMenu()
    return
  }

  const newIdx = navItems.value.findIndex(n => n.path === item.path)
  turnDirection.value = newIdx > lastRouteIdx.value ? 'turn-forward' : 'turn-backward'
  lastRouteIdx.value = newIdx
  isTurning.value = true
  closeMobileMenu()

  await router.push(item.path)
}

function toggleMobileMenu() {
  mobileMenuOpen.value = !mobileMenuOpen.value
}

function closeMobileMenu() {
  mobileMenuOpen.value = false
}

function goToPrev() {
  if (prevPage.value) navigateToPage(prevPage.value)
}

function goToNext() {
  if (nextPage.value) navigateToPage(nextPage.value)
}

function onTurnStart() {
  isTurning.value = true
}

function onTurnEnd() {
  isTurning.value = false
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {})
    isFullscreen.value = true
  } else {
    document.exitFullscreen().catch(() => {})
    isFullscreen.value = false
  }
}

function dustStyle(i: number) {
  const left = 5 + Math.random() * 90
  const delay = Math.random() * 8
  const duration = 6 + Math.random() * 8
  const size = 1 + Math.random() * 2
  return {
    left: `${left}%`,
    animationDelay: `${delay}s`,
    animationDuration: `${duration}s`,
    width: `${size}px`,
    height: `${size}px`,
  }
}

// ── Keyboard navigation ────────────────────────────────────
function handleKeyboard(e: KeyboardEvent) {
  if (e.key === 'ArrowLeft' && prevPage.value) {
    e.preventDefault()
    goToPrev()
  } else if (e.key === 'ArrowRight' && nextPage.value) {
    e.preventDefault()
    goToNext()
  }
}

// ── Mobile detection ───────────────────────────────────────
function checkMobile() {
  isMobile.value = window.innerWidth < 840
  if (!isMobile.value) closeMobileMenu()
}

// ── Lifecycle ───────────────────────────────────────────────
onMounted(() => {
  lastRouteIdx.value = currentIdx.value
  window.addEventListener('keydown', handleKeyboard)
  window.addEventListener('resize', checkMobile)
  document.addEventListener('fullscreenchange', () => {
    isFullscreen.value = !!document.fullscreenElement
  })
  checkMobile()
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyboard)
  window.removeEventListener('resize', checkMobile)
})

// Keep lastRouteIdx in sync on direct URL changes
watch(() => route.fullPath, () => {
  lastRouteIdx.value = currentIdx.value
})
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   LIBRARY SHELL — Full-viewport atmospheric container
   ═══════════════════════════════════════════════════════════ */
.library-shell {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  /* Sizing tokens shared across the layout */
  --book-max-width: 1880px;
  --book-max-height: 1120px;
  /* Nocturne Atelier — deep walnut study with candlelit pooling */
  background:
    radial-gradient(ellipse 60% 50% at 50% 35%, rgba(212, 175, 106, 0.10) 0%, transparent 60%),
    radial-gradient(ellipse 80% 70% at 50% 50%, var(--kb-shell-2) 0%, var(--kb-shell) 70%);
  overflow: hidden;
  font-family: var(--kb-font);
}

/* ── Cinematic video background (original color tones) ───────────────────────── */
.library-bg-video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  z-index: 0;
  pointer-events: none;
  opacity: 0;
  transition: opacity 1.4s var(--kb-ease-out);
  /* No color filters — show the video's natural palette */
  filter: none;
}
.library-bg-video.is-ready {
  opacity: 0.96;
}

/* Soft vignette only — keeps edge UI legible without muting the video's colors */
.library-bg-overlay {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background:
    radial-gradient(ellipse 75% 75% at 50% 50%,
      transparent 0%,
      transparent 45%,
      rgba(15, 12, 9, 0.25) 80%,
      rgba(10, 8, 6, 0.55) 100%);
}

/* ── Library atmosphere ─────────────────────────────────── */
.library-atmosphere {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 1;
}
.shelf-shadow {
  position: absolute;
  background: rgba(0, 0, 0, 0.4);
}
.shelf-shadow.shelf-top {
  top: 0; left: 0; right: 0; height: 8px;
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.55), transparent);
}
.shelf-shadow.shelf-left {
  left: 0; top: 0; bottom: 0; width: 6px;
  background: linear-gradient(90deg, rgba(0, 0, 0, 0.45), transparent);
}
.shelf-shadow.shelf-right {
  right: 0; top: 0; bottom: 0; width: 6px;
  background: linear-gradient(270deg, rgba(0, 0, 0, 0.45), transparent);
}

/* Dust motes — gold motes drifting in candlelight */
.dust-mote {
  position: absolute;
  top: -10px;
  background: radial-gradient(circle, rgba(212, 175, 106, 0.55) 0%, rgba(212, 175, 106, 0.12) 70%, transparent 100%);
  border-radius: 50%;
  animation: dust-float linear infinite;
  filter: blur(0.3px);
  box-shadow: 0 0 4px rgba(212, 175, 106, 0.3);
}
@keyframes dust-float {
  0%   { transform: translateY(0) translateX(0); opacity: 0; }
  10%  { opacity: 0.9; }
  90%  { opacity: 0.5; }
  100% { transform: translateY(105vh) translateX(30px); opacity: 0; }
}

/* ═══════════════════════════════════════════════════════════
   BOOK STAGE — Centered open book with perspective
   ═══════════════════════════════════════════════════════════ */
.book-stage {
  position: relative;
  z-index: 2;
  perspective: 2000px;
  perspective-origin: 50% 50%;
}

.book-container {
  position: relative;
  display: flex;
  align-items: stretch;
  /* Fill the viewport — much larger footprint than before (was 1300×820 capped) */
  width: min(97vw, var(--book-max-width));
  height: min(95vh, var(--book-max-height));
  transform-style: preserve-3d;
  transition: transform 0.6s var(--kb-ease-out);
}

/* Book cover shadow (under the open book) — deep dramatic pool */
.book-cover-shadow {
  position: absolute;
  inset: -32px -44px -52px -44px;
  border-radius: 8px 16px 16px 8px;
  background: radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.82) 100%);
  filter: blur(36px);
  z-index: -1;
  transform: translateZ(-50px);
}

/* ═══════════════════════════════════════════════════════════
   BOOK PAGES — Left & Right (stay bright — the spotlit manuscript)
   ═══════════════════════════════════════════════════════════ */
.book-page {
  position: relative;
  flex: 1;
  background:
    linear-gradient(135deg, #fbf5e8 0%, #f4ecdb 28%, #fbf5e8 55%, #efe6d2 100%);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow:
    inset 0 0 80px rgba(139, 108, 65, 0.10),
    inset 0 1px 0 rgba(255, 250, 235, 0.6);
}

/* Page paper texture overlay */
.page-texture {
  position: absolute;
  inset: 0;
  opacity: 0.04;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
  background-repeat: repeat;
  pointer-events: none;
  z-index: 0;
}

/* ── Left Page ─────────────────────────────────────────── */
.page-left {
  border-radius: 12px 2px 2px 12px;
  border-right: none;
  box-shadow:
    inset 0 0 40px rgba(139, 119, 90, 0.06),
    -3px 0 12px rgba(0,0,0,0.08);
  padding: 32px 28px 22px 38px;
  max-width: 400px;
  min-width: 320px;
}

.page-left-header {
  position: relative;
  z-index: 2;
  text-align: center;
  margin-bottom: 24px;
}

.book-plate {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 18px 14px 14px;
  border: 1.5px solid var(--kb-gold);
  border-radius: 3px;
  background:
    linear-gradient(180deg, rgba(212, 175, 106, 0.10), rgba(184, 71, 36, 0.03));
  position: relative;
  box-shadow:
    inset 0 0 0 3px rgba(244, 237, 224, 0.5),
    inset 0 0 0 4px rgba(184, 148, 90, 0.4),
    0 2px 8px rgba(184, 148, 90, 0.15);
}
/* Gold filigree corners on the bookplate */
.book-plate::before,
.book-plate::after {
  content: '';
  position: absolute;
  width: 14px;
  height: 14px;
  border: 1.5px solid var(--kb-gold-bright);
  opacity: 0.7;
}
.book-plate::before {
  top: 4px; left: 4px;
  border-right: none; border-bottom: none;
}
.book-plate::after {
  bottom: 4px; right: 4px;
  border-left: none; border-top: none;
}
.plate-ornament {
  font-size: 15px;
  color: var(--kb-gold);
  opacity: 0.85;
  text-shadow: 0 1px 2px rgba(184, 148, 90, 0.2);
}
.top-ornament { margin-bottom: 2px; }
.bottom-ornament { margin-top: 2px; }
.plate-text {
  font-family: var(--kb-font-serif);
  font-size: 20px;
  font-weight: 600;
  color: var(--kb-gold-deep);
  letter-spacing: 0.08em;
  font-style: italic;
}

/* Logo inside the bookplate — framed with a gold ring */
.plate-logo {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  padding: 3px;
  background: linear-gradient(135deg, var(--kb-gold-bright), var(--kb-gold-deep));
  box-shadow:
    0 2px 8px rgba(0, 0, 0, 0.25),
    inset 0 1px 0 rgba(255, 240, 200, 0.3);
  transition: transform 0.4s var(--kb-ease-out), box-shadow 0.4s var(--kb-ease-out);
}
.book-plate:hover .plate-logo {
  transform: rotate(-3deg) scale(1.04);
  box-shadow:
    0 4px 14px rgba(212, 175, 106, 0.4),
    inset 0 1px 0 rgba(255, 240, 200, 0.4);
}

/* ── Table of Contents ─────────────────────────────────── */
.book-toc {
  position: relative;
  z-index: 2;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
}

.toc-heading {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  padding: 0 4px;
}
.toc-label {
  font-family: var(--kb-font-serif);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #8b775a;
}
.toc-divider {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, #c4a96a, transparent);
}

.toc-item {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 11px 10px 11px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.25s var(--kb-ease);
  position: relative;
  animation: toc-item-in 0.5s var(--kb-ease-out) both;
  animation-delay: var(--item-delay, 0s);
}
.toc-item:hover {
  background: rgba(184, 71, 36, 0.06);
}
.toc-item.active {
  background: linear-gradient(90deg, rgba(184,71,36,0.1), rgba(184,71,36,0.03));
  border-left: 3px solid var(--kb-primary);
  padding-left: 4px;
}
.toc-item.disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.toc-number {
  font-family: var(--kb-font-mono);
  font-size: 10px;
  color: #b8a080;
  min-width: 18px;
  text-align: right;
}
.toc-item.active .toc-number {
  color: var(--kb-primary);
}

.toc-icon {
  font-size: 15px;
  color: #8b775a;
  flex-shrink: 0;
  transition: color 0.25s;
}
.toc-item:hover .toc-icon,
.toc-item.active .toc-icon {
  color: var(--kb-primary);
}

.toc-title {
  font-size: 14px;
  font-weight: 500;
  color: #4a3b2e;
  white-space: nowrap;
}
.toc-item.active .toc-title {
  color: var(--kb-primary);
  font-weight: 600;
}

.toc-dots {
  flex: 1;
  border-bottom: 1px dotted #c4b99a;
  min-width: 10px;
  margin: 0 2px;
}

.toc-page-num {
  font-family: var(--kb-font-serif);
  font-size: 11px;
  color: #b8a080;
  font-style: italic;
}
.toc-item.active .toc-page-num {
  color: var(--kb-primary);
}

@keyframes toc-item-in {
  from { opacity: 0; transform: translateX(-12px); }
  to   { opacity: 1; transform: translateX(0); }
}

/* ── Left Page Footer ───────────────────────────────────── */
.page-left-footer {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding-top: 16px;
  border-top: 1px solid #e0d5c0;
  margin-top: 8px;
}
.footer-ornament {
  font-size: 12px;
  color: #c4a96a;
}
.footer-text {
  font-size: 10px;
  color: #b8a080;
  letter-spacing: 0.04em;
}

/* ── Right Page ────────────────────────────────────────── */
.page-right {
  border-radius: 2px 12px 12px 2px;
  border-left: none;
  box-shadow:
    inset 0 0 40px rgba(139, 119, 90, 0.06),
    3px 0 12px rgba(0,0,0,0.08);
  padding: 0;
  flex: 1;
  min-width: 0;
}

.page-right-header {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 36px 12px;
  border-bottom: 1px solid #e8e0d2;
}
.page-running-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #8b775a;
  letter-spacing: 0.05em;
}
.running-title {
  font-weight: 500;
  text-transform: uppercase;
}
.running-dot {
  color: #c4a96a;
}
.running-chapter {
  font-family: var(--kb-font-serif);
  font-style: italic;
  color: #b8a080;
}
.header-actions-mini {
  display: flex;
  align-items: center;
  gap: 4px;
}
.mini-btn {
  width: 28px;
  height: 28px;
  border-radius: 5px;
  border: 1px solid #d5c8b0;
  background: rgba(250,245,235,0.6);
  color: #8b775a;
  cursor: pointer;
  display: grid;
  place-items: center;
  font-size: 12px;
  transition: all 0.2s;
}
.mini-btn:hover {
  background: rgba(184,71,36,0.08);
  border-color: var(--kb-primary);
  color: var(--kb-primary);
}

/* ── Page Turn Stage ──────────────────────────────────── */
.page-turn-stage {
  position: relative;
  z-index: 1;
  flex: 1;
  overflow: hidden;
  transform-style: preserve-3d;
}

.page-content {
  height: 100%;
  overflow-y: auto;
  /* Allow horizontal scroll for wide content (tables/graphs/code) instead of clipping */
  overflow-x: auto;
  padding: 24px 36px 14px;
  /* Establish a query container so child pages can respond to their REAL width
     (the book content area), not the viewport — fixes narrow-screen cramping. */
  container-type: inline-size;
}

/* Page turn TRANSITIONS */
.turn-forward-enter-active,
.turn-forward-leave-active,
.turn-backward-enter-active,
.turn-backward-leave-active {
  transition: all 0.45s cubic-bezier(0.4, 0, 0.2, 1);
  position: absolute;
  inset: 0;
}

/* Forward turn (next page) */
.turn-forward-enter-from {
  opacity: 0;
  transform: rotateY(-15deg) translateX(40px);
  transform-origin: left center;
}
.turn-forward-leave-to {
  opacity: 0;
  transform: rotateY(15deg) translateX(-40px);
  transform-origin: right center;
}

/* Backward turn (previous page) */
.turn-backward-enter-from {
  opacity: 0;
  transform: rotateY(15deg) translateX(-40px);
  transform-origin: right center;
}
.turn-backward-leave-to {
  opacity: 0;
  transform: rotateY(-15deg) translateX(40px);
  transform-origin: left center;
}

/* ── Right Page Footer ────────────────────────────────── */
.page-right-footer {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 8px 36px 12px;
  border-top: 1px solid #e8e0d2;
  font-size: 11px;
  color: #b8a080;
}
.page-number {
  font-family: var(--kb-font-serif);
  font-style: italic;
}
.page-decor {
  color: #c4a96a;
  font-size: 10px;
}

/* ═══════════════════════════════════════════════════════════
   SPINE
   ═══════════════════════════════════════════════════════════ */
.book-spine {
  width: 26px;
  flex-shrink: 0;
  background: linear-gradient(
    90deg,
    #6b5230 0%, #8a6d3b 12%, #b8945a 28%, #d4af6a 45%,
    #e8c98a 50%, #d4af6a 55%,
    #b8945a 72%, #8a6d3b 88%, #6b5230 100%
  );
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  padding: 20px 0;
  box-shadow:
    inset 1px 0 4px rgba(0,0,0,0.3),
    inset -1px 0 4px rgba(255, 240, 200, 0.25),
    0 0 12px rgba(0,0,0,0.35);
  position: relative;
  z-index: 3;
}

.spine-groove {
  width: 16px;
  height: 1px;
  background: rgba(0,0,0,0.25);
  box-shadow: 0 1px 0 rgba(255, 240, 200, 0.2);
}

.spine-label {
  font-family: var(--kb-font-serif);
  font-size: 9.5px;
  font-weight: 700;
  color: #3a2a14;
  letter-spacing: 0.12em;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  margin-top: 12px;
  opacity: 0.75;
  text-transform: uppercase;
  text-shadow: 0 1px 0 rgba(255, 240, 200, 0.3);
}

/* ═══════════════════════════════════════════════════════════
   BOOKMARK RIBBON
   ═══════════════════════════════════════════════════════════ */
.bookmark-ribbon {
  position: absolute;
  right: -6px;
  width: 14px;
  height: 32px;
  z-index: 5;
  transition: top 0.4s var(--kb-ease-out);
  pointer-events: none;
}
.bookmark-ribbon::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, #c49a4a 0%, #b84724 35%, #9e3818 70%, #b84724 100%);
  border-radius: 0 2px 2px 0;
  box-shadow:
    0 2px 6px rgba(0,0,0,0.3),
    inset 0 1px 0 rgba(255, 200, 120, 0.4);
}
.ribbon-fold {
  position: absolute;
  top: -5px;
  right: 0;
  width: 0;
  height: 0;
  border-left: 7px solid #7a2810;
  border-bottom: 6px solid transparent;
}

/* ═══════════════════════════════════════════════════════════
   PAGE CURL SHADOWS
   ═══════════════════════════════════════════════════════════ */
.page-curl {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 20px;
  pointer-events: none;
  z-index: 4;
}
.page-curl-left {
  right: -1px;
  background: linear-gradient(90deg, rgba(0,0,0,0.04), transparent);
}
.page-curl-right {
  left: -1px;
  background: linear-gradient(270deg, rgba(0,0,0,0.04), transparent);
}

/* ═══════════════════════════════════════════════════════════
   STACKED PAGE EDGES (3D depth illusion)
   ═══════════════════════════════════════════════════════════ */
.page-stack {
  position: absolute;
  left: 15px;
  right: 15px;
  height: 4px;
  background: #e0d5c0;
  border-radius: 0 0 3px 3px;
  z-index: -1;
}
.page-stack-bottom {
  bottom: -6px;
  opacity: 0.6;
}
.page-stack-bottom2 {
  bottom: -11px;
  opacity: 0.35;
}

/* ═══════════════════════════════════════════════════════════
   NAVIGATION ARROWS
   ═══════════════════════════════════════════════════════════ */
.nav-arrow {
  position: fixed;
  top: 50%;
  transform: translateY(-50%);
  z-index: 10;
  width: 46px;
  height: 46px;
  border-radius: 50%;
  border: 1px solid rgba(212, 175, 106, 0.45);
  background: rgba(30, 24, 18, 0.75);
  color: var(--kb-gold-bright);
  font-size: 16px;
  cursor: pointer;
  display: grid;
  place-items: center;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  transition: all 0.3s var(--kb-ease);
  box-shadow:
    0 4px 16px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(212, 175, 106, 0.15);
}
.nav-arrow:hover {
  background: rgba(184, 148, 90, 0.4);
  border-color: var(--kb-gold-bright);
  color: #fff5e0;
  transform: translateY(-50%) scale(1.12);
  box-shadow:
    0 0 28px rgba(212, 175, 106, 0.45),
    0 6px 20px rgba(0, 0, 0, 0.5);
}
.nav-prev { left: max(calc((100vw - var(--book-max-width)) / 2 - 60px), 12px); }
.nav-next { right: max(calc((100vw - var(--book-max-width)) / 2 - 60px), 12px); }

.nav-arrow-fade-enter-active,
.nav-arrow-fade-leave-active {
  transition: all 0.3s var(--kb-ease);
}
.nav-arrow-fade-enter-from,
.nav-arrow-fade-leave-to {
  opacity: 0;
  transform: translateY(-50%) scale(0.8);
}

/* ═══════════════════════════════════════════════════════════
   MOBILE ELEMENTS — hidden on desktop, shown via media query
   ═══════════════════════════════════════════════════════════ */
.mobile-menu-btn {
  display: none;
}

/* Mobile bottom navigation bar (single-page prev/next) */
.mobile-bottom-nav {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  display: none;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 16px calc(10px + env(safe-area-inset-bottom, 0px));
  background: linear-gradient(180deg, rgba(30, 24, 18, 0.92), rgba(15, 12, 9, 0.97));
  border-top: 1px solid rgba(212, 175, 106, 0.25);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  z-index: 45;
}
.mob-nav-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1px solid rgba(212, 175, 106, 0.35);
  background: rgba(212, 175, 106, 0.08);
  color: var(--kb-gold-bright);
  font-size: 16px;
  cursor: pointer;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  transition: transform 0.15s var(--kb-ease), background 0.2s;
}
.mob-nav-btn:disabled {
  opacity: 0.32;
  cursor: not-allowed;
}
.mob-nav-btn:not(:disabled):active {
  transform: scale(0.9);
  background: rgba(212, 175, 106, 0.2);
}
.mob-page-indicator {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-family: var(--kb-font-serif);
  color: var(--kb-gold-soft);
}
.mob-page-num {
  font-weight: 600;
  color: var(--kb-gold-bright);
  font-size: 17px;
}
.mob-page-sep {
  color: var(--kb-gold-deep);
  font-size: 14px;
}
.mob-page-total {
  color: rgba(212, 175, 106, 0.6);
  font-size: 13px;
  font-style: italic;
}

/* Mobile drawer backdrop */
.mobile-drawer-backdrop {
  position: fixed;
  inset: 0;
  display: none;
  background: rgba(50, 34, 18, 0.42);
  backdrop-filter: blur(2px);
  -webkit-backdrop-filter: blur(2px);
  z-index: 55;
}

/* Drawer backdrop fade */
.backdrop-fade-enter-active,
.backdrop-fade-leave-active {
  transition: opacity 0.3s var(--kb-ease-out);
}
.backdrop-fade-enter-from,
.backdrop-fade-leave-to {
  opacity: 0;
}

/* ═══════════════════════════════════════════════════════════
   MOBILE: Single-page book with slide-in TOC drawer
   ═══════════════════════════════════════════════════════════ */
@media (max-width: 840px) {
  .book-stage {
    width: 100vw;
    height: 100vh;
  }
  /* Only the right (content) page is in-flow; left page becomes a drawer */
  .book-container {
    flex-direction: row;
    width: 100vw;
    height: 100vh;
    max-width: none;
    max-height: none;
  }

  /* LEFT PAGE → slide-in drawer (off-screen by default) */
  .page-left {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: 84vw;
    max-width: 340px;
    min-width: 0;
    max-height: none;
    flex: none;
    border-radius: 0 14px 14px 0;
    padding: 24px 20px 18px;
    z-index: 60;
    transform: translateX(-106%);
    transition: transform 0.35s var(--kb-ease-out);
    box-shadow: none;
  }
  .page-left.drawer-open {
    transform: translateX(0);
    box-shadow: 6px 0 38px rgba(70, 48, 24, 0.30);
  }

  /* Vertical TOC list inside the drawer (same look as desktop) */
  .book-toc {
    flex-direction: column;
    flex-wrap: nowrap;
    gap: 2px;
    overflow-x: hidden;
    overflow-y: auto;
  }
  .toc-heading { display: flex; }
  .toc-item {
    padding: 11px 8px 11px 6px;
    white-space: nowrap;
    border: none;
    border-radius: 4px;
    font-size: 13px;
    gap: 10px;
  }
  .toc-item.active {
    border: none;
    border-left: 3px solid var(--kb-primary);
    background: linear-gradient(90deg, rgba(184,71,36,0.1), rgba(184,71,36,0.03));
    padding-left: 4px;
  }
  .toc-title { font-size: 13px; }
  .page-left-footer { display: flex; }

  /* Show backdrop + drawer open state */
  .mobile-drawer-backdrop { display: block; }

  .book-spine { display: none; }

  /* RIGHT PAGE → single full-screen content page */
  .page-right {
    border-radius: 0;
    flex: 1 1 auto;
    min-width: 0;
    width: 100%;
  }
  .page-right-header { padding: 10px 14px 8px; }
  .page-content {
    /* Extra bottom padding clears the fixed bottom nav */
    padding: 14px 16px 96px;
  }
  .page-right-footer { display: none; }  /* replaced by bottom nav */

  /* Reveal mobile controls */
  .mobile-menu-btn { display: grid; }
  .mobile-bottom-nav { display: flex; }

  /* Hide desktop-only controls */
  .nav-arrow { display: none; }
  .bookmark-ribbon { display: none; }
}

/* Very small phones — tighten the bottom nav */
@media (max-width: 380px) {
  .mob-nav-btn { width: 40px; height: 40px; }
  .mob-page-num { font-size: 16px; }
  .page-right-header { padding: 8px 12px 6px; }
  .page-content { padding: 12px 12px 92px; }
}

/* ═══════════════════════════════════════════════════════════
   IN-BOOK PAGE NORMALIZATION
   Fixes conflicting page styles for book layout without editing pages
   ═══════════════════════════════════════════════════════════ */
/* Neutralize full-height patterns — the book container manages height */
.page-content :deep([class$='-page']),
.page-content :deep(.landing-page),
.page-content :deep(.about-page) {
  min-height: auto !important;
  height: auto !important;
}
/* Fix about page negative margin and background override */
.page-content :deep(.about-page) {
  margin: 0 !important;
  background: transparent !important;
}
/* Fix about hero section — scale to fit, keep the dark gradient aesthetic */
.page-content :deep(.about-page .hero-section) {
  min-height: auto !important;
  padding: 40px 32px !important;
}
/* File system page — remove full-viewport minimum */
.page-content :deep(.file-system-page) {
  min-height: auto !important;
}
/* Knowledge graph canvas — scale to fit book page */
.page-content :deep(.search-graph-canvas) {
  height: auto !important;
  min-height: 400px !important;
}
/* Smooth scrolling within book pages */
.page-content {
  scroll-behavior: smooth;
}
/* Book-themed scrollbars (vertical + horizontal) */
.page-content::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}
.page-content::-webkit-scrollbar-track {
  background: rgba(196, 169, 106, 0.08);
  border-radius: 6px;
}
.page-content::-webkit-scrollbar-thumb {
  background: rgba(139, 119, 90, 0.35);
  border-radius: 6px;
  border: 2px solid transparent;
  background-clip: padding-box;
}
.page-content::-webkit-scrollbar-thumb:hover {
  background: rgba(184, 71, 36, 0.45);
  background-clip: padding-box;
}
.page-content {
  scrollbar-width: thin;
  scrollbar-color: rgba(139, 119, 90, 0.4) rgba(196, 169, 106, 0.08);
}
/* Horizontal-scroll guarantee: wide content scrolls instead of breaking layout.
   Applied broadly so every interface adapts to any width. */
.page-content :deep(pre),
.page-content :deep(.ant-table-wrapper),
.page-content :deep(.ant-table-content),
.page-content :deep(code) {
  overflow-x: auto;
  max-width: 100%;
}
.page-content :deep(table) {
  max-width: 100%;
  display: block;
  overflow-x: auto;
}
/* Prevent wide flex/grid rows from forcing the page wider than the viewport */
.page-content :deep(.ant-row),
.page-content :deep(.ant-card-body) {
  min-width: 0;
}
/* Ant Design overrides inside the book */
.page-content :deep(.ant-card) {
  background: rgba(250, 246, 239, 0.6);
}
.page-content :deep(.ant-table) {
  background: rgba(250, 246, 239, 0.4);
}
/* Book turn animation state */
.is-turning .book-container {
  transform: scale(0.995);
}

/* ═══════════════════════════════════════════════════════════
   CONTAINER QUERIES — pages adapt to their real width inside the book.
   Viewport-based @media in pages is unreliable here because the book's
   content area is far narrower than the viewport, so two-column layouts
   cramp and clip. These rules collapse layouts based on container width.
   ═══════════════════════════════════════════════════════════ */

/* File-system page — collapse sidebar+detail to a single column when the
   content area can't comfortably hold both, and neutralize the viewport-based
   heights / sticky that break inside the book's scroll container. */
.page-content :deep(.file-system-page) {
  overflow-x: auto;   /* wide paths/tables scroll instead of clipping */
}
/* Let the whole detail subtree shrink below its min-content so nothing is
   clipped — grid/flex items default to min-width:auto which forces overflow. */
.page-content :deep(.file-system-page .detail-panel),
.page-content :deep(.file-system-page .detail-content),
.page-content :deep(.file-system-page .info-card),
.page-content :deep(.file-system-page .info-header),
.page-content :deep(.file-system-page .info-body),
.page-content :deep(.file-system-page .info-identity),
.page-content :deep(.file-system-page .info-titles),
.page-content :deep(.file-system-page .info-grid),
.page-content :deep(.file-system-page .info-item),
.page-content :deep(.file-system-page .breadcrumb-bar) {
  min-width: 0 !important;
}
/* Long breadcrumbs scroll horizontally instead of forcing the panel wide */
.page-content :deep(.file-system-page .breadcrumb-bar) {
  overflow-x: auto;
}
.page-content :deep(.file-system-page .breadcrumb-bar .ant-breadcrumb) {
  white-space: nowrap;
}

@container (max-width: 880px) {
  .page-content :deep(.file-system-page .main-content) {
    padding: 12px 4px 4px !important;
  }
  .page-content :deep(.file-system-page .content-grid) {
    grid-template-columns: minmax(0, 1fr) !important;
    gap: 14px !important;
  }
  /* Sidebar: no more viewport-height / sticky — flows naturally with a cap */
  .page-content :deep(.file-system-page .sidebar-panel) {
    height: auto !important;
    max-height: 360px !important;
    position: relative !important;
    top: auto !important;
    min-width: 0 !important;
  }
  .page-content :deep(.file-system-page .detail-panel) {
    min-height: auto !important;
  }
  .page-content :deep(.file-system-page .info-grid) {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
    gap: 14px !important;
  }
  .page-content :deep(.file-system-page .info-body) {
    padding: 18px !important;
  }
}

@container (max-width: 540px) {
  .page-content :deep(.file-system-page .info-grid) {
    grid-template-columns: 1fr !important;
  }
  .page-content :deep(.file-system-page .info-header) {
    flex-direction: column !important;
    align-items: flex-start !important;
    gap: 12px !important;
  }
  .page-content :deep(.file-system-page .breadcrumb-bar) {
    padding: 10px 14px !important;
  }
}
</style>
