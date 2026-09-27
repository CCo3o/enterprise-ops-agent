"""Deterministic tools used by the enterprise incident agent MVP."""
from __future__ import annotations

import json
import math
import re
from collections import Counter

from .llm import embeddings, enabled as llm_enabled
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def search_logs(query: str, service: str | None = None, limit: int = 20) -> list[dict]:
    """Return matching structured logs without asking an LLM to interpret raw data."""
    needle = query.strip().lower()
    records: list[dict] = []
    with (DATA_DIR / "logs.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            if service and record.get("service") != service:
                continue
            haystack = json.dumps(record, ensure_ascii=False).lower()
            if not needle or needle in haystack:
                records.append(record)
            if len(records) >= limit:
                break
    return records


def get_metric_snapshot(service: str | None = None) -> dict:
    """Return the latest metric snapshot for the demo service."""
    snapshot = json.loads((DATA_DIR / "metrics.json").read_text(encoding="utf-8"))
    if service and snapshot.get("service") != service:
        return {"service": service, "found": False}
    return {**snapshot, "found": True}


def search_docs(query: str, limit: int = 5) -> list[dict]:
    """Local TF-IDF vector search with cosine similarity.

    This is an offline RAG baseline: no API key or vector database is needed.
    The returned source metadata is kept so answers can cite evidence.
    """
    documents: list[tuple[str, str]] = []
    for path in sorted((DATA_DIR / "documents").glob("*.md")):
        documents.append((path.name, path.read_text(encoding="utf-8")))

    if llm_enabled():
        try:
            vectors = embeddings([query] + [text for _, text in documents])
            query_vector = vectors[0]
            def cosine(vector: list[float]) -> float:
                dot = sum(a * b for a, b in zip(query_vector, vector))
                left = math.sqrt(sum(a * a for a in query_vector))
                right = math.sqrt(sum(b * b for b in vector))
                return dot / (left * right) if left and right else 0.0
            scored = sorted(((cosine(vector), source, content) for (source, content), vector in zip(documents, vectors[1:])), reverse=True)
            return [{"source": source, "score": round(score, 4), "content": content} for score, source, content in scored[:limit] if score > 0]
        except Exception:
            pass

    def tokenize(text: str) -> list[str]:
        words = re.findall(r"[a-zA-Z0-9_/-]+|[\u4e00-\u9fff]", text.lower())
        # Character tokens keep Chinese queries useful without a segmenter.
        chars = [text[i:i + 2] for i in range(len(text) - 1) if all("\u4e00" <= c <= "\u9fff" for c in text[i:i + 2])]
        return words + chars

    query_terms = Counter(tokenize(query))
    doc_terms = [Counter(tokenize(text)) for _, text in documents]
    df = Counter(term for terms in doc_terms for term in terms)
    def vector_score(terms: Counter[str]) -> float:
        score = 0.0
        for term, count in query_terms.items():
            if term in terms:
                idf = math.log((1 + len(documents)) / (1 + df[term])) + 1
                score += (1 + math.log(count)) * (1 + math.log(terms[term])) * idf * idf
        return score

    hits = []
    for (source, content), terms in zip(documents, doc_terms):
        score = vector_score(terms)
        if score > 0:
            hits.append({"source": source, "score": round(score, 4), "content": content})
    return sorted(hits, key=lambda item: item["score"], reverse=True)[:limit]
