# OsteoLens

**Bone imaging, understood.**

See [QUALITY_ASSURANCE.md](QUALITY_ASSURANCE.md) for the latest tested/partial/unavailable feature status. A collection of synthetic-only Report Analyser fixtures is provided in [sample_reports/](sample_reports/README.md); these files are not BTXRD records and are never automatically linked to cases.

OsteoLens contains a source-linked library of 60 distinct BTXRD radiograph files, plus a ResNet-18 research inference and Grad-CAM path. The case manifest records source IDs, dataset labels, metadata, citation, license, image path, and SHA-256 checksum. The UI loads the selected record's actual JPEG, supports case filters and image navigation, and can request model inference/Grad-CAM from the local API when its PyTorch runtime is available.

## English and Turkish

Use the **English / Türkçe** controls in the header. The choice persists in this browser. Navigation, controls, case/heatmap explanations and report terminology are translated. Source quotations, publication titles and provenance remain in their original language. Turkish research questions are translated for the existing English-language retrieval index and answers are requested in Turkish using the unchanged Qwen model. Translation quality is not clinically validated.

The report analyser also offers **34 attributed CC BY 4.0 published case excerpts**, independent of the 60 BTXRD image records.

The small Qwen model can fail to follow the requested language or produce unreliable prose. If it returns English for a Turkish request, the assistant gives a Turkish explanation of that limitation and exact original-source quotations instead. Existing conversation messages are not retroactively translated when the interface language changes. Citation presence does not establish clinical accuracy.

## Public deployment

See [DEPLOYMENT.md](DEPLOYMENT.md). Production uses one HTTPS origin for the frontend and API. Private uploads, credentials, model weights, vector databases and generated bundles are excluded from this repository. Publishing this source does not itself deploy the backend.

## Run locally

Requirements: Node.js 20.19+ or 22.12+, Python, and a compatible PyTorch/torchvision installation with enough free disk space for the model runtime. The model checkpoint is already present at `models/checkpoints/osteolens_btxrd_resnet18.pth` in this workspace, but is excluded from Git.

Start the inference API in one terminal:

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
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

## Medical report analyser (Phase 5)

Open **Report analyser** in the left navigation, select a PDF or TXT file, and choose **Analyse report**. The local API displays extracted source text, rule-based fields, report-sentence summaries, term definitions, and document-only question retrieval. Findings and summaries quote the report; they do not provide a diagnosis. Turkish report questions use the existing Qwen service only to translate the search query; original quotations stay in their source language. PDF text extraction uses PyMuPDF; scanned-page OCR works only when Tesseract is separately installed and on `PATH`. See [backend/README.md](backend/README.md) for endpoint, retention, and dependency details.

Validate with `python -m unittest discover -s backend/tests -v`. TXT upload, report Q&A, validation errors, the API route, and generated-PDF extraction pass in this workspace. Scanned-PDF OCR still requires a separately installed Tesseract executable.

For repeatable practice files, use the 31 clearly identified synthetic fixtures in [`sample_reports/README.md`](sample_reports/README.md). The collection includes 25 distinct fictional scenarios, four text PDF variants, an image-only OCR fixture, and an empty invalid-input fixture. Successfully processed uploads are stored on this computer under `backend/data/reports/`; select a case explicitly to associate, and use the report page to unlink or delete it. Local development retains its single-user store. Public mode uses a separate browser-session-isolated store with automatic expiry; storage remains unencrypted. Use public or synthetic documents only. Report context is sent to RAG only after an explicit per-question selection.

## RAG AI Assistant (Phase 6)

RAG AI Assistant is a fourth independent workspace feature; Report Analyser remains separate. The assistant uses a local sentence embedding model, persistent Chroma vectors, hybrid semantic/lexical retrieval, and an optional local Ollama generator. No paid API is used. Its ready state stays disabled until the RAG requirements are installed, permitted sources are ingested, and a local Ollama model is available. See [backend/README.md](backend/README.md) for setup, source licenses, evaluation, and case-context limits. Run the 24-question review set with `python -m backend.rag_eval`; human review is required and no medical accuracy score is claimed.
