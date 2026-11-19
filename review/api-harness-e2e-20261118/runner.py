# -*- coding: utf-8 -*-
"""E2E runner for the outward-facing KB agent API (2026-11-18).

SSRF-hardened by construction: every request passes guard_url() which only
allows the local dev servers (127.0.0.1 / localhost, ports 8770 / 6789) and
blocks DNS rebinding — same pattern as scripts/dev_smoke.py.

Subcommands (each saves its result JSON next to this script):
  t2  sync retrieval Q&A via POST /api/kb/agent/chat (mode=sync default)
  t3  OOD honesty via POST /api/kb/agent/chat (sync)
  t4  async retrieval via mode=async + GET /api/kb/agent/tasks/:id polling
  t5  interactive 2-turn continuity via POST /api/claude/chat (kbEnhanced + resume)
  t6  async skill-driven ingest task (KB create + doc + index) via mode=async

Auth: Bearer token from storage/loop-auth.json (refreshed in auth setup).
"""
import ipaddress
import json
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
TOKEN_PATH = ROOT / 'storage' / 'loop-auth.json'
OUT_DIR = Path(__file__).resolve().parent
WEB = 'http://localhost:6789'

ALLOWED_HOSTS = {'127.0.0.1', 'localhost'}
ALLOWED_PORTS = {8770, 6789}


def guard_url(url: str) -> None:
    """SSRF guard: only the local dev servers are legal targets."""
    p = urlparse(url)
    if p.scheme != 'http' or p.hostname not in ALLOWED_HOSTS:
        raise ValueError(f'blocked target (scheme/host): {url!r}')
    if p.port not in ALLOWED_PORTS:
        raise ValueError(f'blocked target (port): {url!r}')
    ip = socket.gethostbyname(p.hostname)
    if ipaddress.ip_address(ip) != ipaddress.ip_address('127.0.0.1'):
        raise ValueError(f'DNS rebinding blocked: {url!r} -> {ip}')


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(_NoRedirect)


def request(url: str, method: str = 'GET', payload=None, token: str = None, timeout: int = 30):
    guard_url(url)
    req = urllib.request.Request(url, method=method)
    req.add_header('Accept', 'application/json')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    data = None
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        req.add_header('Content-Type', 'application/json')
    try:
        resp = OPENER.open(req, data=data, timeout=timeout)
        return resp.status, json.loads(resp.read().decode('utf-8', 'replace'))
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {'raw': raw[:500]}


def save(name: str, payload) -> Path:
    p = OUT_DIR / name
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'[saved] {p.name}', flush=True)
    return p


PROMPT_T2 = (
    'Transformer 模型中的缩放点积注意力（Scaled Dot-Product Attention）的计算公式是什么？'
    '请给出公式并解释其中各符号的含义，并注明出处文档。'
)
PROMPT_T3 = (
    '如何制作四川泡菜？需要哪些原料和发酵条件？请给出完整的制作步骤。'
)
PROMPT_T4 = (
    '在小说《傲慢与偏见》（Pride and Prejudice）中，班纳特夫妇共有几个女儿？'
    '长女的姓名是什么？请依据知识库文档回答并给出出处。'
)
PROMPT_T6 = (
    '请创建一个名为 api-e2e-20261118 的知识库（描述：对外 API harness 验收测试专用库），'
    '然后把下面这篇文档入库到该知识库，完成向量索引并回查验证，最后报告 doc_path 与 chunk 数。\n'
    '---文档开始---\n'
    '# HMRS 对外 API 验收记录（2026-11-18）\n\n'
    '本记录用于验收 POST /api/kb/agent/chat 对外接口的双模式能力。\n'
    '同步模式：HTTP 请求挂起至 agent 回合结束，返回完整信封（reply/tools_used/duration_ms/cost）\n'
    '异步模式：立即返回 task_id，后台执行，结果经 GET /api/kb/agent/tasks/{task_id} 轮询获取。\n'
    '验收要点：鉴权 401 双负测试、知识库增强提示词自动 injection、kb-mcp 工具真实调用、诚实拒答。\n'
    '---文档结束---'
)

T5_TURN1 = '在《傲慢与偏见》中，达西先生第一次向伊丽莎白求婚发生在什么场合？求婚的结果如何？'
T5_TURN2 = (
    '结合你上一轮回答的那次求婚：伊丽莎白拒绝达西时给出的最主要理由是什么？'
    '请基于知识库文档具体说明。'
)

# Bounded retest prompts (single-flight, latency-scoped; still skill-driven).
PROMPT_T2R = (
    '在知识库中查找 Transformer 缩放点积注意力（Scaled Dot-Product Attention）的计算公式。'
    '执行约束：按 /knowledgebase-search skill 的快速路径作业（查询改写 → kb_search_vector/kb_search_two_stage '
    '→ kb_laya_judge 一批（≤6 refs）→ 仅对最优幸存者 kb_doc_read 验证引文），'
    '不要委派子代理做完整图书管理员深检索，不要浏览仓库文件。'
    '最终答案 ≤250 字：公式 + 每个符号一句解释 + 出处文档名与所属知识库。'
)
PROMPT_T4R = (
    '在知识库中查询：《傲慢与偏见》中班纳特夫妇共有几个女儿、长女姓名。'
    '执行约束：按 /knowledgebase-search skill 的快速路径作业（先 kb_list 甄别小说库 → kb_search_vector '
    '→ kb_laya_judge 一批 → 至多 1 次 kb_doc_read 验证），不要委派子代理，不要浏览仓库文件。'
    '最终答案 ≤150 字并给出 doc_path 出处。'
)
PROMPT_T3R = (
    '在知识库中查询：四川泡菜的完整制作工艺（原料清单、盐水配比、发酵条件）。'
    '执行约束：快速路径（kb_list 目录层甄别 + 一轮 kb_search_vector），'
    '若知识库不覆盖该领域，按 skill 规范如实报告未找到（列出已检索的库与查询词），'
    '不要为了给出答案而编造内容，不要浏览仓库文件。最终回复 ≤200 字。'
)


