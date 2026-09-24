"""Round B — apply reviewer fixes to the paper sources (space-neutral edits)."""
from pathlib import Path

TEX = Path(__file__).resolve().parent
ok, miss = [], []


def patch(name, old, new, label):
    p = TEX / name
    t = p.read_text(encoding='utf-8')
    if old not in t:
        miss.append(label)
        print('MISS', label)
        return
    p.write_text(t.replace(old, new, 1), encoding='utf-8')
    ok.append(label)
    print('ok', label)


# ---- abstract rewrite (~205 words: gloss + dedup + active voice + vs labels) ----
abs_old = (
    "Research administrators who maintain shared paper collections must organize\n"
    "documents and inspect the evidence behind the answers drawn from them. We\n"
    "present \\sys{}, an agent-operated platform that couples content-guided\n"
    "knowledge organization with librarian-style retrieval through one shared\n"
    "address space. Packaged agent skills call tool APIs to parse documents,\n"
    "route them by content into category bases, and maintain tags. Retrieval\n"
    "rewrites each query, recalls and reads candidates, gates them with a\n"
    "prompted 0--8 rubric (topic, scenario, evidence), and --- when nothing\n"
    "passes --- escalates to browsing base summaries and tag-matched\n"
    "shelves, returning a scoped not-found report instead of answering from the\n"
    "nearest neighbor. A\n"
    "100-paper, five-base instance, built by the platform's own ingest loop,\n"
    "was audited by ingest, storage, and retrieval probes. In a\n"
    "monitored three-mode run under one harness and model (platform, bare agent,\n"
    "dense retrieval), the platform grounds 9 of 10 designated-paper answers and\n"
    "keyword-verifies 9 of 10; the bare agent even locates the designated\n"
    "paper in all 10 cases yet passes conservative word-boundary verification\n"
    "in only 6, and dense retrieval grounds 9 and verifies 6. Part/section-level\n"
    "citations reach 7 of 10 for the platform versus 4 and 1. A measured\n"
    "dense-mode abstention and three scripted out-of-corpus probes, which\n"
    "receive scoped not-found reports, complete the demonstration. The platform trades\n"
    "roughly three times the bare agent's cost per question for this verified,\n"
    "addressable evidence. Attendees organize a document, inspect an answer's\n"
    "evidence, and\n"
    "examine a failure report. Demo video:\n"
    "\\url{https://github.com/kingdol666/rag-knowledge/blob/master/paper_demo/video/qdcvr-demo.mp4}."
)
abs_new = (
    "Research administrators must organize shared paper collections and inspect\n"
    "the evidence behind the answers drawn from them. We present \\sys{}, an\n"
    "agent-operated platform that couples content-guided knowledge organization\n"
    "with librarian-style retrieval through one shared address space. Packaged\n"
    "agent skills parse documents, route them by content into category bases,\n"
    "and maintain tags. Retrieval rewrites each query, recalls and reads\n"
    "candidates, gates them with a prompted 0--8 rubric (topic, scenario,\n"
    "evidence), and --- when nothing passes --- escalates to browsing base\n"
    "summaries and tag-matched shelves, returning a scoped not-found report\n"
    "instead of answering from the nearest neighbor. The platform's own ingest\n"
    "loop built a 100-paper, five-base instance; ingest, storage, and retrieval\n"
    "probes then audited it. In a monitored three-mode run under one harness and\n"
    "model, the platform grounds 9 of 10 designated-paper answers and\n"
    "keyword-verifies 9 of 10 (gold key facts matched verbatim); the bare agent\n"
    "even locates the designated paper in all 10 cases yet passes conservative\n"
    "word-boundary verification in only 6, and dense retrieval grounds 9 and\n"
    "verifies 6. Part/section-level citations reach 7 of 10 versus 4 (bare\n"
    "agent) and 1 (dense). A measured dense-mode abstention and three scripted\n"
    "out-of-corpus probes complete the demonstration, at roughly three times\n"
    "the bare agent's cost per question for this inspectable, addressable\n"
    "evidence. Attendees organize a document, inspect an answer's evidence, and\n"
    "examine a failure report. Demo video:\n"
    "\\url{https://github.com/kingdol666/rag-knowledge/blob/master/paper_demo/video/qdcvr-demo.mp4}."
)

