<template>
  <span
    class="agent-status-light"
    :class="`size-${size}`"
    role="status"
    :aria-label="label || status"
  >
    <span
      class="lamp"
      :class="[`lamp-${status}`, { running: status === 'running' && pulse }]"
    />
    <span v-if="label" class="lamp-label">{{ label }}</span>
  </span>
</template>

<script setup lang="ts">
interface Props {
  status: 'idle' | 'running' | 'done' | 'error'
  size?: 'small' | 'medium' | 'large'
  label?: string
  /** Show a soft pulsing ring while status === 'running' */
  pulse?: boolean
}

withDefaults(defineProps<Props>(), {
  size: 'medium',
  label: undefined,
  pulse: true,
})
</script>

<style scoped>
.agent-status-light {
  display: inline-flex;
  align-items: center;
  line-height: 1;
  vertical-align: middle;
}

/* ── The lamp dot ───────────────────────────────────────── */
.lamp {
  position: relative;
  display: inline-block;
  border-radius: 50%;
  flex-shrink: 0;
}

/* ── Sizes (small=8 / medium=12 / large=16 px diameter) ── */
.size-small .lamp { width: 8px; height: 8px; }
.size-medium .lamp { width: 12px; height: 12px; }
.size-large .lamp { width: 16px; height: 16px; }

/* ── Status colors ─────────────────────────────────────── */
.lamp-idle {
  background: #9ca3af;
}

.lamp-running {
  background: var(--kb-emerald, #10b981);
}

.lamp-done {
  background: var(--kb-emerald, #10b981);
}

.lamp-error {
  background: #ef4444;
  box-shadow: 0 0 6px rgba(239, 68, 68, 0.5);
}

/* ── Pulsing halo (only when running + pulse enabled) ──── */
.lamp.running::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: var(--kb-emerald, #10b981);
  animation: lamp-pulse 1.4s ease-in-out infinite;
  pointer-events: none;
}

@keyframes lamp-pulse {
  0% { transform: scale(1); opacity: 0.6; }
  100% { transform: scale(1.8); opacity: 0; }
}

/* ── Label ─────────────────────────────────────────────── */
.lamp-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--kb-fg, inherit);
  margin-left: 6px;
  white-space: nowrap;
}

/* ── Respect reduced-motion preference ─────────────────── */
@media (prefers-reduced-motion: reduce) {
  .lamp.running::after {
    animation: none;
  }
}
</style>
