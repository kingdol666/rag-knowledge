# Architecture reference reconstruction audit

- Source: `C:/Users/87287/AppData/Local/Temp/codex-clipboard-516678fa-89c0-4762-8da3-c25e15925641.png`.
- Source and preview canvas: 1754 × 897 pixels, white.
- Editable deliverable: `architecture.drawio`. Native, separately selectable draw.io cells include all headings, labels, containers, backgrounds, solid/dashed connector segments and arrows. Labels reproduce the supplied figure; no manuscript files modified.
- Draw.io CLI generated `architecture.png` and `architecture.pdf`; checker reports 82 cells, 68 vertices and 12 edges. PDF text is selectable.
- Fourteen reference icon crops (`browser`, `terminal`, `nuxt`, `api`, `mineru`, `markdown`, `mcp`, `laya`, `file`, `registry`, `metadata`, `indices`, `retrieval`, `graph`) are individually selectable, movable, replaceable image cells with embedded transparent PNG data. Their pixels are not independently editable vector strokes. Therefore the PDF is mixed vector/raster, not a pure-vector graphic. The crop extraction approximately reconstructs transparency around the black icons.

## Visible-element inventory

| Region | Contents | Medium | Status |
|---|---|---|---|
| Canvas | White 1754 × 897 background | Native | Complete |
| Four vertical groups | Dashed rounded borders for Clients, Access & Orchestration, Knowledge Management Services, Retrieval & Navigation | Native | Complete; dash spacing and radii approximate source |
| Blue group headings | Four rounded pale-blue panels, labels and line breaks | Native | Complete; generated-source font antialiasing and subtle color texture differ |
| Clients | Browser icon, Agent / CLI terminal icon and labels | PNG icons, native text | Complete |
| Access | Nuxt Web, FastAPI (Parsing), MinerU, Parsed Markdown, MCP Tool Server, optional Laya (Evidence Scoring) | PNG icons, native text and boxes | Complete |
| Management | Shared Managed State; Document Files, Tree Registry, Library Metadata and Dense + BM25 Indices; subtitles | PNG icons, native text and boxes | Complete |
| Retrieval | Retrieval with ChromaDB/BGE-M3/BM25 and Neo4j Graph (Navigation Only) | PNG icons, native text and boxes | Complete |
| Connectors | Client-to-service arrows; parse path; two state operations; two optional Laya dashed arrows; state-to-retrieval and graph branches | Native | Complete; routed using editable waypoints |

## Visual comparison / limits

- Source screenshot was generated and has antialiasing, subtle shading and irregular strokes. Native Arial text, flat blue fills, arrowhead geometry and panel border radii approximate those pixels rather than reproducing them exactly. Mean absolute RGB difference is 15.92/255 on the full matching canvas; this is not pixel-identical.
- Label geometry and icon extraction were visually checked against the source; generated source does not supply original editable vector geometry, so exact per-pixel reconstruction is not guaranteed.
- The separate PNG icon crops are embedded; opening the `.drawio` file does not depend on linked local images. Their transparency was reconstructed from the source; some antialiased edges differ from the original.