# ---- intro ----
intro_open_old = (
    "Research administrators maintaining shared paper collections must organize\n"
    "them and show which passages support an answer."
)
intro_open_new = (
    "Maintaining a shared paper collection is organizational work before it is\n"
    "retrieval work: someone must keep the corpus ordered and be able to show\n"
    "which passages support an answer."
)
intro_corpus_old = "verification~\\cite{cyberbot} --- but each treats the collection as given."
intro_corpus_new = "verification~\\cite{cyberbot} --- but each treats the corpus it retrieves\nover as given."

# ---- sec2 ----
s21_old = (
    "offset-addressed reads. Console, CLI, and MCP clients operate the same\n"
    "resources through the same tools; what they do not share is a reasoning\n"
    "policy --- only the packaged skill adds the gate. A retag or a move lands once\n"
    "in the shared store: the console and MCP clients read the same record.\n"
    "ChromaDB stores"
)
s21_new = (
    "offset-addressed reads. Console, CLI, and MCP clients operate the same\n"
    "resources through the same tools; what they do not share is a reasoning\n"
    "policy; only the packaged skill adds the gate. ChromaDB stores"
)
s22_old = (
    "The organization skill inspects the parsed\n"
    "content, selects among existing bases (proposing a new one only when none\n"
    "fits), and places and tags the document."
)
s22_new = (
    "The organization skill inspects the parsed\n"
    "content, selects among existing bases --- the platform's knowledge-base\n"
    "containers --- (proposing a new one only when none fits), and places and\n"
    "tags the document."
)
s23_esc_old = (
    "Any lower initial score invokes the librarian --- base summaries,\n"
    "tag-matched shelves, targeted re-search --- instead of more vector queries;\n"
    "a failed gate is information, not noise: a ranking step cannot repair\n"
    "an absent passage; browsing is the designed route for surfacing one the\n"
    "index missed."
)
s23_esc_new = (
    "Any lower initial score invokes the librarian --- base summaries,\n"
    "tag-matched shelves, targeted re-search --- instead of more vector queries:\n"
    "a ranking step cannot repair a failed recall, so browsing is the designed\n"
    "route for surfacing a passage the ranking missed."
)
s23_end_old = (
    "\\emph{Content-verified} denotes this prompted judgment, not guaranteed\n"
    "correctness. Saved artifacts keep candidate excerpts and answer records;\n"
    "mutable file-tree metadata is not an append-only audit log."
)
s23_end_new = (
    "\\emph{Content-verified} denotes this prompted judgment, not guaranteed\n"
    "correctness; file-tree metadata is mutable, not an append-only audit log.\n"
    "Saved artifacts keep candidate excerpts and answer records."
)

# ---- sec3 ----
s3_t1_old = (
    "holds 100 papers in five bases; attendees inspect documents and drive an\n"
    "agent with the packaged skills."
)
s3_t1_new = (
    "holds 100 papers in five bases (ingest audit: Table~\\ref{tab:pipeline});\n"
    "attendees inspect documents and drive an agent with the packaged skills."
)
s3_sc2_old = (
    "the vector-first search ranks the primer's part~1 of~2 first, at 0.75\n"
    "(0.66 cross-base); a two-stage pass confirms it, and the agent answers\n"
    "with a verbatim quotation whose source block names base, part, and\n"
    "section (``2.~What is the Gene Ontology'') --- score, reading, and\n"
    "quoted evidence are distinct records; the attendee can open the cited part\n"
    "in the console while the kb\\_* tools read it at its line offset."
)
s3_sc2_new = (
    "the vector-first search ranks the primer's part~1 of~2 first, at 0.75\n"
    "(0.66 cross-base); a two-stage pass confirms the candidate, and the agent\n"
    "answers with a verbatim quotation whose source block names base, document,\n"
    "part, and section (``2.~What is the Gene Ontology'') --- score, reading,\n"
    "and quoted evidence are distinct records; the attendee can open the cited\n"
    "part in the console while the kb\\_* tools read it at its line offset."
)
s3_sc3_old = (
    "\\paragraph{3. Examine a failure report.}\n"
    "The attendee asks for training epochs"
)
s3_sc3_new = (
    "\\paragraph{3. Examine a failure report.}\n"
    "Next, the attendee asks for training epochs"
)

