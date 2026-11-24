# Figure and table captions

**Figure 1.** Library analogy for a catalogue-first HMRS access path. The library catalogue, shelf, book and passage correspond to the collection catalogue, document listing, document body and segment. Evidence scoring is optional; pinned search may bypass the catalogue and shelf.

**Figure 2.** HMRS service architecture. The browser and agent/CLI access the web and MCP interfaces. Parsing, management and retrieval operate on shared document files, the tree registry, library metadata and search indices. Laya scoring is optional, and the Neo4j graph supports navigation.

**Figure 3.** Illustrative HMRS workflow from document acquisition to evidence-based reporting. Documents are parsed when needed, organised into collections and indexed according to the entry point. A question can use catalogue navigation or pinned search; optional Laya scoring precedes evidence inspection. A completed review without support is distinct from an incomplete search or tool failure, which may occur at any stage.

**Figure 4.** Tiered access workflow. Pinned search and catalogue navigation supply candidate references. The workflow reads selected evidence directly or calls Laya to fetch, score and admit passages. Failures or limits that prevent completion at any stage yield an incomplete report with the searched scope and any available evidence.

**Figure 5.** One question of the native comparison (BQ07). (a) The HMRS agent's recorded tool calls: two searches issued in one turn, a read of the gold paper and the answer. (b) Two one-shot baselines; each received one prompt with twelve context units that did not include the gold paper, and both declined to answer. HIT/MISS marks whether the gold paper was in the evidence; the strips give the blind judge's verdict and overall score. Answer excerpts are verbatim, with "…" marking omitted words. The footer lists the overall score of all eight configurations on this question; † marks the BM25 answer that cited material beyond its supplied context.

**Figure 6.** Correct collection selections for the two route-card variants. All three runs use the same 72 questions. A3 is nominally name-only.

**Figure 7.** Target-string containment on 72 in-domain questions. (a) Circles and Wilson 95% intervals show the frozen run; open triangles show the same-question follow-up. The dashed line marks frozen A0. The columns give hit counts out of 72; a dash indicates that the read-all follow-up was incomplete. (b) For each frozen-run contrast, the symbols count questions on which only the first or only the second configuration hit. McNemar *p* values are exact, two-sided and unadjusted.

**Figure 8.** Verifier scores and same-pool ordering from separate archives. (a) Laya scores for 191 recorded candidates across 16 hybrid runs. Median scores were 0.88 for the 17 gold candidates and 0.86 for the 174 others. All recorded scores exceeded 0.5; one more candidate (Q14) had no recorded score. Horizontal jitter separates the marks. (b) The same 16 pools in the ordering archive, replayed in fusion and verifier-score order. Filled marks indicate a gold document among the first five.

**Table 1.** Representative systems compared along the dimensions examined here. A dash marks a dimension outside the cited work's main contribution.

**Table 2.** Management levels and the tiered access path. Each level names the objects it maintains, the operations that write them, the state that describes them, the tier that reads them, and the measurement that exercises it. Evidence labels E1–E7 denote the evaluation campaigns of Section 8. The selected access policy determines which tiers are visited; a pinned search can bypass catalogue navigation.

**Table 3.** Management functions, the enforcement or workflow check associated with each, and the evaluation that exercises it. The table separates API/MCP controls from agent procedures and campaign audits; semantic choices such as which collection owns a document are made and recorded by the workflow. Evidence labels E1–E7 denote the campaigns in Section 8.

**Table 4.** Access policies over the tiered path. Modes differ in how candidate collections and documents are selected. The hybrid row describes the experimental composition used in the evaluation.

**Table 5.** Blind answer scores for the eight native configurations on BQ01–BQ10. Each configuration answered each question once. C/P/I denotes correct, partial and incorrect verdict counts. Time and cost are per question; time is end-to-end and cost is estimated for generator calls only. † Gold-paper subset; ‡ DeepRead's native corpus. ᵃ Configured for five collections, but in nine of ten questions at least one search lacked an effective restriction. The audited result lists contained items from 31 collections, including other copies of the corpus (Section 8.3). The configurations differ in source access, and their indexed corpora are not all matched.

**Table 6.** Search scope and evidence construction for the six E4 configurations. Limits are in characters, not model tokens.

**Algorithm 1.** Tiered access with optional evidence gate

---

Figure files are supplied separately as `figures/Figure_1.pdf` … `figures/Figure_8.pdf` (vector PDF, fonts embedded), in order of appearance:

| File | Figure |
|---|---|
| figures/Figure_1.pdf | Figure 1 |
| figures/Figure_2.pdf | Figure 2 |
| figures/Figure_3.pdf | Figure 3 |
| figures/Figure_4.pdf | Figure 4 |
| figures/Figure_5.pdf | Figure 5 |
| figures/Figure_6.pdf | Figure 6 |
| figures/Figure_7.pdf | Figure 7 |
| figures/Figure_8.pdf | Figure 8 |
