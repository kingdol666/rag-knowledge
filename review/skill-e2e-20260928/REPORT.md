# 全 skill 测试报告（检索重点 · 输出内容审读）— 2026-09-28

## 覆盖结论
15 个知识库 skill 全部经过功能级或 agent 级测试；检索四道（search/librarian/hybrid/graph）
双 harness 覆盖，输出内容逐份对照金标审读，**全部达标**。

## 本轮新增 4 格（claude headless，检索+输出审读）

| Skill | 流程执行 | 输出内容评审 |
|---|---|---|
| **hybrid**（S0-S6 串行） | S0 双语查询整容 → S1 向量 30→23 候选 → S2 目录道含 L3 信任头读 → S3 合并 25（both=1/vec=22/cat=2）→ S4 真实 Laya 20 判 7 幸存（top 0.9631）→ S5 全文读 | 位置编码公式逐字（PE=sin/cos(pos/10000^(2i/d))）、波长几何级数 2π→10000·2π、固定偏移 k 的线性表达、学习式消融"nearly identical"+BLEU 25.8 —— **金标全命中** |
| **experience** | 全库盘点：10 条经验/4 库逐条读 + kb_* 交叉验证 + Glob 独立复核 | 逐库分布表 + 逐条标题/分类/要点；**发现并如实披露 permission 缺口**（experience_* 25 次被拒→改走权威落盘读取，未伪造） |
| **graph** | kb_graph_document + 反向遍历 15 邻居 | 16 关联节点/2 种关系（vector_similar 0.7646、shared_tag weight 4 含具体标签）/0 跨库，路径具体 |
| **verify**（只读） | Pre-Flight + 三源一致性逐库 + 重复/标签/索引 | 三源 0 不一致；**2 个 P0**（aw-industrial 4 文档无向量索引、Corpus-Chunks800 37,567 幽灵 chunk）+ 5 孤儿 collection + 627 污染标签；未做任何修复 |

## 由本轮发现并已修复
- **experience_*/kb_tags_cleanup 不在 claude headless 白名单**（25 次 denied，agent 如实披露后
  走落盘兜底）→ settings.local.json 已补 6 个 experience 只读工具 + kb_tags_cleanup。
- OMP API key 3 小时 $30 预算被打爆（429 ExceededBudget）→ 本轮后半改走 claude 通道。

## 遗留问题清单（verify 格实锤，建议排期）
1. aw-industrial 4 文档无向量索引（不可检索）→ 需 kb_index_document/kb_batch_index
2. Corpus-Chunks800 空库 + 37,567 幽灵 chunk + 目录截断 → 建议整库删除重建
3. 627 注册标签含大量测试残留/孤儿（含 8 个烹饪孤儿标签）→ kb_tags_cleanup(dry_run) 后清理
4. 近重复簇 3 组（aw-industrial 诊断报告 (1) 副本、soul 模板三份）
5. web dev 模式在机器内存压力下会被杀（环境因素）→ 稳定性要求高的场景用 headless 启动或 prod 模式

## OMP 配额备注
OMP key 3h 滚动预算 $30 已耗尽（429），hybrid 首跑失败于此；配额恢复后 OMP 通道照常可用。