# ---- sec4 ----
s4_open_old = (
    "The corpus was built by the platform's own ingest loop, so records exist\n"
    "for every stage (Table~\\ref{tab:pipeline}). The monitored run then asks\n"
    "whether the address-space design changes answers: ten questions, each\n"
    "answerable only from its designated paper, ran through three modes that\n"
    "differ only in evidence route, permissions, and prompt framing, on the\n"
    "shared corpus (Figure~\\ref{fig:threeway})."
)
s4_open_new = (
    "Because the platform's own ingest loop built the corpus, records exist\n"
    "for every stage (Table~\\ref{tab:pipeline}). The monitored run then asks\n"
    "whether the address-space design changes answers: ten fixed questions\n"
    "(BQ01--BQ10; full text in the repository), each answerable only from its\n"
    "designated paper, ran through three modes that differ only in evidence\n"
    "route, permissions, and prompt framing --- the platform answers through\n"
    "its packaged skill over the kb\\_* tools; the bare agent is the same model\n"
    "with file tools over the exported papers; the dense mode searches the\n"
    "4{,}528-chunk replica index of Table~\\ref{tab:pipeline}\n"
    "(Figure~\\ref{fig:threeway})."
)
s4_hedge_old = (
    "shown as-is. Correctness reflects our reading; the comparison is\n"
    "operational, not controlled; cache state uncontrolled. Three"
)
s4_hedge_new = (
    "shown as-is. Correctness calls are the authors' reading of each trace;\n"
    "cache state was not controlled. Three"
)

# ---- sec5 ----
s5_cav_old = "(9/10 each), at roughly three times the bare agent's cost."
s5_cav_new = (
    "(9/10 each; one run, one model, one corpus), at roughly three times the\n"
    "bare agent's cost per question."
)
s5_rs_old = (
    "the librarian fallback routes a failed gate to re-assessment, an\n"
    "attributed backstop, or a scoped not-found report."
)
s5_rs_new = (
    "the librarian fallback routes a failed gate to re-search, an\n"
    "attributed backstop, or a scoped not-found report."
)

# ---- backmatter ----
bm_old = (
    "Section~\\ref{sec:eval}. Those runs' saved traces (answers, tool timelines,\n"
    "usage records) are retained artifacts;"
)
bm_new = (
    "Section~\\ref{sec:eval}. The saved traces of those runs (answers, tool\n"
    "timelines, usage records) are retained artifacts;"
)

# ---- main.tex comment ----
mx_old = (
    "% double-column float (dbltop queue); Tables 1-2 are column floats, and\n"
    "% topnumber=1 splits them across the p. 4 column tops (T1 left, T2 right)\n"
    "% instead of stacking both over the left column."
)
mx_new = "% double-column float (dbltop queue); Table 1 is a column float on p. 3."

patch('sec0_abstract.tex', abs_old, abs_new, 'abstract rewrite')
patch('sec1_intro.tex', intro_open_old, intro_open_new, 'intro opening')
patch('sec1_intro.tex', intro_corpus_old, intro_corpus_new, 'intro corpus clause')
patch('sec2_system.tex', s21_old, s21_new, 'sec2.1 dedup')
patch('sec2_system.tex', s22_old, s22_new, 'sec2.2 bases gloss')
patch('sec2_system.tex', s23_esc_old, s23_esc_new, 'sec2.3 escalation')
patch('sec2_system.tex', s23_end_old, s23_end_new, 'sec2.3 ending')
patch('sec3_demo.tex', s3_t1_old, s3_t1_new, 'sec3 T1 anchor')
patch('sec3_demo.tex', s3_sc2_old, s3_sc2_new, 'sec3 scenario2')
patch('sec3_demo.tex', s3_sc3_old, s3_sc3_new, 'sec3 scenario3')
patch('sec4_eval.tex', s4_open_old, s4_open_new, 'sec4 modes defined')
patch('sec4_eval.tex', s4_hedge_old, s4_hedge_new, 'sec4 hedge dedup')
patch('sec5_conclusion.tex', s5_cav_old, s5_cav_new, 'sec5 caveat')
patch('sec5_conclusion.tex', s5_rs_old, s5_rs_new, 'sec5 re-search')
patch('sec4_backmatter.tex', bm_old, bm_new, 'backmatter possessive')
patch('main.tex', mx_old, mx_new, 'main comment')

print(f'applied {len(ok)}/{len(ok) + len(miss)}')
