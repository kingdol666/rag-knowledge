"""Structure-aware document splitting shared by ingestion entry points.

``max_chars`` is a storage/retrieval guardrail, not permission to cut arbitrary
text. Markdown is first segmented into sections. Sections that fit remain
whole; oversized sections are expanded only at paragraph, list, table, code,
blockquote, figure, or sentence boundaries. An Agent may choose among these
source-backed units, but may not rewrite content or invent character offsets.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

DEFAULT_MAX_CHARS = 30_000
DEFAULT_OVERLAP_CHARS = 0
MIN_MAX_CHARS = 500
DEFAULT_DESC_CHARS = 220
DEFAULT_TARGET_UTILIZATION = 0.85

_ATX_RE = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$", re.DOTALL)
_SETEXT_RE = re.compile(r"^ {0,3}(=+|-+)[ \t]*$", re.DOTALL)
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_LIST_RE = re.compile(r"^ {0,3}(?:[-+*]|\d+[.)])[ \t]+")
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{1,}:?\s*(?:\|\s*:?-{1,}:?\s*)+\|?\s*$")
_IMAGE_RE = re.compile(r"^\s*!\[[^\]]*\]\([^)]*\)\s*$")
_CAPTION_RE = re.compile(r"^\s*(?:fig(?:ure)?\.?|table|图|表)\s*[\w一二三四五六七八九十.-]*\s*[:：.-]", re.I)
_SENTENCE_RE = re.compile(r".*?(?:[。！？!?]+|(?<!\.)\.(?:\s+|$)|$)", re.S)


@dataclass(frozen=True)
class StructuralUnit:
    unit_id: str
    kind: str
    heading_path: str
    start_char: int
    end_char: int
    text: str
    section_range: str = ""
    safe_boundary: str = "structural_block"

    @property
    def chars(self) -> int:
        return self.end_char - self.start_char

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "kind": self.kind,
            "heading_path": self.heading_path,
            "section_range": self.section_range,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "chars": self.chars,
            "safe_boundary": self.safe_boundary,
            "head": self.text[:280],
            "tail": self.text[-280:] if len(self.text) > 280 else self.text,
        }


@dataclass
class SplitPart:
    """A source-backed, independently ingestible part."""

    title: str
    content: str
    part_index: int
    part_count: int
    source_title: str
    start_char: int
    end_char: int
    description: str = ""
    description_seed: str = ""
    agent_description: str = ""
    section_range: str = ""
    source_sha256: str = ""
    boundary_kind: str = "structural"
    warnings: list[str] = field(default_factory=list)
    strategy: str = "structural_fallback"
    planner: str = "deterministic"

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "part_index": self.part_index,
            "part_count": self.part_count,
            "source_title": self.source_title,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "source_start": self.start_char,
            "source_end": self.end_char,
            "chars": len(self.content),
            "source_chars": self.end_char - self.start_char,
            "description": self.description,
            "description_seed": self.description_seed or self.description,
            "agent_description": self.agent_description,
            "section_range": self.section_range,
            "source_sha256": self.source_sha256,
            "boundary_kind": self.boundary_kind,
            "warnings": list(self.warnings),
            "strategy": self.strategy,
            "planner": self.planner,
            "description_provenance": "agent" if self.agent_description else "structural_fallback",
        }


def clamp_max_chars(max_chars: int) -> int:
    try:
        return max(MIN_MAX_CHARS, int(max_chars))
    except (TypeError, ValueError):
        return DEFAULT_MAX_CHARS


def should_split(content: str, max_chars: int = DEFAULT_MAX_CHARS) -> bool:
    return len(content or "") > clamp_max_chars(max_chars)


def source_sha256(content: str) -> str:
    return hashlib.sha256((content or "").encode("utf-8")).hexdigest()


def _plain_text(text: str) -> str:
    plain = re.sub(r"```[\s\S]*?```", " ", text or "")
    plain = re.sub(r"~~~[\s\S]*?~~~", " ", plain)
    plain = re.sub(r"`([^`]+)`", r"\1", plain)
    plain = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r"\1", plain)
    plain = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", plain)
    plain = re.sub(r"^#{1,6}\s+", "", plain, flags=re.MULTILINE)
    plain = re.sub(r"[*_~>|]+", " ", plain)
    plain = re.sub(r"\s+", " ", plain).strip()
    return plain


def content_description(text: str, max_desc_chars: int = DEFAULT_DESC_CHARS) -> str:
    """Return a source-derived description seed, never a filename placeholder."""
    max_desc_chars = max(40, int(max_desc_chars or DEFAULT_DESC_CHARS))
    plain = _plain_text(text)
    if len(plain) <= max_desc_chars:
        return plain
    return plain[: max_desc_chars - 1].rstrip() + "…"


def _line_spans(content: str) -> list[tuple[int, int, str]]:
    lines = content.splitlines(keepends=True)
    if not lines and content:
        return [(0, len(content), content)]
    spans: list[tuple[int, int, str]] = []
    pos = 0
    for line in lines:
        end = pos + len(line)
        spans.append((pos, end, line))
        pos = end
    return spans


def _line_text(line: str) -> str:
    return line.rstrip("\r\n")


def _is_blank(line: str) -> bool:
    return not _line_text(line).strip()


def _heading_at(lines: Sequence[str], i: int) -> tuple[int, str, str] | None:
    raw = _line_text(lines[i])
    m = _ATX_RE.match(raw)
    if m:
        return len(m.group(1)), m.group(2).strip(), "atx"
    if i + 1 < len(lines) and raw.strip() and _SETEXT_RE.match(_line_text(lines[i + 1])):
        marker = _line_text(lines[i + 1]).strip()[0]
        return (1 if marker == "=" else 2), raw.strip(), "setext"
    return None


def _is_table_start(lines: Sequence[str], i: int) -> bool:
    if i + 1 >= len(lines):
        return False
    return "|" in _line_text(lines[i]) and bool(_TABLE_SEPARATOR_RE.match(_line_text(lines[i + 1]).strip()))


def _is_list_line(line: str) -> bool:
    return bool(_LIST_RE.match(_line_text(line)))


def _is_special_start(lines: Sequence[str], i: int) -> bool:
    return bool(_heading_at(lines, i) or _FENCE_RE.match(_line_text(lines[i]))
        or _is_table_start(lines, i) or _is_list_line(lines[i])
        or _line_text(lines[i]).lstrip().startswith(">")
        or _IMAGE_RE.match(_line_text(lines[i])))


def _consume_fence(lines: Sequence[str], i: int) -> int:
    first = _FENCE_RE.match(_line_text(lines[i]))
    if not first:
        return i + 1
    marker, width = first.group(1)[0], len(first.group(1))
    for j in range(i + 1, len(lines)):
        if re.match(rf"^ {{0,3}}{re.escape(marker)}{{{width},}}[ \t]*$", _line_text(lines[j])):
            return j + 1
    return len(lines)


def _consume_table(lines: Sequence[str], i: int) -> int:
    j = min(i + 2, len(lines))
    while j < len(lines):
        raw = _line_text(lines[j])
        if "|" in raw:
            j += 1
            continue
        if _is_blank(lines[j]) and j + 1 < len(lines) and "|" in _line_text(lines[j + 1]):
            j += 1
            continue
        break
    return j


def _consume_list(lines: Sequence[str], i: int) -> int:
    j = i + 1
    while j < len(lines):
        raw = _line_text(lines[j])
        if _is_list_line(lines[j]) or (raw.startswith((" ", "\t")) and raw.strip()):
            j += 1
            continue
        if _is_blank(lines[j]) and j + 1 < len(lines):
            nxt = _line_text(lines[j + 1])
            if _is_list_line(lines[j + 1]) or (nxt.startswith((" ", "\t")) and nxt.strip()):
                j += 1
                continue
        break
    return j


def _consume_blockquote(lines: Sequence[str], i: int) -> int:
    j = i + 1
    while j < len(lines):
        raw = _line_text(lines[j])
        if raw.lstrip().startswith(">") or _is_blank(lines[j]):
            j += 1
            continue
        break
    return j


def _find_headings(content: str) -> list[tuple[int, int, str]]:
    """Find headings outside fenced code: (char_start, level, title)."""
    spans = _line_spans(content)
    lines = [s[2] for s in spans]
    found: list[tuple[int, int, str]] = []
    in_fence = False
    fence_marker = ""
    fence_width = 0
    for i, (_, _, line) in enumerate(spans):
        raw = _line_text(line)
        fence = _FENCE_RE.match(raw)
        if fence:
            if not in_fence:
                in_fence = True
                fence_marker = fence.group(1)[0]
                fence_width = len(fence.group(1))
            elif fence.group(1)[0] == fence_marker and len(fence.group(1)) >= fence_width:
                in_fence = False
            continue
        if in_fence:
            continue
        heading = _heading_at(lines, i)
        if heading:
            level, title, form = heading
            found.append((spans[i][0], level, title))
            if form == "setext":
                # The underline is part of the section, so the next heading
                # still starts at its own line; no special offset is needed.
                continue
    return found


def _section_records(content: str) -> list[dict[str, Any]]:
    headings = _find_headings(content)
    if not headings:
        return []
    records: list[dict[str, Any]] = []
    first_start = headings[0][0]
    if first_start > 0:
        records.append({"start": 0, "end": first_start, "heading_path": "",
                        "section_range": "", "kind": "preamble"})
    stack: list[tuple[int, str]] = []
    for index, (start, level, title) in enumerate(headings):
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        end = headings[index + 1][0] if index + 1 < len(headings) else len(content)
        path = " > ".join(x[1] for x in stack)
        records.append({"start": start, "end": end, "heading_path": path,
                        "section_range": path, "kind": "section"})
    return records


def _records_to_units(records: Sequence[Mapping[str, Any]], content: str,
                      prefix: str = "u") -> list[StructuralUnit]:
    result: list[StructuralUnit] = []
    for item in records:
        start, end = int(item["start"]), int(item["end"])
        result.append(StructuralUnit(
            unit_id="", kind=str(item["kind"]),
            heading_path=str(item.get("heading_path") or ""),
            start_char=start, end_char=end, text=content[start:end],
            section_range=str(item.get("section_range") or ""),
            safe_boundary=str(item.get("safe_boundary") or "structural_block"),
        ))
    return result


def _sentence_records(text: str, start: int, heading_path: str,
                      section_range: str) -> list[dict[str, Any]]:
    """Split prose at sentence boundaries while preserving every character."""
    records: list[dict[str, Any]] = []
    cursor = 0
    # A punctuation match includes following whitespace, which keeps the
    # source spans contiguous and prevents leading whitespace from disappearing.
    for match in re.finditer(r"[^。！？!?\.]*?(?:[。！？!?]+|\.(?=\s|$))|.+$", text, re.S):
        if match.start() != cursor:
            # This should only be whitespace between sentences; attach it to
            # the previous sentence rather than dropping it.
            if records:
                records[-1]["end"] = start + match.start()
                records[-1]["text"] = text[records[-1]["start"] - start:match.start()]
        piece = match.group(0)
        end = match.end()
        if piece:
            records.append({"start": start + match.start(), "end": start + end,
                            "heading_path": heading_path, "section_range": section_range,
                            "kind": "sentence", "safe_boundary": "sentence"})
        cursor = end
    if not records and text:
        records.append({"start": start, "end": start + len(text),
                        "heading_path": heading_path, "section_range": section_range,
                        "kind": "oversized_atomic", "safe_boundary": "atomic"})
    # Ensure the records cover the input exactly. The caller adds any leading
    # or trailing whitespace through its enclosing block spans.
    return records


def _scan_blocks(text: str, base_start: int, heading_path: str,
                 section_range: str, max_chars: int) -> list[StructuralUnit]:
    """Scan an oversized section into safe blocks/sentences."""
    spans = _line_spans(text)
    if not spans:
        return []
    lines = [s[2] for s in spans]
    records: list[dict[str, Any]] = []
    i = 0
    block_start = 0
    while i < len(lines):
        if _is_blank(lines[i]):
            i += 1
            continue
        end_i = i + 1
        kind = "paragraph"
        if _FENCE_RE.match(_line_text(lines[i])):
            kind, end_i = "fenced_code", _consume_fence(lines, i)
        elif _is_table_start(lines, i):
            kind, end_i = "table", _consume_table(lines, i)
        elif _is_list_line(lines[i]):
            kind, end_i = "list", _consume_list(lines, i)
        elif _line_text(lines[i]).lstrip().startswith(">"):
            kind, end_i = "blockquote", _consume_blockquote(lines, i)
        elif _IMAGE_RE.match(_line_text(lines[i])):
            kind, end_i = "figure", i + 1
            if end_i < len(lines) and (_CAPTION_RE.match(_line_text(lines[end_i])) or _is_blank(lines[end_i])):
                end_i = min(end_i + 1, len(lines))
        elif _heading_at(lines, i):
            kind = "heading"
            level, _, form = _heading_at(lines, i)  # type: ignore[misc]
            end_i = i + (2 if form == "setext" else 1)
        else:
            end_i = i + 1
            while end_i < len(lines) and not _is_blank(lines[end_i]) and not _is_special_start(lines, end_i):
                end_i += 1
        end_i = max(i + 1, min(end_i, len(lines)))
        end_char = spans[end_i - 1][1]
        # Include all blank lines before this block in the preceding block; for
        # the first block they remain part of this block. This is exact coverage.
        local_start = block_start
        local_end = end_char
        block_text = text[local_start:local_end]
        if len(block_text) > max_chars and kind == "paragraph":
            sentence_start = local_start
            body = text[local_start:local_end]
            sent = _sentence_records(body, base_start + local_start, heading_path, section_range)
            if sent and all(int(x["end"]) > int(x["start"]) for x in sent):
                records.extend(sent)
            else:
                records.append({"start": base_start + local_start, "end": base_start + local_end,
                                "heading_path": heading_path, "section_range": section_range,
                                "kind": "oversized_atomic", "safe_boundary": "atomic"})
        else:
            records.append({"start": base_start + local_start, "end": base_start + local_end,
                            "heading_path": heading_path, "section_range": section_range,
                            "kind": kind,
                            "safe_boundary": "atomic" if len(block_text) > max_chars else "structural_block"})
        block_start = end_char
        i = end_i
    if block_start < len(text):
        if records:
            records[-1]["end"] = base_start + len(text)
            records[-1]["text"] = None
        else:
            records.append({"start": base_start, "end": base_start + len(text),
                            "heading_path": heading_path, "section_range": section_range,
                            "kind": "blank", "safe_boundary": "structural_block"})
    units: list[StructuralUnit] = []
    for item in records:
        start, end = int(item["start"]), int(item["end"])
        units.append(StructuralUnit("", str(item["kind"]), heading_path,
                                    start, end, "", section_range,
                                    str(item.get("safe_boundary") or "structural_block")))
    return units


def _bind_heading_units(units: Sequence[StructuralUnit]) -> list[StructuralUnit]:
    """Keep a heading with the first body unit it introduces."""
    bound: list[StructuralUnit] = []
    i = 0
    while i < len(units):
        unit = units[i]
        if unit.kind != "heading":
            bound.append(unit)
            i += 1
            continue
        j = i + 1
        while j < len(units) and units[j].kind == "heading":
            j += 1
        if j < len(units):
            first_body = units[j]
            bound.append(StructuralUnit(
                unit_id="",
                kind="section_intro",
                heading_path=first_body.heading_path or unit.heading_path,
                start_char=unit.start_char,
                end_char=first_body.end_char,
                text="",
                section_range=first_body.section_range or unit.section_range,
                safe_boundary="heading_section",
            ))
            i = j + 1
        else:
            bound.append(StructuralUnit(
                unit_id="", kind="section_intro", heading_path=unit.heading_path,
                start_char=unit.start_char, end_char=units[j - 1].end_char,
                text="", section_range=unit.section_range,
                safe_boundary="heading_section",
            ))
            i = j
    return bound
def _assign_text(units: Sequence[StructuralUnit], content: str) -> list[StructuralUnit]:
    return [StructuralUnit(u.unit_id, u.kind, u.heading_path, u.start_char, u.end_char,
                           content[u.start_char:u.end_char], u.section_range,
                           u.safe_boundary) for u in units]


def _renumber(units: Sequence[StructuralUnit]) -> list[StructuralUnit]:
    return [StructuralUnit(f"u{i:04d}", u.kind, u.heading_path, u.start_char,
                           u.end_char, u.text, u.section_range, u.safe_boundary)
            for i, u in enumerate(units, 1)]


def scan_structural_units(content: str, max_chars: int | None = None) -> list[StructuralUnit]:
    """Return contiguous source-backed units, expanding only oversized sections."""
    content = content or ""
    if not content:
        return [StructuralUnit("u0001", "empty", "", 0, 0, "", "", "empty")]
    limit = clamp_max_chars(max_chars) if max_chars is not None else len(content) + 1
    sections = _section_records(content)
    if not sections:
        units = _scan_blocks(content, 0, "", "document body", limit)
    else:
        raw: list[StructuralUnit] = []
        for section in sections:
            start, end = int(section["start"]), int(section["end"])
            size = end - start
            if size <= limit:
                raw.extend(_records_to_units([section], content))
            else:
                raw.extend(_scan_blocks(content[start:end], start,
                                         str(section["heading_path"]),
                                         str(section["section_range"]), limit))
        units = raw
    units = _assign_text(_bind_heading_units(units), content)
    units = _renumber(units)
    if units[0].start_char != 0:
        raise ValueError("structural scanner produced a leading gap")
    cursor = 0
    for unit in units:
        if unit.start_char != cursor:
            raise ValueError(f"structural scanner gap/overlap before {unit.unit_id}")
        cursor = unit.end_char
    if cursor != len(content):
        raise ValueError("structural scanner did not cover the source")
    return units


def _unit_groups(units: Sequence[StructuralUnit], max_chars: int,
                 target_utilization: float) -> tuple[list[list[StructuralUnit]], list[str]]:
    del target_utilization  # only a soft target; never creates a logical cut
    groups: list[list[StructuralUnit]] = []
    warnings: list[str] = []
    current: list[StructuralUnit] = []
    current_chars = 0
    for unit in units:
        size = unit.chars
        if size > max_chars:
            if current:
                groups.append(current)
                current, current_chars = [], 0
            groups.append([unit])
            warnings.append(f"oversized_atomic_unit:{unit.unit_id}:{size}>{max_chars}")
            continue
        if current and current_chars + size > max_chars:
            groups.append(current)
            current, current_chars = [], 0
        current.append(unit)
        current_chars += size
    if current:
        groups.append(current)
    return groups or [[]], warnings


def _section_label(group: Sequence[StructuralUnit]) -> str:
    paths = [u.section_range for u in group if u.section_range]
    if not paths:
        return "document body"
    seen: list[str] = []
    for path in paths:
        if path not in seen:
            seen.append(path)
    return seen[0] if len(seen) == 1 else f"{seen[0]} – {seen[-1]}"


def _fallback_description(body: str, section_range: str, index: int,
                          total: int, max_desc_chars: int) -> str:
    # Keep the body-derived excerpt first for compatibility and readback. The
    # part/section label is appended and remains available as metadata context.
    excerpt = content_description(body, max(40, max_desc_chars - 45))
    suffix = f" 【Part {index}/{total} · {section_range}】" if section_range else f" 【Part {index}/{total}】"
    text = excerpt + suffix
    return text[:max_desc_chars].rstrip()


def _make_parts_from_groups(content: str, title: str,
                            groups: Sequence[Sequence[StructuralUnit]], *,
                            strategy: str, planner: str,
                            descriptions: Mapping[int, str] | None = None,
                            boundary_kind: str = "structural",
                            warnings: Iterable[str] = (),
                            desc_chars: int = DEFAULT_DESC_CHARS) -> list[SplitPart]:
    total = len(groups)
    digest = source_sha256(content)
    all_warnings = list(warnings)
    parts: list[SplitPart] = []
    for idx, group in enumerate(groups, 1):
        if not group:
            continue
        start, end = group[0].start_char, group[-1].end_char
        body = content[start:end]
        section = _section_label(group)
        seed = _fallback_description(body, section, idx, total, desc_chars)
        agent_desc = str((descriptions or {}).get(idx) or "").strip()
        description = agent_desc or seed
        part_title = f"{title} (part {idx} of {total})"
        header = [f"# {title}（第 {idx}/{total} 部分）"]
        if section:
            header.append(f"章节: {section}")
        header.append("")
        stored = "\n".join(header) + body
        local_warnings = list(all_warnings)
        if any(u.safe_boundary == "atomic" and u.chars > 0 for u in group):
            local_warnings.append("part_contains_oversized_atomic_unit")
        parts.append(SplitPart(
            title=part_title, content=stored, part_index=idx, part_count=total,
            source_title=title, start_char=start, end_char=end,
            description=description, description_seed=seed,
            agent_description=agent_desc, section_range=section,
            source_sha256=digest, boundary_kind=boundary_kind,
            warnings=local_warnings, strategy=strategy, planner=planner,
        ))
    for i, part in enumerate(parts, 1):
        part.part_index, part.part_count = i, len(parts)
    return parts


def _validate_agent_plan(content: str, units: Sequence[StructuralUnit],
                         agent_plan: Mapping[str, Any], max_chars: int) -> tuple[list[list[StructuralUnit]], dict[int, str], list[str]]:
    errors: list[str] = []
    if not isinstance(agent_plan, Mapping):
        return [], {}, ["agent_plan_not_object"]
    if agent_plan.get("source_sha256") and agent_plan.get("source_sha256") != source_sha256(content):
        errors.append("source_sha256_mismatch")
    unit_map = {u.unit_id: u for u in units}
    parts = agent_plan.get("parts")
    if not isinstance(parts, list) or not parts:
        errors.append("parts_missing_or_empty")
        return [], {}, errors
    groups: list[list[StructuralUnit]] = []
    descriptions: dict[int, str] = {}
    used: list[str] = []
    for pos, raw in enumerate(parts, 1):
        if not isinstance(raw, Mapping):
            errors.append(f"part_{pos}_not_object")
            continue
        if raw.get("part_index", pos) != pos:
            errors.append(f"part_index_not_contiguous:{pos}")
        ids = raw.get("unit_ids")
        if not isinstance(ids, list) or not ids:
            errors.append(f"part_{pos}_unit_ids_missing")
            continue
        group: list[StructuralUnit] = []
        for uid in ids:
            uid = str(uid)
            if uid not in unit_map:
                errors.append(f"unknown_unit:{uid}")
                continue
            if uid in used:
                errors.append(f"duplicate_unit:{uid}")
                continue
            used.append(uid)
            group.append(unit_map[uid])
        if not group:
            errors.append(f"part_{pos}_empty")
            continue
        expected_order = [u.unit_id for u in units if u.unit_id in ids]
        if [u.unit_id for u in group] != expected_order:
            errors.append(f"part_{pos}_unit_order_invalid")
        if group[-1].end_char - group[0].start_char > max_chars and len(group) > 1:
            errors.append(f"part_{pos}_over_max_chars")
        desc = str(raw.get("description") or "").strip()
        if desc and len(desc) > DEFAULT_DESC_CHARS:
            errors.append(f"part_{pos}_description_over_220")
        evidence = raw.get("evidence") or []
        part_text = content[group[0].start_char:group[-1].end_char]
        if not isinstance(evidence, list) or any(str(e).strip() and str(e) not in part_text for e in evidence):
            errors.append(f"part_{pos}_evidence_not_in_part")
        groups.append(group)
        descriptions[pos] = desc
    if used != [u.unit_id for u in units]:
        errors.append("unit_coverage_not_exact")
    for left, right in zip(groups, groups[1:]):
        if left[-1].end_char != right[0].start_char:
            errors.append("part_span_gap_or_overlap")
    return ([], {}, errors) if errors else (groups, descriptions, [])


def split_document(content: str, title: str = "", *,
                   max_chars: int = DEFAULT_MAX_CHARS,
                   overlap_chars: int = DEFAULT_OVERLAP_CHARS,
                   desc_chars: int = DEFAULT_DESC_CHARS,
                   agent_plan: Mapping[str, Any] | None = None,
                   target_utilization: float = DEFAULT_TARGET_UTILIZATION,
                   allow_oversized_atomic_unit: bool = True,
                   allow_hard_fallback: bool = False) -> list[SplitPart]:
    """Split by complete structural units, optionally following a validated plan."""
    del overlap_chars  # retained for API compatibility; structural splits use 0 overlap.
    content = content or ""
    title = (title or "").strip() or "untitled"
    max_chars = clamp_max_chars(max_chars)
    if len(content) <= max_chars:
        seed = content_description(content, desc_chars)
        return [SplitPart(title=title, content=content, part_index=1, part_count=1,
                          source_title=title, start_char=0, end_char=len(content),
                          description=seed, description_seed=seed,
                          section_range="document body", source_sha256=source_sha256(content),
                          strategy="single_document", planner="none")]
    units = scan_structural_units(content, max_chars=max_chars)
    warnings: list[str] = []
    planner = "deterministic"
    descriptions: dict[int, str] = {}
    groups: list[list[StructuralUnit]] = []
    if agent_plan is not None:
        groups, descriptions, errors = _validate_agent_plan(content, units, agent_plan, max_chars)
        if errors:
            warnings.extend(f"agent_plan_rejected:{e}" for e in errors)
            groups = []
        else:
            planner = "agent"
    if not groups:
        groups, fallback_warnings = _unit_groups(units, max_chars, target_utilization)
        warnings.extend(fallback_warnings)
        if any("oversized_atomic_unit" in w for w in fallback_warnings) and not allow_oversized_atomic_unit:
            if not allow_hard_fallback:
                raise ValueError("oversized atomic unit cannot be split without rewriting logical content")
            warnings.append("hard_fallback_requested")
    return _make_parts_from_groups(
        content, title, groups,
        strategy="agent_semantic" if planner == "agent" else "structural_fallback",
        planner=planner,
        descriptions=descriptions,
        boundary_kind="agent_boundary" if planner == "agent" else "structural_block",
        warnings=warnings,
        desc_chars=desc_chars,
    )


def plan_split(content: str, title: str, cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    cfg = dict(cfg or {})
    max_chars = clamp_max_chars(cfg.get("max_chars", DEFAULT_MAX_CHARS))
    auto = bool(cfg.get("auto_split", True))
    target = float(cfg.get("target_utilization", DEFAULT_TARGET_UTILIZATION) or DEFAULT_TARGET_UTILIZATION)
    allow_atomic = bool(cfg.get("allow_oversized_atomic_unit", True))
    allow_hard = bool(cfg.get("allow_hard_fallback", False))
    content = content or ""
    title = (title or "").strip() or "untitled"
    if not auto:
        seed = content_description(content)
        one = SplitPart(title=title, content=content, part_index=1, part_count=1,
                        source_title=title, start_char=0, end_char=len(content),
                        description=seed, description_seed=seed, section_range="document body",
                        source_sha256=source_sha256(content), strategy="auto_split_disabled", planner="none")
        return {"split": False, "reason": "auto_split_disabled", "part_count": 1,
                "source_chars": len(content),
                "units": [u.to_dict() for u in scan_structural_units(content, max_chars=max_chars)],
                "parts": [one.to_dict()]}
    units = scan_structural_units(content, max_chars=max_chars)
    parts = split_document(content, title, max_chars=max_chars,
                           overlap_chars=int(cfg.get("overlap_chars", 0) or 0),
                           desc_chars=int(cfg.get("desc_chars", DEFAULT_DESC_CHARS) or DEFAULT_DESC_CHARS),
                           agent_plan=cfg.get("agent_plan"), target_utilization=target,
                           allow_oversized_atomic_unit=allow_atomic,
                           allow_hard_fallback=allow_hard)
    return {
        "split": len(content) > max_chars,
        "reason": "oversized_structural_split" if len(content) > max_chars else f"shorter_than_{max_chars}",
        "part_count": len(parts), "source_chars": len(content), "max_chars": max_chars,
        "source_sha256": source_sha256(content),
        "strategy": parts[0].strategy if parts else "structural_fallback",
        "planner": parts[0].planner if parts else "deterministic",
        "units": [u.to_dict() for u in units],
        "warnings": sorted({w for p in parts for w in p.warnings}),
        "parts": [p.to_dict() for p in parts],
    }


__all__ = [
    "DEFAULT_DESC_CHARS", "DEFAULT_MAX_CHARS", "DEFAULT_OVERLAP_CHARS", "MIN_MAX_CHARS",
    "StructuralUnit", "SplitPart", "clamp_max_chars", "should_split", "source_sha256",
    "content_description", "scan_structural_units", "split_document", "plan_split",
]