def load_token() -> str:
    return json.loads(TOKEN_PATH.read_text(encoding='utf-8'))['token']


def agent_chat(body: dict, token: str) -> dict:
    t0 = time.time()
    s, b = request(WEB + '/api/kb/agent/chat', 'POST', body, token, timeout=630)
    b['_http_status'] = s
    b['_wall_s'] = round(time.time() - t0, 1)
    return b


def poll_task(task_id: str, token: str, deadline_s: float = 580.0) -> dict:
    t0 = time.time()
    last = None
    while time.time() - t0 < deadline_s:
        s, b = request(WEB + f'/api/kb/agent/tasks/{task_id}', 'GET', None, token, timeout=30)
        if s == 200 and b.get('status') != last:
            last = b.get('status')
            print(f'[poll {int(time.time()-t0)}s] status={last}', flush=True)
        if s == 200 and b.get('status') in ('completed', 'failed'):
            return b
        time.sleep(10)
    return {'success': False, 'error': 'poll deadline exceeded', 'last_status': last}


def run_sync(prompt: str, token: str, tag: str) -> dict:
    print(f'[{tag}] submitting sync agent turn...', flush=True)
    res = agent_chat({'prompt': prompt}, token)
    save(f'{tag}_result.json', res)
    return res


def main() -> None:
    tag = sys.argv[1]
    tok = load_token()

    if tag == 't2':
        run_sync(PROMPT_T2, tok, 't2')

    elif tag == 't3':
        run_sync(PROMPT_T3, tok, 't3')

    elif tag == 't4':
        print('[t4] submitting async task...', flush=True)
        sub = agent_chat({'prompt': PROMPT_T4, 'mode': 'async'}, tok)
        save('t4_submit.json', sub)
        if not sub.get('task_id'):
            print('[t4] no task_id — abort')
            return
        res = poll_task(sub['task_id'], tok)
        save('t4_result.json', res)

    elif tag == 't5':
        print('[t5] turn 1...', flush=True)
        t0 = time.time()
        s1, b1 = request(WEB + '/api/claude/chat', 'POST',
                         {'prompt': T5_TURN1, 'kbEnhanced': True, 'stream': False,
                          'engine': 'claude', 'timeout_ms': 600000},
                         tok, timeout=630)
        turn1 = {'status': s1, 'wall_s': round(time.time() - t0, 1)}
        if s1 == 200 and isinstance(b1, dict):
            turn1['answer_head'] = str(b1.get('answer', ''))[:400]
            turn1['session_id'] = b1.get('sessionId') or b1.get('session_id')
            turn1['tool_calls'] = b1.get('tool_calls')
            turn1['num_turns'] = b1.get('num_turns')
            save('t5_turn1_raw.json', b1)
        else:
            turn1['body'] = b1 if not isinstance(b1, dict) else {k: b1.get(k) for k in ('error', 'code', 'success')}
        print('[t5] turn 1 done:', turn1.get('session_id'), turn1.get('wall_s'), 's', flush=True)

        resume = turn1.get('session_id')
        if not resume:
            save('t5_result.json', {'success': False, 'stage': 'turn1', 'detail': turn1})
            return
        print('[t5] turn 2 (resume=' + str(resume)[:12] + '...)', flush=True)
        t0 = time.time()
        s2, b2 = request(WEB + '/api/claude/chat', 'POST',
                         {'prompt': T5_TURN2, 'kbEnhanced': True, 'stream': False,
                          'engine': 'claude', 'timeout_ms': 600000, 'resume': resume},
                         tok, timeout=630)
        wall2 = round(time.time() - t0, 1)
        turn2 = {'status': s2, 'wall_s': wall2}
        if s2 == 200 and isinstance(b2, dict):
            turn2['answer_head'] = str(b2.get('answer', ''))[:600]
            turn2['tool_calls'] = b2.get('tool_calls')
            turn2['num_turns'] = b2.get('num_turns')
        else:
            turn2['body'] = b2 if not isinstance(b2, dict) else {k: b2.get(k) for k in ('error', 'code', 'success')}
        save('t5_result.json', {'turn1': turn1, 'turn2': turn2})

    elif tag == 't2r':
        run_sync(PROMPT_T2R, tok, 't2r')

    elif tag == 't4r':
        print('[t4r] submitting async task...', flush=True)
        sub = agent_chat({'prompt': PROMPT_T4R, 'mode': 'async'}, tok)
        save('t4r_submit.json', sub)
        if not sub.get('task_id'):
            print('[t4r] no task_id — abort')
            return
        res = poll_task(sub['task_id'], tok)
        save('t4r_result.json', res)

    elif tag == 't3r':
        run_sync(PROMPT_T3R, tok, 't3r')

    elif tag == 't6':
        print('[t6] submitting async ingest task...', flush=True)
        sub = agent_chat({'prompt': PROMPT_T6, 'mode': 'async'}, tok)
        save('t6_submit.json', sub)
        if not sub.get('task_id'):
            print('[t6] no task_id — abort')
            return
        res = poll_task(sub['task_id'], tok)
        save('t6_result.json', res)

    else:
        print('unknown tag', tag)
        sys.exit(2)


if __name__ == '__main__':
    main()
