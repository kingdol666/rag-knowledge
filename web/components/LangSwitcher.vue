<template>
  <a-dropdown :trigger="['click']" placement="bottomRight">
    <button class="lang-switcher-btn">
      <GlobalOutlined />
      <span>{{ locale === 'en' ? 'EN' : '中文' }}</span>
    </button>
    <template #overlay>
      <a-menu @click="handleSwitch">
        <a-menu-item key="en">
          <span :class="{ 'lang-active': locale === 'en' }">🇺🇸 English</span>
        </a-menu-item>
        <a-menu-item key="zh">
          <span :class="{ 'lang-active': locale === 'zh' }">🇨🇳 中文</span>
        </a-menu-item>
      </a-menu>
    </template>
  </a-dropdown>
</template>

<script setup lang="ts">
import { GlobalOutlined } from '@ant-design/icons-vue'
import { useI18n } from 'vue-i18n'

const { locale } = useI18n()

function handleSwitch({ key }: { key: string }) {
  locale.value = key
  if (process.client) {
    localStorage.setItem('kb-lang', key)
  }
}
</script>

<style scoped>
.lang-switcher-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 5px;
  border: 1px solid #d5c8b0;
  background: rgba(250,245,235,0.6);
  color: #8b775a;
  font-size: 11px;
  font-weight: 500;
  font-family: var(--kb-font);
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}
.lang-switcher-btn:hover {
  background: rgba(184,71,36,0.08);
  border-color: var(--kb-primary);
  color: var(--kb-primary);
}
.lang-active {
  font-weight: 700;
  color: var(--kb-primary);
}
</style>