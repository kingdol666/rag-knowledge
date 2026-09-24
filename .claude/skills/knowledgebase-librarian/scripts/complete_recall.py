#!/usr/bin/env python3
"""Complete-recall manifest orchestrator for the librarian skill.

The Archival agent performs L0/L2/L4 MCP reads and writes their results to a
manifest. This script intentionally does not call HTTP/MCP itself. It performs
only high-recall catalog classification, structure-aware segmentation, and the
single fail-closed Jev filtering/aggregation step.

Manifest shape::

  {
    "query": "...",
    "threshold": 0.5,
    "max_segment_chars": 3000,
    "knowledge_bases": [{"kb_id": "...", "name": "...", "description": "..."}],
    "documents": [{"kb_id": "...", "doc_id": "...", "doc_path": "...",
                   "name": "...", "description": "...", "content": "..."}]
  }

A document without content is reported under ``unscanned`` and never silently
represented as a Jev-negative result. A suspicious or empty description keeps
the document in the candidate set when its KB is possible, preventing metadata
errors from becoming recall failures.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from jev_filter import aggregate_survivors, criterion_for, filter_candidates  # noqa: E402

DEFAULT_MAX_SEGMENT_CHARS = 3_000
_STOP = {
    "the", "and", "for", "with", "that", "this", "what", "does", "did", "are",
    "was", "were", "how", "why", "who", "when", "where", "which", "from", "into",
    "的", "了", "和", "是", "在", "与", "什么", "哪些", "如何", "这个", "那个",
}


def _terms(value: str) -> set[str]:
    text = str(value or "").lower()
    latin = set(re.findall(r"[a-z][a-z0-9_-]{1,}", text))
    cjk = set(re.findall(r"[\u4e00-\u9fff]{2,}", text))
    return {token for token in latin | cjk if token not in _STOP}


def _metadata_trust(description: str, sibling_descriptions: Sequence[str]) -> tuple[bool, list[str]]:
    desc = re.sub(r"\s+", " ", str(description or "")).strip()
    reasons: list[str] = []
    if not desc:
        reasons.append("empty")
    if len(desc) < 18:
        reasons.append("content_free")
    if sibling_descriptions and len(desc) >= 18:
        same = sum(1 for other in sibling_descriptions if re.sub(r"\s+", " ", other).strip() == desc)
        if same >= 3:
            reasons.append("boilerplate")
    if re.search(r"\b([IVXLCDM]+)\s*[–-]\s*\1\b", desc, re.I):
        reasons.append("degenerate_range")
    return not reasons, reasons


def classify_kbs(query: str, kbs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Label every KB; complete mode keeps relevant and possible shelves."""
    q = _terms(query)
    rows: list[dict[str, Any]] = []
    for raw in kbs:
        item = dict(raw)
        blob = f"{item.get('name', '')} {item.get('description', '')}"
        overlap = len(q & _terms(blob)) if q else 0
        has_description = bool(str(item.get("description") or "").strip())
        status = "relevant" if overlap >= 2 else ("possible" if overlap >= 1 or not has_description else "out_of_scope")
        item.update({"catalog_status": status, "query_overlap": overlap})
        rows.append(item)
    # If catalog vocabulary cannot overlap because of language/terminology,
    # preserve the entire catalog rather than claiming a negative coverage result.
    if q and rows and not any(row["catalog_status"] != "out_of_scope" for row in rows):
        for row in rows:
            row["catalog_status"] = "possible"
            row["catalog_reason"] = "no_catalog_overlap; high-recall expansion"
    return rows


def _line_spans(content: str) -> list[tuple[int, int, str]]:
    lines = content.splitlines(keepends=True)
    spans: list[tuple[int, int, str]] = []
    cursor = 0
    for line in lines:
        end = cursor + len(line)
        spans.append((cursor, end, line))
        cursor = end
    if content and not spans:
        spans.append((0, len(content), content))
    return spans


def _is_blank(line: str) -> bool:
    return not line.rstrip("\r\n").strip()


def _is_heading(line: str) -> bool:
    return bool(re.match(r"^ {0,3}#{1,6}[ \t]+", line.rstrip("\r\n")))


def _is_list(line: str) -> bool:
    return bool(re.match(r"^ {0,3}(?:[-+*]|\d+[.)])[ \t]+", line.rstrip("\r\n")))


def _is_fence(line: str) -> bool:
    return bool(re.match(r"^ {0,3}(?:`{3,}|~{3,})", line.rstrip("\r\n")))


