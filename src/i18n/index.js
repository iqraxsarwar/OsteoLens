import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './locales/en/common.json'
import tr from './locales/tr/common.json'

function savedLanguage() {
  try { return localStorage.getItem('osteolens-language') === 'tr' ? 'tr' : 'en' }
  catch { return 'en' }
}
i18n.use(initReactI18next).init({
  resources: { en: { common: en }, tr: { common: tr } },
  lng: savedLanguage(), fallbackLng: 'en', supportedLngs: ['en', 'tr'],
  ns: ['common'], defaultNS: 'common', keySeparator: false, nsSeparator: false,
  interpolation: { escapeValue: false },
})
function applyLanguage(language) {
  document.documentElement.lang = language
  document.title = language === 'tr' ? 'OsteoLens — Kemik görüntüleme araştırması' : 'OsteoLens — Bone imaging research'
  try { localStorage.setItem('osteolens-language', language) } catch { /* Storage can be disabled. */ }
}
i18n.on('languageChanged', applyLanguage)
applyLanguage(i18n.language)
export default i18n
