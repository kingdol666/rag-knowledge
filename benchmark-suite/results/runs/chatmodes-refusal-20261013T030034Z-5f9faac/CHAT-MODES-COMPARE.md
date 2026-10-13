# Chat-API 三模式系统臂对照（当前系统官方执行流）

- Run: `chatmodes-refusal-20261013T030034Z-5f9faac` · 生成: 2026-10-13 03:28 UTC
- 通道: `POST /api/claude/chat` 默认**非流式**（一次阻塞 JSON）· `kbEnhanced=true` · A/C 钉库 `kbIds` · 工具门禁由服务端 `disallowedTools` 内建
- 判定门: found=HTTP200∧success∧答案非空∧答案金标词命中; refusal=HTTP200∧success∧如实拒答标记

| 模式 | 题 | 预期 | 耗时s | turns | 门 | 会话 |
|---|---|---|---:|---:|:--:|---|
| A | cm4 | found | 78.5 | 5 | ✅ | `e2b08641` |
| A | cm5 | refusal | 49.9 | 7 | ✅ | `616be73d` |
| A | cm6 | refusal | 35.8 | 6 | ✅ | `cb6b1647` |
| A | cm7 | refusal | 63.8 | 8 | ✅ | `62e0e145` |
| A | cm8 | refusal | 217.4 | 9 | ✅ | `70ad08dc` |
| A | cm9 | refusal | 70.7 | 1 | ✅ | `0c2ac7b0` |
| B | cm4 | found | 106.8 | 9 | ✅ | `002406b1` |
| B | cm5 | refusal | 52.9 | 5 | ✅ | `f265d5e4` |
| B | cm6 | refusal | 83.1 | 9 | ✅ | `ea2b5c92` |
| B | cm7 | refusal | 80.4 | 7 | ✅ | `fd57c00a` |
| B | cm8 | refusal | 178.0 | 12 | ✅ | `52c93ba1` |
| B | cm9 | refusal | 136.4 | 8 | ✅ | `43a3c205` |
| C | cm4 | found | 69.5 | 6 | ✅ | `030b5aad` |
| C | cm5 | refusal | 94.8 | 1 | ✅ | `cbbc97c5` |
| C | cm6 | refusal | 59.6 | 6 | ✅ | `c9dbdb61` |
| C | cm7 | refusal | 125.6 | 9 | ✅ | `22fbab75` |
| C | cm8 | refusal | 148.1 | 7 | ❌ | `eda8d59e` |
| C | cm9 | refusal | 52.2 | 6 | ✅ | `81e22d7b` |

## 逐臂回答摘录