def _is_table_separator(line: str) -> bool:
    return bool(re.match(r"^\s*\|?\s*:?-{1,}:?\s*(?:\|\s*:?-{1,}:?\s*)+\|?\s*$", line.rstrip("\r\n")))


def _blocks(content: str) -> list[tuple[int, int, str]]:
    """Return source-backed Markdown blocks, keeping special blocks whole."""
    spans = _line_spans(content)
    if not spans:
        return []
    lines = [line for _, _, line in spans]
    blocks: list[tuple[int, int, str]] = []
    i = 0
    while i < len(lines):
        if _is_blank(lines[i]):
            i += 1
            continue
        start = spans[i][0]
        end_i = i + 1
        if _is_fence(lines[i]):
            marker = re.match(r"^ {0,3}(`{3,}|~{3,})", lines[i].rstrip("\r\n"))
            char = marker.group(1)[0] if marker else "`"
            width = len(marker.group(1)) if marker else 3
            for j in range(i + 1, len(lines)):
                if re.match(rf"^ {{0,3}}{re.escape(char)}{{{width},}}\s*$", lines[j].rstrip("\r\n")):
                    end_i = j + 1
                    break
            else:
                end_i = len(lines)
        elif i + 1 < len(lines) and "|" in lines[i] and _is_table_separator(lines[i + 1]):
            end_i = i + 2
            while end_i < len(lines) and ("|" in lines[end_i] or _is_blank(lines[end_i])):
                if _is_blank(lines[end_i]) and end_i + 1 < len(lines) and "|" not in lines[end_i + 1]:
                    break
                end_i += 1
        elif _is_list(lines[i]):
            end_i = i + 1
            while end_i < len(lines):
                raw = lines[end_i].rstrip("\r\n")
                if _is_list(lines[end_i]) or (raw.startswith((" ", "\t")) and raw.strip()):
                    end_i += 1
                elif _is_blank(lines[end_i]) and end_i + 1 < len(lines) and (_is_list(lines[end_i + 1]) or lines[end_i + 1].startswith((" ", "\t"))):
                    end_i += 1
                else:
                    break
        elif lines[i].lstrip().startswith(">"):
            end_i = i + 1
            while end_i < len(lines) and (_is_blank(lines[end_i]) or lines[end_i].lstrip().startswith(">")):
                end_i += 1
        else:
            end_i = i + 1
            while end_i < len(lines) and not _is_blank(lines[end_i]):
                if _is_heading(lines[end_i]) or _is_fence(lines[end_i]) or _is_list(lines[end_i]):
                    break
                end_i += 1
        end = spans[min(end_i, len(spans)) - 1][1]
        blocks.append((start, end, content[start:end]))
        i = end_i
    # Preserve trailing whitespace as part of the final segment.
    if blocks and blocks[-1][1] < len(content):
        start, _, _ = blocks[-1]
        blocks[-1] = (start, len(content), content[start:])
    elif not blocks and content:
        blocks.append((0, len(content), content))
    return blocks


def _split_long_block(start: int, end: int, text: str, limit: int) -> list[tuple[int, int, str]]:
    if len(text) <= limit:
        return [(start, end, text)]
    pieces: list[tuple[int, int, str]] = []
    cursor = 0
    # Retrieval segmentation can split prose at sentence boundaries; unlike
    # ingestion, this is a read window and never replaces source content.
    matches = list(re.finditer(r"[^。！？!?\.]*?(?:[。！？!?]+|\.(?=\s|$))|.+$", text, re.S))
    sentence_spans = [(m.start(), m.end()) for m in matches if m.group(0)]
    if not sentence_spans:
        sentence_spans = [(0, len(text))]
    current_start = sentence_spans[0][0]
    current_end = current_start
    for sent_start, sent_end in sentence_spans:
        if current_end > current_start and sent_end - current_start > limit:
            pieces.append((start + current_start, start + current_end, text[current_start:current_end]))
            current_start = sent_start
        current_end = sent_end
    if current_end > current_start:
        pieces.append((start + current_start, start + current_end, text[current_start:current_end]))
    if not pieces:
        pieces = [(start, end, text)]
    return pieces


def segment_document(doc: Mapping[str, Any], max_chars: int = DEFAULT_MAX_SEGMENT_CHARS) -> list[dict[str, Any]]:
    content = str(doc.get("content") or "")
    if not content.strip():
        return []
    blocks = _blocks(content)
    atoms: list[tuple[int, int, str]] = []
    for start, end, text in blocks:
        atoms.extend(_split_long_block(start, end, text, max_chars))
    segments: list[dict[str, Any]] = []
    current: list[tuple[int, int, str]] = []
    current_chars = 0
    for atom in atoms:
        size = atom[1] - atom[0]
        if current and current_chars + size > max_chars:
            segments.append(_segment_record(doc, len(segments), current))
            current, current_chars = [], 0
        current.append(atom)
        current_chars += size
    if current:
        segments.append(_segment_record(doc, len(segments), current))
    return segments


