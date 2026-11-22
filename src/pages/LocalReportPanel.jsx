import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { findReportPassages, readPersonalReport, reportPassages } from '../reports/localReport'

export default function LocalReportPanel() {
  const { i18n } = useTranslation()
  const tr = i18n.language === 'tr'
  const [pages, setPages] = useState([])
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const input = useRef(null)
  const revision = useRef(0)
  const reader = useRef(null)
  useEffect(() => () => { revision.current++; reader.current?.abort() }, [])
  function clear() {
    reader.current?.abort(); reader.current = null
    revision.current++; setPages([]); setMessages([]); setQuestion(''); setError(''); setBusy(false)
    if (input.current) input.current.value = ''
  }
  async function open(file) {
    clear()
    if (!file) return
    const version = revision.current
    const controller = new AbortController(); reader.current = controller
    setBusy(true)
    try { const result = await readPersonalReport(file, { signal: controller.signal }); if (version === revision.current) setPages(result) }
    catch { if (version === revision.current) setError(tr ? 'Dosya okunamadı. En fazla 5 MB ve 80 sayfa, metin içeren PDF/TXT kullanın. Taranmış veya şifreli PDF desteklenmez.' : 'Could not read this file. Use a text-containing PDF/TXT up to 5 MB and 80 pages. Scanned or password-protected PDFs are not supported.') }
    finally { if (version === revision.current) { setBusy(false); if (input.current) input.current.value = '' } }
  }
  function ask(event) {
    event.preventDefault()
    if (!question.trim()) return
    setMessages(current => [...current.slice(-19), { question, passages: findReportPassages(pages, question) }]); setQuestion('')
  }
  return <section className="report-panel local-report-panel">
    <h2>{tr ? 'Kendi raporum · yalnızca bu cihazda' : 'My own report · on this device only'}</h2>
    <p>{tr ? 'Dosya ve sorularınız tarayıcınızda işlenir; sunucuya veya Qwen modeline gönderilmez. Rapor, dosya adı ve sohbet yerel depolamaya kaydedilmez. Temizle düğmesi veya bu bölümden ayrılmak uygulamanın rapor referanslarını kaldırır; bu adli bir güvenli silme garantisi değildir.' : 'Your file and questions are processed in your browser; they are not sent to the server or Qwen. The report, filename and chat are not saved to local storage. Clear or leave this section to remove the app’s report references; this is not a forensic secure-erasure guarantee.'}</p>
    <p>{tr ? 'Yalnızca kullanma yetkiniz olan belgeleri açın. Paylaşılan cihazlarda ekran ve tarayıcı güvenliğini dikkate alın.' : 'Open only documents you are authorised to use. Consider screen and browser security on shared devices.'}</p>
    <label className="report-upload-label">{tr ? 'Cihazımdan rapor seç (PDF/TXT, en fazla 5 MB)' : 'Choose report from my device (PDF/TXT, up to 5 MB)'}
      <input ref={input} type="file" accept=".pdf,.txt,application/pdf,text/plain" disabled={busy} onChange={e => open(e.target.files?.[0])} />
    </label>
    <button className="report-secondary-button" onClick={clear}>{tr ? 'Raporu ve sohbeti temizle' : 'Clear report and conversation'}</button>
    {busy && <p role="status">{tr ? 'Bu cihazda okunuyor…' : 'Reading on this device…'}</p>}
    {error && <p role="alert">{error}</p>}
    {!!pages.length && <>
      <h3>{tr ? 'Rapordan alıntılar' : 'Extracts from the report'}</h3>
      <p>{tr ? 'Aşağıdaki metin raporun başlangıcından alınmıştır; bir tanı veya kapsamlı klinik özet değildir.' : 'The text below is taken from the start of the report; it is not a diagnosis or a comprehensive clinical summary.'}</p>
      {reportPassages(pages).slice(0, 5).map((item, index) => <blockquote key={index}>{item.text} [{tr ? 'sayfa' : 'page'} {item.page}]</blockquote>)}
      <details><summary>{tr ? 'Çıkarılan metni göster' : 'Show extracted text'}</summary>{pages.map(page => <pre className="published-source-text" key={page.page}>{page.text}</pre>)}</details>
      <h3>{tr ? 'Rapora kendi sorunuzu sorun' : 'Ask your own question about this report'}</h3>
      <p>{tr ? 'Cihazda metin araması: ilgili pasajları bulur ve aynen alıntılar. Bu mod Qwen/RAG üretimi yapmaz; tıbbi yorum veya tanı çıkarmaz. Eşleşme olmaması bilginin bulunmadığını kanıtlamaz.' : 'On-device text search finds and quotes matching passages. This mode does not run Qwen/RAG generation or infer a diagnosis. No match does not prove the information is absent.'}</p>
      <form className="rag-composer" onSubmit={ask}><textarea aria-label={tr ? 'Kişisel rapor hakkında soru' : 'Question about my personal report'} value={question} maxLength={1200} onChange={e => setQuestion(e.target.value)} placeholder={tr ? 'Örneğin: Raporda biyopsi hakkında ne yazıyor?' : 'For example: What does the report say about biopsy?'} /><button className="rag-send-button" disabled={!question.trim()}>{tr ? 'Bu cihazda yanıtla' : 'Answer on this device'}</button></form>
      {messages.map((message, index) => <article className="rag-message assistant" key={index}><h4>{message.question}</h4>{message.passages.length ? message.passages.map((item, n) => <blockquote key={n}>{item.text} [{tr ? 'sayfa' : 'page'} {item.page}]</blockquote>) : <p>{tr ? 'Eşleşen pasaj bulunamadı. Farklı terimler deneyin ve özgün raporu kontrol edin.' : 'No matching passage found. Try different terms and check the original report.'}</p>}</article>)}
    </>}
  </section>
}
