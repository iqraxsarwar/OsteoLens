import { useTranslation } from 'react-i18next'
import { useMemo, useRef, useState } from 'react'
import './App.css'
import PrivacyCenter from './pages/PrivacyCenter'
import LanguageSwitcher from './components/LanguageSwitcher'
import { caseRecords, datasetInfo, filterCases } from './data/caseLibrary'
import ImageViewer from './viewer/ImageViewer'
import ReportAnalyzer from './pages/PublishedReportAnalyzer'
import RAGAssistant from './pages/GuidedResearchAssistant'

import { API_URL as INFERENCE_API , apiFetch } from './api'

function Icon({ name, size = 18 }) {
  const icons = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
    book: <><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/></>,
    shield: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="m9 12 2 2 4-4"/></>,
    zoomin: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4M11 8v6m-3-3h6"/></>,
    zoomout: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4m-8-5h6"/></>,
    reset: <><path d="M3 12a9 9 0 1 0 2.64-6.36L3 8"/><path d="M3 3v5h5"/></>,
    external: <><path d="M14 3h7v7m-1-6-9 9"/><path d="M19 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h6"/></>,
    info: <><circle cx="12" cy="12" r="10"/><path d="M12 16v-4m0-4h.01"/></>,
    file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8m-8 4h8"/></>,
    spark: <><path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2L12 3Z"/><path d="m19 15 .8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15Z"/></>,
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{icons[name]}</svg>
}

const uniqueValues = (records, field) => [...new Set(records.flatMap((record) => record[field]))].sort()
const anatomyNames = { 'Hip Bone': 'Hip bone', 'Upper Limb': 'Upper limb', 'Lower Limb': 'Lower limb' }


