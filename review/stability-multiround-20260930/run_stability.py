#!/usr/bin/env python3
"""run_stability — 三模式 × 三任务 × 多轮稳定性矩阵（chat API，默认非流式）。

模式定义（对应当前 chat API 双车道 + 混合语义）：
  A 向量快车道   : kbEnhanced + 指定库（API 注入向量车道提示）
  B 逐级检索通道 : kbEnhanced + 不指定库（API 注入逐级主干提示，无向量工具）
  C 混合         : kbEnhanced + 指定库 + prompt 追加"先向量判定、不足再逐级补全"

任务（均带可核验 ground truth）：
  attention  : Transformer 自注意力公式      → 计算机与人工智能(131篇) Attention Is All You Need
  seismology : 地震波分类与区别（P/S/面波）  → 自然科学与地球科学(75篇) seismology 论文
  pickles    : 四川泡菜腌制（语料库中不存在）→ 期望如实奉告（反幻觉契约）

用法：python run_stability.py r1 r2        # 轮次可任选
输出：results/r{round}_{task}_{mode}.json + 控制台进度行（flush 实时）
"""
import http.client
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'results'
KB_CS = 'b1199132-e4d4-4305-8c2e-82dc1753b0ba'   # 计算机与人工智能
KB_NS = '1e6199ea-f380-44e2-94fc-d431f0f9bb6b'   # 自然科学与地球科学

TASKS = {
    'attention': {
        'prompt': 'Transformer 的自注意力机制（self-attention）的计算公式是什么？',
        'pin': KB_CS,
    },
    'seismology': {
        'prompt': '地震波主要分为哪几类？它们有什么区别？',
        'pin': KB_NS,
    },
    'pickles': {
        'prompt': '如何腌制四川泡菜？',
        'pin': KB_CS,   # 故意指定一个不含此内容的库 → 期望如实奉告
    },
}
HYBRID_SUFFIX = ('【混合检索模式】先用 kb_search_two_stage / kb_search_vector 宽网检索'
                 '并用 kb_laya_judge 判定；若幸存证据不足以回答，再用 kb_list → '
                 'kb_get_documents 逐级检索补齐后才作答。')


def token() -> str:
    """MCP_AUTH_TOKEN from .env; fall back to storage/loop-auth.json."""
    env = REPO / '.env'
    if env.exists():
        for line in env.read_text(encoding='utf-8').splitlines():
            if line.startswith('MCP_AUTH_TOKEN='):
                tok = line.split('=', 1)[1].strip()
                if tok:
                    return tok
    for key in ('MCP_AUTH_TOKEN', 'token', 'access_token'):
        f = REPO / 'storage' / 'loop-auth.json'
        if f.exists():
            data = json.loads(f.read_text(encoding='utf-8'))
            if isinstance(data, dict) and data.get(key):
                return str(data[key])
    raise SystemExit('no MCP_AUTH_TOKEN in .env and no token in storage/loop-auth.json')


# ── 车道契约（论文 sec4 的 27/27 lane-contract compliance 的复算依据） ────────
VECTOR_TOOLS = {'kb_search_vector', 'kb_search_two_stage', 'kb_search_stats'}
CATALOG_TOOLS = {'kb_list', 'kb_get_documents', 'kb_doc_read'}


def _short(names: list[str]) -> set[str]:
    return {str(n).split('__')[-1] for n in names or []}


def lane_check(mode: str, calls: list[str]) -> dict:
    """A=向量快车道（必须真的走向量族）；B=逐级通道（零向量调用，走目录族）；
    C=混合（只要有真实检索调用即可，允许两族并存）。
    `ok=False` 且 `zero_tool=True` 表示这一格根本没检索——该格无效，不是车道结果。
    """
    s = _short(calls)
    zero = len(s) == 0
    if mode == 'A':
        ok = bool(s & VECTOR_TOOLS)
    elif mode == 'B':
        ok = (not (s & VECTOR_TOOLS)) and bool(s & CATALOG_TOOLS)
    else:
        ok = not zero
    return {'mode': mode, 'zero_tool': zero, 'ok': ok,
            'vector_used': sorted(s & VECTOR_TOOLS),
            'catalog_used': sorted(s & CATALOG_TOOLS),
            'tools': sorted(s)}



