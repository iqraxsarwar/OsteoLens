import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { API_URL, apiFetch } from '../api'
import './PrivacyCenter.css'

export default function PrivacyCenter() {
  const { i18n } = useTranslation()
  const tr = i18n.language === 'tr'
  const [policy,setPolicy]=useState(null)
  const [eraseState,setEraseState]=useState('idle')
  const [confirmed,setConfirmed]=useState(false)
  useEffect(()=>{let active=true; apiFetch(`${API_URL}/api/privacy`).then(r=>r.ok?r.json():null).then(p=>{if(active)setPolicy(p)}).catch(()=>{});return()=>{active=false}},[])
  async function erase() {
    setEraseState('working')
    try {
      const response=await apiFetch(`${API_URL}/api/privacy/erase-session`,{method:'POST'})
      if(!response.ok)throw new Error('Deletion failed')
      localStorage.removeItem('osteolens-language')
      setEraseState('complete')
    } catch { setEraseState('error') }
  }
  function downloadRequest() {
    const text=tr ? 'KVKK ilgili kişi başvurusu taslağı\n\nAlıcı: doğrulanmış veri sorumlusu\nİstenen işlem: bilgi / erişim / düzeltme / silme / itiraz\nİlgili kullanım tarihi veya oturum: [yalnızca gerekli bilgi]\nYanıt iletişim yolu: [doldurunuz]\n\nBu taslak otomatik gönderilmez. Sağlık raporu, T.C. kimlik numarası veya gereksiz kişisel veri eklemeyin. Kimlik doğrulamasını veri sorumlusunun doğrulanmış özel kanalı üzerinden tamamlayın.' : 'Draft KVKK data-subject request\n\nRecipient: verified data controller\nRequested action: information / access / correction / erasure / objection\nRelevant use date or session: [minimum necessary details]\nResponse contact: [complete]\n\nThis draft is not sent automatically. Do not attach medical reports, national ID numbers or unnecessary personal data. Complete proportionate identity verification through the controller\'s verified private channel.'
    const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}))
    const link=document.createElement('a');link.href=url;link.download=tr?'KVKK-basvuru-taslagi.txt':'KVKK-request-draft.txt';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
  }
  return <section className="privacy-page">
    <h1>{tr ? 'Gizlilik ve veri koruma' : 'Privacy and data protection'}</h1>
    <p>{tr ? 'Bildirim sürümü' : 'Notice version'}: {policy?.notice_version || '2026-11-22.1'}</p>
    <div className="privacy-notice"><h2>{tr ? 'Araştırma demosu: kişisel rapor kabul edilmez' : 'Research demo: personal reports are not accepted'}</h2>
      <p>{tr ? 'Kişisel PDF/TXT yükleme, serbest metin gönderme ve kişisel raporları yapay zekâya iletme kapalıdır. Yalnızca uygulamadaki yayımlanmış kaynaklar ve önceden belirlenmiş araştırma soruları kullanılabilir. Bu kısıtlamalar tam hukuki uyum sertifikası değildir.' : 'Personal PDF/TXT uploads, free-text submissions and sending personal reports to AI are disabled. Use only the published sources and predefined research questions. These restrictions are not a certification of legal compliance.'}</p></div>
    <h2>{tr ? 'Veri sorumlusu ve iletişim' : 'Controller and contact'}</h2>
    <p>{policy?.controller_name || (tr ? 'Henüz doğrulanmadı. Harici yayına geçiş engellenmiştir.' : 'Not yet confirmed. External release is blocked.')}</p>
    <p>{policy?.privacy_email ? <a href={`mailto:${policy.privacy_email}`}>{policy.privacy_email}</a> : (tr ? 'Doğrulanmış özel başvuru kanalı henüz tanımlanmadı. GitHub sorunlarına veya herkese açık mesajlara kişisel bilgi yazmayın.' : 'A verified private request channel has not been configured. Do not put personal information in GitHub issues or public messages.')}</p>
    <h2>{tr ? 'Hangi bilgiler işlenir?' : 'What information is processed?'}</h2>
    <p>{tr ? 'Sunucu, seçilen yayımlanmış kaynak/olgu kimliğini, araştırma sorusu kimliğini ve yanıt dilini alır. Kaynak metinleri önceden sunucuda bulunan yayımlanmış materyallerdir. Yeni kullanıcı raporları kaydedilmez ve model eğitimi yapılmaz. Görüntülenen analizler sayfa belleğinde tutulur.' : 'The server receives the selected published source/case identifier, research-question identifier and response language. Source text is published material already on the server. No new user reports are saved and no model training takes place. Displayed analyses remain in page memory.'}</p>
    <p>{tr ? 'Dil tercihi bu tarayıcının yerel depolamasında tutulur. Yeni oturum izleme çerezi oluşturulmaz. Önceki sürümden kalan imzalı çerez yalnızca o oturuma ait eski raporları silmek için kullanılabilir. Kimlik doğrulaması yapılmış bir kullanıcı hesabı değildir.' : 'Your language preference is stored in this browser’s local storage. No new session-tracking cookie is issued. A signed cookie from the previous version can only be used to erase that session’s old reports; it is not an authenticated user account.'}</p>
    <h2>{tr ? 'Teknik veriler ve hizmet sağlayıcılar' : 'Technical data and service providers'}</h2>
    <p>{tr ? 'Ağ bağlantısı IP adresi, tarayıcı bilgisi ve bağlantı zamanları gibi teknik bilgileri işleyebilir. Uygulama istek içeriğini günlüğe kaydetmez; herkese açık sunucunun erişim günlükleri kapalıdır. Hız sınırlaması bellekte kısa süreli, anahtarlı IP özetleri kullanır. Bunlar anonimlik garantisi değildir.' : 'Network connections can process technical information such as IP addresses, browser information and connection times. The app does not log request bodies; public-server access logging is disabled. Rate limiting uses short-lived keyed IP hashes in memory; that is not a guarantee of anonymisation.'}</p>
    <p>{tr ? 'Önceki demo Cloudflare Tunnel kullanıyordu. Bu sağlayıcı trafik ve teknik verileri uluslararası altyapıda işleyebilir. KVKK madde 9 kapsamındaki aktarım koşulları ve sağlayıcı saklama koşulları ayrıca doğrulanmalıdır. HTTPS tek başına bu yükümlülükleri karşılamaz. Harici yazı tipi ve analiz hizmeti çağrıları kaldırılmıştır.' : 'The previous demo used Cloudflare Tunnel, which can process traffic and technical data on international infrastructure. KVKK Article 9 transfer conditions and provider retention arrangements need separate verification. HTTPS alone does not satisfy those obligations. External font requests and analytics calls are not used.'}</p>
    <p><b>{tr ? 'Teknik veri hukuki sebebi: ' : 'Technical-data legal basis: '}</b>{policy?.technical_data_legal_basis || (tr ? 'Operatör incelemesi bekleniyor.' : 'Pending operator review.')}</p>
    <p><b>{tr ? 'Aktarım düzenlemesi: ' : 'Transfer arrangement: '}</b>{policy?.provider_transfer_assessment || (tr ? 'Doğrulanmadı; yeniden yayın engelli.' : 'Unverified; relaunch blocked.')}</p>
    <p><b>{tr ? 'Teknik veri saklama: ' : 'Technical-data retention: '}</b>{policy?.technical_data_retention || (tr ? 'Sağlayıcı ve operatör koşulları doğrulanmadı.' : 'Provider and operator arrangements have not been verified.')}</p>
    <h2>{tr ? 'Haklarınız ve yerel kontroller' : 'Your rights and local controls'}</h2>
    <p>{tr ? 'KVKK madde 11 kapsamındaki haklar; işleme hakkında bilgi edinme, amacı ve alıcıları öğrenme, düzeltme, koşulları oluştuğunda silme/yok etme, ilgili üçüncü kişilere bildirim, yalnızca otomatik analizden doğan aleyhe sonuca itiraz ve kanuna aykırı işleme nedeniyle zararın giderilmesini istemeyi kapsar. Resmî başvurular doğrulanmış veri sorumlusuna yapılmalıdır.' : 'Article 11 rights include information about processing, purposes and recipients; correction; erasure/destruction where the conditions apply; notification to relevant third parties; objection to adverse results arising exclusively from automated analysis; and compensation for damage from unlawful processing. Formal requests must go to the verified controller.'}</p>
    <button className="secondary-button" onClick={downloadRequest}>{tr ? 'Başvuru taslağını cihazıma indir' : 'Download a request draft to my device'}</button>
    <div className="privacy-notice"><label><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>{tr ? 'Bu tarayıcı oturumuyla ilişkili önceki raporların ve kaydedilmiş dil tercihimin silinmesini istiyorum.' : 'I want to erase previous reports linked to this browser session and my saved language preference.'}</label>
      <button className="report-delete-button" disabled={!confirmed || eraseState==='working'} onClick={erase}>{tr ? 'Bu oturumun verilerini sil' : 'Erase this session’s data'}</button>
      <p role="status">{eraseState==='complete' ? (tr ? 'Bu oturum için silme isteği tamamlandı. Diğer oturumlar, yedekler veya sağlayıcı kayıtları için operatör incelemesi gerekir. Sayfayı kapatmak görüntülenen geçici belleği temizler.' : 'The deletion request for this session completed. Other sessions, backups and provider records require operator review. Close the page to clear displayed page memory.') : eraseState==='error' ? (tr ? 'Silme doğrulanamadı. Lütfen daha sonra tekrar deneyin; operatöre başvuru gerekebilir.' : 'Deletion could not be confirmed. Please retry later; an operator request may be needed.') : ''}</p>
    </div>
    <p>{tr ? 'Bu sayfa, operatör bilgileri tamamlanmadan madde 10 kapsamındaki eksiksiz bir aydınlatma metni olarak sunulmaz. Kişisel sağlık verisi işleme için ayrıca hukuki ve teknik inceleme gerekir.' : 'Until operator details are completed, this page is not presented as a complete Article 10 information notice. Processing personal health data requires a separate legal and technical review.'}</p>
    <a href="https://www.kvkk.gov.tr/Icerik/2051/Ozel-Nitelikli-Kisisel-Veriler" target="_blank" rel="noreferrer">{tr ? 'KVKK: özel nitelikli kişisel veriler' : 'KVKK: special categories of personal data'}</a>
  </section>
}
