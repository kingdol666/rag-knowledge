# 全量 Skill 实测总结 — 2026-09-27

## 范围与结论

对全部 **21 个 skill** 做了四层递进实测(静态→只读→沙盒全生命周期写→distillation 闭环),
最终状态:**全部通过,无退化**。所有写操作仅作用于本次沙盒(KB s-audit-a/b、s-probe-*、
soul-skillaudit、soul-skillaudit-musk),全部清理验证零残留。

| 层 | 工具 | 覆盖 | 结果 |
|---|---|---|---|
| L1 静态审计 | scripts/118_skill_audit.py | 21 skill × frontmatter/断链/工具引用/核心结构 | 0 FAIL 0 WARN |
| L2 规范一致性 | scripts/validate_skills.cjs + sync_skills.py | 15 kb 系 skill 跨文件一致性 + 镜像同步 | PASS |
| L3 只读冒烟 | scripts/119_skill_smoke.py | 18 skill 26 调用(真实 MCP stdio 通道) | 0 失败 |
| L4 全生命周期 | scripts/120_skill_fulltest.py(v6) | 45 步: 建库→入库→检索→深检索→查重→改名→移动→重建索引→统计→图谱→经验 CRUD→soul 全链→边界用例→清理 | **0 FAIL** |
| L5 butian 闭环 | scripts/122_butian_distill_e2e.py | musk 种子→nuwa_to_seed 转换→ragctl soul distill 落地→4 宪法文档→qdcvr 人格作答→清理 | **ALL PASS** |
| 单元 | librarian tests | complete_recall/Jev 14 用例 | 14/14 |

## 发现并修复的真实缺陷(7 项)

| # | 缺陷 | 位置 | 修复 |
|---|---|---|---|
| 1 | parse_doc 对不支持的 .md 静默"成功"返回空 markdown(违 fail-closed),是入库失踪链根源 | kb-mcp/server.py | 格式白名单校验,显式拒绝+指引文本格式直存 |
| 2 | 空查询返回无关垃圾结果 | kb-mcp/server.py | kb_search/kb_search_vector/kb_search_two_stage/soul_ask/soul_qdcvr_ask 五处空查询门禁 |
| 3 | .md 源文件名存成 "x.md.md"/"x.md (1).md" | web/server/api/parse/save-parsed-files.post.ts | 去扩展名正则补 md/markdown/txt |
| 4 | rename 后立即 move 404 "Document not found"(跨 worker 陈旧内存索引,_dirty 永不重载) | web tree-file-system-service + move.post/update.patch | 新增 getFileByPathWithReload(miss 时强制盘载一次);探针 5/5 稳定 |
| 5 | kb_doc_move 不接受 "kbUuid/doc.md" 前缀(与全系统 kb_id 双形态惯例不一致) | web move.post.ts | UUID 前缀回退解析 |
| 6 | ragctl soul distill 建库/写文档 fetch 无 Authorization 头,token 过期即 401(butian Step 4 全链断) | command/ragctl.js | getAuthCandidates(.env+loop-auth.json)+401 逐候选重试 |
| 7 | skill 文档漂移: soul/butian REST 回退端口 8765 已死(真实 8771)且未提 Bearer;dot-skill 全文 python3 在 Windows 落 Store 桩 | 3 个 SKILL.md | 端口改 BACKEND_PORT 现值+auth 提示;补 Windows python 说明 |

## 验证为"设计行为"的疑点(未改代码)

- **A0 内容去重**: 同 KB 同内容 kb_doc_create 返回既有文档+`deduped:true`,不落新文件 — 契约如此,测试断言已按此校准。
- **kb_find_duplicates**: 近重复=同库向量相似度≥0.90(可调 threshold),实测 0.9947 检出;batch_index 后瞬间查询可能遇 HNSW 落盘可见性延迟,重试即可。
- **experience severity 枚举**: critical/important/normal/tip(签名文档已补注)。
- **soul_init Windows 保留名/kb_create 重名**: 均为结构化 success=False 拒绝(fail-closed 正确),非异常。

## soul 真机证据(每轮一致)

- soul_qdcvr_ask: "Zephyr-7 的冷却液容量为 42 升" + 2-3 条引用,PAS 4.0-5.0
- soul_ask 自动路由: 无人格名提问→自动选中 skill-audit 人格→答对"恰好 3 次往返"+引用
- soul_train_rl(rounds=1): ~140-190s,reward 2.67-2.75,六维评分+11/6 个记忆草稿产出
- checkpoint→rollback: 恢复 6-11 条记忆,宪法层不回滚(契约)
- butian 落地人格作答呈第一性原理语言风格("把问题压到物理常数上"),人格注入真实生效

## 逐 skill 判定

| skill | 判定 | 依据 |
|---|---|---|
| knowledgebase | ✅ | 调度器入口 kb_list/kb_project_status 全通 |
| knowledgebase-list | ✅ | kb_list/kb_get_documents(catalog) 45 步内全过 |
| knowledgebase-ingest | ✅ | A3b/A5/A6 全过;.md 命名修复后 save→tag→index 链完整(修复#1#3) |
| knowledgebase-search | ✅ | Phase1 向量 0.73 命中/Phase2 two_stage 命中/空查询门禁(修复#2) |
| knowledgebase-librarian | ✅ | complete_recall 对 3 文档沙盒保留全部 Zephyr 事实;单测 14/14 |
| knowledgebase-hybrid | ✅ | 双 lane 工具面(vector+catalog)各自验证 |
| knowledgebase-organize | ✅ | kb_find_duplicates 0.9947 检出近重复 |
| knowledgebase-manage | ✅ | 改名→移动→计数(修复#4#5 后 0.3s 窗口稳定) |
| knowledgebase-batch | ✅ | kb_batch_index force 全量重建 |
| knowledgebase-verify | ✅ | kb_search_stats 21 collections 覆盖 |
| knowledgebase-graph | ✅ | build(轮询 done)→search zephyr 节点→central_documents |
| knowledgebase-experience | ✅ | create→search 命中→update(合法枚举)→list 回读→delete |
| knowledgebase-experience-summarize | ✅ | experience_list/summary 前置面 |
| knowledgebase-init | ✅ | kb_project_status runtime 面;栈健康实测(backend/web/neo4j 在线) |
| knowledgebase-update | ✅ | kb_project_status show_version |
| soul | ✅ | §A 创建/状态/删除+§B RL 训练+§C 双问答+§D 审批/检查点/回滚/反思/导出(修复#7) |
| soul-rag | ✅ | 检索→人格合成统一入口 soul_qdcvr_ask 真机三轮一致 |
| butian | ✅ | Step3 转换器+Step4 落地(修复#6)+Step6 使用全通 |
| nuwa-skill | ✅ | 产物契约→nuwa_to_seed 真转换(6757+19409 字符种子)→落地 |
| dot-skill | ✅ | tools 层(skill_writer/version_manager)实测;示例 3 个可列;Windows python 说明(修复#7) |
| musk-perspective | ✅ | 真实夹具完成转换→落地→人格化作答 |

## 工件

- scripts/120_skill_fulltest.py(驱动器 v6) / scripts/121_probe_dup_move.py(探针) / scripts/122_butian_distill_e2e.py
- review/skill-fulltest-20260927/: REPORT.md(45 步明细)+steps.json+librarian-manifest/output+musk-seed
- console 日志: review-skill-fulltest-v1..v6-console.log(演进轨迹)
