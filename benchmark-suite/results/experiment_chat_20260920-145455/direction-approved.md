# direction-approved.md — Visual direction record (iteration exemption)

- **Date**: 2026-09-20
- **Deliverable**: Interactive HTML visual report for the retrieval benchmark
  (`results/experiment_chat_20260920-145455/` → `VISUAL_REPORT.html`)
- **Exemption used**: huashu-design Fallback gate, "已选定方向后的迭代" clause —
  this report evolves the ALREADY-ACCEPTED `benchmark_visual_report.html`
  direction (same project, same report family, judge-loop verified and pushed;
  user opened it in-browser and asked to extend it to the new retrieval benchmark
  with interactive per-question rendering).
- **Direction (accepted, reused)**: ink-on-paper light theme; established color
  semantics teal = platform (Track A) / gray = baselines (B/C) / orange-red =
  warnings & failures; serif display + monospace data accents ("terminal trace"
  motif matching monitored-run content).
- **User request (original)**: "把当前的检索的benchmark报告绘制为HTML的可视化报告，
  把所有的问题，以及对应的模式的完整回答交互式的渲染，满足 huashu-design 的skill
  设计规范，确保艺术设计感并且是一个好的benchmark报告"
- **Anti-slop notes**: no gradients, no emoji icons, no purple; all content is
  real experiment data (30 monitored runs); text-wrap pretty; one 120% detail:
  per-run telemetry chips styled as terminal trace lines.
