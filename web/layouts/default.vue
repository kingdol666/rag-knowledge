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
        <div
          class="book-page page-left"
          :class="{ 'drawer-open': mobileMenuOpen }"
          id="book-toc-drawer"
          ref="leftPage"
        >
          <!-- Page texture -->
          <div class="page-texture"></div>

          <!-- Drawer affordances (mobile only) -->
          <button class="drawer-close" aria-label="关闭目录 / Close contents" @click="closeMobileMenu">
            <CloseOutlined />
          </button>
          <span class="drawer-grip" aria-hidden="true"></span>

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
            <span class="footer-text">RAG Knowledge Platform v{{ appVersion }}</span>
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

          <!-- Drawer scrim: dims and captures taps on the content page only.
               It lives inside .page-right (which clips) so it can never cover
               the slide-in drawer — the previous top-level backdrop sat in the
               shell's stacking context and swallowed every TOC tap. -->
          <Transition name="backdrop-fade">
            <div v-if="mobileMenuOpen" class="mobile-drawer-backdrop" @click="closeMobileMenu"></div>
          </Transition>

          <!-- Right page header bar -->
          <div class="page-right-header">
            <!-- Mobile: menu button + title act as the app bar -->
            <button
              class="mini-btn mobile-menu-btn"
              :aria-expanded="mobileMenuOpen"
              aria-controls="book-toc-drawer"
              aria-label="打开目录 / Open contents"
              @click="toggleMobileMenu"
            >
              <MenuOutlined />
            </button>

            <div class="page-running-head">
              <component :is="currentItem.icon" class="running-icon" />
              <span class="running-title">{{ currentPageTitle }}</span>
              <span class="running-dot">·</span>
              <span class="running-chapter">{{ currentChapter }}</span>
            </div>
            <div class="header-actions-mini">
              <button
                class="mini-btn"
                :aria-label="isFullscreen ? '退出全屏' : '全屏'"
                @click="toggleFullscreen"
                :title="isFullscreen ? 'Exit fullscreen' : 'Fullscreen'"
              >
                <ExpandOutlined v-if="!isFullscreen" />
                <CompressOutlined v-else />
              </button>
              <LangSwitcher />
              <Theme-toggle />
            </div>

            <!-- Reading progress: how far through the book you are -->
            <div class="reading-progress" aria-hidden="true">
              <span class="reading-progress-fill" :style="{ width: progressPct + '%' }"></span>
            </div>
          </div>

          <!-- Page turn animation wrapper -->
          <div class="page-turn-stage" ref="turnStage">
            <Transition :name="turnDirection" @before-enter="onTurnStart" @after-enter="onTurnEnd">
              <div
                class="page-content"
                :key="route.fullPath"
                ref="pageContent"
                @touchstart.passive="onTouchStart"
                @touchend.passive="onTouchEnd"
              >
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

    <!-- Mobile drawer backdrop is rendered inside .page-right (see above) -->

    <!-- Mobile bottom navigation (single-page prev/next) -->
    <nav class="mobile-bottom-nav" aria-label="翻页导航 / Page navigation">
      <button class="mob-nav-btn" @click="goToPrev" :disabled="!prevPage" :aria-label="prevPage ? '上一页：' + prevPage.label : '已是第一页'" :title="prevPage ? prevPage.label : ''">
        <LeftOutlined />
      </button>
      <button class="mob-page-indicator" @click="toggleMobileMenu" aria-label="打开目录 / Open contents">
        <span class="mob-page-num">{{ currentPageNum }}</span>
        <span class="mob-page-sep">/</span>
        <span class="mob-page-total">{{ String(navItems.length).padStart(2, '0') }}</span>
        <span class="mob-page-name">{{ currentPageTitle }}</span>
      </button>
      <button class="mob-nav-btn" @click="goToNext" :disabled="!nextPage" :aria-label="nextPage ? '下一页：' + nextPage.label : '已是最后一页'" :title="nextPage ? nextPage.label : ''">
        <RightOutlined />
      </button>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  HomeOutlined, FolderOpenOutlined, DatabaseOutlined,
  SearchOutlined, ShareAltOutlined, RobotOutlined,
  SettingOutlined, QuestionCircleOutlined, KeyOutlined,
  ExpandOutlined, CompressOutlined, LeftOutlined, RightOutlined,
  MenuOutlined, CloseOutlined,
} from '@ant-design/icons-vue'

import pkg from '../package.json'

const route = useRoute()
const router = useRouter()

// Project version — single source: web/package.json (aligned with root VERSION)
const appVersion = pkg.version

