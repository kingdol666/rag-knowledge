# References and public-artifact audit

Audit date: 2026-09-19. Scope: `paper_demo/tex/refs.bib` and this new audit only. No other TeX, implementation, package, repository settings, or published artifacts changed. Sources were fetched live without authentication using read-only HTTP GETs. Web search returned no usable output; direct primary-source fetches supplied the evidence. Local context consulted: `paper_demo/README.md`, root `README.md`, existing bibliography and demo URLs in TeX. This is a metadata/retrievability audit, not independent approval of the manuscript or a system reproduction.

## Recommended compact citation set

Use nine works if each supports an actual claim: `rag-lewis`, `dpr`, `bge-m3`, `selfrag`, `crag`, `mineru`, `mcp`, `deepread`, `cyberbot`. An optional tenth is `kamath` if selective answering/abstention is substantively discussed. All 18 original keys remain, with the two requested keys added (20 total). Do not use `\nocite{*}`. Main-paper author controls which works are cited. AppAgent-Pro was not added: no demonstrated content-level connection warrants spending a citation on it. This omission is a relevance decision, not a claim that the work does not exist.

DeepRead is a close document-navigation comparison: its authors describe structure-aware locate-then-read reasoning with Retrieve and ReadSection. CyberBOT is a relevant deployed, domain-specific RAG demo with ontology-based answer validation. These papers do not by themselves establish that QDCVR is novel or better; make explicit, bounded comparisons rather than claiming competitors lack all verification.

## Core metadata: evidence and changes

### `rag-lewis`
- Publisher record: https://proceedings.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html
- Publisher BibTeX: https://proceedings.neurips.cc/paper_files/paper/2020/file/6b493230205f780e1bc26945df7481e5-Bibtex.bib
- Confirmed NeurIPS 2020, volume 33, pages 9459–9474, Curran Associates. Added verified fields and URL.
- **No author was missing in the inspected entry.** All 12 authors, including both Patrick Lewis and Mike Lewis, Wen-tau Yih, Sebastian Riedel and Douwe Kiela, match the primary record. Do not remove an author to shorten the rendered reference.

### `dpr`
- Official exported record: https://aclanthology.org/2020.emnlp-main.550.bib
- EMNLP 2020, pages 6769–6781, DOI 10.18653/v1/2020.emnlp-main.550. Added pages, DOI and canonical URL. All eight authors match; retained the existing accented rendering of Barlas Oğuz (Anthology export uses Oguz).

### `bge-m3`
- Official exported record: https://aclanthology.org/2024.findings-acl.137.bib
- **Published in Findings of the Association for Computational Linguistics: ACL 2024**, not an ACL main-track paper. Pages 2318–2335; DOI 10.18653/v1/2024.findings-acl.137.
- Converted preprint entry to proceedings. Corrected first author to **Jianlyu Chen**, the publisher's spelling, from Jianlv Chen. Retained the published M3-Embedding title rather than inventing a BGE-M3 title.

### `selfrag`
- Conference page: https://iclr.cc/virtual/2024/poster/18095
- Paper record: https://arxiv.org/abs/2310.11511
- Proceedings link: https://openreview.net/forum?id=hSyW5go0v8
- Confirmed ICLR 2024 from conference site; title and five authors from paper record. Retained Avirup Sil as on arXiv (conference profile displays Avi Sil). Added OpenReview URL; no page range invented. OpenReview itself returned a browser challenge, and its API returned HTTP 429; these were not treated as successful metadata fetches.

### `crag`
- Primary paper: https://arxiv.org/abs/2401.15884v3
- Authors' repository: https://github.com/HuskyInSalt/CRAG
- Four authors and title match. Retained a 2024 arXiv preprint, version 3 dated October 7, 2024; added DOI and versioned URL. No verified proceedings venue was found in the consulted sources, so none was invented. This is not a claim that no later publication exists.

### `mineru`
- Primary paper: https://arxiv.org/abs/2409.18839
- September 27, 2024 technical report. Expanded all **18 authors** from the primary record rather than truncating the database with `and others`; added DOI and URL. This is the original MinerU report, not MinerU2.5 and not a claim about the installed runtime version.

