# Organize Skill -- Shared References

This skill reuses procedures defined in other skills. See the linked references for each operation code.

| Operation | Reference | Location |
|-----------|-----------|----------|
| **O2-E / O11** -- Description writing | [Description Writing Guide](../knowledgebase-ingest/references/description-guide.md) | A4 section |
| **O9** -- Document splitting | [Document Splitting Procedure](../knowledgebase-ingest/references/doc-splitting.md) | A5b section |
| **O10** -- Sub-KB creation | [Sub-KB Creation Guide](../knowledgebase-ingest/references/sub-kb-creation.md) | A9 section |
| **O13** -- YAML cleanup | [fix_yaml_index.py](scripts/fix_yaml_index.py) | Use modes: `audit-all`, `clean`, `unparent` |
| **O14** -- Graph verification | [Graph Tools Reference](../knowledgebase-graph/references/graph-tools.md) | Query and stats tools |

## Usage

When executing any of the above operations, import the procedure from the linked reference rather than re-deriving it. The shared files are the single source of truth -- updates to the procedure are made in the originating skill's reference and picked up here automatically.
