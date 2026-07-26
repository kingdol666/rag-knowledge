<template>
  <div :class="['empty-state', `empty-state--${size}`, { 'empty-state--fill': fill }]">
    <!-- Icon: #icon slot takes precedence, then the icon component prop -->
    <div v-if="$slots.icon || icon" class="empty-state__icon">
      <slot name="icon">
        <component :is="icon" v-if="icon" />
      </slot>
    </div>

    <!-- Title (serif, per Nocturne Atelier brand) -->
    <p v-if="title" class="empty-state__title">{{ title }}</p>

    <!-- Hint -->
    <p v-if="hint" class="empty-state__hint">{{ hint }}</p>

    <!-- Optional action slot (buttons, etc.) -->
    <div v-if="$slots.action" class="empty-state__action">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Component } from 'vue'

interface Props {
  /** Icon component (e.g. an @ant-design/icons-vue icon). Overridden by the #icon slot. */
  icon?: Component
  /** Primary message — rendered in the serif display face. */
  title?: string
  /** Secondary, muted helper line. */
  hint?: string
  /** Density: 'default' for page-level, 'compact' for sidebars / panels. */
  size?: 'default' | 'compact'
  /** When true, the state stretches to fill its parent (height:100%, centered). */
  fill?: boolean
}

withDefaults(defineProps<Props>(), {
  icon: undefined,
  title: undefined,
  hint: undefined,
  size: 'default',
  fill: false,
})
</script>

<style scoped>
/* ── Container ─────────────────────────────────────────────
 * Centered column. All color/spacing comes from theme.css
 * CSS variables, so it renders correctly under both the dark
 * "Nocturne Atelier" and light "Day Atelier" themes.
 * ────────────────────────────────────────────────────────── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 56px 20px;
  text-align: center;
  box-sizing: border-box;
}

.empty-state--fill {
  height: 100%;
  min-height: 160px;
}

/* ── Icon tile ────────────────────────────────────────────
 * Rounded copper-tinted well; the icon inherits font-size. */
.empty-state__icon {
  width: 64px;
  height: 64px;
  border-radius: 18px;
  display: grid;
  place-items: center;
  font-size: 28px;
  line-height: 1;
  color: var(--kb-primary);
  background: var(--kb-primary-soft);
  border: 1px solid var(--kb-border);
  margin-bottom: 2px;
}

/* ── Title (serif display) ─────────────────────────────── */
.empty-state__title {
  margin: 0;
  font-family: var(--kb-font-serif);
  font-weight: 600;
  font-size: 18px;
  letter-spacing: 0.01em;
  line-height: 1.35;
  color: var(--kb-fg-2);
}

/* ── Hint ──────────────────────────────────────────────── */
.empty-state__hint {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--kb-fg-mute);
  max-width: 320px;
}

/* ── Action slot ───────────────────────────────────────── */
.empty-state__action {
  margin-top: 4px;
}

/* ── Compact density (sidebars / panels / drawers) ─────── */
.empty-state--compact {
  gap: 8px;
  padding: 22px 12px;
}

.empty-state--compact .empty-state__icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  font-size: 22px;
  margin-bottom: 0;
}

.empty-state--compact .empty-state__title {
  font-size: 14.5px;
}

.empty-state--compact .empty-state__hint {
  font-size: 12px;
  max-width: 260px;
}

.empty-state--compact .empty-state__action {
  margin-top: 2px;
}
</style>
