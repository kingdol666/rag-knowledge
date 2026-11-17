# 2026-11-12 清理归档 MANIFEST（更正版 v2，经 reviewer 复核整改）

清理执行者：ZCode（用户指令：清理过期过时资源）
原则：先归档后删除、可完全恢复；不动任何生产/服务/论文/语料/基线目录。

## 本次实际归档并删除的内容（stale-20261112.tar.gz，1 个 tarball，196 条）
1. repo 根垃圾文件：NUL（0 字节保留名残留）、_n10_orig.tmp、texput.log、e2e-hitl-allow-E2E-HITL-*.txt ×3、qdcvr_kbs.log
2. repo 根过期 console 日志：review-skill-fulltest*-console.log ×8（2026-09-27）
3. tmp/ 整目录（旧分析草稿 104 文件，14MB）
4. garden-gpt-image-2/（空目录）

## 更正与披露（v1 MANIFEST 的第 5 条作废）
v1 曾写"归档 experiment-redesign 混沌期日志（2026-11-11 之前）"——**该表述失实**：
- 经核查，`review/experiment-redesign-20261101/logs/` 在本次清理开始时就只有 2026-11-12 的
  R3 轮日志（12 个）。
- 混沌期/pilot/污染 checkpoint 日志**早在 2026-11-10 的终版清场轮已被删除**（该轮删除动作当时
  已记录于该目录 RESULTS.md "Stage 9 清场与终态"节："旧 timestamped traces、污染 checkpoint、
  pilot、混沌期日志均已删除"），**不是本次会话删除的**，本次会话没有经手这批文件。
- 佐证：本次清理尝试为这批日志建第二个 tarball 时 tar 报"空归档拒绝"——因为可归档对象为空。

## 明确保留（不清理）
final_bench、replication_bench_20261112、e2e_validation*、provenance、archive-superseded（含既有 tarball）、
.bench_backup_20260917（KBS 论文 provenance）、benchmark-web、paper_demo、paper-kbs、skills-archive、
storage/ chroma_db/ corpus/ baselines/ web/ backend/ kb-mcp/ docs/ tex/ command/ vibe_images/、
review/experiment-redesign-20261101/logs/（11-12 R3 轮 12 个日志全部保留）