### `mcp`
- Authoritative pinned specification: https://modelcontextprotocol.io/specification/2025-11-25
- Replaced moving homepage with the **2025-11-25 specification revision**, kept 2025 as document year, and recorded access on September 19, 2026. Used Model Context Protocol Contributors as a collective project attribution rather than implying sole authorship by Anthropic of this revision.
- This is a cited protocol revision, **not a verified claim about the project's negotiated protocol version or the latest revision**. The specification defines host/client/server relationships and JSON-RPC-based integration; it does not prove QDCVR's implementation or security properties.

### New `deepread`
- Required primary version: https://arxiv.org/abs/2602.05014v3
- Zhanli Li, Huiwen Tian, Lvzhou Luo, Yixuan Cao, Ping Luo. *DeepRead: Document Structure-Aware Reasoning to Enhance Agentic Search*. arXiv:2602.05014v3, 2026; DOI 10.48550/arXiv.2602.05014.
- Version 3 was submitted February 12, 2026. Version 2 was withdrawn; do not accidentally cite it. Entry pins v3 in the journal field and URL; the arXiv DOI identifies the work, not specifically v3. No venue/pages invented.

### New `cyberbot`
- Publisher-deposited Crossref metadata: https://api.crossref.org/works/10.1145/3746252.3761478
- Published DOI: https://doi.org/10.1145/3746252.3761478
- Author preprint: https://arxiv.org/abs/2504.00389v2
- Published title: **CyberBOT: Ontology-Grounded Retrieval Augmented Generation for Reliable Cybersecurity Education**.
- Published venue: Proceedings of the 34th ACM International Conference on Information and Knowledge Management (2025), pages **6752–6756**. Crossref publication date: November 10, 2025.
- All ten authors and their order follow the publisher deposit: Chengshuai Zhao; Riccardo De Maria; Tharindu Kumarage; Kumar Satvik Chaudhary; Garima Agrawal; Yiwen Li; Jongchan Park; **Ying-Chih Chen; Yuli Deng**; Huan Liu. Preserved De Maria as the family name in BibTeX.
- Preprint title is different: *CyberBOT: Towards Reliable Cybersecurity Education via Ontology-Grounded Retrieval Augmented Generation*. The preprint also places Yuli Deng before Ying-Chih Chen. Do not merge the preprint title/order into the published citation. Its arXiv record links the same ACM DOI, connecting the two versions.
- Direct ACM DL GET returned HTTP 403. Published metadata was verified through ACM's Crossref deposit, not a claimed successful ACM page access.

## Remaining original references inspected

- `bm25`: existing journal/volume 3(4), 333–389, 2009 retained, **not newly certified**. Publisher landing page https://www.nowpublishers.com/article/Details/INR-019 returned 403. The deposit at https://api.crossref.org/works/10.1561/1500000019 unexpectedly reports volume 4, issue 1–2, pages 1–174 for the same title, conflicting with the existing entry. Do not silently overwrite from that inconsistent record. Resolve against a publisher PDF if this optional reference is selected.
- `kamath`: checked https://aclanthology.org/2020.acl-main.503.bib; three authors, ACL 2020; added verified pages 5684–5696, DOI and URL.
- `flare`: checked https://aclanthology.org/2023.emnlp-main.495.bib; nine authors, EMNLP 2023. Normalized Frank Xu to the publisher export (previously Frank F. Xu); added pages 7969–7992, DOI and URL.
- `graphrag`: https://arxiv.org/abs/2404.16130 lists ten authors. **Added Dasha Metropolitansky and Robert Osazuwa Ness**, absent from the inspected entry. Retained the 2024 preprint citation and added URL. This is a current-record author correction, not a version-by-version history reconstruction.
- `lightrag`: https://arxiv.org/abs/2410.05779 confirms title and five authors; left original 2024 preprint entry intact. Current record has later revisions; no later venue upgrade was certified in this audit.
- `raptor`: https://arxiv.org/abs/2401.18059 confirms title and six authors; official ICLR 2024 listing https://iclr.cc/virtual/2024/papers.html links https://iclr.cc/virtual/2024/poster/19034. Original entry retained.
- `siren`: https://arxiv.org/abs/2309.01219 confirms the title and 16 authors. Expanded the existing `and others` to the full list and added URL. First submission is 2023; current record is v3 from September 14, 2025. No claim of a proceedings publication.
- `chroma`: https://www.trychroma.com returned HTTP 200; site currently calls itself open-source search infrastructure for AI. Existing descriptive entry retained; its 2026 year is a web-resource citation convention, not a verified release/publication date.
- `neo4j`: https://neo4j.com returned HTTP 200. Existing web-resource entry retained with the same date caveat.
- `langchain`: https://python.langchain.com returned HTTP 200 after redirect to https://docs.langchain.com/oss/python/langchain/overview. Existing entry retained. No installed version inferred from current docs.
- `llamaindex`: https://docs.llamaindex.ai returned HTTP 200 after redirect to https://developers.llamaindex.ai/python/framework/. Existing entry retained. No installed version inferred.

