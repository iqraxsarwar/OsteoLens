import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { API_URL, apiFetch } from '../api'
import './RAGAssistant.css'

export default function ResearchAssistant({ selectedCase, initialCaseMode, source, onPrivacy }) {
  const { t, i18n } = useTranslation()
  const tr = i18n.language === 'tr'
  const [caseMode, setCaseMode] = useState(Boolean(initialCaseMode))
  const [question, setQuestion] = useState('')
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState(false)
  const [messages, setMessages] = useState([])
  const [error, setError] = useState(false)
  const pending = useRef(null)
  useEffect(() => {
    const controller = new AbortController()
    apiFetch(`${API_URL}/api/assistant/status`, { signal: controller.signal }).then(r => r.ok ? r.json() : null).then(setStatus).catch(() => {})
    return () => { controller.abort(); pending.current?.abort() }
  }, [])
  function clear() {
    pending.current?.abort(); pending.current = null
    setMessages([]); setQuestion(''); setError(false); setBusy(false)
  }
  async function ask(event) {
    event.preventDefault()
    const text = question.trim()
    if (!text || busy) return
    const controller = new AbortController(); pending.current = controller
    setBusy(true); setError(false)
    try {
      const response = await apiFetch(`${API_URL}/api/assistant/research`, {
        method: 'POST', signal: controller.signal, headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text, language: tr ? 'tr' : 'en', case_id: caseMode && !source ? selectedCase?.case_id : null, source_id: source?.id || null }),
      })
      if (!response.ok) throw new Error('Research unavailable')
      const answer = await response.json()
      if (controller.signal.aborted) return
      setMessages(current => [...current.slice(-19), { question: text, ...answer }]); setQuestion('')
    } catch { if (!controller.signal.aborted) setError(true) }
    finally { if (pending.current === controller) { pending.current = null; setBusy(false) } }
  }
  const prompts = source
    ? [tr ? 'Bu raporda hangi bulgular belirtiliyor?' : 'What findings are described in this report?', tr ? 'Bu raporda biyopsi hakkında ne yazıyor?' : 'What does this report say about biopsy?']
    : caseMode ? [t('Explain the available information for {{caseId}}.', { caseId: selectedCase?.case_id }), t('What does the Grad-CAM visualization mean for this case?')]
      : [t('How do osteosarcoma and Ewing sarcoma differ?'), t('What imaging modalities are used to assess a suspected bone tumour?')]
  return <section className="rag-page">
    <div className="rag-heading"><div><div className="eyebrow">{t('EVIDENCE-LED MEDICAL RESEARCH')}</div><h2>{t('RAG AI Assistant')}</h2></div>
      <div><div className={`rag-ready-state ${status?.ready ? 'ready' : ''}`}>{status?.ready ? t('LOCAL RAG READY') : t('SETUP REQUIRED')}</div>{status?.ready && <small>{status.indexed_chunks} {t('indexed chunks ·')} {status.generation_model}</small>}</div>
    </div>
    <p>{tr ? 'Sorunuzu kendi sözcüklerinizle yazın. Metin yanıt için sunucuya ve sunucudaki Qwen modeline gönderilir; sohbet geçmişi sunucuya gönderilmez veya kaydedilmez. Buraya kimlik bilgisi veya kişisel rapor yapıştırmayın. Kişisel belgeler için cihazda rapor modunu kullanın.' : 'Write your own question. Your text is sent to the server and its Qwen model for a response; conversation history is not sent or saved on the server. Do not paste identifiers or personal reports here. Use on-device report mode for personal documents.'}</p>
    {onPrivacy && <button className="secondary-button" onClick={onPrivacy}>{tr ? 'Gizlilik ayrıntıları' : 'Privacy details'}</button>}
    {source ? <p><b>{tr ? 'Seçilen yayımlanmış rapor: ' : 'Selected published report: '}</b>{source.title}</p> : selectedCase && <div className="rag-mode-switch" role="group" aria-label={t('Question context')}>
      <button className={!caseMode ? 'selected' : ''} onClick={() => { clear(); setCaseMode(false) }}>{t('General research')}</button>
      <button className={caseMode ? 'selected' : ''} onClick={() => { clear(); setCaseMode(true) }}>{t('Selected case')} · {selectedCase.case_id}</button>
    </div>}
    <div className="rag-prompt-grid">{prompts.map(prompt => <button key={prompt} onClick={() => setQuestion(prompt)}>{prompt}</button>)}</div>
    <form className="rag-composer" onSubmit={ask}>
      <textarea aria-label={t('Ask the RAG AI Assistant')} placeholder={tr ? 'Kendi sorunuzu yazın…' : 'Type your own question…'} value={question} maxLength={1200} onChange={e => setQuestion(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); e.currentTarget.form.requestSubmit() } }} />
      <button className="rag-send-button" disabled={busy || !question.trim()}>{busy ? t('Searching…') : t('Ask assistant')}</button>
      <small>{tr ? 'Enter: gönder · Shift+Enter: yeni satır · Her soruda gerekli bağlamı belirtin.' : 'Enter to send · Shift+Enter for a new line · Include the context needed for each question.'}</small>
    </form>
    <button className="secondary-button" onClick={clear}>{t('Clear conversation')}</button>
    {error && <p className="rag-error" role="alert">{t('Assistant unavailable.')} {tr ? 'Sorunuzu kontrol edin ve yeniden deneyin.' : 'Check your question and try again.'}</p>}
    {busy && <p role="status">{t('Retrieving evidence and generating a cited response…')}</p>}
    {messages.map((message, index) => <article className="rag-message assistant" key={index}>
      <h3>{message.question}</h3><div className="rag-message-body">{message.answer}</div>
      <div className="rag-citations">{message.citations?.map(citation => <a className="rag-citation" key={citation.citation_id} href={citation.url} target="_blank" rel="noreferrer"><span>[{citation.citation_id}]</span><span><b>{citation.title}</b><small>{citation.author_or_institution} · {citation.license}</small><em>{citation.excerpt}</em></span></a>)}</div>
      <p className="rag-answer-notice">{message.notice}</p>
    </article>)}
    <p>{tr ? 'Araştırma amaçlıdır; tanı veya tedavi önerisi değildir. Atıfları özgün kaynakla doğrulayın.' : 'For research; not a diagnosis or treatment recommendation. Verify citations against the original source.'}</p>
  </section>
}
