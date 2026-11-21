# Phase 1 data sources and attribution

## November 2026 library expansion

The current manifest contains 60 distinct BTXRD source images, 20 in each broad class. The original 30 records are retained. Additional images and structured metadata were read from the official v1 archive through bounded HTTP ranges, with ZIP CRC checks and per-image SHA-256 checks. The image-record count does not establish patient-level uniqueness.

The Report Analyser also offers published case-section excerpts from Europe PMC. Each entry in `src/data/openAccessReports.json` records its article title, authors, source URL, publication date, extracted section headings and CC BY 4.0 licence. Text is stored in `public/case_reports/` with attribution. These published case reports have independent provenance from BTXRD and are loaded without automatic X-ray association. The existing synthetic test documents remain labelled synthetic.

Reproducible import scripts are `sample_reports/expand_xray_cases.py` and `sample_reports/import_open_access.py`. The historical 60-image selection details below describe the initial subset.

## BTXRD sample images

- **Dataset:** Bone Tumor X-ray Radiograph Dataset (BTXRD), version 1.
- **Primary record:** [Figshare DOI 10.6084/m9.figshare.27865398.v1](https://doi.org/10.6084/m9.figshare.27865398.v1)
- **Archive file:** `BTXRD.zip`, Figshare file ID `50653575`; source record reports 840,474,929 bytes and MD5 `59132a5036d030580ccade8add8f13df`.
- **License on publisher record:** [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/). Attribution is included in every manifest record and this file.
- **Paper citation:** Yao S, Huang Y, Wang X, et al. A Radiograph Dataset for the Classification, Localization, and Segmentation of Primary Bone Tumors. *Scientific Data*. 2025;12:88. [https://doi.org/10.1038/s41597-024-04311-y](https://doi.org/10.1038/s41597-024-04311-y).
- **Source formats checked:** archive index, `BTXRD/dataset.xlsx` (3,746 image rows), `BTXRD/images/` JPEG/JPG entries, and `BTXRD/Annotations/` JSON entries. The dataset paper describes the images and their structured metadata/annotations.
- **Sample selection:** 60 image records, twenty each labeled Normal, Benign, and Malignant by the source metadata. The sample is a demonstration subset, not a training/evaluation split. Every included image has its original BTXRD image ID, archive path, SHA-256, source label, anatomical field(s), projection, collection-center code, and source-provided age/sex values where present in the metadata.
- **Patient linkage limitation:** the inspected metadata identifies image records, not a verified patient-level key. Some records may belong to the same person/study; this project does not claim 60 distinct patients.
- **Narrative limitation:** BTXRD's included metadata is structured, not a free-text radiology or teaching report. `clinical_description` is `null` for all 60 records. The UI explicitly says no narrative is provided.
- **Archive handling:** to avoid storing the 840 MB archive, the selected images and metadata entry were retrieved by HTTP byte ranges from the official archive. Each image was inflated, checked for JPEG markers, and SHA-256 hashed. The full archive was not downloaded locally, so the archive-wide MD5 was not independently recalculated; the MD5 above is copied from the Figshare API record.

## MedPix feasibility decision

MedPix is described by the U.S. National Library of Medicine's data catalog as an image-and-text patient-case resource, and the catalog lists programmatic access through the Open-i API. That makes it a potential linked case source in principle. However, those facts do not grant reuse rights for every contributed image. MedPix/Open-i usage notes state that image reuse depends on the rights attached to each individual image; library guidance summarizing MedPix's licensing terms says cases are for personal/local teaching and that other uses require permission from the contributor.

**Decision for Phase 1:** no MedPix case or image is bundled. We did not verify a set of at least 30 suitable bone-tumour radiograph cases with image-specific permission to redistribute in OsteoLens. The MedPix licensing landing page redirected during inspection, preventing confirmation of its current primary-page details. Reconsider only after querying Open-i, recording stable case/image identifiers, confirming modality and image/text linkage, and recording each image's explicit license or contributor permission. Link-out may be possible even where redistribution is not.

## External references

- BTXRD paper: [Nature Scientific Data](https://www.nature.com/articles/s41597-024-04311-y)
- BTXRD Figshare API record: [Figshare public API](https://api.figshare.com/v2/articles/27865398)
- MedPix catalog and Open-i API pointer: [Data.gov / NLM MedPix](https://catalog.data.gov/dataset/medpix)
- Open-i image reuse depends on each image's attached license: [Open-i FAQ](https://openi-vip.nlm.nih.gov/faq)
- MedPix licensing URL (redirected at inspection): [MedPix licensing](https://medpix.nlm.nih.gov/licensing)

## Separate Phase 3 training workflow

`training/` contains the Colab notebook and inference contract for the full BTXRD archive. This does not replace or expand the 60-image website sample in `src/data/cases.json` and `public/images/btxrd/`. The full archive, metadata sheet, and annotations were not stored in this repository. See `training/README.md` for the data layout expected by the notebook, run instructions, patient/study split limitation, and research-only inference contract.

## Published report excerpts

The report selector contains 34 published case-section excerpts. `src/data/openAccessReports.json` records each title, author/institution, publication date, source URL, CC BY 4.0 licence and bundled excerpt path. Each text file in `public/case_reports/` preserves its attribution. These are independent publications, not clinical reports linked to BTXRD images.
