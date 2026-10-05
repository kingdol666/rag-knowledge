# A2.5 Split Gate — scanner detail

Summarized in [SKILL.md](../SKILL.md) §A2.5; this file holds the scanner contract the main flow compresses.

## Unit taxonomy recorded by the scanner

The scanner records contiguous units with `unit_id`, `kind`, `heading_path`, `start_char`, `end_char`:

- ATX and Setext headings, with headings inside fenced code ignored;
- standalone chapter titles (`第一章 …` / `Chapter 12`) in flat prose — novels without Markdown structure still get chapter-granular units;
- complete paragraphs, lists with continuations, tables, fenced code, blockquotes, figures/captions, and sentence boundaries inside oversized prose sections;
- per unit: `source_sha256`, `section_range`, head/tail probes, and a safe boundary type.

## Source-span invariant

Concatenating every unit must reproduce the input byte-for-character (Python character count) with no gap and no accidental overlap. This is what makes "parts keep the original body exactly" verifiable instead of aspirational.

## Agent plan JSON schema

The Archival agent emits (after validating) and passes via `--agent-plan`:

```json
{
  "source_sha256": "<sha256>",
  "parts": [
    {
      "part_index": 1,
      "unit_ids": ["u0001", "u0002"],
      "section_range": "Introduction – Methods",
      "boundary_reason": "complete subsection boundary",
      "description": "paper-level subject/method + this-part content, <=220 chars",
      "evidence": ["literal body evidence used for the description"]
    }
  ]
}
```

The script prints one JSON object: `success` / `source_chars` / `max_chars` / `split` / `strategy` (`agent_semantic|structural_fallback`) / `planner` (`agent|deterministic`) / `source_sha256` / `parts[{file, source_start, source_end, section_range, description_seed, warnings}]`.

## Plan validation checklist (before `--agent-plan` is accepted)

- Hash matches the scanned source.
- Unit coverage is contiguous, in order, with no gaps.
- Every boundary is safe: no mid-sentence cut, no severed continuous scene/argument.
- Every description is ≤220 chars and grounded in that part's real body.
- Every `evidence` string reads back literally in the part's body.

Any failure → the Agent re-plans. The script never silently "fixes" a plan.

## Deterministic fallback

Running without `--agent-plan` uses the deterministic structural fallback (heading/chapter/paragraph joints) and records `planner=deterministic`. It is a safety net, not a result to pass off as Agent segmentation: reports must never claim Agent planning when the plan was deterministic.
