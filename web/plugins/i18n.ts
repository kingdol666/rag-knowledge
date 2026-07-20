import { createI18n } from 'vue-i18n'
import en from '~/locales/en.json'
import zh from '~/locales/zh.json'

export default defineNuxtPlugin((nuxtApp) => {
  // Detect stored preference or browser language
  const stored = process.client ? localStorage.getItem('kb-lang') : null
  const browserLang = process.client ? navigator.language?.split('-')[0] : null
  const defaultLocale = stored || (browserLang === 'zh' ? 'zh' : 'en')

  const i18n = createI18n({
    legacy: false,
    globalInjection: true,
    locale: defaultLocale,
    fallbackLocale: 'en',
    messages: { en, zh },
  })

  nuxtApp.vueApp.use(i18n)

  return {
    provide: {
      i18n,
    },
  }
})