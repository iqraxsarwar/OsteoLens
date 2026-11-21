import { useTranslation } from 'react-i18next'
import { useCallback, useEffect, useRef, useState } from 'react'
import './ReportAnalyzer.css'
import { caseRecords } from '../data/caseLibrary'

import { API_URL , apiFetch } from '../api'
import openAccessReports from '../data/openAccessReports.json'

function HighlightedText({ text, phrases }) {
  const usable = [...new Set((phrases || []).filter((phrase) => phrase && phrase.length > 1))]
    .sort((left, right) => right.length - left.length)
  if (!usable.length) return text
  const expression = new RegExp(`(${usable.map((phrase) => phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi')
  return text.split(expression).map((part, index) => (
    usable.some((phrase) => phrase.toLowerCase() === part.toLowerCase())
      ? <mark key={`${part}-${index}`}>{part}</mark>
      : <span key={`${index}-${part.slice(0, 8)}`}>{part}</span>
  ))
}

function SourceSentences({ items, emptyText }) {
  const { t } = useTranslation()
  if (!items?.length) return <p className="report-empty-note">{emptyText}</p>
  return <ul className="report-source-list">{items.map((item, index) => (
    <li key={`${item.page_number}-${index}`}>
      <blockquote>“{item.text}”</blockquote>
      {item.page_number && <small>{t("Source · page")}{' '}{item.page_number}</small>}
    </li>
  ))}</ul>
}

export default function ReportAnalyzer({ initialReportId = null, initialCaseId = '' }) {
  const { t, i18n } = useTranslation()
  const inputRef = useRef(null)
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')
  const [report, setReport] = useState(null)
  const [question, setQuestion] = useState('')
  const [qaStatus, setQaStatus] = useState('idle')
  const [qaError, setQaError] = useState('')
  const [answers, setAnswers] = useState([])
  const [selectedCaseId, setSelectedCaseId] = useState(initialCaseId || '')
  const [savedReports, setSavedReports] = useState([])
  const [savedReportsStatus, setSavedReportsStatus] = useState('loading')
  const [savedReportsError, setSavedReportsError] = useState('')
  const [sourceQuery, setSourceQuery] = useState('')
  const [sourceId, setSourceId] = useState('')
  const sourceReport = openAccessReports.find((item) => item.id === sourceId)
  const matchingSources = openAccessReports.filter((item) =>
    (item.title + ' ' + item.topic + ' ' + item.id).toLowerCase().includes(sourceQuery.toLowerCase()))

  async function analyzeSource() {
    if (!sourceReport) return
    setStatus('loading')
    setError('')
    try {
      const response = await apiFetch(sourceReport.path)
      if (!response.ok) throw new Error('The source excerpt could not be loaded.')
      const sourceFile = new File([await response.text()], sourceReport.id + '.txt', { type: 'text/plain' })
      setFile(sourceFile)
      setSelectedCaseId('')
      await analyze(null, sourceFile, '')
    } catch (requestError) {
      setStatus('error')
      setError(requestError.message)
    }
  }

  const refreshSavedReports = useCallback(async () => {
    setSavedReportsStatus('loading')
    try {
      const response = await apiFetch(`${API_URL}/api/reports`)
      const result = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(result.detail || `Report store returned HTTP ${response.status}.`)
      setSavedReports(result.reports || [])
      setSavedReportsError('')
      setSavedReportsStatus('complete')
    } catch (requestError) {
      setSavedReports([])
      setSavedReportsError(requestError instanceof Error ? requestError.message : 'Could not load saved reports.')
      setSavedReportsStatus('error')
    }
  }, [])

  useEffect(() => { refreshSavedReports() }, [refreshSavedReports])

  useEffect(() => {
    if (!initialReportId) return
    let active = true
    setStatus('loading')
    apiFetch(`${API_URL}/api/reports/item/${encodeURIComponent(initialReportId)}`)
      .then(async (response) => {
        const result = await response.json().catch(() => ({}))
        if (!response.ok) throw new Error(result.detail || `Report service returned HTTP ${response.status}.`)
        if (!active) return
        setReport(result)
        setSelectedCaseId(result.persistence?.case_id || '')
        setFile(null)
        setAnswers([])
        setStatus('complete')
      })
      .catch((requestError) => {
        if (!active) return
        setStatus('error')
        setError(requestError instanceof Error ? requestError.message : 'Could not reopen this saved report.')
      })
    return () => { active = false }
  }, [initialReportId])

  function chooseFile(candidate) {
    setError('')
    setReport(null)
    setAnswers([])
    setQuestion('')
    setQaStatus('idle')
    if (!candidate) { setFile(null); setStatus('idle'); return }
    const extension = candidate.name.split('.').pop()?.toLowerCase()
    if (!['pdf', 'txt'].includes(extension)) {
      setFile(null)
      setStatus('error')
      setError('Choose a PDF or TXT report.')
      return
    }
    if (candidate.size === 0) {
      setFile(null)
      setStatus('error')
      setError('This file is empty. Upload a readable report.')
      return
    }
    if (candidate.size > 20 * 1024 * 1024) {
      setFile(null)
      setStatus('error')
      setError('The file exceeds the 20 MB upload limit.')
      return
    }
    setFile(candidate)
    setStatus('idle')
  }

  async function analyze(event, candidate = file, association = selectedCaseId) {
    event?.preventDefault()
    if (!candidate) return
    setStatus('loading')
    setError('')
    setReport(null)
    setAnswers([])
    const body = new FormData()
    body.append('file', candidate)
    if (association) body.append('case_id', association)
    try {
      const response = await apiFetch(`${API_URL}/api/reports/analyze`, { method: 'POST', body })
      const result = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(result.detail || `Report service returned HTTP ${response.status}.`)
      if (!result.original_text?.trim()) throw new Error('The service returned no extracted report text. No analysis was shown.')
      setReport(result)
      setStatus('complete')
      await refreshSavedReports()
    } catch (requestError) {
      setStatus('error')
      setError(requestError instanceof Error ? requestError.message : 'Could not connect to the report service.')
    }
  }

  async function updateAssociation(caseId) {
    if (!report?.report_id) return
    setError('')
    try {
      const response = await apiFetch(`${API_URL}/api/reports/${encodeURIComponent(report.report_id)}/association`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ case_id: caseId || null }),
      })
      const result = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(result.detail || `Association update returned HTTP ${response.status}.`)
      setSelectedCaseId(result.case_id || '')
      setReport((current) => ({ ...current, persistence: { ...current.persistence, ...result } }))
      await refreshSavedReports()
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not update the report association.')
    }
  }

  async function openSavedReport(reportId) {
    setStatus('loading')
    setError('')
    setAnswers([])
    try {
      const response = await apiFetch(`${API_URL}/api/reports/item/${encodeURIComponent(reportId)}`)
      const result = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(result.detail || `Report service returned HTTP ${response.status}.`)
      setReport(result)
      setSelectedCaseId(result.persistence?.case_id || '')
      setFile(null)
      setStatus('complete')
    } catch (requestError) {
      setStatus('error')
      setError(requestError instanceof Error ? requestError.message : 'Could not reopen this saved report.')
    }
  }

  async function deleteSavedReport() {
    if (!report?.report_id || !window.confirm(t('Delete {{filename}} and its saved extracted text from the application server?', {filename:report.document.filename}))) return
    setError('')
    try {
      const response = await apiFetch(`${API_URL}/api/reports/${encodeURIComponent(report.report_id)}`, { method: 'DELETE' })
      const result = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(result.detail || `Delete returned HTTP ${response.status}.`)
      setReport(null)
      setAnswers([])
      setStatus('idle')
      await refreshSavedReports()
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not delete this saved report.')
    }
  }

  async function askQuestion(event) {
    event.preventDefault()
    if (!report || !question.trim()) return
    setQaStatus('loading')
    setQaError('')
    try {
      const response = await apiFetch(`${API_URL}/api/reports/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: report.report_id, question, language:i18n.language }),
      })
      const result = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(result.detail || `Question service returned HTTP ${response.status}.`)
      setAnswers((current) => [...current, result])
      setQuestion('')
      setQaStatus('complete')
    } catch (requestError) {
      setQaStatus('error')
      setQaError(requestError instanceof Error ? requestError.message : 'Could not answer this question.')
    }
  }

  const findings = report?.extracted_findings

  return <section className="report-page">
    <div className="report-page-heading">
      <div><div className="eyebrow">{t("DOCUMENT REVIEW · SOURCE-GROUNDED")}</div><h1>{t("Medical report analyser")}</h1>
        <p>{t("Read a PDF or TXT report, inspect the extracted text, and explore only information present in that document.")}</p></div>
      <span className="report-local-badge"><i/>{' '}{t("PROCESSED LOCALLY")}</span>
    </div>

    <div className="report-disclaimer"><b>{t("Research tool.")}</b>{' '}{t("Original report statements stay separate from generated structure and general terminology explanations. This is not a diagnosis. Reports are stored locally on this computer; use de-identified test documents only.")}</div>

    <section className="report-saved-library" aria-label={t("Locally saved reports")}><div className="report-saved-heading"><div><div className="eyebrow">{t("LOCAL REPORT STORE")}</div><h2>{t("Saved uploads")}</h2></div><span>{savedReportsStatus === 'loading' ? t("Loading…") : t("{{v0}} reports", { v0: savedReports.length })}</span></div>
      {savedReportsError && <div className="report-error" role="alert">{savedReportsError}</div>}
      {!savedReportsError && savedReports.length === 0 && savedReportsStatus === 'complete' && <p>{t("No saved reports yet. An upload is kept locally after successful text extraction.")}</p>}
      <div className="report-saved-list">{savedReports.map((item) => <button type="button" key={item.report_id} onClick={() => openSavedReport(item.report_id)} className={`report-saved-item ${report?.report_id === item.report_id ? 'selected' : ''}`}><b>{item.filename}</b><span>{item.case_id || t("Unassociated")} · {new Date(item.uploaded_at).toLocaleString(i18n.language === 'tr' ? 'tr-TR' : 'en-GB')}</span><small>{item.extraction_status}</small></button>)}</div>
    </section>

    <section className="report-saved-library" aria-label={t("Open-access case reports")}>
      <h2>{t("Open-access case reports")}</h2>
      <p>{openAccessReports.length}{' '}{t("published case reports · CC BY 4.0. Select a case section to analyse its published text. Each excerpt includes authorship, source link and licence.")}</p>
      <div className="report-source-controls">
        <input aria-label={t("Search published cases")} placeholder={t("Search title, tumour type or PMC ID")} value={sourceQuery}
          onChange={(event) => { setSourceQuery(event.target.value); setSourceId('') }}/>
        <select aria-label={t("Published case report")} value={sourceId} onChange={(event) => setSourceId(event.target.value)}>
          <option value="">{t("Select a published case report (")}{matchingSources.length})</option>
          {matchingSources.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
        </select>
        <button type="button" className="report-primary-button" disabled={!sourceReport || status === 'loading'} onClick={analyzeSource}>{t("Analyse published case")}</button>
      </div>
      {sourceReport && <p>{sourceReport.author_or_institution} · {sourceReport.publication_date} · <a href={sourceReport.url} target="_blank" rel="noreferrer">{t("Read original article")}</a> · <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noreferrer">{t("CC BY 4.0")}</a></p>}
      <p>{t("Published cases and BTXRD radiographs have independent provenance. Associate an uploaded report with an X-ray only when you have verified the relationship.")}</p>
    </section>

    <form className="report-upload" onSubmit={analyze}>
      <input ref={inputRef} type="file" accept=".pdf,.txt,application/pdf,text/plain" hidden onChange={(event) => chooseFile(event.target.files?.[0])}/>
      <div className={`report-dropzone ${dragging ? 'dragging' : ''}`} onDragOver={(event) => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); chooseFile(event.dataTransfer.files?.[0]) }}>
        <div className="report-upload-symbol">{t("PDF")}</div>
        <div className="report-upload-copy"><b>{file ? file.name : t("Add a medical report")}</b><span>{file ? `${(file.size / 1024).toFixed(0)} KB · ${file.name.split('.').pop().toUpperCase()}` : t("PDF or TXT · 20 MB maximum · successful uploads are stored locally")}</span></div>
        <button type="button" className="report-secondary-button" onClick={() => inputRef.current?.click()}>{file ? t("Replace file") : t("Choose file")}</button>
      </div>
      <div className="report-association-row"><label htmlFor="report-case-association">{t("Explicitly associate this report with a Case ID")}{' '}<span>{t("(optional; no patient match is inferred)")}</span></label><select id="report-case-association" value={report ? (report.persistence?.case_id || '') : selectedCaseId} onChange={(event) => report?.persistence?.stored_locally ? updateAssociation(event.target.value) : setSelectedCaseId(event.target.value)}><option value="">{t("Do not associate with a case")}</option>{caseRecords.map((record) => <option key={record.case_id} value={record.case_id}>{record.case_id} · {record.image_id} · {t(record.classification)}</option>)}</select></div>
      {error && <div className="report-error" role="alert"><b>{t("Could not process this report.")}</b> {t(error)}</div>}
      <div className="report-upload-footer"><span>{t("PDF text extraction · optional OCR for scanned pages when Tesseract is installed")}</span><button className="report-primary-button" type="submit" disabled={!file || status === 'loading'}>{status === 'loading' ? t("Reading report…") : t("Analyse report")}</button></div>
      {status === 'loading' && <div className="report-progress" role="status">{t("Extracting text and identifying source passages…")}</div>}
    </form>

    {report && <>
      <div className="report-results-heading"><div><div className="eyebrow">{t("ANALYSIS RESULT")}</div><h2>{report.document.filename}</h2></div><div className="report-meta-tags"><span>{report.document.format}</span><span>{report.document.page_count} {report.document.page_count === 1 ? t("page") : t("pages")}</span><span>{t(report.document.extraction_method)}</span><span>{t("OCR ·")}{' '}{t(report.document.ocr_status)}</span></div></div>
      <div className="report-persistence-bar"><span>{t("Case association:")}{' '}<b>{report.persistence?.case_id || t("None")}</b></span><span>{t("Uploaded:")}{' '}{report.persistence?.uploaded_at ? new Date(report.persistence.uploaded_at).toLocaleString(i18n.language === 'tr' ? 'tr-TR' : 'en-GB') : t("Unavailable")}</span><span>{t("Extraction:")}{' '}{report.persistence?.extraction_status || report.document.extraction_method}</span><button type="button" className="report-delete-button" onClick={deleteSavedReport}>{t("Delete saved report")}</button></div>
      {report.document.warnings?.length > 0 && <div className="report-warning">{report.document.warnings.map((warning) => <p key={warning}>{warning}</p>)}</div>}

      <div className="report-results-grid">
        <section className="report-panel report-original-panel">
          <div className="report-panel-title"><div><div className="eyebrow">{t("SOURCE DOCUMENT")}</div><h3>{t("Original extracted text")}</h3><small>{t("Original source text and citations stay in their published language.")}</small></div><span>{t("Highlighted phrases appear in the text")}</span></div>
          <div className="report-page-list">{report.pages.map((page) => <article className="report-text-page" key={page.page_number}>
            <div className="report-page-label"><span>{t("PAGE")}{' '}{page.page_number}</span><span>{page.method.replaceAll('_', ' ')}</span></div>
            {page.text ? <pre><HighlightedText text={page.text} phrases={report.highlight_phrases}/></pre> : <p className="report-empty-note">{t("No text was extracted from this page.")}</p>}
          </article>)}</div>
        </section>

        <div className="report-side-column">
          <section className="report-panel">
            <div className="report-panel-title"><div><div className="eyebrow">{t("EXTRACTED FROM SOURCE")}</div><h3>{t("Structured findings")}</h3></div></div>
            <div className="report-findings">
              <div><span>{t("Anatomical location")}</span><b>{findings.anatomical_location.length ? findings.anatomical_location.join(', ') : t("Unavailable in report")}</b></div>
              <div><span>{t("Mentioned diagnosis / tumour terms")}</span><b>{findings.mentioned_diagnosis_terms.length ? findings.mentioned_diagnosis_terms.join(', ') : t("Unavailable in report")}</b></div>
              <div><span>{t("Reported characteristics")}</span><SourceSentences items={findings.reported_characteristics} emptyText={t("No matching characteristics were explicitly identified.")}/></div>
              <div><span>{t("Imaging findings")}</span><SourceSentences items={findings.imaging_findings} emptyText={t("No imaging finding sentence was identified.")}/></div>
              <div><span>{t("Recommendations and follow-up")}</span><SourceSentences items={findings.recommendations_and_follow_up} emptyText={t("No recommendation or follow-up text was found.")}/></div>
              <div className="report-missing"><span>{t("Missing or unclear")}</span><ul>{findings.missing_or_unclear.length ? findings.missing_or_unclear.map((item) => <li key={item}>{t(item)}</li>) : <li>{t("No requested field was missing from the text rules.")}</li>}</ul></div>
            </div>
          </section>

          <section className="report-panel report-summary-panel">
            <div className="report-panel-title"><div><div className="eyebrow">{t("SOURCE-SENTENCE SUMMARY")}</div><h3>{t("Summary")}</h3></div></div>
            <p className="report-method-note">{t("Extractive summary; each statement below is copied from the report.")}</p>
            <SourceSentences items={report.summary.statements} emptyText={t("No summary statements could be extracted.")}/>
          </section>

          <section className="report-panel">
            <div className="report-panel-title"><div><div className="eyebrow">{t("GENERAL DEFINITIONS")}</div><h3>{t("Medical terminology")}</h3></div></div>
            {report.terminology.length ? <ul className="report-terms">{report.terminology.map((item) => <li key={item.term}><b>{item.term}</b><p>{t(item.general_definition)}</p><small>{t("General definition · source mentions this term on page")}{' '}{item.page_number}</small><blockquote>“{item.source_excerpt}”</blockquote></li>)}</ul> : <p className="report-empty-note">{t("No listed terminology terms were found in the extracted report text.")}</p>}
          </section>

          <section className="report-panel report-qa-panel">
            <div className="report-panel-title"><div><div className="eyebrow">{t("DOCUMENT-ONLY RETRIEVAL")}</div><h3>{t("Ask about this report")}</h3></div></div>
            <p className="report-method-note">{t("Answers quote matching sentences from this upload. If the report does not contain an answer, the analyser says so.")}</p>
            <form className="report-question-form" onSubmit={askQuestion}><input aria-label={t("Question about report")} value={question} onChange={(event) => setQuestion(event.target.value)} maxLength={500} placeholder={t("Ask about a finding or recommendation…")}/><button className="report-primary-button" disabled={!question.trim() || qaStatus === 'loading'}>{qaStatus === 'loading' ? t("Searching…") : t("Ask")}</button></form>
            {qaError && <div className="report-error" role="alert">{qaError}</div>}
            {answers.map((item, index) => <article className="report-answer" key={`${index}-${item.question}`}><b>{t("Q ·")}{' '}{item.question}</b><p>{i18n.language === 'tr' ? t(item.answer_status === 'source_excerpt' ? 'Matching passages from the original report are quoted below.' : 'The report does not contain enough information to answer this question.') : item.answer}</p>{item.source_excerpts?.map((source, sourceIndex) => <small key={sourceIndex}>{t("Source · page")}{' '}{source.page_number}: “{source.text}”</small>)}<em>{t(item.notice)}</em></article>)}
          </section>
        </div>
      </div>
      <p className="report-retention-note">{t("The uploaded file and extracted text are stored locally on this computer until you delete the report. Follow-up questions use the saved extracted text. Upload de-identified documents only; local storage is not encrypted or access-controlled by this prototype.")}</p>
    </>}
  </section>
}