export default function App() {
  const { t, i18n } = useTranslation()
  const pretty = (value) => t(anatomyNames[value] || value)
  const [selected, setSelected] = useState(caseRecords[0])
  const [query, setQuery] = useState('')
  const [classification, setClassification] = useState('All classes')
  const [anatomy, setAnatomy] = useState('All locations')
  const [source, setSource] = useState('All sources')
  const [section, setSection] = useState('Case library')
  const [assistantCaseMode, setAssistantCaseMode] = useState(false)
  const [analysis, setAnalysis] = useState(null)
  const [analysisState, setAnalysisState] = useState('idle')
  const [analysisError, setAnalysisError] = useState('')
  const analysisRequest = useRef(0)
  const visibleCases = useMemo(() => filterCases(caseRecords, { query, classification, anatomy, source }), [query, classification, anatomy, source])
  const anatomyOptions = uniqueValues(caseRecords, 'anatomical_location')
  const classCounts = caseRecords.reduce((counts, record) => ({ ...counts, [record.classification]: (counts[record.classification] || 0) + 1 }), {})

  function selectCase(record) {
    analysisRequest.current += 1
    setSelected(record)
    setAnalysis(null)
    setAnalysisState('idle')
    setAnalysisError('')
    setSection('Case library')
  }

  function openAssistant(withSelectedCase) {
    setAssistantCaseMode(Boolean(withSelectedCase))
    setSection('RAG AI Assistant')
  }

  function openReport() { setSection('Report analyser') }

  async function analyzeSelectedCase() {
    const requestId = ++analysisRequest.current
    const caseId = selected.case_id
    setAnalysis(null)
    setAnalysisState('loading')
    setAnalysisError('')
    try {
      const response = await apiFetch(`${INFERENCE_API}/api/analyze/${encodeURIComponent(caseId)}`, { method: 'POST' })
      const result = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(result.detail || `Inference API returned HTTP ${response.status}.`)
      if (requestId !== analysisRequest.current) return
      setAnalysis(result)
      setAnalysisState('complete')
    } catch (error) {
      if (requestId !== analysisRequest.current) return
      setAnalysisError(error instanceof Error ? error.message : 'Could not connect to the OsteoLens inference API.')
      setAnalysisState('error')
    }
  }

  const resultLabel = (record) => record.source_subtype || t('{{label}} bone', {label: t(record.classification)})

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><span/><span/><span/><span/></div><div><strong>{t("OsteoLens")}</strong><small>{t("RESEARCH WORKSPACE")}</small></div></div>
      <div className="workspace-label">{t("WORKSPACE")}</div>
      <nav>
        <button className={`nav-item ${section === 'Case library' ? 'active' : ''}`} onClick={() => setSection('Case library')}><Icon name="grid"/><span>{t("Case library")}</span><b>{caseRecords.length}</b></button>
        <button className={`nav-item ${section === 'Dataset information' ? 'active' : ''}`} onClick={() => setSection('Dataset information')}><Icon name="book"/><span>{t("Dataset information")}</span></button>
        <button className={`nav-item ${section === 'Report analyser' ? 'active' : ''}`} onClick={() => openReport()}><Icon name="file"/><span>{t("Report analyser")}</span></button>
        <button className={`nav-item ${section === 'RAG AI Assistant' ? 'active' : ''}`} onClick={() => openAssistant(false)}><Icon name="spark"/><span>{t("RAG AI Assistant")}</span></button>
      </nav>
      <div className="side-rule"/>
      <div className="workspace-label">{t("DATA SOURCE")}</div>
      <div className="library-link"><span className="library-dot"/>{t("BTXRD")}{' '}<span>{caseRecords.length}</span></div>
      <div className="sidebar-bottom"><div className="advisor"><div className="avatar">{t("OL")}</div><div><b>{t("OsteoLens")}</b><small>{t("Academic research prototype")}</small></div></div><p><Icon name="shield" size={14}/>{' '}{t("Educational use only")}</p></div>
    </aside>

    <main className="main-area">
      <header className="topbar"><div className="breadcrumbs">{t("Workspace")}{' '}<span>/</span> {t(section)}</div><div className="top-actions"><LanguageSwitcher/><span className="status-live"><i/>{' '}{t("DATASET CONNECTED")}</span><div className="top-avatar">{t("OL")}</div></div></header>
      <div className="privacy-banner"><span>{i18n.language === 'tr' ? 'Araştırma demosu · Kişisel raporlar cihazınızda kalır' : 'Research demo · Personal reports stay on your device'}</span><button onClick={() => setSection('Privacy')}>{i18n.language === 'tr' ? 'Gizlilik ve veri koruma' : 'Privacy and data protection'}</button></div>
      {section === 'Privacy' ? <PrivacyCenter/> : section === 'Case library' ? <>
        <section className="page-heading"><div><div className="eyebrow">{t("BONE IMAGING, UNDERSTOOD.")}</div><h1>{t("Case library")}</h1><p>{t("Browse source-labelled BTXRD radiograph records. Select a case to load its original image and metadata.")}</p></div><div className="page-heading-actions"><button className="secondary-button" onClick={() => openAssistant(false)}><Icon name="spark" size={14}/>{' '}{t("Research assistant")}</button><a className="primary-button" href={datasetInfo.source_url} target="_blank" rel="noreferrer"><Icon name="external" size={15}/>{' '}{t("Dataset source")}</a></div></section>
        <section className="metrics">
          <div className="metric"><span>{t("SOURCE IMAGE RECORDS")}</span><b>{caseRecords.length}</b><small>{caseRecords.length}{' '}{t("selected samples")}</small></div>
          <div className="metric"><span>{t("NORMAL LABELS")}</span><b>{classCounts.Normal || 0}</b><small>{t("BTXRD metadata")}</small></div>
          <div className="metric"><span>{t("TUMOUR LABELS")}</span><b>{(classCounts.Benign || 0) + (classCounts.Malignant || 0)}</b><small>{t("Benign + malignant")}</small></div>
          <div className="metric metric-note"><span><Icon name="shield" size={14}/>{' '}{t("PROVENANCE")}</span><b>{t("BTXRD · CC BY 4.0")}</b><small>{t("Source citation attached to every record")}</small></div>
        </section>

        <div className="work-layout">
          <section className="case-panel">
            <div className="panel-heading"><div><h2>{t("Sample cases")}</h2><span>{t("Source labels · distinct image checksums")}</span></div></div>
            <div className="search-row">
              <div className="searchbox"><Icon name="search" size={17}/><input aria-label={t("Search cases")} placeholder={t("Search ID, label or anatomy…")} value={query} onChange={(event) => setQuery(event.target.value)}/></div>
              <select aria-label={t("Filter by classification")} value={classification} onChange={(event) => setClassification(event.target.value)}><option value="All classes">{t("All classes")}</option>{['Normal', 'Benign', 'Malignant'].map((item) => <option key={item} value={item}>{t(item)}</option>)}</select>
              <select aria-label={t("Filter by anatomy")} value={anatomy} onChange={(event) => setAnatomy(event.target.value)}><option value="All locations">{t("All locations")}</option>{anatomyOptions.map((item) => <option key={item} value={item}>{pretty(item)}</option>)}</select>
              <select aria-label={t("Filter by source")} value={source} onChange={(event) => setSource(event.target.value)}><option value="All sources">{t("All sources")}</option>{uniqueValues(caseRecords, 'dataset_source').map((item) => <option key={item} value={item}>{t(item)}</option>)}</select>
            </div>
            <div className="table-wrap"><table><thead><tr><th>{t("CASE ID")}</th><th>{t("ANATOMY / VIEW")}</th><th>{t("BTXRD SOURCE LABEL")}</th><th>{t("CENTER")}</th></tr></thead><tbody>
              {visibleCases.map((record) => <tr key={record.case_id} className={selected.case_id === record.case_id ? 'selected-row' : ''} onClick={() => selectCase(record)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') selectCase(record) }} tabIndex={0} aria-selected={selected.case_id === record.case_id}>
                <td><b className="mono">{record.case_id}</b><small>{record.image_id}</small></td>
                <td><b>{record.anatomical_location.map(pretty).join(', ')}</b><small>{record.metadata.projection.map(pretty).join(', ') || t("Projection unavailable")}</small></td>
                <td><span className={`finding ${record.classification.toLowerCase()}`}><i/>{resultLabel(record)}</span><small>{t(record.classification)}{' '}{t("class")}</small></td>
                <td><span className="center-label">{t("Center")}{' '}{record.metadata.collection_center}</span></td>
              </tr>)}
            </tbody></table>{visibleCases.length === 0 && <div className="empty-state">{t("No source records match these filters.")}</div>}</div>
            <div className="table-footer"><span>{t('Showing {{shown}} of {{total}} source image records', {shown: visibleCases.length,total:caseRecords.length})}</span><span>{t("Clinical narrative unavailable in BTXRD metadata")}</span></div>
          </section>

          <section className="detail-panel">
            <div className="detail-top"><div><span className="mono case-code">{selected.case_id}</span><span className={`class-pill ${selected.classification.toLowerCase()}`}>{t(selected.classification)}</span></div><a className="icon-button" href={selected.source_url} target="_blank" rel="noreferrer" aria-label={t("Open source dataset")}><Icon name="external" size={15}/></a></div>
            <h2>{selected.source_subtype || t("{{v0}} bone image", { v0: t(selected.classification) })}</h2>
            <div className="detail-meta">{t("BTXRD")}{' '}<i/> {selected.image_id} <i/> {selected.metadata.projection.map(pretty).join(', ') || t("Projection unavailable")}</div>
            <ImageViewer key={`${selected.case_id}:${selected.image_path}`} record={selected} analysis={analysis} analysisState={analysisState} analysisError={analysisError} onRunAnalysis={analyzeSelectedCase} />
            <button className="secondary-button case-assistant-action" onClick={() => openAssistant(true)}><Icon name="spark" size={14}/>{' '}{t("Ask the research assistant about this case")}</button>
            <div className="record-card">
              <div className="record-heading"><div><div className="eyebrow">{t("SOURCE-PROVIDED RECORD")}</div><h3>{t(selected.classification)}{selected.source_subtype ? ` · ${selected.source_subtype}` : ''}</h3></div></div>
              <div className="record-grid"><div><span>{t("ANATOMICAL LOCATION")}</span><b>{selected.anatomical_location.map(pretty).join(', ') || t("Unavailable")}</b></div><div><span>{t("PROJECTION")}</span><b>{selected.metadata.projection.map(pretty).join(', ') || t("Unavailable")}</b></div><div><span>{t("AGE / SEX (SOURCE)")}</span><b>{selected.metadata.age_years} / {t(selected.metadata.sex)}</b></div><div><span>{t("COLLECTION CENTER")}</span><b>{selected.metadata.collection_center}</b></div></div>
              <div className="description-missing"><Icon name="info" size={15}/><span><b>{t("Clinical description unavailable.")}</b>{' '}{t("BTXRD provides structured labels and metadata for this record, not a free-text case narrative.")}</span></div>
              <a className="source-citation" href={selected.source_url} target="_blank" rel="noreferrer">{selected.source_citation} <Icon name="external" size={13}/></a>
              <p className="privacy-notice">{i18n.language === 'tr' ? 'Kişisel rapor yükleme ve olguya bağlama kapalıdır. Rapor analiz aracında yayımlanmış örnekleri inceleyebilirsiniz.' : 'Personal report uploads and case association are disabled. Published examples are available in the report analyser.'}</p>
            </div>
          </section>
        </div>
        <div className="phase-note"><Icon name="shield" size={14}/><span>{t("Research output only. Source labels are separate from model predictions. Grad-CAM indicates image regions influencing a prediction; it is not a tumour boundary or diagnosis. Lesion localization is unavailable.")}</span><a href={selected.license_url} target="_blank" rel="noreferrer">{t("CC BY 4.0")}</a></div>
      </> : section === 'Dataset information' ? <section className="placeholder-page"><div className="eyebrow">{t("DATA PROVENANCE")}</div><h1>{t("Dataset information")}</h1><p>{t("Source details and limitations for the current sample library.")}</p><div className="placeholder-card"><div className="assistant-icon"><Icon name="book"/></div><h2>{datasetInfo.name}</h2><p>{datasetInfo.citation}</p><p><b>{t("License:")}</b> <a href={datasetInfo.license_url} target="_blank" rel="noreferrer">{datasetInfo.license}</a></p><p><b>{t("Sample:")}</b> {caseRecords.length}{' '}{t("real source image records, selected evenly across the dataset’s Normal, Benign, and Malignant labels. Original image IDs and SHA-256 checksums are included in the manifest.")}</p><p><b>{t("Clinical text:")}</b>{' '}{t("BTXRD provides structured metadata but no free-text case description in the included source file. No narrative has been added or inferred.")}</p><p><b>{t("Patient linkage:")}</b>{' '}{t("The dataset record does not expose a verified patient-level identifier here. The")}{' '}{caseRecords.length}{' '}{t("records have distinct image checksums. Patient-level uniqueness is unverified.")}</p><p><b>{t("Full source archive:")}</b> {datasetInfo.archive}{t("; archive MD5")}{' '}{datasetInfo.archive_md5}.</p><a className="secondary-button" href={datasetInfo.source_url} target="_blank" rel="noreferrer">{t("Open BTXRD on Figshare")}{' '}<Icon name="external" size={14}/></a></div></section> : section === 'Report analyser' ? <ReportAnalyzer onPrivacy={() => setSection('Privacy')} /> : <RAGAssistant onPrivacy={() => setSection('Privacy')} selectedCase={selected} modelAnalysis={analysisState === 'complete' ? analysis : null} initialCaseMode={assistantCaseMode}/ >}
      <footer className="footer"><span>{t("OSTEOLENS")}{' '}<i>·</i>{' '}{t("RESEARCH PROTOTYPE")}</span><span>{t("Bone imaging, understood.")}</span><span>{section === 'Report analyser' ? t("Phase 5 · Report analyser") : section === 'RAG AI Assistant' ? t("Phase 6 · Evidence-grounded research") : t("Phase 4 · Research image analysis")}</span></footer>
    </main>
  </div>
}
