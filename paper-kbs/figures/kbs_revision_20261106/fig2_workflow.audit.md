# Visual audit: fig2_workflow

Reference: GPT Image 2.5 visual-direction board in `garden-gpt-image-2/image/hmrs-kbs-visual-direction-20261106.png`.

Each visible region and element was recreated with native Draw.io shapes, text and connectors.

| ID | Visible element / check | Medium | Status |
|---|---|---|---|
| 01 | Canvas, title, and two swimlane panels on white background. | Native Draw.io | preview checked |
| 02 | Ingestion steps: source files, parse/quality, agent content-aware routing, save, separate index/probe. | Native Draw.io | preview checked |
| 03 | Placement note states that destination selection is agent-mediated, not a server classifier. | Native Draw.io | preview checked |
| 04 | Shared knowledge state bridge joins ingestion to query-time retrieval. | Native Draw.io | preview checked |
| 05 | Query steps: question, lane selection, candidate retrieval, optional Laya gate. | Native Draw.io | preview checked |
| 06 | Three distinct outcomes: evidence pack, completed empty search, and execution failure. | Native Draw.io | preview checked |
| 07 | Connector styles distinguish normal flow, optional gate, and failure path. | Native Draw.io | preview checked |

Preview was visually inspected from the exported PNG. The source is editable mxGraph XML; an application open/save round-trip remains unverified.
