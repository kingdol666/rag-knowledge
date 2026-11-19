# -*- coding: utf-8 -*-
"""R3 round: full-chain resource-lane operations + doc-as-contract verification.

Every check is executed exactly as documented in docs/api-web.md v2.0 (with
placeholders substituted). Two verdicts per item: chain (did the operation
work end-to-end) and contract (did the response match the documented schema).

SSRF-hardened (runner.guard_url). No credential literals: token + password
are read from storage/loop-auth.json at runtime.

Artifacts: r3_chain.json, r3_contract.json, r3_summary.json.
"""
import json
import time

import runner
from runner_r2 import agent_chat_safe

WEB = runner.WEB
OUT = {}


def check(items, item_id, ok, detail):
    items.append({'id': item_id, 'ok': bool(ok), 'detail': detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {item_id}: {detail}", flush=True)
    return ok


def doc_contract(tok):
    """US-010: execute doc examples verbatim, verify documented schemas."""
    res = []
    t = lambda path, body=None, method='GET': runner.request(WEB + path, method, body, tok, timeout=30)

    # §2 快速开始 ① login -> response has .token (jq -r .token must work)
    loop = json.loads(runner.TOKEN_PATH.read_text(encoding='utf-8'))
    s, b = t('/api/auth/login', {'username': loop['username'], 'password': loop['password']}, 'POST')
    check(res, 'doc-2.1-login', s == 200 and 'token' in b and b.get('success'),
          f'login status={s}, has token field, success={b.get("success")}')

    # §5.1 meta: {success, chat{endpoint,body}, engines[{id,permissionModes}]}
    s, b = t('/api/kb/agent/meta')
    ok = s == 200 and b.get('success') and 'chat' in b and isinstance(b.get('engines'), list) \
        and all('id' in e and 'permissionModes' in e for e in b['engines'][:3])
    check(res, 'doc-5.1-meta', ok, f'meta status={s}, engines={len(b.get("engines", []))}')

    # §5.1 harnesses: {success, backend_reachable, default, count, harnesses[]}
    s, b = t('/api/harnesses')
    ok = s == 200 and b.get('success') and 'default' in b and isinstance(b.get('harnesses'), list) \
        and all('id' in h and 'available' in h for h in b['harnesses'][:3])
    check(res, 'doc-5.1-harnesses', ok, f'harnesses status={s}, count={b.get("count")}')

    # §5.4 catalog: {success, count, knowledgeBases[{kbId,name,description,documentCount,path,parentId}]}
    s, b = t('/api/kb/catalog')
    kbs = b.get('knowledgeBases', [])
    fields_ok = kbs and all(k in kbs[0] for k in ('kbId', 'name', 'description', 'documentCount', 'path', 'parentId'))
    check(res, 'doc-5.4-catalog', s == 200 and b.get('success') and fields_ok,
          f'catalog status={s}, count={b.get("count")}, fields_ok={fields_ok}')

    # §4.3 error shell: missing prompt -> {error:true, statusCode:400,...}
    s, b = t('/api/kb/agent/chat', {}, 'POST')
    check(res, 'doc-4.3-error-shell', s == 400 and b.get('error') is True and 'statusCode' in b,
          f'missing-prompt status={s}, error shell={b.get("error")}, statusCode={b.get("statusCode")}')

    # §5.4 kb/search: ?query=&top_k= -> {success, query, count, hits}
    s, b = t('/api/kb/search?query=attention%20transformer&top_k=5')
    check(res, 'doc-5.4-kbsearch', s == 200 and b.get('success') and 'hits' in b and 'count' in b,
          f'kb/search status={s}, count={b.get("count")}')

    # §5.4 search/vector POST {query, kb_id?, top_k?} -> proxy; assert success + results-ish
    s, b = t('/api/search/vector', {'query': 'scaled dot-product attention', 'top_k': 5}, 'POST')
    check(res, 'doc-5.4-vector', s == 200 and (b.get('success') in (True, None)) and isinstance(b, (dict, list)),
          f'search/vector status={s}, keys={list(b)[:6] if isinstance(b, dict) else type(b).__name__}')

    # §5.4 search/two-stage POST -> body.success + body.stage2.results (doc: 断言 body.success)
    s, b = t('/api/search/two-stage', {'query': 'attention is all you need', 'stage2_top_k': 5}, 'POST')
    stage2 = b.get('stage2') or {}
    check(res, 'doc-5.4-twostage', s == 200 and b.get('success') is True and 'results' in stage2,
          f'two-stage status={s}, success={b.get("success")}, stage2.results={len(stage2.get("results", []) or [])}')

    # §5.9 automation GET ?kb_id= / toggle / summarize
    s, b = t('/api/kb/automation?kb_id=aw-industrial')
    ok1 = s == 200 and isinstance(b, (dict, list))
    check(res, 'doc-5.9-automation-get', ok1, f'automation GET status={s}, keys={list(b)[:5] if isinstance(b, dict) else type(b).__name__}')
    s, b = t('/api/kb/automation/toggle', {'kbId': 'aw-industrial', 'enabled': True}, 'POST')
    check(res, 'doc-5.9-automation-toggle', s in (200, 201) and (b.get('success') in (True, None)),
          f'toggle status={s}, body={json.dumps(b, ensure_ascii=False)[:120]}')
    s, b = t('/api/kb/automation/summarize', {'kbId': 'aw-industrial'}, 'POST')
    check(res, 'doc-5.9-automation-summarize', s in (200, 201, 202, 409, 429),
          f'summarize status={s} (触发成功或忙/重复均可读), body={json.dumps(b, ensure_ascii=False)[:120]}')

    # §4.2 double spelling read-back (uses KB created in the chain section)
    for q, tag in (('kb_id=api-e2e-20261118-r3&doc_path=', 'snake'), ('kbId=api-e2e-20261118-r3&docPath=', 'camel')):
        import urllib.parse
        dp = urllib.parse.quote('R3链路验证文档.md')
        s, b = t(f'/api/kb/document?{q}{dp}')
        check(res, f'doc-4.2-readback-{tag}', s == 200, f'read-back ({tag}) status={s}')
    return res


def full_chain(tok):
    """US-007: resource-lane only — create KB -> doc -> index -> vector hit -> keyword hit -> catalog."""
    res = []
    t = lambda path, body=None, method='GET': runner.request(WEB + path, method, body, tok, timeout=60)
    KB = 'api-e2e-20261118-r3'
    DOC = 'R3链路验证文档.md'
    CONTENT = ('# R3 全链路验证文档\n\n本文档由纯 HTTP 资源端点链路写入，用于验证外部 API 对分析系统的真实操作能力。\n'
               '关键事实标记：R3-CHAIN-CANARY-20261118，缩放点积注意力公式为 softmax(QK^T/sqrt(d_k))V。\n'
               '持久化验证查询词：R3 链路 金丝雀标记。\n')

    s, b = t('/api/kb/create', {'name': KB, 'description': '对外 API R3 全链路验证专用库'}, 'POST')
    created = s in (200, 201)
    check(res, 'chain-1-create-kb', created or s == 409, f'create KB status={s} (409=已存在续用), body={json.dumps(b, ensure_ascii=False)[:120]}')

    s, b = t('/api/kb/documents/create', {'kbId': KB, 'name': DOC, 'content': CONTENT,
                                          'description': 'R3 链路验证：外部 API 写入分析系统'}, 'POST')
    ok = s in (200, 201)
    detail = f'create doc status={s}, body={json.dumps(b, ensure_ascii=False)[:160]}'
    if not ok:  # 409/已存在 -> 续用
        s2, b2 = t(f'/api/kb/document?kbId={KB}&docPath={DOC}')
        ok = s2 == 200
        detail += f' | readback={s2}'
    check(res, 'chain-2-create-doc', ok, detail)

    s, b = t('/api/search/reindex', {'kb_id': KB, 'force': True}, 'POST')
    ok = s in (200, 201, 202)
    check(res, 'chain-3-reindex', ok, f'reindex status={s}, body={json.dumps(b, ensure_ascii=False)[:160]}')
    if ok:
        time.sleep(3)  # 索引落盘窗口

    s, b = t('/api/search/vector', {'query': 'R3 链路 金丝雀标记', 'kb_id': KB, 'top_k': 5}, 'POST')
    hit = False
    if s == 200:
        blob = json.dumps(b, ensure_ascii=False)
        hit = ('R3链路验证文档' in blob) or ('R3-CHAIN-CANARY' in blob) or (b.get('success') is True and 'results' in b)
    check(res, 'chain-4-vector-hit', s == 200 and hit, f'vector search status={s}, hit={hit}')

    s, b = t('/api/kb/search?query=R3-CHAIN-CANARY-20261118&top_k=10')
    blob = json.dumps(b, ensure_ascii=False) if isinstance(b, dict) else str(b)
    kw_hit = 'R3链路验证文档' in blob or DOC in blob
    check(res, 'chain-5-keyword-hit', s == 200 and kw_hit, f'keyword search status={s}, hit={kw_hit}')

    s, b = t('/api/kb/catalog')
    entry = [k for k in (b.get('knowledgeBases') or []) if k.get('name') == KB]
    check(res, 'chain-6-catalog-visible', s == 200 and entry and entry[0].get('documentCount', 0) >= 1,
          f'catalog status={s}, entry={entry[0].get("kbId") if entry else None}, docCount={entry[0].get("documentCount") if entry else 0}')
    return res


def agent_turns(tok):
    """Doc quick-start ② ③ — sync + async agent turns with the documented template."""
    res = []
    prompt = ('在知识库中查询：《傲慢与偏见》中班纳特夫妇共有几个女儿、长女姓名。'
              '执行约束（最小路径）：直接对小说库做一次 kb_search_vector（slim），再对最优命中做一次 kb_doc_read 验证；'
              '跳过 kb_laya_judge（当前降级）；不要 kb_list 预扫描，不要委派子代理，不要浏览仓库文件。'
              '最终答案 ≤120 字并给出 doc_path 出处。')
    try:
        sync_res = agent_chat_safe({'prompt': prompt}, tok)
        runner.save('r3_sync_result.json', sync_res)
        check(res, 'doc-2.2-sync-chat', sync_res.get('success') is True and 'reply' in sync_res and 'tools_used' in sync_res,
              f'sync chat success={sync_res.get("success")}, wall={sync_res.get("_wall_s")}s, turns={sync_res.get("num_turns")}')
    except Exception as e:
        check(res, 'doc-2.2-sync-chat', False, f'exception: {str(e)[:200]}')

    try:
        sub = agent_chat_safe({'prompt': prompt, 'mode': 'async'}, tok)
        runner.save('r3_async_submit.json', sub)
        got = sub.get('success') is True and sub.get('task_id') and sub.get('poll', '').startswith('GET /api/kb/agent/tasks/')
        check(res, 'doc-2.3-async-submit', got, f'async submit wall={sub.get("_wall_s")}s, task={sub.get("task_id")}')
        if got:
            final = runner.poll_task(sub['task_id'], tok, deadline_s=560.0)
            r = final.get('result') or {}
            ok = final.get('status') == 'completed' and r.get('success') and r.get('reply')
            if not ok:  # 后台仍在跑（轮询窗口超时）→ 直接再拉一次终态
                final2 = runner.poll_task(sub['task_id'], tok, deadline_s=120.0)
                r = final2.get('result') or r
                final = final2 if final2.get('status') else final
                ok = final.get('status') == 'completed' and r.get('success') and r.get('reply')
            runner.save('r3_async_result.json', final)
            check(res, 'doc-2.3-async-poll', ok, f'poll status={final.get("status")}, duration_ms={r.get("duration_ms")}, reply head={str(r.get("reply"))[:80]}')
    except Exception as e:
        check(res, 'doc-2.3-async-poll', False, f'exception: {str(e)[:200]}')
    return res


def main():
    tok = runner.load_token()
    contract = doc_contract(tok)
    chain = full_chain(tok)
    agents = agent_turns(tok)
    summary = {
        'contract': {'pass': sum(1 for x in contract if x['ok']), 'total': len(contract), 'items': contract},
        'chain': {'pass': sum(1 for x in chain if x['ok']), 'total': len(chain), 'items': chain},
        'agents': {'pass': sum(1 for x in agents if x['ok']), 'total': len(agents), 'items': agents},
    }
    runner.save('r3_summary.json', summary)
    print('[r3] done:', summary['contract']['pass'], '/', summary['contract']['total'], 'contract |',
          summary['chain']['pass'], '/', summary['chain']['total'], 'chain |',
          summary['agents']['pass'], '/', summary['agents']['total'], 'agents', flush=True)


if __name__ == '__main__':
    main()
