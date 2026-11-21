"""Generate the clearly fictional OsteoLens report-analyser test corpus.

All source text in this file is synthetic and is not based on a patient record.
Run from the project root with: python sample_reports/build_sample_library.py
PyMuPDF is needed to generate the PDF variants.
"""

from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
MARKER = "SYNTHETIC TEST DOCUMENT – NOT A REAL PATIENT RECORD"

REPORTS = [
    ("synthetic/normal/radiograph_normal.txt", "Normal radiograph", "Bone radiograph", "The synthetic left femur radiograph shows preserved alignment and mineralisation. No focal lytic or sclerotic lesion, cortical destruction, periosteal reaction, or fracture is identified. Impression: no focal osseous abnormality in this fictional example."),
    ("synthetic/normal/radiograph_followup_normal.txt", "Normal follow-up radiograph", "Follow-up radiograph", "Comparison is made with the prior synthetic radiograph dated 2025-01-10. The previously described cortical irregularity is not reproduced. No focal bone lesion or acute fracture is seen. Impression: no progressive osseous finding in this fictional follow-up example."),
    ("synthetic/benign/osteochondroma_xray.txt", "Osteochondroma radiograph", "Bone radiograph", "A synthetic exophytic osseous projection arises from the posteromedial distal femoral metaphysis. The cortex and medullary cavity appear continuous with the parent bone. No aggressive periosteal reaction is described. Impression: appearance is compatible with osteochondroma in this fictional report; clinical correlation is advised."),
    ("synthetic/benign/osteochondroma_mri.txt", "Osteochondroma MRI", "MRI report", "MRI of the synthetic proximal humerus demonstrates a pedunculated metaphyseal lesion with corticomedullary continuity. The cartilage cap is measured at 8 mm in this fictional example. No adjacent soft-tissue mass is identified. Impression: osteochondroma; correlate with symptoms and prior imaging."),
    ("synthetic/benign/giant_cell_tumour_mri.txt", "Giant cell tumour MRI", "MRI report", "A synthetic eccentric, expansile lytic lesion extends to the subarticular region of the distal radius. The cortex is thinned but appears intact. No definite extraosseous component is identified. The imaging differential includes giant cell tumour of bone. Tissue diagnosis is not provided in this report."),
    ("synthetic/benign/giant_cell_tumour_ct.pdf.txt", "Giant cell tumour CT", "CT report", "CT of the synthetic distal femur shows a well-defined expansile lytic lesion with a narrow transition zone and no mineralised matrix. There is cortical thinning without a displaced fracture. Imaging appearance may be seen with a giant cell tumour, among other entities. Histology is not available."),
    ("synthetic/benign/simple_bone_cyst_xray.txt", "Simple bone cyst radiograph", "Bone radiograph", "The synthetic proximal humerus contains a central, geographic lucency with a narrow zone of transition and mild cortical thinning. No aggressive periosteal reaction is described. Impression: a simple bone cyst is in the differential. No fracture is identified."),
    ("synthetic/benign/aneurysmal_bone_cyst_mri.txt", "Aneurysmal bone cyst MRI", "MRI report", "MRI demonstrates a synthetic expansile multiloculated lesion in the posterior elements of a fictional long bone. Multiple fluid-fluid levels are present. These findings are nonspecific and can occur in an aneurysmal bone cyst. The report does not establish a final diagnosis; specialist review is recommended."),
    ("synthetic/benign/enostosis_ct.txt", "Enostosis CT", "CT report", "A small, sharply marginated sclerotic focus is present in the synthetic iliac bone. No cortical destruction or soft-tissue component is seen. Impression: likely enostosis in this fictional example. No prior study is supplied for comparison."),
    ("synthetic/malignant/osteosarcoma_xray.txt", "Osteosarcoma radiograph", "Bone radiograph", "The synthetic distal femoral metaphysis contains an aggressive mixed lytic and sclerotic lesion with interrupted periosteal reaction and a possible adjacent soft-tissue component. Impression: aggressive bone lesion; osteosarcoma is included in the differential. This imaging report is not histopathologic confirmation."),
    ("synthetic/malignant/osteosarcoma_mri_staging.txt", "Osteosarcoma MRI staging", "MRI report", "MRI of the synthetic distal femur describes marrow replacement over 11 cm, cortical breach, and an extraosseous soft-tissue component. The neurovascular bundle is reported as separate from the lesion. Findings are concerning for a primary bone malignancy; histology and staging results are not included."),
    ("synthetic/malignant/ewing_sarcoma_mri.txt", "Ewing sarcoma MRI", "MRI report", "A synthetic diaphyseal lesion in the tibia has low T1 and heterogeneous high fluid-sensitive signal with an adjacent soft-tissue component. The imaging appearance is aggressive but nonspecific. Ewing sarcoma is mentioned in the differential. Biopsy and clinical staging are not supplied."),
    ("synthetic/malignant/chondrosarcoma_ct.txt", "Chondrosarcoma CT", "CT report", "CT shows a synthetic central chondroid matrix lesion in the pelvis with ring-and-arc mineralisation and focal endosteal scalloping. No extraosseous mass is described. The report states that imaging alone cannot determine grade; correlation with MRI and tissue sampling is suggested."),
    ("synthetic/malignant/histopath_osteosarcoma.txt", "Osteosarcoma histopathology", "Histopathology report", "Synthetic core biopsy material contains atypical spindle cells associated with malignant osteoid in the sampled tissue. The fictional pathology impression is osteosarcoma. This sample report gives no patient identifiers, stage, margins, or treatment plan."),
    ("synthetic/malignant/oncology_consult.txt", "Oncology consultation", "Oncology consultation", "This fictional consultation records referral for an aggressive proximal tibial lesion described on outside imaging. The referring differential includes osteosarcoma and Ewing sarcoma. The source images and pathology are not available to this note. Plan recorded in this synthetic example: multidisciplinary review and biopsy planning."),
    ("synthetic/malignant/followup_posttreatment.txt", "Post-treatment follow-up", "Oncology follow-up", "The synthetic follow-up MRI describes decreased size of the previously measured extraosseous component after fictional neoadjuvant treatment. Marrow signal remains abnormal. No comparison measurements are provided here. This text does not establish treatment response category or recommend a change in care."),
    ("synthetic/inconclusive/inconclusive_mri.txt", "Indeterminate MRI lesion", "MRI report", "An indeterminate marrow lesion is present in the synthetic proximal fibula. Signal characteristics are not specific. No cortical breakthrough is identified. The report recommends correlation with radiographs and interval imaging; no diagnosis is stated."),
    ("synthetic/incomplete/missing_diagnosis.txt", "Report without diagnosis", "Bone radiograph", "Synthetic report: there is a 2.1 cm lucent focus in the left calcaneus. Margins are incompletely described. No fracture is mentioned. Impression: [not provided]. Recommendation: [not provided]."),
    ("synthetic/incomplete/poorly_structured.txt", "Poorly structured report", "Unstructured imaging note", "SYNTHETIC TEST DOCUMENT – NOT A REAL PATIENT RECORD\nXR tibia. metaphysis? lucency noted. Cortex maybe intact. Comparison none. Recommend MRI if clinically needed. diagnosis not entered."),
    ("synthetic/inconclusive/conflicting_findings.txt", "Conflicting findings", "MRI report", "The findings section of this fictional report describes an intact cortex and no soft-tissue component. The impression section states that cortical breakthrough with a soft-tissue mass is present. These statements conflict within the supplied synthetic text. No clarification or final diagnosis is provided."),
    ("synthetic/incomplete/unsupported_terminology.txt", "Unsupported terminology", "Imaging report", "Synthetic report: a 14 mm intramedullary focus is seen in the fictional ulna. The term 'trabeculoplastic hyperdensity' appears in the source note but is not defined here. No diagnosis or recommendation is supplied."),
    ("synthetic/normal/no_malignancy_mention.txt", "No mention of malignancy", "Bone radiograph", "Synthetic radiograph of the right hand: joint spaces are maintained. No acute fracture or focal osseous lesion is identified. The report contains no statement about malignancy or tumour diagnosis."),
    ("synthetic/malignant/pathologic_fracture.txt", "Pathologic fracture report", "CT report", "CT describes a synthetic fracture through a pre-existing lytic lesion in the proximal humeral shaft. The lesion has cortical thinning and a small extraosseous component. The report raises concern for an underlying neoplasm but does not state a tumour type. Tissue diagnosis is unavailable."),
    ("synthetic/malignant/metastatic_lesion.txt", "Secondary bone lesion", "Oncology imaging note", "A synthetic CT note describes multiple sclerotic foci in the vertebral bodies in a fictional patient with a separately stated history of carcinoma. The note says osseous metastatic disease is a consideration. The primary pathology and current staging are not included in this document."),
    ("synthetic/benign/osteoid_osteoma_ct.txt", "Osteoid osteoma CT", "CT report", "Thin-section CT shows a synthetic 6 mm cortical lucency with central mineralisation in the proximal femur and surrounding sclerosis. The appearance may represent an osteoid osteoma in this fictional example. No biopsy result or treatment recommendation is included."),
]

