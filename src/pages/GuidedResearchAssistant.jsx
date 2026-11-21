import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { API_URL, apiFetch } from '../api'
import './RAGAssistant.css'

const questions=[
  ['compare_tumours','How do osteosarcoma and Ewing sarcoma differ?'],
  ['imaging','What imaging modalities are used to assess a suspected bone tumour?'],
  ['transition','What does a wide zone of transition mean in bone imaging?'],
  ['benign_malignant','How are benign bone tumours different from malignant ones?'],
  ['case_summary','Explain the available information for {{caseId}}.'],
  ['heatmap','What does the Grad-CAM visualization mean for this case?'],
  ['source_label','What does the source label tell us, and what does it not tell us?'],
  ['limitations','What limitations matter when interpreting this model output?'],
]
const caseQuestions=new Set(['case_summary','heatmap','source_label','limitations'])

export default function GuidedResearchAssistant({selectedCase,initialCaseMode,onPrivacy}) {
  const {t,i18n}=useTranslation()
  const tr=i18n.language==='tr'
  const [selection,setSelection]=useState(initialCaseMode?'case_summary':'imaging')
  const [status,setStatus]=useState(null)
  const [busy,setBusy]=useState(false)
  const [messages,setMessages]=useState([])
  const [error,setError]=useState(false)
  useEffect(()=>{let active=true;apiFetch(`${API_URL}/api/assistant/status`).then(r=>r.ok?r.json():null).then(s=>{if(active)setStatus(s)}).catch(()=>{});return()=>{active=false}},[])
  async function ask(event) {
    event.preventDefault();setBusy(true);setError(false)
    const label=t(questions.find(([id])=>id===selection)[1],{caseId:selectedCase?.case_id})
    try {
      const response=await apiFetch(`${API_URL}/api/assistant/research`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question_id:selection,language:i18n.language,case_id:caseQuestions.has(selection)?selectedCase?.case_id:null})})
      if(!response.ok)throw new Error('Research unavailable')
      const answer=await response.json()
      setMessages(current=>[...current,{question:label,...answer}])
    } catch {setError(true)} finally {setBusy(false)}
  }
  return <section className="rag-page">
    <div className="rag-heading"><div><div className="eyebrow">{t('EVIDENCE-LED MEDICAL RESEARCH')}</div><h1>{t('RAG AI Assistant')}</h1></div>
      <div><div className={`rag-ready-state ${status?.ready?'ready':''}`}>{status?.ready?t('LOCAL RAG READY'):t('SETUP REQUIRED')}</div>{status?.ready&&<small>{status.indexed_chunks} {t('indexed chunks ·')} {status.generation_model}</small>}</div>
    </div>
    <div className="privacy-notice"><b>{tr?'Kişisel bilgi göndermeyen araştırma modu':'Research mode without personal submissions'}</b>
      <p>{tr?'Serbest metin ve rapor yapıştırma kapalıdır. Bir araştırma sorusu seçin; sunucu yalnızca soru kimliğini, dili ve gerekiyorsa yayımlanmış olgu kimliğini alır. Önceki sohbet metni gönderilmez.':'Free-text entry and pasted reports are disabled. Select a research question; the server receives only its identifier, language and, when needed, the published case identifier. Previous chat text is not sent.'}</p>
      <button className="secondary-button" onClick={onPrivacy}>{tr?'Gizlilik ayrıntıları':'Privacy details'}</button>
    </div>
    <form className="research-selection" onSubmit={ask}>
      <select aria-label={tr?'Araştırma sorusu seçin':'Select research question'} value={selection} onChange={e=>setSelection(e.target.value)} disabled={busy}>
        {questions.map(([id,label])=><option key={id} value={id} disabled={caseQuestions.has(id)&&!selectedCase}>{t(label,{caseId:selectedCase?.case_id})}</option>)}
      </select>
      <button className="primary-button" disabled={busy||!status?.ready}>{busy?t('Searching…'):t('Ask assistant')}</button>
      <button type="button" className="secondary-button" disabled={busy||!messages.length} onClick={()=>{setMessages([]);setError(false)}}>{t('Clear conversation')}</button>
    </form>
    {caseQuestions.has(selection)&&selectedCase&&<p>{t('CASE CONTEXT')}: {selectedCase.case_id} · {t(selectedCase.classification)}</p>}
    {error&&<p className="rag-error" role="alert">{t('Assistant unavailable.')}</p>}
    {busy&&<p role="status">{t('Retrieving evidence and generating a cited response…')}</p>}
    {messages.map((message,index)=><article className="rag-message assistant" key={index}>
      <h3>{message.question}</h3><div className="rag-message-body">{message.answer}</div>
      <div className="rag-citations">{message.citations?.map(source=><a className="rag-citation" key={source.citation_id} href={source.url} target="_blank" rel="noreferrer"><span>[{source.citation_id}]</span><span><b>{source.title}</b><small>{source.author_or_institution} · {source.license}</small><em>{source.excerpt}</em></span></a>)}</div>
      <p className="rag-answer-notice">{message.notice}</p>
    </article>)}
    <p>{tr?'Yanıtlar tıbbi tanı değildir. Atıf bulunması, yanıtın doğru olduğunu garanti etmez. Kaynak alıntıları özgün dillerinde kalır.':'Answers are not medical diagnoses. Citations do not guarantee accuracy. Source quotations remain in their original language.'}</p>
  </section>
}
