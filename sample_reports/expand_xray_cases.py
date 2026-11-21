"""Fetch additional CC BY 4.0 BTXRD images with bounded HTTP range requests."""
import copy
import hashlib
import io
import json
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
import requests

ROOT = Path(__file__).resolve().parents[1]


class RemoteArchive(io.RawIOBase):
    def __init__(self, url, size):
        self.url, self.size, self.position = url, size, 0
        self.session = requests.Session()

    def seekable(self):
        return True

    def seek(self, offset, whence=0):
        self.position = offset + (self.position if whence == 1 else self.size if whence == 2 else 0)
        return self.position

    def tell(self):
        return self.position

    def read(self, size=-1):
        size = self.size - self.position if size < 0 else min(size, self.size - self.position)
        if size <= 0:
            return b""
        start = self.position
        response = self.session.get(self.url, headers={"Range": f"bytes={start}-{start + size - 1}"}, timeout=60, stream=True)
        try:
            response.raise_for_status()
            if response.status_code != 206:
                raise ValueError("Server did not honour the bounded range request")
            data = response.content
            if len(data) != size:
                raise ValueError("Unexpected range length")
            self.position += size
            return data
        finally:
            response.close()


def main():
    metadata = requests.get("https://api.figshare.com/v2/articles/27865398/versions/1", timeout=30).json()
    assert "creativecommons.org/licenses/by/4.0" in metadata["license"]["url"]
    source = next(item for item in metadata["files"] if item["id"] == 50653575)
    archive = zipfile.ZipFile(RemoteArchive(source["download_url"], source["size"]))
    workbook = zipfile.ZipFile(io.BytesIO(archive.read("BTXRD/dataset.xlsx")))
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    strings = ["".join(node.itertext()) for node in ET.fromstring(workbook.read("xl/sharedStrings.xml"))]
    rows = []
    for row in ET.fromstring(workbook.read("xl/worksheets/sheet1.xml")).findall(".//s:row", ns):
        values = {}
        for cell in row:
            value = cell.find("s:v", ns)
            if value is not None:
                values[cell.attrib["r"].rstrip("0123456789")] = strings[int(value.text)] if cell.attrib.get("t") == "s" else value.text
        rows.append(values)
    manifest_path = ROOT / "src/data/cases.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = manifest["cases"]
    names = {item["image_id"] for item in cases}
    hashes = {item["sha256"] for item in cases}
    headings = rows[0]
    for label in ("Normal", "Benign", "Malignant"):
        for row in rows[1:]:
            if sum(item["classification"] == label for item in cases) >= 20:
                break
            row_label = "Malignant" if row.get("V") == "1" else "Benign" if row.get("U") == "1" else "Normal"
            if row_label != label or row["A"] in names:
                continue
            name = row["A"]
            content = archive.read(f"BTXRD/images/{name}")
            digest = hashlib.sha256(content).hexdigest()
            if digest in hashes:
                continue
            if not content.startswith(b"\xff\xd8") or not content.endswith(b"\xff\xd9"):
                raise ValueError(f"Invalid JPEG: {name}")
            record = copy.deepcopy(cases[0])
            record.update({"case_id": f"BTXRD-{Path(name).stem}", "image_id": name,
                           "image_path": f"/images/btxrd/{name}", "sha256": digest,
                           "source_archive_path": f"BTXRD/images/{name}", "classification": label,
                           "anatomical_location": [headings[key].replace("-", " ").title() for key in
                               ["E","F","G","H","I","J","K","L","M","N","O","P","Q","R","S","AF","AG","AH"] if row.get(key) == "1"],
                           "source_subtype": next((headings[key] for key in ["W","X","Y","Z","AA","AB","AC","AD","AE"] if row.get(key) == "1"), None),
                           "metadata": {"collection_center": int(row["B"]), "age_years": float(row["C"]),
                                        "sex": row["D"], "projection": [headings[key].title() for key in ["AI","AJ","AK"] if row.get(key) == "1"]}})
            (ROOT / "public/images/btxrd" / name).write_bytes(content)
            cases.append(record)
            names.add(name)
            hashes.add(digest)
            print(f"{len(cases)} {record['case_id']} {label}", flush=True)
    manifest["dataset"]["selection_note"] = "60 source image records, 20 per broad class, from the official CC BY 4.0 BTXRD v1 archive. Image records may share patients. Structured metadata is supplied without clinical narratives."
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