def run_once(round_no: int, task: str, mode: str) -> dict:
    spec = TASKS[task]
    prompt = spec['prompt']
    kb_ids = [spec['pin']] if mode in ('A', 'C') else []
    if mode == 'C':
        prompt = prompt + ' ' + HYBRID_SUFFIX
    body = {
        'prompt': prompt,
        'kbEnhanced': True,
        'kbIds': kb_ids,
        'engine': 'claude',
        'permissionMode': 'default',
        'timeout_ms': 480000,
        # 2026-10-13: without this the kb-mcp mount races the SDK init and the
        # cell silently answers with zero kb tools (KB_TOOLS_NOT_READY), which
        # is an environment artifact, not a lane result.
        'mcpMount': 'stdio',
    }
    conn = http.client.HTTPConnection('127.0.0.1', 6789, timeout=540)
    t0 = time.time()
    try:
        conn.request('POST', '/api/claude/chat', body=json.dumps(body),
                     headers={'Content-Type': 'application/json',
                              'Authorization': f'Bearer {token()}'})
        resp = conn.getresponse()
        raw = resp.read().decode('utf-8')
    finally:
        conn.close()
    wall = time.time() - t0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = {'success': False, 'error': raw[:300]}
    rec = {
        'round': round_no, 'task': task, 'mode': mode,
        'http': resp.status, 'wall_s': round(wall, 1),
        'success': payload.get('success'),
        'session_id': payload.get('sessionId'),
        'turns': payload.get('num_turns'),
        'cost': payload.get('total_cost_usd'),
        'duration_ms': payload.get('duration_ms'),
        'answer': payload.get('answer') or payload.get('error', ''),
        # 2026-10-13: chat.post.ts 现在回传本轮的 kb 工具调用序（toolCalls）。
        # 车道合规（fast=向量族 / librarian=目录族且零向量调用）必须能从落盘
        # 文件复算，否则 27/27 只能靠人工读 session trace。
        'tool_calls': payload.get('toolCalls') or [],
        'tool_call_count': payload.get('toolCallCount'),
    }
    # 落盘前算一次车道契约，让「合规」成为每个单元自带的字段而非事后断言
    rec['lane'] = lane_check(mode, rec['tool_calls'])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'r{round_no}_{task}_{mode}.json').write_text(
        json.dumps(rec, ensure_ascii=False, indent=1), encoding='utf-8')
    return rec


if __name__ == '__main__':
    argv = [a for a in sys.argv[1:]]
    if '--out' in argv:
        i = argv.index('--out')
        OUT = Path(argv[i + 1]).resolve()
        del argv[i:i + 2]
    rounds = argv or ['r1']
    total = len(rounds) * len(TASKS) * 3
    done = 0
    for rnd in rounds:
        n = int(rnd[1:]) if rnd.startswith('r') else int(rnd)
        for task in TASKS:
            for mode in ('A', 'B', 'C'):
                done += 1
                tag = f'{rnd}_{task}_{mode}'
                print(f'[{done}/{total}] RUN {tag} …', flush=True)
                try:
                    rec = run_once(n, task, mode)
                    head = (rec['answer'] or '').replace('\n', ' ')[:120]
                    ln = rec.get('lane') or {}
                    print(f'  → HTTP {rec["http"]} · {rec["wall_s"]}s · ok={rec["success"]} '
                          f'· turns={rec["turns"]} · ${rec["cost"]} · sess={str(rec["session_id"])[:12]}\n'
                          f'    lane={"OK" if ln.get("ok") else "VIOLATION"}'
                          f'{"(zero-tool)" if ln.get("zero_tool") else ""}'
                          f' vec={ln.get("vector_used")} cat={ln.get("catalog_used")}\n'
                          f'    {head}', flush=True)
                except Exception as exc:  # noqa: BLE001 — 记录后继续下一跑
                    print(f'  → EXCEPTION {type(exc).__name__}: {exc}', flush=True)
                    OUT.mkdir(parents=True, exist_ok=True)
                    (OUT / f'{tag}_EXCEPTION.txt').write_text(
                        f'{type(exc).__name__}: {exc}', encoding='utf-8')
    print('STABILITY-RUNS-DONE', flush=True)
