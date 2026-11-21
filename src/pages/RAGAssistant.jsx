import { useTranslation } from 'react-i18next'
import { useEffect, useRef, useState } from 'react'
import './RAGAssistant.css'

import { API_URL , apiFetch } from '../api'

const GENERAL_PROMPTS = [
  'How do osteosarcoma and Ewing sarcoma differ?',
  'What imaging modalities are used to assess a suspected bone tumour?',
  'What does a wide zone of transition mean in bone imaging?',
  'How are benign bone tumours different from malignant ones?',
]

export default function RAGAssistant({ selectedCase, modelAnalysis, initialCaseMode = false }) {
  const { t, i18n } = useTranslation()
  const [caseMode, setCaseMode] = useState(Boolean(initialCaseMode && selectedCase))
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [caseReports, setCaseReports] = useState([])
  const [caseReportsError, setCaseReportsError] = useState('')
  const [selectedReportId, setSelectedReportId] = useState('')
  const [includeReport, setIncludeReport] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    let active = true
    apiFetch(`${API_URL}/api/assistant/status`).then(async (response) => {
      const value = await response.json()
      if (active) setStatus(value)
    }).catch(() => { if (active) setStatus({ ready: false, generation_status: 'unavailable', indexed_chunks: null }) })
    return () => { active = false }
  }, [])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages, loading])

  useEffect(() => {
    setMessages([])
    setQuestion('')
    setSelectedReportId('')
    setIncludeReport(false)
    setError('')
    if (!selectedCase?.case_id) { setCaseReports([]); return undefined }
    let active = true
    apiFetch(`${API_URL}/api/reports?case_id=${encodeURIComponent(selectedCase.case_id)}`)
      .then(async (response) => {
        const result = await response.json().catch(() => ({}))
        if (!response.ok) throw new Error(result.detail || `Report service returned HTTP ${response.status}.`)
        if (active) { setCaseReports(result.reports || []); setCaseReportsError('') }
      })
      .catch((requestError) => {
        if (active) { setCaseReports([]); setCaseReportsError(requestError instanceof Error ? requestError.message : 'Could not load case-linked reports.') }
      })
    return () => { active = false }
  }, [selectedCase?.case_id])

  function switchMode(nextMode) {
    if (nextMode && !selectedCase) return
    setCaseMode(nextMode)
    setIncludeReport(false)
    setMessages([])
    setError('')
  }

  async function ask(event) {
    event.preventDefault()
    const text = question.trim()
    if (!text || loading) return
    setQuestion('')
    setError('')
    const userMessage = { role: 'user', content: text }
    const previous = messages
    setMessages((current) => [...current, userMessage])
    setLoading(true)
    try {
      const response = await apiFetch(`${API_URL}/api/assistant/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: text,
          language: i18n.language,
          case_id: caseMode ? selectedCase?.case_id : null,
          report_id: caseMode && includeReport ? selectedReportId || null : null,
          conversation: previous.slice(-6).map(({ role, content }) => ({ role, content })),
        }),
      })
      const result = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(result.detail || `Assistant returned HTTP ${response.status}.`)
      if (result.case_context?.case_id === selectedCase?.case_id) setCaseMode(true)
      setMessages((current) => [...current, {
        role: 'assistant', content: result.answer, citations: result.citations || [], status: result.status,
        notice: result.notice, method: result.method, included_report: result.included_report,
      }])
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not reach the local RAG assistant.')
    } finally {
      setLoading(false)
    }
  }

  const prompts = caseMode
    ? [
      t('Explain the available information for {{caseId}}.', {caseId:selectedCase?.case_id}),
      t('What does the source label tell us, and what does it not tell us?'),
      t('What does the Grad-CAM visualization mean for this case?'),
      t('What limitations matter when interpreting this model output?'),
    ]
    : GENERAL_PROMPTS.map(prompt => t(prompt))

  return <section className="rag-page">
    <div className="rag-heading">
      <div><div className="eyebrow">{t("EVIDENCE-LED MEDICAL RESEARCH")}</div><h1>{t("RAG AI Assistant")}</h1>
        <p>{t("Answers are generated from retrieved medical sources, with source references attached. The assistant does not interpret X-ray pixels.")}</p></div>
      <div>
        <div className={`rag-ready-state ${status?.ready ? 'ready' : ''}`}><i/>{status?.ready ? t("LOCAL RAG READY") : t("SETUP REQUIRED")}</div>
        {status?.ready && <small>{status.indexed_chunks}{' '}{t("indexed chunks ·")}{' '}{status.generation_model}</small>}
      </div>
    </div>

    <div className="rag-mode-bar">
      <div className="rag-mode-switch" role="group" aria-label={t("Question context")}>
        <button className={!caseMode ? 'selected' : ''} onClick={() => switchMode(false)}>{t("General research")}</button>
        <button className={caseMode ? 'selected' : ''} onClick={() => switchMode(true)} disabled={!selectedCase}>{t("Selected case")}</button>
      </div>
      {caseMode && selectedCase ? <div className="rag-case-indicator">
        <span>{t("CASE CONTEXT")}</span><b>{selectedCase.case_id}</b><span>{selectedCase.image_id}</span>
        <em>{t(selectedCase.classification)}{' '}{t("· source label")}</em>
        <em>{selectedCase.anatomical_location?.join(', ') || t("Anatomy unavailable")} · {selectedCase.metadata?.projection?.join(', ') || t("projection unavailable")}</em>
        {modelAnalysis && <em>{t("Model:")}{' '}{t(modelAnalysis.prediction)} · {modelAnalysis.model_version || t("version unavailable")}{' '}{t("· uncalibrated")}</em>}
        {modelAnalysis && <em>{t("Grad-CAM")}{' '}{modelAnalysis.gradcam_overlay_data_url ? t("available") : t("unavailable")}</em>}
        <small>{t("Structured case fields only unless you explicitly include a linked report · image pixels are never sent to the language model")}</small>
        {caseReportsError && <small className="rag-report-error" role="alert">{t("Case report list unavailable:")}{' '}{caseReportsError}</small>}
        {caseReports.length > 0 && <div className="rag-report-context"><label htmlFor="rag-report-select">{t("Optional user report")}</label><select id="rag-report-select" value={selectedReportId} onChange={(event) => { setSelectedReportId(event.target.value); setIncludeReport(false) }}><option value="">{t("Do not include a report")}</option>{caseReports.map((item) => <option key={item.report_id} value={item.report_id}>{item.filename} · {item.extraction_status}</option>)}</select><label className="rag-report-check"><input type="checkbox" checked={includeReport} disabled={!selectedReportId} onChange={(event) => setIncludeReport(event.target.checked)}/>{' '}{t("Include selected report text for this question")}</label><small>{t("Only extracted passages from the explicitly selected report are sent to the local model. The report is not added to medical literature citations.")}</small></div>}
      </div> : <div className="rag-general-indicator">{t("Literature sources only · no case selected")}</div>}
      <button className="rag-clear-button" onClick={() => { setMessages([]); setError('') }} disabled={!messages.length && !error}>{t("Clear conversation")}</button>
    </div>

    {!status?.ready && <div className="rag-setup-note" role="status">
      <b>{status?.generation_status === 'model_missing' ? t("Local language model not found.") : t("Local RAG setup is incomplete.")}</b>
      <span>{status?.indexed_chunks === 0 ? t("The source corpus has not been embedded into the local vector database.") : t("Install the optional RAG packages, ingest permitted sources, and configure a local Ollama model. No answers are generated until these components are ready.")}</span>
      <small>{t("Index status:")}{' '}{status?.indexed_chunks ?? t("not detected")}{' '}{t("chunks · Generator:")}{' '}{status?.generation_status || t("checking")}{' '}{t("· Embeddings:")}{' '}{status?.retrieval_dependencies || t("checking")}</small>
    </div>}

    <div className="rag-chat-frame">
      {!messages.length && <div className="rag-empty-state">
        <div className="rag-orbit"><span>{t("OL")}</span></div>
        <h2>{t("Ask a bone tumour research question")}</h2>
        <p>{t("The local system searches cited medical sources first. Answers may be withheld when it cannot retrieve enough evidence.")}</p>
        <div className="rag-prompt-grid">{prompts.map((prompt) => <button key={prompt} onClick={() => setQuestion(prompt)}>{prompt}<span>↗</span></button>)}</div>
      </div>}
      {messages.length > 0 && <div className="rag-message-list">
        {messages.map((message, index) => <article className={`rag-message ${message.role}`} key={`${index}-${message.role}`}>
          <div className="rag-message-byline"><b>{message.role === 'user' ? t('YOU') : t("OSTEOLENS RESEARCH ASSISTANT")}</b>{message.status === 'insufficient_evidence' && <span className="rag-insufficient-tag">{t("INSUFFICIENT EVIDENCE")}</span>}</div>
          <div className="rag-message-body">{message.content}</div>
          {message.citations?.length > 0 && <div className="rag-citations"><div className="eyebrow">{t("SOURCES USED")}</div>
            {message.citations.map((source) => source.source_type === 'uploaded_report' ? <div key={source.citation_id} className="rag-citation rag-uploaded-citation">
              <span className="rag-citation-id">{t("[RPT]")}</span><span><b>{source.title}</b><small>{t("User-provided report · cited report passages")}</small><em>{source.excerpt}</em></span>
            </div> : <a key={source.citation_id} href={source.url} target="_blank" rel="noreferrer" className="rag-citation">
              <span className="rag-citation-id">[{source.citation_id}]</span>
              <span><b>{source.title}</b><small>{source.author_or_institution}{source.publication_date ? ` · ${source.publication_date}` : ''} · {source.license}</small><em>“{source.excerpt}”</em></span>
              <span aria-hidden="true">↗</span>
            </a>)}
          </div>}
          {message.notice && <p className="rag-answer-notice">{t(message.notice)}</p>}
          {message.included_report && <p className="rag-answer-notice">{message.included_report.has_matching_passages ? t("This answer could use passages from {{v0}}, which you explicitly selected.", { v0: message.included_report.filename }) : t("You selected {{v0}}, but no matching report passage was found for this question.", { v0: message.included_report.filename })}</p>}
        </article>)}
        {loading && <div className="rag-loading" role="status"><i/><i/><i/>{' '}{t("Retrieving evidence and generating a cited response…")}</div>}
        <div ref={bottomRef}/>
      </div>}
    </div>

    {error && <div className="rag-error" role="alert"><b>{t("Assistant unavailable.")}</b> {t(error)}</div>}
    <form className="rag-composer" onSubmit={ask}>
      <textarea aria-label={t("Ask the RAG AI Assistant")} value={question} onChange={(event) => setQuestion(event.target.value)} maxLength={1200}
        onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit() } }}
        placeholder={caseMode ? t("Ask about {{v0}} and relevant literature…", { v0: selectedCase?.case_id }) : t("Ask about bone tumours, imaging, diagnosis, or research…")} />
      <button className="rag-send-button" type="submit" disabled={!question.trim() || loading || !status?.ready}>{loading ? t("Searching…") : t("Ask assistant")}</button>
      <small>{t("Enter to send · Shift+Enter for a new line · retrieved source content may be incomplete")}</small>
    </form>
    <p className="rag-disclaimer">{t("For academic research and education. Not medical advice, diagnosis, or treatment guidance. Confirm clinical information with qualified clinicians and the linked original sources.")}</p>
  </section>
}
