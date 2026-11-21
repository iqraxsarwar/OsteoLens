# OsteoLens system integration and quality assurance

**Review date:** 2026-11-16  
**Status:** Academic research prototype; Phase 7 integration and Phase 8 quality review are not complete because the live RAG service and user-interface end-to-end review remain outstanding.

## Architecture

- **Frontend:** React 19 and Vite. The Case Library imports the 30-record manifest from `src/data/cases.json`; original JPEG files are under `public/images/btxrd/`. The same manifest and image directory are read by FastAPI, so case IDs and source image identity are shared.
- **API:** FastAPI in `backend/main.py`. It checksum-verifies the selected source image before inference, provides report processing and report-grounded Q&A, and exposes separate RAG status/chat endpoints.
- **Image model:** ResNet-18 checkpoint at `models/checkpoints/osteolens_btxrd_resnet18.pth`; inference and Grad-CAM are implemented in `training/src/inference.py`. The model outputs are uncalibrated research scores. There is no localization/detection/segmentation model connected.
- **Report Analyser:** Separate React navigation feature and `/api/reports/*` routes. Extracted document text and source-only answers stay distinct from general term definitions. Successful uploads are stored locally with optional explicit case links and deletion.
- **RAG:** Separate assistant page and `/api/assistant/*` routes. The intended local stack uses Sentence Transformers embeddings, persistent Chroma retrieval, lexical rank fusion, and local Ollama generation. The live status endpoint confirms missing retrieval dependencies, no detected index, and unavailable Ollama generation.

## Tests actually run

| Check | Result | Evidence / limit |
|---|---|---|
| Case manifest and assets | Passed | 30 unique case IDs, all 30 images present, unique SHA-256 checksums, all checksums match the manifest. |
| Case filters and viewer state | Passed | `npm test`: 8 tests passed, covering manifest provenance, image formats/missing states, filtering, zoom/pan/reset, and AI visualization availability. |
| Backend report, RAG safeguards, and model tests | Passed | `python -m unittest discover -s backend/tests -v`: 32 passed. FitZ emitted a deprecation warning; PDF extraction passed. This run includes persistence and sample-library tests. |
| Training artifact and annotation-audit tests | Passed | `python -m unittest discover -s training/tests -v`: 9 passed. These test code/artifacts, not a new training run or the full BTXRD archive. |
| Real checkpoint | Passed | Checkpoint metadata matched ResNet-18, 256px input, class order Normal/Benign/Malignant, version `btxrd-resnet18-seed42`; invalid checkpoint and invalid image were rejected. |
| Real model and Grad-CAM | Passed | Five different source images across all three labels produced model scores and image-specific heatmaps/overlays; localization status remained unavailable. |
| FastAPI image-analysis journey | Passed | Five API requests returned their requested Case ID, correct image ID and manifest checksum, probabilities summing to 1, model version, and Grad-CAM overlay. An unknown Case ID returned HTTP 404. |
| Example predictions | Observed, not an evaluation metric | Selected labels/predictions: Normal→Normal; Benign→Benign; Malignant→Benign; Normal→Normal; Normal→Normal. This is a five-image smoke test, not a representative accuracy estimate. |
| Report upload/questions | Passed at API/unit-test level | Tests cover TXT, generated text PDF extraction, follow-up Q&A grounded in report sentences, empty/binary/unsupported inputs. Browser opened a persisted linked report and showed its extracted text. Browser file chooser upload and OCR accuracy were not verified. |
| RAG | Not ready; deliberately failed closed | `GET /api/assistant/status` reported missing retrieval dependencies, no detected index, unavailable Ollama. `POST /api/assistant/chat` returned HTTP 503. No answer, live retrieval, live citation, or 24-question review is claimed. |
| Frontend lint/build | Passed | `npm run lint` passed; Vite production build completed. |
| Browser interaction/responsive sizes | Partial | Browser review opened Case Library, navigated to Report Analyser, reopened a persisted case-linked synthetic report, reviewed extraction and asked a report-grounded question; it also confirmed that the RAG page clearly reports setup required. Dataset Information, browser file chooser upload, full model journey, and tablet/mobile viewports were not browser-tested. |
| Synthetic report sample library | Passed | 25 unique fictional scenarios, four text PDF variants, one scanned-style PDF, and one zero-byte input fixture (31 files total); all are documented as synthetic and not attached to a case. `python -m unittest backend.tests.test_sample_report_library -v`: 5 passed. |
| Local report persistence/link/delete | Passed at API level | Tests cover associated/unassociated upload, list, reopen, restore report Q&A, reject unknown/mismatched cases, unlink, and delete. A browser review opened a linked synthetic report and displayed source-grounded Q&A. |
| Training evaluation metrics | Not available for independent confirmation here | Training notebook can produce held-out metrics, but no evaluation-results artifact was present in this workspace. No accuracy, precision, recall, F1, specificity, sensitivity, confusion matrix, or ROC-AUC is asserted in this report. |

