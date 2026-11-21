import { useTranslation } from 'react-i18next'
export default function LanguageSwitcher() {
  const { t, i18n } = useTranslation()
  return <div className="language-switch" role="group" aria-label={t('Interface language')}>
    <button type="button" lang="en" aria-pressed={i18n.resolvedLanguage === 'en'} onClick={() => i18n.changeLanguage('en')}>English</button>
    <button type="button" lang="tr" aria-pressed={i18n.resolvedLanguage === 'tr'} onClick={() => i18n.changeLanguage('tr')}>Türkçe</button>
  </div>
}
