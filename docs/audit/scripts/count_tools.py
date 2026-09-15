"""Extract the exact set of @mcp.tool()-decorated functions from kb-mcp/server.py
and check the README's claimed disjoint partition."""
import re

src = open("kb-mcp/server.py", encoding="utf-8").read()
lines = src.split("\n")

# collect (decorator_line_no, function_name) for each @mcp.tool()
tools = []
for i, ln in enumerate(lines):
    if re.match(r"\s*@mcp\.tool\(", ln):
        # find the next 'async def NAME' or 'def NAME' within 12 lines
        for j in range(i + 1, min(i + 12, len(lines))):
            m = re.match(r"\s*(?:async\s+)?def\s+(\w+)", lines[j])
            if m:
                tools.append((i + 1, m.group(1)))
                break
        else:
            tools.append((i + 1, "<UNRESOLVED>"))

print(f"decorated tools: {len(tools)}")
names = [n for _, n in tools]
print(f"unique names   : {len(set(names))}")
dupes = [n for n in set(names) if names.count(n) > 1]
if dupes:
    print(f"DUPLICATES     : {dupes}")

README_PARTITION = {
    "Service lifecycle": 4,
    "KB CRUD": 4,
    "Document CRUD + listing": 9,
    "Search": 4,
    "Vector / index": 6,
    "File system": 3,
    "Knowledge graph": 11,
    "Experience (incl. meditation)": 26,
    "Tags": 4,
    "Parse": 3,
    "SOUL persona": 20,
}
print(f"\nREADME partition sums to: {sum(README_PARTITION.values())}")

# assign every tool to exactly one bucket, mirroring the README's naming
def bucket(n):
    if n.startswith("soul_"): return "SOUL persona"
    if n.startswith("experience_") or n.startswith("kb_meditation"): return "Experience (incl. meditation)"
    if n.startswith("kb_graph_"): return "Knowledge graph"
    if n.startswith("parse_"): return "Parse"
    if n.startswith("fs_"): return "File system"
    if n in ("kb_tags_list", "kb_tags_cleanup", "kb_doc_update_tags", "kb_doc_get_by_tag"): return "Tags"
    if n in ("kb_search", "kb_search_vector", "kb_search_two_stage", "kb_search_stats"): return "Search"
    if n in ("kb_index_document", "kb_batch_index", "kb_reindex",
             "kb_cleanup_orphan_collections", "kb_find_duplicates", "kb_task_status"): return "Vector / index"
    if n in ("kb_list", "kb_create", "kb_update", "kb_delete"): return "KB CRUD"
    if n in ("kb_project_start", "kb_project_status", "kb_project_update",
             "backend_status", "health_check"): return "Service lifecycle"
    if n.startswith("kb_doc_") or n == "kb_get_documents": return "Document CRUD + listing"
    return "UNCLASSIFIED: " + n


from collections import Counter
actual = Counter(bucket(n) for n in names)

print(f"\n{'category':<34} {'README':>7} {'actual':>7}  delta")
print("-" * 62)
for cat, claimed in README_PARTITION.items():
    act = actual.get(cat, 0)
    flag = "" if act == claimed else "   <-- MISMATCH"
    print(f"{cat:<34} {claimed:>7} {act:>7}{flag}")

extra = {k: v for k, v in actual.items() if k not in README_PARTITION}
if extra:
    print("\nNOT IN README PARTITION:")
    for k, v in extra.items():
        print(f"  {k}: {v}")
        for n in names:
            if bucket(n) == k:
                print(f"      {n}")
