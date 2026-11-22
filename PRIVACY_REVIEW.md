# OsteoLens privacy restrictions and unresolved release review

Reviewed against official KVKK guidance on 22 November 2026. This is an engineering record and review checklist, not legal advice, a compliance certificate, a retrospective audit, or a statement that no violation has occurred.

## Current decision

The deferred review was resumed on 22 November 2026. Technical controls and deployment requirements have been reviewed; closure remains pending the actual controller and approved privacy contact, confirmation of any past real-report use, and selection/review of the host. These are factual dependencies, not fields an automated review can supply. No approval configuration has been fabricated. The local research app remains available for inspection; the public service is not reopened.

The installed Chroma 1.5.9 product-telemetry `capture` implementation was inspected and is a no-op. This narrow observation does not establish that every dependency or provider makes no outbound connection. The prepared server unit additionally disables Hugging Face telemetry and enables offline embedding-cache loading; those settings require validation on the eventual server.

Server-side personal health-report upload/processing is disabled. Visitors can read personal PDF/TXT files and ask passage-search questions entirely in their browser. This is a data-minimisation design, not a legal exemption or certification. The public tunnel was stopped. Public relaunch is blocked until the operator's identity, contact channel, technical-data basis, provider arrangements and review are completed. Completing the configuration does **not** enable personal uploads.

The app retains 60 published BTXRD image records, the unchanged ResNet-18 checkpoint and 638-chunk RAG index, and 34 published report excerpts. Published/open-licensed material is not automatically anonymous or exempt from data-protection law. The operator must review source provenance, research permissions and re-identification risks separately.

## Implemented controls

| Area | Implementation | Boundary |
|---|---|---|
| Personal reports | Browser-only PDF/TXT extraction and local passage search; no network submission, persistent browser storage or Qwen processing. Legacy server upload routes return 403 before body parsing | Traffic may already have reached the network/provider; this is not a claim that a malicious submission can never reach infrastructure |
| Published examples | Server accepts an allowlisted source identifier and reads the bundled source file | No visitor document, filename or path accepted; no new saved report or report-session cache |
| Assistant | Editable questions, optional suggestions, language and validated published case/source ID; extra fields forbidden and body/field limits enforced | Question text reaches the server and its local Qwen model. The UI warns against identifiers or personal-health narratives, but warnings cannot prevent their inclusion. No chat-history or arbitrary report-context fields are accepted. Server/provider operational review remains necessary |
| Notices | English/Turkish privacy centre, persistent restriction notice, version identifier | Incomplete Article 10 notice until the controller details and legal grounds are established |
| Browser data | Language preference only; no new visitor-session cookies | Earlier signed cookies can identify only the owner's legacy data for erasure |
| Erasure | Owner-scoped legacy erasure, cookie removal, local preference clearing | Other sessions, provider logs and backups require an operator procedure; deleting a file is not a certified forensic wipe |
| External requests | Google Fonts import removed; no analytics integration; same-origin connection policy | Opening cited external links is a separate user action |
| Response protection | No-store API/HTML responses, no-referrer, restrictive CSP, disabled camera/microphone/geolocation permissions | This does not replace penetration testing or infrastructure security |
| Minimised logging | Public launcher disables Uvicorn access logs; no request-body logging; validation errors do not echo submitted content | Existing logs/provider logs are not silently deleted; rate-limit identifiers are keyed hashes retained briefly in memory, not guaranteed anonymous data |
| Deployment | Launcher and public backend reject incomplete operator-review configuration | Checks establish presence of operator review fields; code cannot verify their legal accuracy |

No existing model weights, Ollama configuration, embeddings or Chroma content were changed. Existing private local report data has not been published or inspected for content. A read-only count of the public report database returned **0 stored reports** during this review. This does not establish that personal reports were never previously transmitted, processed, logged, deleted or included in backups.

## Operator decisions still required

