# Figure and table captions

**Figure 1.** Library analogy for a catalogue-first HMRS access path. The library catalogue, shelf, book and passage correspond to the collection catalogue, document listing, document body and segment. Evidence scoring is optional; pinned search may bypass the catalogue and shelf.

**Figure 2.** HMRS service architecture. The browser and agent/CLI access the web and MCP interfaces. Parsing, management and retrieval operate on shared document files, the tree registry, library metadata and search indices. Laya scoring is optional; the Neo4j graph supports navigation and optional candidate expansion.

**Figure 3.** Illustrative HMRS workflow from document acquisition to evidence-based reporting. Documents are parsed when needed, organised into collections and indexed according to the entry point. A question can use catalogue navigation or pinned search; optional Laya scoring precedes evidence inspection. A completed review without support is distinct from an incomplete search or tool failure, which may occur at any stage.

**Figure 4.** Tiered access workflow. Pinned search and catalogue navigation supply candidate references. The workflow can read candidates directly or use Laya to admit passages before checking source text. A failure or limit that prevents completion yields an incomplete report with the searched scope and any available evidence.

**Figure 5.** Catalogue-first retrieval on BQ07 in a separate captured run. The trace follows the query through the catalogue, paginated shelf and stored-part selection, then through a bounded evidence filter and one follow-up source read. This example illustrates the workflow; it is not an observation in the native E2 comparison or the E3 routing audit.

**Figure 6.** Correct collection selections out of 72 for A0 (name and description) and A3 (nominally name-only) in the frozen, same-question follow-up and 17 November rerun. Bars give the number of questions in which the selector chose the labelled collection; the denominator is fixed at 72 in every run. A0 remains at 72/72, whereas A3 rises from 37/72 to 49/72 in both reruns. Because fallbacks to descriptions or searches outside the evaluated collections were not logged, this comparison is a routing diagnostic rather than a causal description ablation.

**Figure 7.** Target-string containment on 72 in-domain questions. (a) Filled circles and Wilson 95% intervals show the frozen run; open triangles show the same-question follow-up, with the adjacent columns giving the corresponding hit counts. The dashed line marks frozen A0. A3 is an auxiliary routing control, and read-all is a separate capped corpus scan whose follow-up was incomplete. (b) For each displayed frozen-run contrast, a filled circle counts questions hit only by the first configuration and an open diamond counts questions hit only by the second; the connecting segment connects the two discordant counts, and the symbols identify which configuration each count favours. McNemar *p* values are exact, two-sided and unadjusted; values below 0.001 are displayed as <0.001.

**Figure 8.** Verifier scores and same-pool ordering from two records over the same 16 candidate pools. (a) Each point is one of 191 recorded Laya scores (17 gold and 174 non-gold candidates); the vertical jitter separates points only for display. Black ticks mark the group medians (0.8759 and 0.86265), the dashed line marks the 0.5 cutoff, and Q14 has one candidate without a recorded score. (b) Each row is one pool in the separate ordering replay: filled circles mark a gold document in Fusion's top five and filled diamonds mark a gold document in verifier-score order; open symbols mark a miss. The replay changes ordering only: Fusion retains 15/16 Hit@5 pools, whereas verifier-score order retains 7/16, with eight losses and no gains (exact McNemar *p* = 0.0078). The panels do not test the admission benefit of the score.

**Table 1.** Representative systems compared along the dimensions examined here. A dash marks a dimension outside the cited work's main contribution.

**Table 2.** Management levels and the tiered access path. Each level names the objects it maintains, the operations that write them, the state that describes them, the tier that reads them, and the measurement that exercises it. Evidence labels E1–E7 denote the evaluation campaigns of Section 8. The selected access policy determines which tiers are visited; a pinned search can bypass catalogue navigation.

**Table 3.** Management functions, the enforcement or workflow check associated with each, and the evaluation that exercises it. The table separates API/MCP controls from agent procedures and campaign audits; semantic choices such as which collection owns a document are made and recorded by the workflow. Evidence labels E1–E7 denote the campaigns in Section 8.

**Table 4.** Access policies over the tiered path. Modes differ in how candidate collections and documents are selected. The hybrid row describes the experimental composition used in the evaluation.

**Table 5.** Answer-quality rubric applied by the blind judge in E2. Scores are integers 1–5; 2–4 are intermediate. Overall is the unweighted mean; the holistic verdict is separate, not a mean threshold. The judge saw the question, a head-only gold excerpt and eight anonymised answers, not retrieved contexts or system names.

**Table 6.** Blind answer scores for the eight configurations in the native deployment case study on BQ01–BQ10. Each configuration answered each question once; dimension scores are 1–5 (Table 5). C/P/I denotes correct, partial and incorrect verdict counts. Time and cost are per question; time is end-to-end and cost is estimated for generator calls only. † Gold-paper subset; ‡ DeepRead's native corpus. ᵃ Configured for five collections, but in nine of ten questions at least one search lacked an effective restriction. The audit reported 31 distinct collection-ID values in the result lists (Section 8.3). The configurations differ in source access, and their indexed corpora are not all matched.

**Table 7.** Six main E4 configurations. A3 and read-all are separate comparators. Limits are in characters, not tokens.

**Algorithm 1.** Tiered access with optional evidence gate

---

Figure files are supplied separately in `05-editorial-manager/figures/` as `Figure_1.pdf` … `Figure_8.pdf` (vector PDF, fonts embedded), in order of appearance:

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