PDF_SOURCES = {
    "synthetic/normal/radiograph_normal.pdf": "synthetic/normal/radiograph_normal.txt",
    "synthetic/benign/osteochondroma_xray.pdf": "synthetic/benign/osteochondroma_xray.txt",
    "synthetic/malignant/osteosarcoma_xray.pdf": "synthetic/malignant/osteosarcoma_xray.txt",
    "synthetic/inconclusive/inconclusive_mri.pdf": "synthetic/inconclusive/inconclusive_mri.txt",
}


def _safe_name(path: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", path)


def main() -> None:
    report_text = {path: f"{MARKER}\n\nTEST TITLE: {title}\nMODALITY / DOCUMENT TYPE: {kind}\n\n{body}\n" for path, title, kind, body in REPORTS}
    for relative_path, contents in report_text.items():
        destination = ROOT / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(contents, encoding="utf-8")

    # An actually empty upload fixture cannot contain the report disclaimer;
    # its adjacent manifest entry labels it as a synthetic invalid-input case.
    empty_path = ROOT / "synthetic/incomplete/empty_report.txt"
    empty_path.parent.mkdir(parents=True, exist_ok=True)
    empty_path.write_bytes(b"")

    import fitz

    for pdf_path, txt_path in PDF_SOURCES.items():
        contents = report_text[txt_path]
        destination = ROOT / pdf_path
        doc = fitz.open()
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(54, 48, 540, 750), contents, fontsize=11, fontname="helv", lineheight=1.4)
        destination.parent.mkdir(parents=True, exist_ok=True)
        doc.save(destination)
        doc.close()

    # Raster-only duplicate for exercising the OCR path; without Tesseract the
    # analyser must report OCR unavailable instead of pretending extraction worked.
    source_text = report_text["synthetic/benign/simple_bone_cyst_xray.txt"]
    source_doc = fitz.open()
    source_page = source_doc.new_page()
    source_page.insert_textbox(fitz.Rect(54, 48, 540, 750), source_text, fontsize=11, fontname="helv", lineheight=1.4)
    pixmap = source_page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    raster_pdf = fitz.open()
    raster_page = raster_pdf.new_page(width=612, height=792)
    raster_page.insert_image(raster_page.rect, stream=pixmap.tobytes("png"))
    scan_path = ROOT / "synthetic/scanned_ocr/simple_bone_cyst_scanned_style.pdf"
    scan_path.parent.mkdir(parents=True, exist_ok=True)
    raster_pdf.save(scan_path)
    raster_pdf.close()
    source_doc.close()

    manifest = {
        "notice": MARKER,
        "licensing": "All reports are fictional synthetic test content generated specifically for OsteoLens. They are not derived from real patient records or copied from published reports. No BTXRD case is associated automatically.",
        "unique_scenarios": len(REPORTS),
        "documents": [],
    }
    for relative_path, title, kind, _body in REPORTS:
        manifest["documents"].append({"path": relative_path.replace("\\", "/"), "title": title, "document_type": kind, "format": "TXT", "source_status": "synthetic", "license": "Project-created synthetic content"})
    for pdf_path, txt_path in PDF_SOURCES.items():
        title = next(item[1] for item in REPORTS if item[0] == txt_path)
        manifest["documents"].append({"path": pdf_path, "title": f"{title} (PDF text extraction variant)", "document_type": "PDF", "format": "PDF", "source_status": "synthetic format variant", "license": "Project-created synthetic content"})
    manifest["documents"].append({"path": "synthetic/scanned_ocr/simple_bone_cyst_scanned_style.pdf", "title": "Simple bone cyst scanned-style OCR fixture", "document_type": "Scanned-style PDF", "format": "image-only PDF", "source_status": "synthetic format variant", "license": "Project-created synthetic content"})
    manifest["documents"].append({"path": "synthetic/incomplete/empty_report.txt", "title": "Empty report validation fixture", "document_type": "Empty invalid-input fixture", "format": "empty TXT", "source_status": "synthetic invalid-input fixture; intentionally zero bytes", "license": "Project-created synthetic content"})
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated {len(REPORTS)} synthetic scenarios and {len(manifest['documents'])} uploadable documents under {ROOT}")


if __name__ == "__main__":
    main()