## Feature status

### Works in this workspace

- 30 source-traceable BTXRD sample records and their distinct original images.
- Case selection/filter logic and viewer zoom, pan, reset, original image, and API-produced Grad-CAM views.
- Actual checkpoint loading and inference through FastAPI, with case-image checksum checks.
- Separate Report Analyser with local persistence, optional explicit case linking, saved report reopening, unlink/delete controls, report-grounded Q&A, and the synthetic fixture library available for manual repeats.
- Separate RAG UI and API wiring, including selected-case structured context and explicit unavailable behavior.

### Partial or unavailable

- RAG knowledge ingestion, vector embeddings, retrieval, local generation, citation verification on actual generated answers, and 24-question human evaluation remain unverified because Chroma, Sentence Transformers, an index, and Ollama model/service were absent.
- Case-linked clinical narratives/reports are not supplied by the currently connected BTXRD manifest; those fields correctly remain unavailable. Report Analyser uploads are independent and are not automatically attached to a case.
- Grad-CAM is a classifier attribution visualization, not a confirmed lesion boundary. There is no localization output to connect.
- OCR depends on an external Tesseract installation and language data; Tesseract is absent here. The scanned-style fixture correctly produced an explicit OCR error, but successful OCR and accuracy were not tested.
- Browser file-chooser upload, responsive UI behavior, and OCR success remain unverified. Uploaded reports are stored locally in unencrypted files; do not use identifiable patient reports.
- Classifier outputs are not calibrated and the current five-case smoke test included a malignant source label predicted Benign. Held-out model metrics must be reviewed from the actual run artifacts before academic performance claims.

## API routes

- `GET /api/health` — model/checkpoint and case count status.
- `POST /api/analyze/{case_id}` — verified image inference, scores, Grad-CAM heatmap/overlay, localization availability.
- `POST /api/reports/analyze` — PDF/TXT processing and optional explicit local persistence/linking.
- `GET /api/reports`, `GET /api/reports/item/{report_id}`, `PATCH /api/reports/{report_id}/association`, `DELETE /api/reports/{report_id}` — list, reopen, link/unlink, and delete saved reports.
- `POST /api/reports/ask` — source-grounded report question.
- `GET /api/assistant/status` — local RAG readiness.
- `POST /api/assistant/chat` — evidence retrieval and local answer generation when configured.

FastAPI's interactive schema is available at `http://127.0.0.1:8000/docs` while the backend is running.

## Reproduce local checks

From the project root:

```powershell
python -m unittest discover -s backend/tests -v
python -m unittest discover -s training/tests -v
npm test
npm run lint
npm run build -- --configLoader runner
```

Real checkpoint tests require compatible PyTorch/torchvision and the checkpoint file. They should not be counted as passed if the test runner skips them.

## Remaining work before declaring the system complete

1. Install/configure the optional local RAG stack, ingest only permitted source documents, confirm the index count, and run the 24-question review with human checks of passage relevance, answer support, and citation correctness.
2. Run browser-level tests of navigation, case switching, report upload, assistant state, error/loading states, and representative viewport sizes. Only desktop Case Library was visually opened in this review.
3. Review the actual held-out training metrics and confusion matrix from the saved training run; verify the test split and its patient-level limitations.
4. If OCR is part of the demonstration, run scanned-PDF tests with the actual Tesseract installation.
5. Continue to label localization unavailable unless a separate trained and evaluated localization system is integrated.

Until these items are complete, present OsteoLens as an academic research prototype, not a clinically validated diagnostic system.
