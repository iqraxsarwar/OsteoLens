"""Download permitted source text, chunk, embed, and persist it in local Chroma."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from backend.rag_assistant import CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = Path(__file__).with_name("rag_sources.json")
SOURCE_CACHE = CHROMA_DIR.parent / "source_cache"
USER_AGENT = "OsteoLensAcademicResearch/1.0 (source text retrieval; contact via project README)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})


def _fetch(url: str) -> bytes:
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            response = SESSION.get(url, timeout=(10, 40))
            response.raise_for_status()
            if len(response.content) > 30 * 1024 * 1024:
                raise ValueError(f"Source document exceeds 30 MiB: {url}")
            return response.content
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Could not retrieve source {url}: {last_error}")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].casefold()


def _first_text(root: ET.Element, name: str) -> str | None:
    for element in root.iter():
        if _local_name(element.tag) == name.casefold():
            text = " ".join("".join(element.itertext()).split())
            if text:
                return text
    return None


def _pmc_text(source: dict[str, Any]) -> dict[str, Any]:
    pmcid = source["pmcid"]
    endpoint = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
    payload = _fetch(endpoint)
    root = ET.fromstring(payload)
    license_nodes = [element for element in root.iter() if _local_name(element.tag) == "license"]
    license_text = " ".join(" ".join("".join(element.itertext()).split()) for element in license_nodes)
    license_hrefs = " ".join(value for element in license_nodes for key, value in element.attrib.items() if key.rsplit("}",1)[-1].casefold() in {"href", "{http://www.w3.org/1999/xlink}href"})
    license_evidence = (license_text + " " + license_hrefs).casefold()
    if "creativecommons.org/licenses/by/4.0" not in license_evidence and not re.search(r"creative commons attribution 4\.0", license_evidence):
        raise ValueError(f"{pmcid} was not verified as CC BY 4.0; it will not be ingested. Observed license: {license_text[:300]}")
    title = _first_text(root, "article-title") or source["title"]
    authors = []
    for person in root.iter():
        if _local_name(person.tag) == "contrib" and person.attrib.get("contrib-type") == "author":
            names = []
            for child in person.iter():
                if _local_name(child.tag) in {"surname", "given-names"} and child.text:
                    names.append(child.text.strip())
            if names:
                authors.append(" ".join(names))
    publication_date = None
    for element in root.iter():
        if _local_name(element.tag) == "pub-date":
            parts = [child.text.strip() for child in element if _local_name(child.tag) in {"year", "month", "day"} and child.text]
            if parts:
                publication_date = "-".join(parts)
                break
    chunks = []
    body = next((element for element in root.iter() if _local_name(element.tag) == "body"), None)
    if body is None:
        raise ValueError(f"No article body was found for {pmcid}.")

    def reusable_paragraphs(element: ET.Element) -> list[str]:
        name = _local_name(element.tag)
        if name in {"fig", "table-wrap", "supplementary-material", "media", "graphic"}:
            return []
        if name == "p":
            value = " ".join("".join(element.itertext()).split())
            return [value] if len(value) > 60 else []
        return [paragraph for child in element for paragraph in reusable_paragraphs(child)]

    for section in body:
        if _local_name(section.tag) != "sec":
            continue
        section_title = next((_first_text(child, "title") for child in section if _local_name(child.tag) == "title"), None)
        paragraphs = reusable_paragraphs(section)
        if paragraphs:
            chunks.append((section_title or "Article body", "\n\n".join(paragraphs)))
    if not chunks:
        raise ValueError(f"No usable article paragraphs were found for {pmcid}.")
    return {"title": title, "author_or_institution": ", ".join(authors) or source["institution"],
            "publication_date": publication_date, "url": source["url"], "license": "CC BY 4.0",
            "source_type": "peer-reviewed article", "chunks": chunks}


def _nci_text(source: dict[str, Any]) -> dict[str, Any]:
    payload = _fetch(source["url"])
    soup = BeautifulSoup(payload, "html.parser")
    main = soup.find("main") or soup.find("article") or soup
    for element in main.select("script, style, nav, footer, header, form, .related-resources, .share-tools"):
        element.decompose()
    title = (main.find("h1") or soup.find("h1"))
    title_text = " ".join(title.get_text(" ", strip=True).split()) if title else source["title"]
    publication_date = None
    for attr in ("article:modified_time", "og:updated_time", "dateModified", "article:published_time"):
        tag = soup.find("meta", attrs={"property": attr}) or soup.find("meta", attrs={"name": attr})
        if tag and tag.get("content"):
            publication_date = tag["content"][:10]
            break
    sections = []
    current_heading = title_text
    current_paragraphs: list[str] = []
    for element in main.find_all(["h2", "h3", "h4", "p", "li", "tr"]):
        text = " ".join(element.get_text(" ", strip=True).split())
        if not text:
            continue
        if element.name.startswith("h"):
            if current_paragraphs:
                sections.append((current_heading, "\n\n".join(current_paragraphs)))
                current_paragraphs = []
            current_heading = text
        elif len(text) > (25 if element.name == "tr" else 50):
            current_paragraphs.append(text)
    if current_paragraphs:
        sections.append((current_heading, "\n\n".join(current_paragraphs)))
    if not sections:
        raise ValueError(f"No usable page text was extracted from {source['url']}.")
    return {"title": title_text, "author_or_institution": source.get("author", source["institution"]),
            "publication_date": publication_date, "url": source["url"],
            "license": "NCI text reuse policy (credit NCI; see linked policy)", "source_type": "NCI medical reference", "chunks": sections}


def _split_text(text: str, max_chars: int = 1400, overlap: int = 180) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    output: list[str] = []
    current = ""
    for paragraph in paragraphs:
        while len(paragraph) > max_chars:
            if current:
                output.append(current)
                current = ""
            cut = paragraph.rfind(" ", 0, max_chars)
            cut = cut if cut > max_chars // 2 else max_chars
            output.append(paragraph[:cut].strip())
            paragraph = paragraph[max(0, cut - overlap):].strip()
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > max_chars and current:
            output.append(current)
            current = f"{current[-overlap:]}\n\n{paragraph}" if overlap else paragraph
        else:
            current = candidate
    if current:
        output.append(current)
    return [chunk for chunk in output if len(chunk) >= 120]


def load_permitted_documents() -> list[dict[str, Any]]:
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    documents = []
    rejected = []
    for source in manifest["sources"]:
        try:
            document = _nci_text(source) if source["kind"] == "nci_html" else _pmc_text(source)
            documents.append(document)
            print(f"Verified {document['source_type']}: {document['title']} ({document['license']})")
        except Exception as exc:
            rejected.append({"source": source.get("url"), "reason": str(exc)})
            print(f"SKIPPED source: {source.get('url')} — {exc}")
    if not documents:
        raise RuntimeError("No sources could be safely ingested. Check network access and source licenses.")
    SOURCE_CACHE.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat()
    cache_records = []
    for document in documents:
        cache_records.append({key: document[key] for key in ("title", "author_or_institution", "publication_date", "url", "license", "source_type")})
    (SOURCE_CACHE / "source_inventory.json").write_text(json.dumps({"fetched_at": fetched_at, "sources": cache_records, "rejected": rejected}, indent=2, ensure_ascii=False), encoding="utf-8")
    return documents


def build_index(rebuild: bool = False) -> dict[str, Any]:
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("Install backend/rag-requirements.txt before building the RAG index.") from exc
    documents = load_permitted_documents()
    model = SentenceTransformer(EMBEDDING_MODEL, device="cpu")
    chunks: list[str] = []
    metadatas: list[dict[str, Any]] = []
    ids: list[str] = []
    for document in documents:
        for section, text in document["chunks"]:
            for index, chunk in enumerate(_split_text(text)):
                chunk_id = hashlib.sha256(f"{document['url']}|{section}|{index}|{chunk}".encode()).hexdigest()
                ids.append(chunk_id)
                chunks.append(chunk)
                metadatas.append({
                    "title": document["title"], "author_or_institution": document["author_or_institution"],
                    "publication_date": document["publication_date"] or "Date unavailable in source metadata",
                    "url": document["url"], "license": document["license"], "source_type": document["source_type"],
                    "section": section[:500], "chunk_index": index,
                })
    if not chunks:
        raise RuntimeError("Source text was extracted, but no chunks were long enough to index.")
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    if rebuild:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
    collection = client.get_or_create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine", "embedding_model": EMBEDDING_MODEL})
    embeddings = model.encode(chunks, batch_size=32, normalize_embeddings=True, show_progress_bar=True).tolist()
    # Upsert is repeatable; records are keyed by content hash.
    for start in range(0, len(chunks), 128):
        end = min(start + 128, len(chunks))
        collection.upsert(ids=ids[start:end], documents=chunks[start:end], metadatas=metadatas[start:end], embeddings=embeddings[start:end])
        print(f"Indexed {end:,}/{len(chunks):,} chunks")
    return {"source_documents": len(documents), "indexed_chunks": collection.count(), "embedding_model": EMBEDDING_MODEL,
            "vector_store": "Chroma persistent local", "path": str(CHROMA_DIR)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true", help="Delete and rebuild the local collection")
    args = parser.parse_args()
    print(json.dumps(build_index(rebuild=args.rebuild), indent=2))