The old blanket header saying every entry was verified was removed: the BM25 conflict and source-access limitations make that claim too strong. Foundational publications from 2020 and earlier, and some 2023–2024 works, are more than two years old as of this audit; age is not a reason to replace their historical attribution with a newer paper. Dynamic docs should be pinned or access-dated instead.

## Public repository and actual video: unauthenticated evidence

All requests below were anonymous; no cookies, tokens, login, posting, push or upload was used.

- https://github.com/kingdol666/rag-knowledge — HTTP 200.
- https://api.github.com/repos/kingdol666/rag-knowledge — HTTP 200, `visibility=public`, `default_branch=master`.
- https://github.com/kingdol666/rag-knowledge/blob/master/paper_demo/video/qdcvr-demo.mp4 — HTTP 200.
- https://api.github.com/repos/kingdol666/rag-knowledge/contents/paper_demo/video/qdcvr-demo.mp4?ref=master — HTTP 200; ordinary file, size **27,380,220 bytes**, blob SHA **77756d323b858af3340238b7f1688442c4e60a74**.
- https://raw.githubusercontent.com/kingdol666/rag-knowledge/master/paper_demo/video/qdcvr-demo.mp4 — full anonymous GET HTTP 200, **27,380,220 bytes**, content-type `application/octet-stream`; downloaded bytes SHA-256 **bf736568f09bfc2b1b2d53e2db9d5d3f59d3d59b445df5b23b20e3176de973d8**.
- Local actual file `paper_demo/video/qdcvr-demo.mp4` has the same byte length and SHA-256. Local `ffprobe` reports **176.938042 seconds** (approximately 2 min 57 sec).

Conclusion: this is an accessible real video payload matching the local artifact, not merely an existing HTML link or LFS pointer. Anonymous download accessibility is verified; browser inline playback, narration quality, and full visual/content review were **not** performed. The local README's old “after push” caveat is no longer accurate for this particular public file, but README was not edited.

## Official CIKM 2026 demonstration requirements

Primary source fetched September 19, 2026: https://cikm2026.diag.uniroma1.it/demonstration-papers/

- At most **four pages including appendices and acknowledgments**; unlimited extra pages for **GenAI Usage Disclosure and references**. This is not permission to move arbitrary data-availability/protocol/evaluation text beyond page four.
- Prepare a **three-minute demo video** and include its URL in the paper. The current file's approximately 2:57 runtime is close to the stated target; this audit does not claim organizer acceptance.
- Review is **single-blind**; include author names and affiliations.
- Use ACM two-column **sigconf**, PDF submission. Public source code/data/prototype links are permitted supplementary materials, but reviewers are not obliged to inspect them.
- Describe intended audience, innovative aspects, audience experience, supported functionality, user scenarios, interface/interaction, and comparisons where applicable.
- At least one author must be nominated as a reviewer; failure leads to desk rejection. At least one author of an accepted paper must register and present on site.
- Published dates are May 30, 2026 (abstract), June 6, 2026 (full paper), August 7, 2026 (notification), and **August 23, 2026 (camera-ready)**. All are in the past on September 19, 2026. Do not describe this rewrite as an on-time ordinary submission without separate organizer authorization/status evidence. No submission or contact with organizers was made.

## Validation and handoff

Only the bibliography and this audit were authored in this task. Existing unused keys were not deleted; no other contributor's changes were reverted. Main-paper editor should use the proposed nine-key set, ensure all citation claims are supported, and rerun full document compilation/page inspection after merging. Metadata correctness does not validate scientific claims or guarantee the final page count.

Mechanical validation completed: BibTeX 0.99d (TeX Live 2025), plain.bst, external temporary directory, exit code 0 with no warnings; all 20 unique keys rendered into 20 bibliography items. All nine proposed core keys are present. This checks BibTeX syntax, not the final ACM layout; independent manuscript review remains the main editor's responsibility.
