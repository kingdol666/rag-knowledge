# Subagent 逐级检索作业简报（零提示 · 全程监控）

你是一个检索 subagent。平台 = D:/codes/ClaudeGPT/rag_project/rag-knowledge 上的知识库系统（已启动：web:6789 / backend:8771 / kb-mcp:8000）。

## 问题（必须跨库回答）
参数高效微调方法是为解决大语言模型（LLM）的什么问题而设计的？LoRA 这类方法在 GPT-3 175B 上能把可训练参数量降低多少倍、GPU 显存需求降低多少倍？

## 作业规范（必须先读）
1. 先读逐级检索 skill 规范：D:/codes/ClaudeGPT/rag_project/rag-knowledge/.claude/skills/knowledgebase-librarian/SKILL.md，严格按其阶梯执行。
2. **零提示约束**：你不会得到任何库名/文档名/领域名提示——必须从 kb_list 的目录与描述层自主路由。
3. MCP 调用方式（工作目录 = 仓库根）：
   python -X utf8 scripts/mcp_call.py <tool> '<json-args>' --raw
   常用工具：kb_list(lightweight=true) → kb_get_documents(kb_id,lightweight,page,page_size) → kb_search_vector(query,kb_id,top_k,score_threshold,slim) → kb_laya_judge(query,documents,criterion="auto") → kb_doc_read(kb_id,doc_path,max_chars,limit)
4. 预算：≤16 次工具调用；每次调用后立刻把一条 trace 追加写到
   D:/codes/ClaudeGPT/rag_project/rag-knowledge/review/experiment-redesign-20261101/artifacts/demo-20261112/round2/subagent_trace.jsonl
   trace 行格式：{"n":序号,"tool":工具名,"args":参数摘要(≤120字),"result":关键结果摘要(≤200字),"s":耗时秒,"decision":本次调用后你决定下一步什么及为什么(≤80字)}
5. 读取 kb_doc_read 用 max_chars=60000, limit=100000（行数上限陷阱）。

## 作答要求（最后一步，也写进 trace 之外的 ANSWER.md）
把最终回答写到
D:/codes/ClaudeGPT/rag_project/rag-knowledge/review/experiment-redesign-20261101/artifacts/demo-20261112/round2/ANSWER.md
必须包含：①答案正文（两问都答）②每个关键结论的 doc_path + 逐字引用句 ③可信度标注 ④盲区申报（检索不到的部分如实说）。
禁止编造：检索/读取不到的内容如实写"未找到"。
