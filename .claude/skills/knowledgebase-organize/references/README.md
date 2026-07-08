# Organize Skill — Shared References

This skill reuses procedures defined in other skills. See the linked references for each operation code.

| Operation | Reference | Location |
|-----------|-----------|----------|
| **O2b / O4a** — Description audit & fix | [Description Writing Guide](../knowledgebase-ingest/references/description-guide.md) | A4 section |
| **O9** — Sub-KB creation | [Sub-KB Creation Guide](../knowledgebase-ingest/references/sub-kb-creation.md) | A8 section |
| **O12** — Graph rebuild & verification | [Graph Tools Reference](../knowledgebase-graph/references/graph-tools.md) | Query and stats tools |

## Usage

When executing any of the above operations, import the procedure from the linked reference rather than re-deriving it. The shared files are the single source of truth — updates to the procedure are made in the originating skill's reference and picked up here automatically.

## Note

**No document splitting.** Documents are stored as single units regardless of size. The old `doc-splitting.md` reference is deprecated and no longer used. The vector index handles chunking internally during embedding.
