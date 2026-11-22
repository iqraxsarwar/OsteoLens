# OsteoLens

**Bone imaging, understood.**

**Privacy status — 22 November 2026:** custom research questions and the published-report RAG assistant are available. Personal PDF/TXT documents can be read and searched entirely in the visitor’s browser; they are not uploaded to the backend. Browser report questions use passage retrieval, not Qwen generation. The public demo is offline pending controller/contact, legal-basis and provider-transfer review. The research prototype is not certified KVKK-compliant. See [PRIVACY_REVIEW.md](PRIVACY_REVIEW.md) for implemented controls and unresolved obligations.

See [QUALITY_ASSURANCE.md](QUALITY_ASSURANCE.md) for the latest tested/partial/unavailable feature status. A collection of synthetic-only Report Analyser fixtures is provided in [sample_reports/](sample_reports/README.md); these files are not BTXRD records and are never automatically linked to cases.

OsteoLens contains a source-linked library of 60 distinct BTXRD radiograph files, plus a ResNet-18 research inference and Grad-CAM path. The case manifest records source IDs, dataset labels, metadata, citation, license, image path, and SHA-256 checksum. The UI loads the selected record's actual JPEG, supports case filters and image navigation, and can request model inference/Grad-CAM from the local API when its PyTorch runtime is available.

## English and Turkish

Use the **English / Türkçe** controls in the header. The choice persists in this browser. Navigation, controls, case/heatmap explanations and report terminology are translated. Source quotations, publication titles and provenance remain in their original language. Research questions can be written freely, with answers requested in the selected language using the unchanged Qwen model. Translation quality is not clinically validated.

The report analyser also offers **34 attributed CC BY 4.0 published case excerpts**, independent of the 60 BTXRD image records.

The small Qwen model can fail to follow the requested language or produce unreliable prose. If it returns English for a Turkish request, the assistant gives a Turkish explanation of that limitation and exact original-source quotations instead. Existing conversation messages are not retroactively translated when the interface language changes. Citation presence does not establish clinical accuracy.

## Public deployment

See [DEPLOYMENT.md](DEPLOYMENT.md). Production uses one HTTPS origin for the frontend and API. Private uploads, credentials, model weights, vector databases and generated bundles are excluded from this repository. Publishing this source does not itself deploy the backend.

## Run locally

Requirements: Node.js 20.19+ or 22.12+, Python, and a compatible PyTorch/torchvision installation with enough free disk space for the model runtime. The model checkpoint is already present at `models/checkpoints/osteolens_btxrd_resnet18.pth` in this workspace, but is excluded from Git.

Start the inference API in one terminal:

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Start the frontend in another terminal:

```powershell
npm install
npm run dev
```

Open the local URL printed by Vite. Choose a case and click **Analyze case** to request the model prediction and Grad-CAM. If the checkpoint/runtime is unavailable, the viewer displays an error and does not show substitute results. To check the case library and viewer:

```powershell
npm test
npm run lint
npm run build
```

## Dataset and limits

The sample images are from the [BTXRD Figshare record](https://doi.org/10.6084/m9.figshare.27865398.v1), licensed CC BY 4.0. See [DATA_SOURCES.md](DATA_SOURCES.md) and `src/data/cases.json` for attribution and record-level provenance. BTXRD supplies structured classifications and metadata, but no free-text narrative for these records; the interface marks that information unavailable rather than adding text.

These 60 entries are verified distinct **image records**, not 60 verified distinct patients. BTXRD does not expose a verified patient identifier in the included metadata. The displayed source class/subtype is kept separate from the OsteoLens model output. The checkpoint metadata says patient-independent splitting was not verified. Grad-CAM is qualitative model attribution, not a confirmed lesion contour or diagnosis. No localization model is currently available.

MedPix is not included in the sample library. It has case-linked image/text content and an Open-i access path, but the item-level image rights vary and MedPix describes use as personal/local teaching unless additional permission is obtained from the contributor. The dataset-level catalog license does not establish that each image may be redistributed in this application. See `DATA_SOURCES.md`.

## Model training preparation (Phase 3)

The Phase 3 Colab workflow and inference loader are in [`training/README.md`](training/README.md). A trained ResNet-18 checkpoint is present locally at `models/checkpoints/osteolens_btxrd_resnet18.pth` (it is excluded from Git). The local inference API and Phase 4 limitations are documented in [`backend/README.md`](backend/README.md). No localization weights or annotation JSON files are present in this workspace; the full BTXRD annotation archive must be available before inspecting joins or evaluating a localization model.

## Medical report analyser

Choose **Report analyser**, then select one of the 34 published CC BY 4.0 case excerpts. The server reads its own allowlisted source file and returns extracted text, source-sentence summaries, structured findings and terminology. The separate **My own report · on device** tab accepts text-containing PDF/TXT files up to 5 MB (PDF: up to 80 pages), with local passage search and a clear control. Scanned/encrypted PDFs are unsupported. Personal content is never automatically attached to server RAG. No new report is saved. The legacy PDF/TXT processing utilities remain for offline synthetic tests; their upload, saved-report retrieval, association and question APIs are blocked.

The bilingual **Privacy and data protection** page explains the restricted mode, shows unresolved controller information, offers a locally downloaded rights-request draft and supports erasure of legacy uploads belonging to a verified old browser-session cookie. It does not claim to replace a complete Article 10 notice or a statutory rights process.

Validate with `python -m unittest discover -s backend/tests -v`. Tests cover rejection before body parsing, allowlisted examples without storage, rejection of arbitrary assistant content, non-reflecting errors, security headers, legacy owner-scoped deletion and the public-release gate. Synthetic fixtures remain in `sample_reports/` for internal testing.

## RAG AI Assistant (Phase 6)

RAG AI Assistant accepts editable questions about literature, published cases and heatmaps. Report Analyser includes the same custom-question assistant for its 34 published examples. Suggestions are optional. The server receives the current question and source identifiers, not browser-held personal report text or chat history. The assistant uses a local sentence embedding model, persistent Chroma vectors, hybrid semantic/lexical retrieval, and an optional local Ollama generator. No paid API is used. Its ready state stays disabled until the RAG requirements are installed, permitted sources are ingested, and a local Ollama model is available. See [backend/README.md](backend/README.md) for setup, source licenses, evaluation, and case-context limits. Run the 24-question review set with `python -m backend.rag_eval`; human review is required and no medical accuracy score is claimed.
