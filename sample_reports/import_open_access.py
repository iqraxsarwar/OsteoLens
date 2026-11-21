"""Build the selectable report corpus from licensed published case sections."""
import json
from pathlib import Path
import re
import time
import sys

from backend.rag_ingest import SESSION, _pmc_text

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "public" / "case_reports"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    DEST.mkdir(parents=True, exist_ok=True)
    records = []
    seen = set()
    for topic in ("osteosarcoma", "osteochondroma", "giant cell tumor bone", "Ewing sarcoma", "chondrosarcoma", "aneurysmal bone cyst"):
        response = SESSION.get(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            params={"query": f'({topic}) AND TITLE:"case report" AND OPEN_ACCESS:Y',
                    "format": "json", "pageSize": 50}, timeout=40,
        )
        response.raise_for_status()
        count = 0
        for hit in response.json()["resultList"]["result"]:
            pmcid = hit.get("pmcid")
            if not pmcid or pmcid in seen:
                continue
            seen.add(pmcid)
            try:
                source = _pmc_text({"pmcid": pmcid, "title": hit["title"],
                                    "institution": hit.get("authorString", ""),
                                    "url": f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"})
                sections = [(heading, text) for heading, text in source["chunks"]
                            if re.search(r"case|presentation|patient", heading, re.I)]
                if not sections:
                    continue
                text = "\n\n".join(f"{heading}\n{body}" for heading, body in sections)
                record = {key: value for key, value in source.items() if key != "chunks"}
                record.update({"id": pmcid, "topic": topic, "path": f"/case_reports/{pmcid}.txt",
                               "section_titles": [heading for heading, _ in sections]})
                attribution = (f"Published case report excerpt\n{source['title']}\n"
                               f"{source['author_or_institution']}\n{source['url']}\n"
                               "CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/\n"
                               "Case sections extracted from the published article.\n\n")
                (DEST / f"{pmcid}.txt").write_text(attribution + text, encoding="utf-8")
                records.append(record)
                (ROOT / "src" / "data" / "openAccessReports.json").write_text(
                    json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
                count += 1
                print(f"{len(records)} {pmcid} {source['title']}", flush=True)
                if count == 6:
                    break
            except Exception as exc:
                print(f"Skipped {pmcid}: {exc}", flush=True)
            time.sleep(0.2)
    if len(records) <= 30:
        raise RuntimeError(f"Only {len(records)} licensed case reports found")
    (ROOT / "src" / "data" / "openAccessReports.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
