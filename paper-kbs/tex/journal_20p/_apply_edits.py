# -*- coding: utf-8 -*-
"""五席评审修复：n2 文献方向 / n7 ensure_stack 句 / n8b 阈值依据。"""
import io

HERE = r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\tex\journal_20p"

addition = (
    "Two further lines border the design without competing with it. Agent memory\n"
    "systems treat memory as an agent-managed store of interaction records:\n"
    "MemGPT pages memory between a context window and an external store\n"
    "\\citep{memgpt}, Mem0 extracts and consolidates long-term memory from\n"
    "conversations \\citep{mem0}, and A-MEM organises notes as an agentic memory\n"
    "graph \\citep{amem}. HMRS manages a document corpus with audited lifecycle\n"
    "state; the stores are complementary rather than competing, and an ingest\n"
    "agent of the kind these frameworks assume still needs the collection\n"
    "assignment and consistency guarantees this paper measures. Knowledge\n"
    "organisation standards such as SKOS \\citep{skos} and Dublin Core describe\n"
    "curated descriptive metadata for controlled vocabularies; HMRS borrows the\n"
    "description-first discipline but derives descriptions from parsed content at\n"
    "ingest time rather than from editorial metadata.\n\n"
)
anchor2 = "Self-RAG and CRAG integrate evidence assessment or retrieval correction into"

add7 = (
    "A stack-ensure script checks the API, web front end and MCP endpoints\n"
    "before any scripted campaign and restarts missing services in a fixed\n"
    "order with an end-to-end retrieval probe; three acceptance campaigns\n"
    "started from a fully stopped stack and recovered without manual\n"
    "intervention.\n\n"
)
anchor7 = ("The implementation and scripts are available\n"
           "at \\url{https://github.com/kingdol666/rag-knowledge};")

add8 = ("Retrieval thresholds follow platform defaults (score 0.35 with a 0.30\n"
        "retry, top-30 wide net).\n")
anchor8 = "A0h recorded 309 KB and 13.8 s per question versus"


def patch(fname, anchor, addition):
    p = HERE + "\\" + fname
    src = io.open(p, encoding="utf-8").read()
    if addition.strip()[:40] in src:
        print(fname, "already patched")
        return
    assert anchor in src, "anchor missing in " + fname
    src = src.replace(anchor, addition + anchor, 1)
    io.open(p, "w", encoding="utf-8", newline="\n").write(src)
    print(fname, "patched")


patch("n2_related.tex", anchor2, addition)
patch("n7_implementation.tex", anchor7, add7)
patch("n8b_eval.tex", anchor8, add8)
