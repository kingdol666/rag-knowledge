<template>
  <div class="login-wrap">
    <div class="login-card">
      <img src="/images/logo.svg" alt="logo" class="logo" onerror="this.style.display='none'" />
      <h1>{{ mode === 'login' ? '登录 RAG Knowledge' : '注册新用户' }}</h1>
      <p class="sub">{{ mode === 'login' ? '使用用户名与密码登录知识库平台' : '首个注册用户自动获得管理员角色' }}</p>

      <form @submit.prevent="submit">
        <label>用户名</label>
        <input v-model="username" type="text" autocomplete="username" required minlength="2" />

        <label>密码</label>
        <input v-model="password" type="password" autocomplete="current-password"
               required :minlength="mode === 'register' ? 8 : 1" />

        <label v-if="mode === 'register'">邮箱（可选）</label>
        <input v-if="mode === 'register'" v-model="email" type="email" autocomplete="email" />

        <div v-if="error" class="error">{{ error }}</div>

        <button type="submit" :disabled="busy">{{ busy ? '处理中…' : (mode === 'login' ? '登录' : '注册并登录') }}</button>
      </form>

      <div class="switch">
        <a v-if="mode === 'login'" @click.prevent="mode = 'register'" href="#">没有账号？注册</a>
        <a v-else @click.prevent="mode = 'login'" href="#">已有账号？登录</a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: false })

const route = useRoute()
const router = useRouter()
const { login, register, isLoggedIn } = useAuth()

const mode = ref<'login' | 'register'>(route.query.mode === 'register' ? 'register' : 'login')
const username = ref('')
const password = ref('')
const email = ref('')
const busy = ref(false)
const error = ref('')

if (isLoggedIn()) router.replace('/')

async function submit() {
  error.value = ''
  busy.value = true
  try {
    if (mode.value === 'login') {
      await login(username.value, password.value)
    } else {
      await register(username.value, password.value, email.value)
    }
    const redirect = (route.query.redirect as string) || '/'
    router.replace(redirect)
  } catch (e: any) {
    const data = e?.data || e?.response?._data
    error.value = data?.message || data?.detail?.message || e?.message || '请求失败'
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.login-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(160deg, #0f172a 0%, #1e293b 100%); }
.login-card { width: 380px; padding: 40px 36px; border-radius: 16px;
  background: #fff; box-shadow: 0 20px 60px rgba(0,0,0,.35); }
.logo { display:block; margin: 0 auto 12px; width: 56px; height: 56px; }
h1 { font-size: 20px; text-align: center; margin: 0 0 6px; color: #0f172a; }
.sub { font-size: 13px; color: #64748b; text-align: center; margin: 0 0 22px; }
label { display: block; font-size: 13px; color: #334155; margin: 12px 0 4px; }
input { width: 100%; box-sizing: border-box; padding: 10px 12px; border: 1px solid #cbd5e1;
  border-radius: 8px; font-size: 14px; outline: none; }
input:focus { border-color: #4338ca; box-shadow: 0 0 0 3px rgba(67,56,202,.12); }
button { width: 100%; margin-top: 20px; padding: 11px; border: none; border-radius: 8px;
  background: #4338ca; color: #fff; font-size: 15px; cursor: pointer; }
button:disabled { opacity: .6; cursor: default; }
.error { margin-top: 14px; padding: 10px; border-radius: 8px; background: #fee2e2;
  color: #b91c1c; font-size: 13px; }
.switch { margin-top: 18px; text-align: center; font-size: 13px; }
.switch a { color: #4338ca; cursor: pointer; text-decoration: none; }
</style>
