# -*- coding: utf-8 -*-
"""R2 round full test suite (2026-11-18, second acceptance run).

Runs five agent-turn groups SEQUENTIALLY (single flight, no contention):
  r2sync   sync retrieval (gold: scaled dot-product attention)
  r2ood    OOD honest refusal (pickles, domain absent)
  r2async  async retrieval (task_id -> poll -> envelope)
  r2chat   interactive 2-turn kbEnhanced + resume continuity
  r2full   run all of the above + ingest task (new KB api-e2e-20261118-r2)

SSRF-hardened: all HTTP through runner.py's guard_url/OPENER.
Artifacts: r2_*.json next to this script. No credential literals.
"""
import json
import sys
import time

import runner  # reuses guard_url/OPENER/request/agent_chat/poll_task/save

WEB = runner.WEB

PROMPT_SYNC = (
    '在知识库中查找 Transformer 缩放点积注意力（Scaled Dot-Product Attention）的计算公式。'
    '执行约束：按 /knowledgebase-search skill 的快速路径作业（查询改写 → kb_search_vector/kb_search_two_stage '
    '→ kb_laya_judge 一批（≤6 refs）→ 仅对最优幸存者 kb_doc_read 验证引文），'
    '不要委派子代理做完整图书管理员深检索，不要浏览仓库文件。'
    '最终答案 ≤250 字：公式 + 每个符号一句解释 + 出处文档名与所属知识库。'
)
PROMPT_OOD = (
    '在知识库中查询：四川泡菜的完整制作工艺（原料清单、盐水配比、发酵条件）。'
    '执行约束：快速路径（kb_list 目录层甄别 + 一轮 kb_search_vector），'
    '若知识库不覆盖该领域，按 skill 规范如实报告未找到（列出已检索的库与查询词），'
    '不要为了给出答案而编造内容，不要浏览仓库文件。最终回复 ≤200 字。'
)
PROMPT_ASYNC = (
    '在知识库中查询：《傲慢与偏见》中班纳特夫妇共有几个女儿、长女姓名。'
    '执行约束：按 /knowledgebase-search skill 的快速路径作业（先 kb_list 甄别小说库 → kb_search_vector '
    '→ kb_laya_judge 一批 → 至多 1 次 kb_doc_read 验证），不要委派子代理，不要浏览仓库文件。'
    '最终答案 ≤150 字并给出 doc_path 出处。'
)
CHAT_TURN1 = '在《傲慢与偏见》中，达西先生第一次向伊丽莎白求婚发生在什么场合？求婚的结果如何？'
CHAT_TURN2 = (
    '结合你上一轮回答的那次求婚：伊丽莎白拒绝达西时给出的最主要理由是什么？'
    '请基于知识库文档具体说明。'
)
PROMPT_INGEST = (
    '请创建一个名为 api-e2e-20261118-r2 的知识库（描述：对外 API R2 轮验收测试专用库），'
    '然后把下面这篇文档入库到该知识库，完成向量索引并回查验证，最后报告 doc_path 与 chunk 数。\n'
    '---文档开始---\n'
    '# R2 轮对外 API 验收记录（2026-11-18）\n\n'
    '本记录是第二轮对外接口验收的入库测试文档，验证建库→入库→索引→回查全管线。\n'
    '同步模式返回完整信封：reply、tools_used、duration_ms、total_cost_usd、session_id。\n'
    '异步模式即返 task_id，后台执行完毕后经 GET /api/kb/agent/tasks/{task_id} 取全信封。\n'
    'R2 轮新增检查点：文档须含四要素描述与标签，索引后 chunk 数必须大于等于 1。\n'
    '---文档结束---'
)


def run_sync(prompt: str, tag: str, tok: str) -> dict:
    print(f'[{tag}] sync submit...', flush=True)
    try:
        res = runner.agent_chat({'prompt': prompt}, tok)
    except Exception as e:  # client-side socket timeout etc. — one retry
        print(f'[{tag}] client error ({e}); retrying once...', flush=True)
        time.sleep(5)
        res = runner.agent_chat({'prompt': prompt}, tok)
    runner.save(f'{tag}_result.json', res)
    return res


