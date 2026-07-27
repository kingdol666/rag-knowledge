<template>
  <button
    class="theme-toggle-btn"
    @click="toggle"
    :title="theme === 'dark' ? $t('common.theme.light') : $t('common.theme.dark')"
    :aria-label="theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'"
  >
    <BulbFilled v-if="theme === 'light'" />
    <BulbOutlined v-else />
  </button>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { BulbFilled, BulbOutlined } from '@ant-design/icons-vue'

type Theme = 'dark' | 'light'
const STORAGE_KEY = 'kb-theme'

const theme = ref<Theme>('light')

function applyTheme(t: Theme) {
  if (process.client) {
    document.documentElement.setAttribute('data-theme', t)
  }
}

function toggle() {
  theme.value = theme.value === 'light' ? 'dark' : 'light'
}

onMounted(() => {
  let initial: Theme = 'light'
  if (process.client) {
    const saved = localStorage.getItem(STORAGE_KEY) as Theme | null
    if (saved === 'dark' || saved === 'light') {
      initial = saved
    }
  }
  theme.value = initial
  applyTheme(initial)
})

watch(theme, (t) => {
  applyTheme(t)
  if (process.client) {
    localStorage.setItem(STORAGE_KEY, t)
  }
})
</script>

<style scoped>
.theme-toggle-btn {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border-radius: 6px;
  border: 1px solid var(--kb-border);
  background: var(--kb-bg-subtle);
  color: var(--kb-gold-deep);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s var(--kb-ease);
}
.theme-toggle-btn:hover {
  background: var(--kb-gold-soft);
  border-color: var(--kb-gold);
  color: var(--kb-gold);
  transform: rotate(15deg);
}
.theme-toggle-btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px var(--kb-primary-glow);
}
</style>