def _segment_record(doc: Mapping[str, Any], index: int, atoms: Sequence[tuple[int, int, str]]) -> dict[str, Any]:
    start, end = atoms[0][0], atoms[-1][1]
    kb = str(doc.get("kb_id") or "")
    path = str(doc.get("doc_path") or doc.get("doc_id") or doc.get("name") or "")
    part = doc.get("part_index") or doc.get("part") or 0
    candidate_id = f"{kb}/{path}/part-{part}/segment-{index:04d}"
    return {
        "candidate_id": candidate_id,
        "kb_id": kb,
        "kb_name": doc.get("kb_name"),
        "doc_id": doc.get("doc_id") or doc.get("file_id"),
        "doc_path": doc.get("doc_path"),
        "doc_name": doc.get("name"),
        "part_index": part,
        "section_path": doc.get("section_path") or doc.get("section_range") or "",
        "start_char": start,
        "end_char": end,
        "start_line": str(doc.get("content") or "")[:start].count("\n") + 1,
        "end_line": str(doc.get("content") or "")[:end].count("\n") + 1,
        "text": str(doc.get("content") or "")[start:end],
    }


def build_manifest_candidates(manifest: Mapping[str, Any], max_chars: int = DEFAULT_MAX_SEGMENT_CHARS) -> dict[str, Any]:
    query = str(manifest.get("query") or "").strip()
    kbs = classify_kbs(query, manifest.get("knowledge_bases") or manifest.get("kbs") or [])
    kept_kb_ids = {str(k.get("kb_id") or k.get("id") or k.get("kbId") or k.get("name") or "")
                   for k in kbs if k.get("catalog_status") in {"relevant", "possible"}}
    docs = manifest.get("documents") or []
    candidates: list[dict[str, Any]] = []
    unscanned: list[dict[str, Any]] = []
    document_rows: list[dict[str, Any]] = []
    for raw in docs:
        if not isinstance(raw, Mapping):
            continue
        doc = dict(raw)
        kb_id = str(doc.get("kb_id") or doc.get("kbId") or "")
        if kept_kb_ids and kb_id not in kept_kb_ids:
            continue
        sibling_descs = [str(other.get("description") or "") for other in docs
                         if isinstance(other, Mapping) and str(other.get("kb_id") or other.get("kbId") or "") == kb_id]
        trusted, reasons = _metadata_trust(str(doc.get("description") or ""), sibling_descs)
        doc["description_trust"] = "trusted" if trusted else "untrusted"
        doc["description_trust_reasons"] = reasons
        if not str(doc.get("content") or "").strip():
            unscanned.append({"kb_id": kb_id, "doc_id": doc.get("doc_id") or doc.get("file_id"),
                              "doc_path": doc.get("doc_path"), "reason": "content_missing"})
            document_rows.append(doc)
            continue
        segments = segment_document(doc, max_chars=max_chars)
        candidates.extend(segments)
        document_rows.append({**doc, "segment_count": len(segments)})
    return {"query": query, "criterion": criterion_for(query), "catalog": kbs,
            "documents": document_rows, "candidates": candidates,
            "unscanned": unscanned, "candidate_count": len(candidates)}


def run_manifest(manifest: Mapping[str, Any], *, score_fn: Any = None, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    prepared = build_manifest_candidates(manifest, int(manifest.get("max_segment_chars", DEFAULT_MAX_SEGMENT_CHARS)))
    verdict = filter_candidates({
        "query": prepared["query"],
        "criterion": manifest.get("criterion", "auto"),
        "threshold": manifest.get("threshold", 0.5),
        "max_evidence_chars": manifest.get("max_evidence_chars", 20_000),
        "candidates": prepared["candidates"],
    }, score_fn=score_fn, env=env)
    return {**prepared, "jev": verdict, "survivors": verdict.get("survivors", []),
            "evidence_pack": verdict.get("evidence_pack", ""),
            "provenance": verdict.get("provenance", [])}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run complete-recall segmentation and Jev filtering")
    parser.add_argument("--input", required=True, help="MCP-produced manifest JSON")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(Path(args.input).read_text(encoding="utf-8"))
        result = run_manifest(manifest)
        rendered = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        else:
            print(rendered)
        return 0 if result["jev"].get("status") in {"ok", "unavailable", "error"} else 1
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
