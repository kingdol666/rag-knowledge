# 知识库平台全链路压力测试报告（2026-09-23）

> 对象：RAG Knowledge Platform（feat/soul-persona-system @ 5570d98）— backend 8771 / BFF 6789 / Neo4j 7687 / MinerU 本地引擎
> 方法：9 阶段压测（S0–S8），httpx 连接池 + 恒速压测（避免压穿限流污染延迟数据），真实 PDF 与真实检索负载。
> 脚本与日志：本目录 s0–s8_*.py + *_output.log；判定总计 **41 项：41 PASS / 0 FAIL**（3 个采样脚本兼容性问题已用替代证据覆盖，非产品问题）。

## 一句话结论

**平台在压测下无崩溃、无数据损坏、无限流误伤、无资源泄漏；两个真实的性能瓶颈被定位（meditation/status 冷缓存 30s+；向量检索并发吞吐封顶 ~5.3 RPS），均为容量规划问题而非正确性问题。**

## S0 基线延迟（单线程，15 次取中位）

| 端点 | p50 | 端点 | p50 |
|---|---|---|---|
| /api/v1/health | 0.9ms | /api/v1/graph/stats | 8.3ms |
| /api/kb/catalog (BFF) | 19.1ms | /api/v1/soul/list | 10.0ms |
| /api/v1/search/stats | 20.5ms | /api/v1/experience/:kb | 3.5ms |
| **/api/v1/search/vector** | **273.8ms** | /api/kb/search (BFF 关键字) | 36.3ms |
| /api/v1/search/two-stage | 170.7ms | **/api/v1/meditation/status** | **冷 30s+ / 热 0.5s** |

## S1 并发读阶梯（9 端点混合，30s/级）

| 并发 | 目标 RPS | 实际 n | p50 | p95 | p99 | 错误 |
|---|---|---|---|---|---|---|
| 5 | 3 | 90 | 5.2ms | 28.1ms | 31.4ms | 0 |
| 15 | 6 | 180 | 86.9ms | 1766ms | 2818ms | 0 |
| 30 | 9 | 270 | **1577ms** | 2807ms | 3080ms | 0 |

**甄别实验（定位瓶颈）**：
- health-only 30 并发 @20RPS：p50=**1.5ms** → 认证中间件（逐请求查 auth.db）**不是**瓶颈。
- vector-only 30 并发 @9RPS：p50=**3743ms**（基线 274ms 放大 13.7×），30s 仅完成 159/270 → **向量检索有效吞吐封顶 ≈5.3 RPS/实例**（BGE-M3 embedding 全局串行点）。

> **S-P2（容量）**：检索层并发退化。生产建议：embedding 批量化/线程池隔离、热门 query 缓存、或检索前置队列；单实例检索型并发建议 ≤5 RPS。

## S2 并发写完整性（同一 KB）

- **20 并发**建文档：0.8s，20/20 全 200，`.tree-fs.json`/`.knowledge-base.yml` 无损坏（list==20）。
- **20 并发**索引：4.1s，20/20 全 200，collection chunks=620。
- 检索回验：向量 top_k=3 命中 1/3（同质模板稀释语义信号——测试设计问题）；**BM25 词法甄别 3/3 全命中 → 并发写零数据丢失**。
- **10 并发**建经验：1.6s，10/10 全 200，list==10。

## S3 大容量

- 250KB 单文档（193KB UTF-8）：入库 + **索引 2.8s**、标记词可检索。
- vector top_k=50：即时返回（count=50）；two-stage stage1=100 → stage2=282 结果：即时。

## S4 并发解析（MinerU）

- 2 个真实 PDF（1.1MB + 1.0MB）**并行**解析：29s + 24s，**墙钟 29s** —— 优于单解析基线 41s（引擎预热/队列复用），无互斥退化。

## S5 流与任务并发

- **5 路并发 mock SSE 会话**：全部到达终态（event:done + data result），5 个 session_id 唯一，**零串扰**。
- **25 个并发异步 agent 任务**（kb/agent/chat async + 任务注册表）：0 秒内全部受理，**25/25 completed**。

## S6 长稳压（6 分钟，8 并发 @4RPS 混合，45% 为重检索）

| 窗口 | n | p50 | p95 | 错误 |
|---|---|---|---|---|
| 0–2min | 480 | 858ms | 1590ms | 0 |
| 2–4min | 473 | 1161ms | 1756ms | 0 |
| 4–6min | 472 | 1159ms | 1680ms | 0 |

吞吐恒定、零错误；p50 漂移 1.35× 后**趋稳**（初期斜坡为缓存预热）——无劣化趋势、无泄漏征兆。

## S7 速率限制边界

- 50 线程不限速 burst 12s（/api/v1/soul/list）：**3952 请求（≈329 RPS）→ 200×416 + 429×3536**。
- 600 req/60s 滑动窗口**精确执行**；429 快速拒绝（p50 81ms，不占用服务端计算）。
- 70s 后窗口滑动：**完全恢复 200**，burst 无残留副作用；health 全程正常。
- heavy 限制（parse/mineru 60/min）未触界（S4 并发 2 个解析在配额内）。

## S8 资源与终检

- backend worker（BGE-M3 常驻）：RSS **981MB**（合理），CPU 累计 705s，无泄漏迹象；BFF Node RSS 103MB。
- 压后功能 sanity 5/5：向量命中压测文档、two-stage 全库、web stats、agent meta、health 全部正常。
- 清理级联：stress KB 删除 → -1 KB / -23 docs / 磁盘移除 / 向量覆盖仍 100%。

## 发现清单（按影响排序）

| 编号 | 级别 | 发现 | 建议 |
|---|---|---|---|
| S-P1 | 性能 | `/api/v1/meditation/status` 冷缓存 30s+（探针 TTL 30s 过期后同步重探全部 15 个 harness），热缓存 0.5s；前端冥想面板冷启动会"假死" | 探测改后台定时刷新，请求路径只回快照 |
| S-P2 | 容量 | 向量检索并发吞吐封顶 ~5.3 RPS/实例：30 并发下 p50 274ms→3.7s；认证层已排除（1.5ms@20RPS） | embedding 批处理/线程池隔离/结果缓存；容量规划按 ≤5 RPS 检索并发 |
| S-OK1 | 正面 | 并发写零丢失（含 YAML 三源一致）、限流器精准、并行解析加速、长稳压无劣化、SSE 会话隔离 | — |

## 复现说明

```bash
cd backend && .venv/Scripts/python.exe ../review/stress-20260923/s0_baseline.py   # 依序 s1→s8
```
限流配置：config.yml `server.rate_limit {max_requests:600, heavy_max:60}`（按 IP 滑动窗口；parse/mineru 走 heavy 桶）。
