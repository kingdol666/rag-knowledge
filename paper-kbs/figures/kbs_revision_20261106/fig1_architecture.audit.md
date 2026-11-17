# Visual audit: fig1_architecture

Reference: GPT Image 2.5 visual-direction board in `garden-gpt-image-2/image/hmrs-kbs-visual-direction-20261106.png`.

Each visible region and element was recreated with native Draw.io shapes, text and connectors.

| ID | Visible element / check | Medium | Status |
|---|---|---|---|
| 01 | Canvas and title; white background; restrained blue, green, purple, amber and grey palette. | Native Draw.io | preview checked |
| 02 | Entry-point band: Browser / Web UI and Agent / CLI. | Native Draw.io | preview checked |
| 03 | Service band: Nuxt 3 server, FastAPI parse API, managed MinerU worker, MCP server (95 tools). | Native Draw.io | preview checked |
| 04 | Connectors separate web and MCP entry paths, the parse path, and data access. | Native Draw.io | preview checked |
| 05 | Platform-function band: ingest quality/split/enrich, KB lifecycle/audits, retrieval engines, optional Laya call. | Native Draw.io | preview checked |
| 06 | Shared-state band: Markdown/assets, tree registry and per-KB YAML, Chroma/BM25, Neo4j. | Native Draw.io | preview checked |
| 07 | Dashed data-access connectors and footer clarify separate save/index/judge operations. | Native Draw.io | preview checked |

Preview was visually inspected from the exported PNG. The source is editable mxGraph XML; an application open/save round-trip remains unverified.
