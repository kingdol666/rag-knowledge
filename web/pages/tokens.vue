<template>
  <div class="tokens-page">
    <h1>API Token 管理</h1>
    <p class="sub">每个 Token 可独立命名、设定有效期；明文仅在创建时显示一次。调用任意 API 时在请求头携带
      <code>Authorization: Bearer &lt;token&gt;</code>。</p>

    <div class="create-card">
      <h2>创建新 Token</h2>
      <div class="row">
        <input v-model="newName" placeholder="Token 名称，如：ci-robot / my-script" />
        <select v-model.number="newTtl">
          <option :value="1">1 天</option>
          <option :value="7">7 天</option>
          <option :value="30">30 天</option>
          <option :value="90">90 天</option>
          <option :value="365">1 年</option>
          <option :value="0">永不过期</option>
        </select>
        <button :disabled="!newName.trim() || busy" @click="create">创建</button>
      </div>
      <div v-if="freshToken" class="fresh">
        <strong>请立即复制（仅显示这一次）：</strong>
        <code>{{ freshToken }}</code>
      </div>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <table v-if="tokens.length">
      <thead>
        <tr><th>名称</th><th>前缀</th><th>创建时间</th><th>过期时间</th><th>最近使用</th><th>状态</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="t in tokens" :key="t.id">
          <td>{{ t.name }}</td>
          <td><code>{{ t.token_prefix }}…</code></td>
          <td>{{ fmt(t.created_at) }}</td>
          <td>{{ t.expires_at ? fmt(t.expires_at) : '永不过期' }}</td>
          <td>{{ t.last_used_at ? fmt(t.last_used_at) : '从未使用' }}</td>
          <td><span :class="status(t).cls">{{ status(t).label }}</span></td>
          <td><button v-if="!t.revoked_at" class="revoke" @click="revoke(t.id)">撤销</button></td>
        </tr>
      </tbody>
    </table>
    <p v-else class="empty">还没有 Token，创建一个开始调用 API。</p>
  </div>
</template>

<script setup lang="ts">
const { listTokens, createToken, revokeToken, logout } = useAuth()

const tokens = ref<any[]>([])
const newName = ref('')
const newTtl = ref(30)
const freshToken = ref('')
const busy = ref(false)
const error = ref('')

function fmt(iso: string) {
  try { return new Date(iso).toLocaleString() } catch { return iso }
}
function status(t: any) {
  if (t.revoked_at) return { label: '已撤销', cls: 'revoked' }
  if (t.expires_at && new Date(t.expires_at) < new Date()) return { label: '已过期', cls: 'expired' }
  return { label: '有效', cls: 'active' }
}

async function load() {
  try { tokens.value = await listTokens() }
  catch (e: any) { error.value = e?.data?.message || e?.message || '加载失败' }
}

async function create() {
  busy.value = true; error.value = ''; freshToken.value = ''
  try {
    const res: any = await createToken(newName.value.trim(), newTtl.value)
    freshToken.value = res.token
    newName.value = ''
    await load()
  } catch (e: any) {
    error.value = e?.data?.message || e?.message || '创建失败'
  } finally { busy.value = false }
}

async function revoke(id: string) {
  try { await revokeToken(id); await load() }
  catch (e: any) { error.value = e?.data?.message || e?.message || '撤销失败' }
}

onMounted(load)
</script>

<style scoped>
.tokens-page { max-width: 960px; margin: 0 auto; padding: 40px 24px; }
h1 { font-size: 22px; color: #0f172a; margin: 0 0 6px; }
.sub { color: #64748b; font-size: 13px; line-height: 1.6; }
code { background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
.create-card { margin: 24px 0; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; }
.create-card h2 { font-size: 15px; margin: 0 0 12px; }
.row { display: flex; gap: 10px; }
.row input { flex: 1; padding: 9px 12px; border: 1px solid #cbd5e1; border-radius: 8px; }
.row select { padding: 9px; border: 1px solid #cbd5e1; border-radius: 8px; }
.row button { padding: 9px 22px; border: none; border-radius: 8px; background: #4338ca; color: #fff; cursor: pointer; }
.fresh { margin-top: 14px; padding: 12px; border-radius: 8px; background: #ecfdf5; border: 1px solid #6ee7b7;
  font-size: 13px; word-break: break-all; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid #e2e8f0; }
th { color: #64748b; font-weight: 500; }
.active { color: #047857; } .expired { color: #b45309; } .revoked { color: #b91c1c; }
.revoke { padding: 4px 12px; border: 1px solid #fca5a5; background: #fff; color: #b91c1c;
  border-radius: 6px; cursor: pointer; }
.empty { color: #94a3b8; margin-top: 24px; }
.error { margin: 12px 0; padding: 10px; border-radius: 8px; background: #fee2e2; color: #b91c1c; font-size: 13px; }
</style>
