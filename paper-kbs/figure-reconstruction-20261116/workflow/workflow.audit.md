# Workflow reconstruction audit

Reference: `codex-clipboard-da681d0d-38bf-446b-a6b3-8ed6c75dc78c.png`, 1997 × 788 px. The draw.io export `workflow.png` has the same pixel dimensions. The original remains unchanged.

## Visible-element inventory

| ID | Approximate region (px) | Elements and medium | Review |
|---|---|---|---|
| canvas | 0, 0, 1997, 788 | Off-white background, native rectangle | done |
| S1 | 18, 58, 395, 680 | Blue title band; documents, parse, review cards; native shapes and labels; three separate source-cropped icons | done |
| S2 | 446, 58, 466, 680 | Title, content assignment, tags, save, index, shared collection; native shapes and labels; five separate source-cropped icons | done |
| S3 | 946, 58, 481, 680 | Title, question, catalogue, shelf, document, pinned search, candidates; native shapes and labels; six separate source-cropped icons | done |
| S4 | 1453, 58, 527, 680 | Title, optional Laya diamond, score, read evidence and three outcomes; native shapes and labels; six separate source-cropped icons | done |
| connectors | across four stages | All vertical, branching and cross-stage arrows and Yes/No labels as native editable cells | done |

## Editability and checks

- 26 native editable text cells, 22 native connectors and native card, panel and decision shapes; 20 independently movable source-cropped icon image cells.
- Cropped icons preserve reference artwork, but their internal strokes are raster pixels and cannot be edited individually as vectors. All wording remains separate from the icons.
- XML was parsed and `check_drawio.py` passed; the actual draw.io desktop application exported both PNG and PDF. The PDF is hybrid artwork because it contains those 20 embedded raster icons.
- After export the reference and reconstruction were inspected visually. Typography, antialiasing, very subtle source gradients, icon transparency edges and individual arrowhead geometry are approximations, not pixel-identical tracing. RGB mean absolute differences are approximately 15.2, 14.4 and 14.0 on the 0–255 scale; this is not a formal perceptual quality metric.
- The workflow is reconstructed as shown, including the reference image's “Quality review (agent, optional)” wording and its sequence. It has not been checked against the underlying software implementation, because this request was image reconstruction only.