def agent_chat_safe(body: dict, tok: str) -> dict:
    """agent_chat with client-side read timeout raised to 750s (server cap is
    600s + observed abort-settle overhead can exceed 630s under load)."""
    t0 = time.time()
    s, b = runner.request(runner.WEB + '/api/kb/agent/chat', 'POST', body, tok, timeout=750)
    b['_http_status'] = s
    b['_wall_s'] = round(time.time() - t0, 1)
    return b


def run_async(prompt: str, tag: str, tok: str) -> dict:
    print(f'[{tag}] async submit...', flush=True)
    try:
        sub = agent_chat_safe({'prompt': prompt, 'mode': 'async'}, tok)
    except Exception as e:
        print(f'[{tag}] client error ({e}); retrying once...', flush=True)
        time.sleep(5)
        sub = agent_chat_safe({'prompt': prompt, 'mode': 'async'}, tok)
    runner.save(f'{tag}_submit.json', sub)
    if not sub.get('task_id'):
        runner.save(f'{tag}_result.json', {'success': False, 'stage': 'submit', 'detail': sub})
        return sub
    res = runner.poll_task(sub['task_id'], tok)
    runner.save(f'{tag}_result.json', res)
    return res


def run_chat2(tag: str, tok: str) -> dict:
    print(f'[{tag}] turn 1...', flush=True)
    t0 = time.time()
    s1, b1 = runner.request(WEB + '/api/claude/chat', 'POST',
                            {'prompt': CHAT_TURN1, 'kbEnhanced': True, 'stream': False,
                             'engine': 'claude', 'timeout_ms': 600000}, tok, timeout=630)
    turn1 = {'status': s1, 'wall_s': round(time.time() - t0, 1)}
    if s1 == 200 and isinstance(b1, dict):
        turn1['answer_head'] = str(b1.get('answer', ''))[:400]
        turn1['session_id'] = b1.get('sessionId') or b1.get('session_id')
        turn1['toolCalls'] = b1.get('toolCalls')
        turn1['num_turns'] = b1.get('num_turns')
        turn1['cost'] = b1.get('total_cost_usd')
        runner.save(f'{tag}_turn1_raw.json', b1)
    else:
        turn1['error'] = str(b1)[:300]
    print(f'[{tag}] turn1 done {turn1.get("session_id")} {turn1["wall_s"]}s', flush=True)

    resume = turn1.get('session_id')
    if not resume:
        runner.save(f'{tag}_result.json', {'success': False, 'stage': 'turn1', 'detail': turn1})
        return {'turn1': turn1}
    t0 = time.time()
    s2, b2 = runner.request(WEB + '/api/claude/chat', 'POST',
                            {'prompt': CHAT_TURN2, 'kbEnhanced': True, 'stream': False,
                             'engine': 'claude', 'timeout_ms': 600000, 'resume': resume}, tok, timeout=630)
    turn2 = {'status': s2, 'wall_s': round(time.time() - t0, 1)}
    if s2 == 200 and isinstance(b2, dict):
        turn2['answer_head'] = str(b2.get('answer', ''))[:600]
        turn2['toolCalls'] = b2.get('toolCalls')
        turn2['num_turns'] = b2.get('num_turns')
        turn2['cost'] = b2.get('total_cost_usd')
        turn2['session_id_echo'] = b2.get('sessionId')
        runner.save(f'{tag}_turn2_raw.json', b2)
    else:
        turn2['error'] = str(b2)[:300]
    runner.save(f'{tag}_result.json', {'turn1': turn1, 'turn2': turn2})
    return {'turn1': turn1, 'turn2': turn2}


def main() -> None:
    tok = runner.load_token()
    which = sys.argv[1] if len(sys.argv) > 1 else 'r2full'

    groups = [
        ('r2sync', lambda: run_sync(PROMPT_SYNC, 'r2sync', tok)),
        ('r2ood', lambda: run_sync(PROMPT_OOD, 'r2ood', tok)),
        ('r2async', lambda: run_async(PROMPT_ASYNC, 'r2async', tok)),
        ('r2chat', lambda: run_chat2('r2chat', tok)),
        ('r2ingest', lambda: run_async(PROMPT_INGEST, 'r2ingest', tok)),
    ]
    for name, fn in groups:
        if which not in (name, 'r2full'):
            continue
        try:
            fn()
        except Exception as e:
            print(f'[{name}] GROUP FAILED: {e}', flush=True)
            runner.save(f'{name}_crash.json', {'error': str(e)[:500]})

    print('[r2] all requested groups done', flush=True)


if __name__ == '__main__':
    main()