// ── Navigation items ───────────────────────────────────────
const navItems = computed(() => [
  { path: '/',              label: 'Home',             icon: HomeOutlined,         pageNum: '01', chapter: 'Front Matter' },
  { path: '/file-system',   label: 'File System',      icon: FolderOpenOutlined,   pageNum: '02', chapter: 'Repository' },
  { path: '/knowledge-base',label: 'Knowledge Base',   icon: DatabaseOutlined,     pageNum: '03', chapter: 'Collections' },
  { path: '/knowledge-search', label: 'KB Search',     icon: SearchOutlined,       pageNum: '04', chapter: 'Retrieval' },
  { path: '/knowledge-graph',  label: 'Graph Explorer',icon: ShareAltOutlined,     pageNum: '05', chapter: 'Relations' },
  { path: '/soul',             label: 'SOUL Personas',   icon: RobotOutlined,        pageNum: '06', chapter: 'Persona' },
  { path: '/claude-chat',      label: 'Claude Chat',      icon: RobotOutlined,        pageNum: '07', chapter: 'Assistant' },
  { path: '/settings',         label: 'Settings',         icon: SettingOutlined,      pageNum: '08', chapter: 'Configuration' },
  { path: '/tokens',           label: 'API Tokens',       icon: KeyOutlined,          pageNum: '09', chapter: 'Security' },
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
const pageContent = ref<HTMLElement | null>(null)

// Reading progress through the book (drives the thin gold bar under the header)
const progressPct = computed(() =>
  navItems.value.length <= 1 ? 0 : (currentIdx.value / (navItems.value.length - 1)) * 100
)

// ── Computed ────────────────────────────────────────────────
const currentIdx = computed(() => {
  const idx = navItems.value.findIndex(item => isActive(item.path))
  return idx >= 0 ? idx : 0
})

const currentItem = computed(() => navItems.value[currentIdx.value] || navItems.value[0])

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

// ── Touch gestures (mobile): horizontal swipe turns the page ──
// Vertical intent is ignored so in-page scrolling never triggers a turn.
const SWIPE_MIN_X = 62
const SWIPE_MAX_Y = 46
let touchStart: { x: number; y: number; t: number } | null = null

function onTouchStart(e: TouchEvent) {
  if (e.touches.length !== 1) { touchStart = null; return }
  const t = e.touches[0]
  touchStart = { x: t.clientX, y: t.clientY, t: Date.now() }
}

function onTouchEnd(e: TouchEvent) {
  if (!touchStart) return
  const t = e.changedTouches[0]
  if (!t) { touchStart = null; return }
  const dx = t.clientX - touchStart.x
  const dy = t.clientY - touchStart.y
  const dt = Date.now() - touchStart.t
  touchStart = null

  if (dt > 800 || Math.abs(dx) < SWIPE_MIN_X || Math.abs(dy) > SWIPE_MAX_Y) return
  // Swipe right → previous page; swipe left → next page
  if (dx > 0) goToPrev()
  else goToNext()
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
  // Escape always dismisses the mobile contents drawer first.
  if (e.key === 'Escape' && mobileMenuOpen.value) {
    closeMobileMenu()
    return
  }
  // Never hijack arrows while the user is typing or has a field focused.
  const el = document.activeElement as HTMLElement | null
  const tag = el?.tagName?.toLowerCase()
  if (tag === 'input' || tag === 'textarea' || tag === 'select' || el?.isContentEditable) return

  if (e.key === 'ArrowLeft' && prevPage.value) {
    e.preventDefault()
    goToPrev()
  } else if (e.key === 'ArrowRight' && nextPage.value) {
    e.preventDefault()
    goToNext()
  }
}

// ── Mobile detection ───────────────────────────────────────
let lastIsMobile = false
function checkMobile() {
  // 840px is the single source of truth for "the book becomes one page".
  isMobile.value = window.innerWidth <= 840
  if (!isMobile.value && lastIsMobile) closeMobileMenu()
  lastIsMobile = isMobile.value
}

// ── Lifecycle ───────────────────────────────────────────────
onMounted(() => {
  lastRouteIdx.value = currentIdx.value
  window.addEventListener('keydown', handleKeyboard)
  window.addEventListener('resize', checkMobile)
  document.addEventListener('fullscreenchange', onFullscreenChange)
  checkMobile()
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyboard)
  window.removeEventListener('resize', checkMobile)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  document.body.style.removeProperty('overflow')
})

function onFullscreenChange() {
  isFullscreen.value = !!document.fullscreenElement
}

// Lock the page behind the drawer so the book doesn't scroll underneath.
watch(mobileMenuOpen, (open) => {
  if (import.meta.client) {
    document.body.style.overflow = open ? 'hidden' : ''
  }
})

// Keep lastRouteIdx in sync on direct URL changes, and reset the reading
// position so every page opens at its top (a page-turn shouldn't inherit
// the previous page's scroll offset).
watch(() => route.fullPath, async () => {
  lastRouteIdx.value = currentIdx.value
  closeMobileMenu()
  await nextTick()
  pageContent.value?.scrollTo({ top: 0, left: 0, behavior: 'auto' })
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
  opacity: 0.42;
  filter: saturate(0.7) brightness(1.08) sepia(0.12);
}

/* Warm vignette — soft wash for light theme default */
.library-bg-overlay {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background:
    radial-gradient(ellipse 80% 80% at 50% 50%,
      rgba(255, 250, 235, 0.35) 0%,
      rgba(245, 238, 222, 0.55) 60%,
      rgba(220, 205, 175, 0.75) 100%);
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
  background: rgba(120, 100, 70, 0.10);
}
.shelf-shadow.shelf-top {
  top: 0; left: 0; right: 0; height: 8px;
  background: linear-gradient(180deg, rgba(120, 100, 70, 0.18), transparent);
}
.shelf-shadow.shelf-left {
  left: 0; top: 0; bottom: 0; width: 6px;
  background: linear-gradient(90deg, rgba(120, 100, 70, 0.14), transparent);
}
.shelf-shadow.shelf-right {
  right: 0; top: 0; bottom: 0; width: 6px;
  background: linear-gradient(270deg, rgba(120, 100, 70, 0.14), transparent);
}

/* Dust motes — gold motes drifting in daylight */
.dust-mote {
  position: absolute;
  top: -10px;
  background: radial-gradient(circle, rgba(200, 169, 106, 0.35) 0%, rgba(200, 169, 106, 0.08) 70%, transparent 100%);
  border-radius: 50%;
  animation: dust-float linear infinite;
  filter: blur(0.3px);
  box-shadow: 0 0 4px rgba(200, 169, 106, 0.2);
  opacity: 0.25;
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
  opacity: 0.9;
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
  font-size: var(--kb-fs-sm);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  /* was #8b775a — 3.5:1 on the linen shell, under AA for 12px text */
  color: var(--kb-fg-3);
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
  transition: background 0.25s var(--kb-ease), transform 0.25s var(--kb-ease-out),
              padding 0.25s var(--kb-ease-out);
  position: relative;
  animation: toc-item-in 0.5s var(--kb-ease-out) both;
  animation-delay: var(--item-delay, 0s);
}
/* Gold rail that grows in on hover — a bookmark being pulled out */
.toc-item::after {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  width: 2px;
  height: 0;
  border-radius: 2px;
  background: linear-gradient(180deg, var(--kb-gold-bright), var(--kb-primary));
  transform: translateY(-50%);
  transition: height 0.28s var(--kb-ease-out);
  opacity: 0.85;
}
.toc-item:hover {
  background: rgba(184, 71, 36, 0.06);
  transform: translateX(2px);
}
@media (hover: hover) {
  .toc-item:hover::after { height: 60%; }
}
.toc-item:active { transform: translateX(2px) scale(0.985); }
.toc-item.active {
  background: linear-gradient(90deg, rgba(184,71,36,0.1), rgba(184,71,36,0.03));
  border-left: 3px solid var(--kb-primary);
  padding-left: 4px;
}
.toc-item.active::after { height: 0; }
.toc-item.disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.toc-number {
  font-family: var(--kb-font-mono);
  font-size: var(--kb-fs-xs);
  /* was #b8a080 — 2.0:1 on the linen shell, well under AA for small text */
  color: var(--kb-fg-3);
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
  font-size: var(--kb-fs-xs);
  /* was #b8a080 — 2.0:1 on the linen shell */
  color: var(--kb-fg-3);
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
  font-size: var(--kb-fs-sm);
  color: var(--kb-gold);
}
.footer-text {
  font-size: var(--kb-fs-xs);
  /* was #b8a080 — 2.0:1 on the linen shell */
  color: var(--kb-fg-3);
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
  gap: 12px;
  padding: 16px 36px 12px;
  border-bottom: 1px solid #e8e0d2;
}
.page-running-head {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  font-size: var(--kb-fs-xs);
  /* was #8b775a — 3.5:1 on the linen shell, under AA for 11px text */
  color: var(--kb-fg-2);
  letter-spacing: 0.05em;
}
.running-icon { display: none; font-size: 14px; color: var(--kb-primary); flex-shrink: 0; }
.running-title {
  font-weight: 600;
  text-transform: uppercase;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.running-dot {
  color: var(--kb-gold-bright);
  flex-shrink: 0;
}
.running-chapter {
  font-family: var(--kb-font-serif);
  font-style: italic;
  /* was #b8a080 — 2.0:1 on the linen shell */
  color: var(--kb-fg-3);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Reading progress — a hairline gold bar pinned to the header's bottom edge */
.reading-progress {
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 2px;
  background: transparent;
  overflow: hidden;
  pointer-events: none;
}
.reading-progress-fill {
  display: block;
  height: 100%;
  border-radius: 0 2px 2px 0;
  background: linear-gradient(90deg, var(--kb-gold), var(--kb-primary));
  box-shadow: 0 0 8px var(--kb-gold-glow);
  transition: width 0.5s var(--kb-ease-out);
}

.header-actions-mini {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
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
.mini-btn:active { transform: scale(0.92); }

/* Drawer-only affordances — dormant until the mobile breakpoint */
.drawer-close,
.drawer-grip { display: none; }

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

/* Mobile: a full-screen 3D flip is expensive and disorienting — slide
   instead, in the direction the swipe went. */
@media (max-width: 840px) {
  .turn-forward-enter-from { transform: translateX(28px); }
  .turn-forward-leave-to { transform: translateX(-20px); }
  .turn-backward-enter-from { transform: translateX(-28px); }
  .turn-backward-leave-to { transform: translateX(20px); }
  .turn-forward-enter-active,
  .turn-forward-leave-active,
  .turn-backward-enter-active,
  .turn-backward-leave-active { transition: all 0.3s var(--kb-ease-out); }
}

/* Reduced motion: cross-fade only, no page movement. */
@media (prefers-reduced-motion: reduce) {
  .turn-forward-enter-active,
  .turn-forward-leave-active,
  .turn-backward-enter-active,
  .turn-backward-leave-active { transition: opacity 0.2s linear; }
  .turn-forward-enter-from, .turn-forward-leave-to,
  .turn-backward-enter-from, .turn-backward-leave-to {
    transform: none !important;
  }
  .dust-mote { display: none; }
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
  font-size: var(--kb-fs-xs);
  /* was #b8a080 — 2.0:1 on the linen shell */
  color: var(--kb-fg-3);
}
.page-number {
  font-family: var(--kb-font-serif);
  font-style: italic;
}
.page-decor {
  color: var(--kb-gold-bright);
  font-size: var(--kb-fs-xs);
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
  width: 42px;
  height: 42px;
  border-radius: 50%;
  border: 1px solid var(--kb-border-strong);
  /* Parchment glass instead of charcoal — the arrows belong to the book. */
  background: var(--kb-glass-bg-strong, rgba(255, 252, 246, 0.78));
  color: var(--kb-gold-deep);
  font-size: 15px;
  cursor: pointer;
  display: grid;
  place-items: center;
  backdrop-filter: blur(10px) saturate(1.05);
  -webkit-backdrop-filter: blur(10px) saturate(1.05);
  transition: all 0.3s var(--kb-ease);
  box-shadow:
    0 4px 16px rgba(85, 65, 40, 0.16),
    inset 0 1px 0 rgba(255, 250, 235, 0.6);
}
.nav-arrow:hover {
  background: var(--kb-gold-soft);
  border-color: var(--kb-gold-bright);
  color: var(--kb-primary);
  transform: translateY(-50%) scale(1.1);
  box-shadow:
    0 0 26px var(--kb-gold-glow),
    0 6px 20px rgba(85, 65, 40, 0.22);
}
.nav-arrow:active { transform: translateY(-50%) scale(0.96); }
/* Sit just outside the book when there is room; hug the edge when there isn't. */
.nav-prev { left: max(calc((100vw - min(97vw, var(--book-max-width))) / 2 - 58px), 6px); }
.nav-next { right: max(calc((100vw - min(97vw, var(--book-max-width))) / 2 - 58px), 6px); }

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
  align-items: center;
  gap: 6px;
  font-family: var(--kb-font-serif);
  /* The bottom nav is a LIGHT cream bar in light mode, so the indicator text
     must be ink — it was var(--kb-gold-soft) (#f3ead0), i.e. 1.07:1, invisible. */
  color: var(--kb-fg);
  background: rgba(158, 122, 56, 0.10);
  border: 1px solid rgba(158, 122, 56, 0.34);
  border-radius: 999px;
  padding: 6px 16px;
  cursor: pointer;
  max-width: 46vw;
  transition: background 0.2s var(--kb-ease), border-color 0.2s var(--kb-ease);
  /* Button reset */
  appearance: none;
  -webkit-appearance: none;
}
.mob-page-indicator:active {
  background: rgba(158, 122, 56, 0.22);
  border-color: rgba(158, 122, 56, 0.5);
  transform: scale(0.97);
}
.mob-page-num {
  font-weight: 600;
  /* --kb-primary (#b24422) only reaches 4.11:1 on this cream bar; the hover
     shade clears AA at small sizes while staying in the same hue. */
  color: var(--kb-primary-hover);
  font-size: 17px;
}
.mob-page-sep {
  color: var(--kb-fg-3);
  font-size: 14px;
}
.mob-page-total {
  color: var(--kb-fg-3);
  font-size: 13px;
  font-style: italic;
}
/* Current page name — reveals the target of the contents tap */
.mob-page-name {
  font-family: var(--kb-font);
  font-size: var(--kb-fs-sm);
  font-style: normal;
  color: var(--kb-fg-2);
  letter-spacing: 0.04em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding-left: 6px;
  border-left: 1px solid rgba(158, 122, 56, 0.3);
}

/* Drawer scrim — absolutely positioned inside the content page so it is
   clipped by the page and can never rise above the slide-in drawer. */
.mobile-drawer-backdrop {
  position: absolute;
  inset: 0;
  display: none;
  background: rgba(50, 34, 18, 0.42);
  backdrop-filter: blur(2px);
  -webkit-backdrop-filter: blur(2px);
  z-index: 20;
  cursor: pointer;
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

  /* ── Mobile app bar ──────────────────────────────────────
     Menu · icon+title · actions, on one comfortable 56px row that
     respects the status-bar inset. */
  .page-right-header {
    padding: calc(10px + var(--kb-safe-top)) 14px 10px;
    gap: 10px;
    min-height: 56px;
    align-items: center;
    position: sticky;
    top: 0;
    z-index: 30;
    border-bottom-color: rgba(196, 169, 106, 0.35);
    box-shadow: 0 2px 12px rgba(90, 66, 36, 0.06);
  }
  .running-icon { display: block; }
  .page-running-head {
    flex: 1;
    min-width: 0;
    font-size: 12px;
    gap: 7px;
  }
  .running-title {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.02em;
    color: var(--kb-fg);
    text-transform: none;
  }
  .running-chapter {
    font-size: 11.5px;
    min-width: 0;
  }
  /* The chapter is the first thing to go when space runs out. */
  .page-running-head .running-dot,
  .page-running-head .running-chapter { transition: opacity 0.2s; }

  .page-content {
    /* Extra bottom padding clears the fixed bottom nav */
    padding: 16px 16px calc(104px + var(--kb-safe-bottom));
    scroll-padding-top: 12px;
  }
  .page-right-footer { display: none; }  /* replaced by bottom nav */

  /* Reveal mobile controls */
  .mobile-menu-btn {
    display: grid;
    width: 38px;
    height: 38px;
    font-size: 16px;
    flex-shrink: 0;
    border-radius: 9px;
  }
  .mobile-bottom-nav { display: flex; }

  /* Touch-sized controls in the bar (44px minimum target) */
  .header-actions-mini { gap: 6px; }
  .header-actions-mini :deep(.mini-btn),
  .header-actions-mini :deep(button) {
    width: 38px;
    height: 38px;
    border-radius: 9px;
    font-size: 14px;
  }

  /* Hide desktop-only controls */
  .nav-arrow { display: none; }
  .bookmark-ribbon { display: none; }
  .page-stack { display: none; }
  .book-cover-shadow { display: none; }

  /* Drawer affordances */
  .drawer-close {
    display: grid;
    place-items: center;
    position: absolute;
    top: calc(10px + var(--kb-safe-top));
    right: 10px;
    width: 36px;
    height: 36px;
    border-radius: 10px;
    border: 1px solid rgba(196, 169, 106, 0.4);
    background: rgba(250, 245, 235, 0.85);
    color: #8b775a;
    font-size: 14px;
    cursor: pointer;
    z-index: 12;
    transition: background 0.2s, color 0.2s;
  }
  .drawer-close:active { background: var(--kb-primary-soft); color: var(--kb-primary); }
  .drawer-grip {
    display: block;
    position: absolute;
    top: 50%;
    right: 5px;
    transform: translateY(-50%);
    width: 3px;
    height: 46px;
    border-radius: 3px;
    background: rgba(196, 169, 106, 0.45);
    z-index: 12;
  }
  /* Give the drawer's own header room for the close button */
  .page-left-header { padding-right: 34px; }
}

/* Very small phones — tighten everything one more notch */
@media (max-width: 380px) {
  .mob-nav-btn { width: 40px; height: 40px; }
  .mob-page-num { font-size: 16px; }
  .mob-page-name { display: none; }
  .page-right-header { padding: calc(8px + var(--kb-safe-top)) 10px 8px; min-height: 52px; }
  .page-content { padding: 12px 12px calc(98px + var(--kb-safe-bottom)); }
  .mobile-menu-btn, .header-actions-mini :deep(.mini-btn),
  .header-actions-mini :deep(button) { width: 34px; height: 34px; }
}

/* Narrow phones — drop the running chapter before the title can clip */
@media (max-width: 430px) {
  .running-dot, .running-chapter { display: none; }
}

/* Short landscape phones — reclaim vertical space */
@media (max-width: 900px) and (max-height: 520px) {
  .page-right-header { min-height: 46px; padding-top: calc(6px + var(--kb-safe-top)); padding-bottom: 6px; }
  .page-content { padding-top: 10px; padding-bottom: calc(84px + var(--kb-safe-bottom)); }
  .mobile-bottom-nav { padding-top: 4px; padding-bottom: calc(6px + var(--kb-safe-bottom)); }
  .mob-nav-btn { width: 38px; height: 38px; }
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
/* ═══════════════════════════════════════════════════════════
   COMPACT DESKTOP (841px–1180px)
   Between the two-page book and the mobile drawer, the content page is the
   narrowest it ever gets. Shrink the contents page and the gutters so the
   reading column keeps a usable measure instead of collapsing.
   ═══════════════════════════════════════════════════════════ */
@media (min-width: 841px) and (max-width: 1180px) {
  .page-left {
    max-width: 306px;
    min-width: 262px;
    padding: 24px 18px 18px 24px;
  }
  .plate-text { font-size: 17px; }
  .plate-logo { width: 44px; height: 44px; border-radius: 12px; }
  .book-plate { padding: 14px 10px 12px; }
  .toc-item { padding: 9px 8px 9px 6px; gap: 9px; }
  .toc-title { font-size: 13px; }
  .toc-number { min-width: 15px; font-size: var(--kb-fs-xs); }
  .page-right-header { padding: 12px 20px 10px; }
  .page-content { padding: 20px 22px 14px; }
  .page-right-footer { padding: 6px 20px 10px; }
}

/* ═══════════════════════════════════════════════════════════
   UNIVERSAL ADAPTIVE NORMALIZATION — container queries
   The book's content column is far narrower than the viewport, so
   viewport-based @media inside pages mis-fires (a 1440px window leaves a
   900px column; a 900px window leaves ~480px). These rules adapt to the
   REAL reading width, so every page behaves at every screen size.
   ═══════════════════════════════════════════════════════════ */

/* ── Page titles: wrap gracefully, never break mid-word ────── */
.page-content :deep(h1),
.page-content :deep(h2),
.page-content :deep(.section-title),
.page-content :deep([class*="title"]) {
  overflow-wrap: break-word;
  word-break: normal;
  hyphens: auto;
}
.page-content :deep(h1) { line-height: 1.22; }

/* ── ≤1080px: two-column workspaces get tighter gutters ─────── */
@container (max-width: 1080px) {
  .page-content :deep(.manage-layout),
  .page-content :deep(.graph-layout),
  .page-content :deep(.history-layout) { gap: 14px !important; }
  .page-content :deep(.stats-row) { gap: 12px !important; }
  .page-content :deep(.field-row) { padding: 14px 18px; }
}

/* ── ≤900px: side-by-side panels stack ─────────────────────── */
@container (max-width: 900px) {
  /* Management / graph / settings / soul two-pane layouts collapse */
  .page-content :deep(.manage-layout),
  .page-content :deep(.graph-layout),
  .page-content :deep(.history-layout),
  .page-content :deep(.settings-body),
  .page-content :deep(.studio-body) {
    grid-template-columns: minmax(0, 1fr) !important;
    display: grid !important;
    gap: 16px !important;
  }
  .page-content :deep(.settings-body),
  .page-content :deep(.studio-body) {
    display: flex !important;
    flex-direction: column !important;
    /* Soul/settings set align-items:start for the two-pane layout; in a
       column that makes the rail shrink to content width instead of
       spanning the page. */
    align-items: stretch !important;
  }
  /* Rails become full-width blocks in the stacked layout */
  .page-content :deep(.persona-rail),
  .page-content :deep(.studio-main) { width: 100% !important; }

  /* Pane heights: no viewport math inside a scrolling container */
  .page-content :deep(.kb-list-panel),
  .page-content :deep(.doc-panel),
  .page-content :deep(.detail-panel),
  .page-content :deep(.persona-rail),
  .page-content :deep(.settings-sidebar),
  .page-content :deep([class*="sidebar-panel"]) {
    max-height: none !important;
    height: auto !important;
    position: static !important;
    top: auto !important;
    min-height: 0 !important;
  }
  .page-content :deep(.kb-list-panel),
  .page-content :deep(.persona-rail) { max-height: 320px !important; }
  .page-content :deep(.doc-panel) { min-height: 0 !important; }

  /* Sidebars that were vertical rails become horizontal swipe rails */
  .page-content :deep(.settings-sidebar) {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    overflow-x: auto;
    scrollbar-width: none;
    padding: 8px !important;
    gap: 6px !important;
    width: 100% !important;
  }
  .page-content :deep(.settings-sidebar)::-webkit-scrollbar { display: none; }
  .page-content :deep(.settings-sidebar .nav-item),
  .page-content :deep(.settings-sidebar [class*="nav-item"]) {
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: max-content;
  }

  /* Graph-specific */
  .page-content :deep(.graph-canvas-wrapper) { min-height: 420px !important; }
  .page-content :deep(.stats-row) { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }
  .page-content :deep(.view-tabs) { flex-wrap: wrap; }
  .page-content :deep(.graph-toolbar) { top: 10px; right: 10px; }
  .page-content :deep(.graph-legend) {
    left: 10px; right: 10px; bottom: 10px;
    flex-wrap: wrap; gap: 8px; padding: 7px 12px; font-size: 11px;
  }
}

/* ── ≤760px: settings rows stack, controls go full width ───── */
@container (max-width: 760px) {
  .page-content :deep(.config-field) {
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 10px !important;
  }
  .page-content :deep(.field-control) {
    width: 100% !important;
    flex-shrink: 1 !important;
    min-width: 0 !important;
  }
  .page-content :deep(.field-row) { padding: 14px 16px !important; }
  .page-content :deep(.field-group) { margin: 8px 12px 14px !important; padding: 14px !important; }
  .page-content :deep(.section-header) { padding: 18px 16px !important; }
  .page-content :deep(.section-card) { min-width: 0 !important; }
  .page-content :deep(.settings-content) { width: 100% !important; min-width: 0 !important; }
}

/* ── ≤720px: page headers stack, actions go full-width ─────── */
@container (max-width: 720px) {
  .page-content :deep(.header-content),
  .page-content :deep(.page-header-content),
  .page-content :deep(.page-header) {
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 14px !important;
  }
  .page-content :deep(.header-left) {
    align-items: flex-start !important;
    gap: 12px !important;
    min-width: 0 !important;
  }
  .page-content :deep(.header-icon) {
    width: 44px !important;
    height: 44px !important;
    font-size: 20px !important;
    border-radius: 12px !important;
    flex-shrink: 0;
  }
  .page-content :deep(.header-text),
  .page-content :deep(.header-title-row) { min-width: 0 !important; flex: 1; }
  .page-content :deep(.header-text h1),
  .page-content :deep(.page-title),
  .page-content :deep(.header-title) {
    font-size: 21px !important;
    line-height: 1.25 !important;
    letter-spacing: -0.3px !important;
  }
  .page-content :deep(.header-text p),
  .page-content :deep(.page-subtitle),
  .page-content :deep(.header-subtitle) { font-size: 13px !important; }

  /* Action rows: wrap and share the width evenly */
  .page-content :deep(.header-actions),
  .page-content :deep(.doc-list-actions) {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 8px !important;
    width: 100% !important;
    justify-content: flex-start !important;
  }
  .page-content :deep(.header-actions .ant-btn),
  .page-content :deep(.header-actions .action-btn) {
    flex: 1 1 auto;
    min-width: 0;
    height: 40px;
    padding-inline: 12px;
  }
  .page-content :deep(.header-actions .ant-btn > span:not(.anticon)) {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Toolbars, filter bars and result summaries stack */
  .page-content :deep(.mode-bar),
  .page-content :deep(.options-bar),
  .page-content :deep(.tag-bar),
  .page-content :deep(.results-summary),
  .page-content :deep(.doc-list-header),
  .page-content :deep(.effective-banner),
  .page-content :deep(.action-bar) {
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 10px !important;
  }
  .page-content :deep(.action-bar) {
    left: 12px !important;
    right: 12px !important;
    width: auto !important;
    min-width: 0 !important;
  }
  .page-content :deep(.action-bar .action-buttons) { flex-wrap: wrap; }
  .page-content :deep(.action-bar .action-buttons .ant-btn) { flex: 1 1 auto; }
  .page-content :deep(.banner-divider) { display: none !important; }
  .page-content :deep(.banner-item) { padding: 0 !important; }

  /* Search inputs are already full width — just cap the pill height */
  .page-content :deep(.search-row) :deep(.ant-input-search-large .ant-input-affix-wrapper),
  .page-content :deep(.search-row) :deep(.ant-input-search-large .ant-btn) { height: 46px !important; }

  /* Card grids: single comfortable column */
  .page-content :deep(.doc-grid),
  .page-content :deep(.sub-kb-grid),
  .page-content :deep(.cross-kb-grid),
  .page-content :deep(.kb-grid),
  .page-content :deep(.feature-grid),
  .page-content :deep(.quick-links),
  .page-content :deep(.children-grid),
  .page-content :deep(.stats-row) {
    grid-template-columns: minmax(0, 1fr) !important;
    gap: 12px !important;
  }

  /* List rows: stack the trailing meta under the main line */
  .page-content :deep(.doc-item),
  .page-content :deep(.result-card),
  .page-content :deep(.sub-kb-card),
  .page-content :deep(.related-item),
  .page-content :deep(.info-header) {
    flex-direction: column !important;
    align-items: flex-start !important;
    gap: 10px !important;
  }
  .page-content :deep(.doc-item-side) { width: 100%; }
  .page-content :deep(.result-scores) { gap: 12px; }
  .page-content :deep(.result-path) { max-width: 100%; }
  .page-content :deep(.path-selector) { flex-direction: column !important; }
  .page-content :deep(.path-arrow) { display: none !important; }
  .page-content :deep(.info-grid) { grid-template-columns: minmax(0, 1fr) !important; }
  .page-content :deep(.info-identity) { align-items: flex-start !important; }

  /* Cards & panels: reclaim horizontal padding */
  .page-content :deep(.search-card),
  .page-content :deep(.section-card),
  .page-content :deep(.sub-kb-section),
  .page-content :deep(.doc-table-wrapper),
  .page-content :deep(.doc-list-header) { padding: 16px !important; }
  .page-content :deep(.info-body) { padding: 16px !important; }
  .page-content :deep(.kb-item) { padding: 10px !important; }
  .page-content :deep(.kb-item-icon) {
    width: 34px !important; height: 34px !important;
    font-size: 15px !important; border-radius: 9px !important;
  }
}

/* ── ≤460px: phones — one more compression pass ─────────────── */
@container (max-width: 460px) {
  .page-content :deep(.header-text h1),
  .page-content :deep(.page-title),
  .page-content :deep(.header-title) { font-size: 19px !important; }

  /* Any remaining fixed multi-column grid goes single column */
  .page-content :deep(.info-grid),
  .page-content :deep(.stats-row),
  .page-content :deep([style*="grid-template-columns"]) {
    grid-template-columns: minmax(0, 1fr) !important;
  }

  /* Buttons keep a comfortable tap height and share the row */
  .page-content :deep(.ant-btn) { min-height: 38px; }
  .page-content :deep(input),
  .page-content :deep(.ant-input),
  .page-content :deep(.ant-select-selector) { min-height: 38px; }

  /* Table-ish rows: let content breathe vertically */
  .page-content :deep(.related-item),
  .page-content :deep(.doc-item) { padding: 12px !important; }

  /* Typography floors so nothing becomes unreadable */
  .page-content :deep(p),
  .page-content :deep(li) { font-size: 13.5px; line-height: 1.65; }
}

/* ═══════════════════════════════════════════════════════════
   DARK MODE OVERRIDES — [data-theme="dark"]
   Inverts the book pages and shell to true dark backgrounds

<style>
/* ============================================================
 * DARK MODE — global overrides (non-scoped)
 * ============================================================ */
[data-theme='dark'] .library-shell {
  background:
    radial-gradient(ellipse 60% 50% at 50% 35%, rgba(88, 166, 255, 0.06) 0%, transparent 60%),
    radial-gradient(ellipse 80% 70% at 50% 50%, #161b22 0%, #0d1117 70%);
}
[data-theme='dark'] .library-bg-video.is-ready {
  opacity: 0.15;
  filter: saturate(0.4) brightness(0.6);
}
[data-theme='dark'] .library-bg-overlay {
  background:
    radial-gradient(ellipse 75% 75% at 50% 50%,
      transparent 0%, transparent 45%,
      rgba(0, 0, 0, 0.35) 80%, rgba(0, 0, 0, 0.75) 100%);
}
[data-theme='dark'] .shelf-shadow.shelf-top {
  background: linear-gradient(180deg, rgba(0,0,0,0.6), transparent);
}
[data-theme='dark'] .shelf-shadow.shelf-left {
  background: linear-gradient(90deg, rgba(0,0,0,0.5), transparent);
}
[data-theme='dark'] .shelf-shadow.shelf-right {
  background: linear-gradient(270deg, rgba(0,0,0,0.5), transparent);
}
[data-theme='dark'] .dust-mote {
  background: radial-gradient(circle, rgba(88, 166, 255, 0.3) 0%, rgba(88, 166, 255, 0.06) 70%, transparent 100%);
  box-shadow: 0 0 4px rgba(88, 166, 255, 0.2);
  opacity: 0.4 !important;
}
[data-theme='dark'] .book-page {
  background:
    linear-gradient(135deg, #1c2128 0%, #161b22 28%, #1c2128 55%, #0d1117 100%) !important;
  box-shadow:
    inset 0 0 80px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.03) !important;
}
[data-theme='dark'] .page-texture { opacity: 0.02; }
[data-theme='dark'] .book-plate {
  border-color: var(--kb-gold);
  background: linear-gradient(180deg, rgba(212,175,106,0.08), rgba(224,85,58,0.03));
  box-shadow: inset 0 0 0 3px rgba(22,27,34,0.5), inset 0 0 0 4px rgba(212,175,106,0.3), 0 2px 8px rgba(0,0,0,0.4);
}
[data-theme='dark'] .plate-text { color: var(--kb-gold-bright); }
/* --kb-fg-mute is 4.12:1 on the dark page background — under AA for small
   text. --kb-fg-3 (6.15:1) is the correct token for these captions. */
[data-theme='dark'] .toc-label { color: var(--kb-fg-3); }
[data-theme='dark'] .toc-divider { background: linear-gradient(90deg, var(--kb-gold), transparent); }
[data-theme='dark'] .toc-number { color: var(--kb-fg-3); }
[data-theme='dark'] .toc-icon { color: var(--kb-fg-3); }
[data-theme='dark'] .toc-title { color: var(--kb-fg); }
[data-theme='dark'] .toc-dots { border-bottom-color: var(--kb-border-strong); }
[data-theme='dark'] .toc-page-num { color: var(--kb-fg-3); }
[data-theme='dark'] .toc-item:hover { background: var(--kb-primary-tint); }
[data-theme='dark'] .toc-item.active {
  background: linear-gradient(90deg, var(--kb-primary-soft), rgba(224,85,58,0.02));
}
[data-theme='dark'] .page-left-footer { border-top-color: var(--kb-border); }
[data-theme='dark'] .footer-ornament { color: var(--kb-gold); }
[data-theme='dark'] .footer-text { color: var(--kb-fg-3); }
[data-theme='dark'] .page-right-header { border-bottom-color: var(--kb-border); }
[data-theme='dark'] .page-running-head { color: var(--kb-fg-3); }
[data-theme='dark'] .running-dot { color: var(--kb-gold); }
[data-theme='dark'] .running-chapter { color: var(--kb-fg-3); }
[data-theme='dark'] .mini-btn {
  border-color: var(--kb-border-strong);
  background: var(--kb-bg-subtle);
  color: var(--kb-fg-3);
}
[data-theme='dark'] .mini-btn:hover {
  background: var(--kb-primary-soft);
  border-color: var(--kb-primary);
  color: var(--kb-primary);
}
/* --kb-fg-mute is 4.12:1 on the dark page background; --kb-fg-3 clears AA. */
[data-theme='dark'] .page-right-footer { border-top-color: var(--kb-border); color: var(--kb-fg-3); }
[data-theme='dark'] .page-decor { color: var(--kb-gold); }
[data-theme='dark'] .book-spine {
  box-shadow: inset 1px 0 4px rgba(0,0,0,0.5), inset -1px 0 4px rgba(255,240,200,0.1), 0 0 12px rgba(0,0,0,0.6);
}
[data-theme='dark'] .spine-groove { background: rgba(0,0,0,0.4); box-shadow: 0 1px 0 rgba(255,240,200,0.1); }
/* The spine is a gold gradient in BOTH themes, so its label must stay dark ink.
   Do not retheme this with --kb-fg tokens: that made it 1.17:1 in dark mode. */
[data-theme='dark'] .spine-label { color: #3a2a14; text-shadow: 0 1px 0 rgba(255,240,200,0.22); }
[data-theme='dark'] .page-curl-left { background: linear-gradient(90deg, rgba(0,0,0,0.15), transparent); }
[data-theme='dark'] .page-curl-right { background: linear-gradient(270deg, rgba(0,0,0,0.15), transparent); }
[data-theme='dark'] .page-stack { background: var(--kb-border); }
[data-theme='dark'] .nav-arrow {
  border-color: var(--kb-border-strong);
  background: rgba(13,17,23,0.85);
  color: var(--kb-gold);
  box-shadow: 0 4px 16px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05);
}
[data-theme='dark'] .nav-arrow:hover {
  background: var(--kb-primary-soft);
  border-color: var(--kb-gold);
  color: var(--kb-gold-bright);
  box-shadow: 0 0 28px var(--kb-primary-glow), 0 6px 20px rgba(0,0,0,0.6);
}
[data-theme='dark'] .mobile-bottom-nav {
  background: linear-gradient(180deg, rgba(22,27,34,0.95), rgba(13,17,23,0.98));
  border-top-color: var(--kb-border);
}
[data-theme='dark'] .mob-nav-btn {
  border-color: var(--kb-border-strong);
  background: var(--kb-bg-subtle);
  color: var(--kb-gold);
}
[data-theme='dark'] .mob-page-num { color: var(--kb-gold-bright); }
[data-theme='dark'] .mob-page-sep { color: var(--kb-gold); }
/* --kb-fg-mute is only 3.65:1 on the dark bar; --kb-fg-3 clears AA. */
[data-theme='dark'] .mob-page-total { color: var(--kb-fg-3); }
[data-theme='dark'] .mobile-drawer-backdrop { background: rgba(0,0,0,0.55); }
[data-theme='dark'] .page-content::-webkit-scrollbar-track { background: rgba(48,54,61,0.3); }
[data-theme='dark'] .page-content::-webkit-scrollbar-thumb { background: rgba(139,148,158,0.4); }
[data-theme='dark'] .page-content::-webkit-scrollbar-thumb:hover { background: rgba(88,166,255,0.5); }
[data-theme='dark'] .page-content { scrollbar-color: rgba(139,148,158,0.4) rgba(48,54,61,0.3); }
</style>
