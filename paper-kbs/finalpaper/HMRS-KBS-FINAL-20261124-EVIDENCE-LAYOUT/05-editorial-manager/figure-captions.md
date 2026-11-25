# Figure and table captions

**Figure 1.** Library analogy for a catalogue-first HMRS access path. The library catalogue, shelf, book and passage correspond to the collection catalogue, document listing, document body and segment. Evidence scoring is optional; pinned search may bypass the catalogue and shelf.

**Figure 2.** HMRS service architecture. The browser and agent/CLI access the web and MCP interfaces. Parsing, management and retrieval operate on shared document files, the tree registry, library metadata and search indices. Laya scoring is optional; the Neo4j graph supports navigation and optional candidate expansion.

**Figure 3.** Illustrative HMRS workflow from document acquisition to evidence-based reporting. Documents are parsed when needed, organised into collections and indexed according to the entry point. A question can use catalogue navigation or pinned search; optional Laya scoring precedes evidence inspection. A completed review without support is distinct from an incomplete search or tool failure, which may occur at any stage.

**Figure 4.** Tiered access workflow. Pinned search and catalogue navigation supply candidate references. The workflow can read candidates directly or use Laya to admit passages before checking source text. A failure or limit that prevents completion yields an incomplete report with the searched scope and any available evidence.

**Figure 5.** Catalogue-first retrieval on BQ07 in a separate captured run. The trace follows the query through the catalogue, paginated shelf and stored-part selection, then through a bounded evidence filter and one follow-up source read. This example illustrates the workflow; it is not an observation in the native E2 comparison or the E3 routing audit.

**Figure 6.** Correct collection selection out of 72 for A0 (name and description) and A3 (nominal name-only) across the frozen, follow-up and 17 November runs. Unlogged fallbacks to descriptions or searches outside the evaluated collections mean this contrast does not isolate a causal effect of descriptions.

**Figure 7.** Target-string containment on 72 in-domain questions. (a) Circles and Wilson 95% intervals show the frozen run; open triangles show the same-question follow-up. The dashed line marks frozen A0. The numbers give hit counts out of 72. A3 is the auxiliary routing control; read-all is a separate capped scan whose follow-up was incomplete. (b) For the frozen-run contrasts shown, the symbols count questions on which only the first or only the second configuration hit. McNemar *p* values are exact, two-sided and unadjusted; values below 0.001 are displayed as <0.001.

**Figure 8.** Verifier scores and same-pool ordering from two records of the same pools. (a) Laya scores for 191 of the 192 candidates across the 16 hybrid pools. Median scores were 0.88 for the 17 gold candidates and 0.86 for the 174 others. All recorded scores exceeded 0.5; one more candidate (Q14) had no recorded score. Horizontal jitter separates the marks. (b) In the ordering record, each pool is replayed in fusion and verifier-score order. Filled marks indicate a gold document among the first five.

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
