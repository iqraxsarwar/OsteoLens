import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import sources from '../data/openAccessReports.json'
import { API_URL, apiFetch } from '../api'
import './ReportAnalyzer.css'
import ResearchAssistant from './GuidedResearchAssistant'
import LocalReportPanel from './LocalReportPanel'

export default function PublishedReportAnalyzer({ onPrivacy }) {
  const { t, i18n } = useTranslation()
  const tr = i18n.language === 'tr'
  const [sourceId, setSourceId] = useState('')
  const [report, setReport] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(false)
  const [mode, setMode] = useState('published')
  async function analyze() {
    setBusy(true); setError(false); setReport(null)
    try {
      const response = await apiFetch(`${API_URL}/api/reports/examples/${encodeURIComponent(sourceId)}`, { method:'POST' })
      if (!response.ok) throw new Error('Example unavailable')
      setReport(await response.json())
    } catch { setError(true) } finally { setBusy(false) }
  }
  return <section className="report-page">
    <div className="eyebrow">{tr ? 'YAYIMLANMIŞ ARAŞTIRMA ÖRNEKLERİ' : 'PUBLISHED RESEARCH EXAMPLES'}</div>
    <h1>{t('Medical report analyser')}</h1>
    <div className="privacy-notice" role="note">
      <h2>{tr ? 'Yayımlanmış örnekler veya kendi raporunuz' : 'Published examples or your own report'}</h2>
      <p>{tr ? 'Yayımlanmış örneklerle RAG asistanına kendi sorunuzu sorabilirsiniz. Kendi belgenizi cihazda rapor modunda açın; kişisel rapor sunucuya yüklenmez.' : 'Ask the RAG assistant your own questions about published examples. Open your own document in on-device report mode; personal reports are not uploaded to the server.'}</p>
      <button className="secondary-button" onClick={onPrivacy}>{tr ? 'Gizlilik ve veri koruma' : 'Privacy and data protection'}</button>
    </div>
    <div className="rag-mode-switch" role="group" aria-label={tr ? 'Rapor modu' : 'Report mode'}><button className={mode==='published'?'selected':''} onClick={()=>setMode('published')}>{tr ? 'Yayımlanmış örnekler' : 'Published examples'}</button><button className={mode==='personal'?'selected':''} onClick={()=>setMode('personal')}>{tr ? 'Kendi raporum · cihazda' : 'My own report · on device'}</button></div>
    {mode==='personal' ? <LocalReportPanel/> : <><section className="report-saved-library">
      <h2>{t('Open-access case reports')}</h2>
      <p>{tr ? `${sources.length} yayımlanmış olgu özeti. Yalnızca seçilen kaynak kimliği sunucuya gönderilir; cihazınızdan dosya alınmaz. Örneğin analizi yeni bir kullanıcı raporu olarak kaydedilmez.` : `${sources.length} published case excerpts. Only the selected source identifier is sent to the server; no file is read from your device. Analysing an example does not create a saved user report.`}</p>
      <div className="report-source-controls">
        <select aria-label={t('Published case report')} value={sourceId} disabled={busy} onChange={e=>{setSourceId(e.target.value);setReport(null)}}>
          <option value="">{tr ? 'Yayımlanmış bir örnek seçin' : 'Select a published example'}</option>
          {sources.map(source=><option key={source.id} value={source.id}>{source.title}</option>)}
        </select>
        <button className="report-primary-button" disabled={!sourceId || busy} onClick={analyze}>{busy ? t('Reading report…') : t('Analyse published case')}</button>
        {report && <button className="report-secondary-button" onClick={()=>{setReport(null);setSourceId('')}}>{tr ? 'Ekrandaki analizi temizle' : 'Clear displayed analysis'}</button>}
      </div>
      {error && <p role="alert">{tr ? 'Örnek şu anda analiz edilemiyor. Lütfen daha sonra tekrar deneyin.' : 'This example could not be analysed. Please try again later.'}</p>}
    </section>
    {report && <div className="report-results-grid">
      <section className="report-panel">
        <h2>{report.source.title}</h2>
        <p>{report.source.author_or_institution} · {report.source.license}</p>
        <a href={report.source.url} target="_blank" rel="noreferrer">{t('Read original article')}</a>
        <h3>{t('Original extracted text')}</h3>
        <p>{t('Original source text and citations stay in their published language.')}</p>
        <pre className="published-source-text">{report.original_text}</pre>
      </section>
      <div className="report-side-column">
        <section className="report-panel"><h3>{t('Structured findings')}</h3>
          <p><b>{t('Anatomical location')}: </b>{report.extracted_findings.anatomical_location.join(', ') || t('Unavailable in report')}</p>
          <p><b>{t('Mentioned diagnosis / tumour terms')}: </b>{report.extracted_findings.mentioned_diagnosis_terms.join(', ') || t('Unavailable in report')}</p>
          <h3>{t('Summary')}</h3><p>{t('Extractive summary; each statement below is copied from the report.')}</p>
          {report.summary.statements.map((item,index)=><blockquote key={index}>{item.text}</blockquote>)}
        </section>
        <section className="report-panel"><h3>{t('Medical terminology')}</h3>
          {report.terminology.map(item=><div key={item.term}><b>{item.term}</b><p>{t(item.general_definition)}</p></div>)}
        </section>
      </div>
    </div>}
    {report && <ResearchAssistant key={report.source.id} source={report.source} onPrivacy={onPrivacy}/>}
    </>}
  </section>
}