1. Establish the actual controller: the student, university, another entity, or a joint-controller arrangement. Obtain institutional approval where needed. Confirm a private contact channel; do not use public GitHub issues for rights requests or health information.
2. Record each purpose, category, recipient, retention period and legal basis. Health data is a special category. Assess the amended Article 6 conditions rather than assuming an academic project qualifies for a health-care exception. A consent checkbox alone does not establish lawful processing or adequate safeguards. [KVKK special-category guidance](https://www.kvkk.gov.tr/Icerik/2051/Ozel-Nitelikli-Kisisel-Veriler), [2024 amendment guidance](https://www.kvkk.gov.tr/Icerik/8184/Ozel-Nitelikli-Kisisel-Verilerin-Islenmesine-Iliskin-Rehber).
3. Finalise an accurate Article 10 notice before collecting personal data, covering the controller, purposes, recipients, collection method/legal grounds and rights. Information notices and any consent collection must be kept distinct. Do not assert a legal basis until it has been assessed. [Official information-notice rules](https://www.kvkk.gov.tr/Icerik/4132/aydinlatma-yukumlulugunun-yerine-getirilmesinde-uyulacak-usul-ve-esaslar-hakkinda-teblig).
4. Assess Cloudflare and all hosting/AI/storage/logging providers, subprocessors, processing locations, contracts, retention, and Article 9 transfer conditions. The previous tunnel crosses international infrastructure; HTTPS does not itself establish lawful cross-border transfer. Do not assume an old general transfer-consent statement covers an ongoing service. [Current KVKK transfer guidance](https://www.kvkk.gov.tr/Icerik/2053/Yurtdisina-Aktarim).
5. Before considering personal uploads again, design an authenticated service with appropriate authorisation, multi-factor remote access, encryption with separate key management, secure audit records, regular security testing, patching, staff confidentiality/training and documented access revocation. None of these organisational requirements is satisfied merely by adding this privacy page. [Board decision 2018/10](https://www.kvkk.gov.tr/Icerik/4110/2018-10).
6. Establish a rights-request procedure with proportionate identity verification, a secure submission channel, a request register and written/electronic responses within the applicable deadline (normally no later than 30 days under the cited KVKK guidance). The downloaded in-app draft is a preparation aid, not a completed statutory application or proof of submission. Required formal particulars must be supplied through the approved channel. [Response obligation](https://www.kvkk.gov.tr/Icerik/2046/Ilgili-Kisiler-Tarafindan-Yapilan-Basvurularin-Cevaplanmasi-Yukumlulugu), [application procedure](https://www.kvkk.gov.tr/Icerik/6938/Kurumumuza-Yapilan-Sikayetlerin-Usul-Sartlarina-Iliskin-Kamuoyu-Duyurusu).
7. Define deletion and retention across originals, extracted text, temporary files, databases, caches, backups and processors. Validate deletion, document exceptions, and use approved secure disposal methods. A UI delete button and a request-triggered cleanup are not a complete retention programme. [Official deletion/destruction/anonymisation regulation](https://www.kvkk.gov.tr/Icerik/5441/KISISEL-VERILERIN-SILINMESI-YOK-EDILMESI-VEYA-ANONIM-HALE-GETIRILMESI-HAKKINDA-YONETMELIK).
8. Assess VERBIS registration/exemptions and other applicable obligations with the controller and qualified Turkish data-protection counsel. Also assess relevant health-data/research rules and other territorial regimes where applicable; no universal exemption or worldwide compliance is claimed. [Registry regulation](https://www.kvkk.gov.tr/Icerik/5442/VERI-SORUMLULARI-SICILI-HAKKINDA-YONETMELIK).

## If a real report may already have been submitted

Do not issue a statement that no breach or unlawful processing occurred. Keep collection stopped, restrict access and involve the controller/privacy adviser. Establish the relevant times, systems, recipients, legal basis, retention and access history without placing report contents in tickets or chat. Preserve appropriate incident evidence under restricted access; do not indiscriminately copy or erase it. Distinguish a processing-lawfulness issue from an actual data-security breach. If a reportable breach is identified, the Board's guidance requires notification without delay and no later than 72 hours from awareness, and affected-person notification as specified. [Board breach-notification guidance](https://www.kvkk.gov.tr/Icerik/5362/Veri-Ihlali-Bildirimi).

## Release procedure

The private example configuration is `deploy/privacy-config.example.json`. After the substantive review, the operator can create `deploy/runtime/privacy-config.json` (Git-ignored) with the approved public notice fields and review record. The application displays controller/contact/legal-basis/transfer/retention fields; do not put confidential legal opinions or secrets in those display fields. The internal reviewer and review date are not returned by the public privacy endpoint.

Both `deploy/start_public_demo.py` and `backend.main` in public mode require the review. Do not populate approval fields with invented or placeholder information. No settings switch enables personal PDF/TXT uploads. That feature would require a separately reviewed implementation and deployment.

Until the deferred review is completed, run the app on loopback for local review. The previous public URL is offline intentionally.

## Restored workflows, 22 November 2026

Custom questions are restored in the main assistant and in Report Analyser for published examples. The caller sends its own question and an allowlisted source ID; the server reconstructs source text rather than accepting arbitrary report context. Report chat does not require pretending that a published case report belongs to a BTXRD image. Browser-only personal documents and questions stay separate from server RAG. New questions/answers are not saved by the application; provider retention must still be verified. Research-chat warnings are not an anonymisation filter or a legal basis.

PDF.js 6.5.438 was added with the owner’s express approval of this dependency exception. It is served from the same origin, including its worker. Only text extraction is used, with evaluation disabled, 5 MB / 80-page / extracted-text limits. Scanned and encrypted PDFs are rejected. The app does not implement OCR, personal-document LLM generation, diagnostic interpretation, or certified secure erasure. These limitations are displayed. Review browser extensions, shared-device access and source-document permissions separately.
