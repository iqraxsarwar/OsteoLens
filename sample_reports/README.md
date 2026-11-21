# OsteoLens synthetic report test library

All documents in this folder are fictional test fixtures. They begin with **“SYNTHETIC TEST DOCUMENT – NOT A REAL PATIENT RECORD”** and are not based on BTXRD patients, clinical records, or published case reports. Nothing in this library is automatically attached to a Case ID.

## Contents

- `synthetic/`: 25 distinct text scenarios (normal, benign, malignant, inconclusive, incomplete, conflicting, and poorly structured examples).
- Four text-based PDF variants for testing PDF extraction.
- `synthetic/scanned_ocr/simple_bone_cyst_scanned_style.pdf`: image-only synthetic PDF for testing OCR. OCR only works if Tesseract and its English language data are separately installed.
- `synthetic/incomplete/empty_report.txt`: intentionally zero-byte invalid-input fixture. Its synthetic status is recorded in the manifest because a genuinely empty file cannot contain an in-file disclaimer.
- `manifest.json`: inventory, scenario title, format and synthetic provenance for every document.
- `build_sample_library.py`: reproducibly creates the fixture files using only the included fictional report content; PyMuPDF is required for PDFs.

There are **31 uploadable files** representing **25 unique report scenarios**, plus an empty-file validation fixture. PDF variants are alternate file formats of existing synthetic scenarios, not additional clinical cases. No public research report is redistributed because permission for those items was not established.

## Upload and test

1. Start OsteoLens locally (backend and Vite frontend; see the project [README](../README.md)).
2. Open **Report analyser** in the left navigation.
3. Choose **Choose file**, then select any `.txt` or text-based `.pdf` from this folder.
4. Select **Analyse report**. Check the original extracted text first; it should contain the synthetic notice and the content in the source fixture.
5. Review the extracted fields. Unsupported/missing values should remain unavailable. The summary is extractive, not a generated diagnosis.
6. Ask a question answered by the document, then one not answered by it. The first should quote matching source sentences; the second should say the document does not contain enough information.
7. Try `synthetic/incomplete/empty_report.txt` for the empty-document validation response.
8. Try the scanned-style PDF. If Tesseract is absent, an explicit OCR-unavailable error is expected and counts as correct failure handling, not successful OCR.

The analyser currently holds uploaded report text in backend memory for its question session and does **not** persist, associate, unlink, or delete reports. That separate case-linking feature has not yet been implemented. Do not put real patient-identifiable documents into this prototype.

## Useful fixtures

| Path | Test purpose |
|---|---|
| `synthetic/normal/radiograph_normal.txt` | Clear normal radiograph and negative finding phrases |
| `synthetic/benign/osteochondroma_xray.pdf` | PDF text extraction and benign terminology |
| `synthetic/malignant/osteosarcoma_mri_staging.txt` | Malignant concern, imaging findings, missing histology/stage |
| `synthetic/inconclusive/conflicting_findings.txt` | Contradictory findings that should not be reconciled by invention |
| `synthetic/incomplete/missing_diagnosis.txt` | Explicit missing impression and recommendation |
| `synthetic/incomplete/unsupported_terminology.txt` | Unknown phrase that should not receive an invented definition |
| `synthetic/normal/no_malignancy_mention.txt` | No tumour/malignancy statement in source |
| `synthetic/scanned_ocr/simple_bone_cyst_scanned_style.pdf` | Image-only PDF / optional OCR path |

Regenerate the included files from project root with:

```powershell
python sample_reports/build_sample_library.py
```

This overwrites only files inside `sample_reports/` and regenerates the declared synthetic fixtures.
