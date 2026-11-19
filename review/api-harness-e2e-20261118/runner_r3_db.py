# -*- coding: utf-8 -*-
"""R3 US-008: persistence verification — API-operated results must survive in
the database layer. Read-only; every SQL statement is a constant string with
? placeholders (parameter binding, no string assembly).

Checks:
  A. claude-chat.db — interactive-lane session (R2 chat) + messages persisted
  B. auth.db — users + api_tokens rows exist
  C. chroma.sqlite3 — vector collections for R1/R2/R3 test KBs (+ embedding rows)
  D. tree storage — .tree-fs.json global index + per-KB .knowledge-base.yml
  E. claude SDK session JSONL — agent/chat lane sessions persisted by the harness

Artifacts: r3_db_persistence.json
"""
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = []


def check(cid, ok, detail):
    OUT.append({'id': cid, 'ok': bool(ok), 'detail': detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {cid}: {detail}", flush=True)


def connect_ro(db_path: Path):
    return sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)


def main():
    # A. claude-chat.db — interactive-lane persistence
    with connect_ro(ROOT / 'storage' / 'claude-chat.db') as con:
        sid = 'b9585f1c-94fc-441d-be2e-ffaa242c9d60'  # R2 interactive turn1
        rows = con.execute(
            'SELECT session_id, engine, created_at FROM sessions WHERE session_id = ?',
            (sid,)).fetchall()
        n = con.execute(
            'SELECT COUNT(*) FROM messages WHERE session_id = ?',
            (sid,)).fetchall()[0][0]
    check('db-A1-chat-session-row', bool(rows), f'sessions row for {sid[:8]}: {rows[:1]}')
    check('db-A2-chat-messages', n >= 1, f'messages persisted for session: {n} rows')

    # B. auth.db — users + tokens
    with connect_ro(ROOT / 'storage' / 'auth.db') as con:
        users = con.execute(
            'SELECT COUNT(*) FROM users WHERE status = ?', ('active',)).fetchall()[0][0]
        toks = con.execute(
            'SELECT COUNT(*) FROM api_tokens WHERE revoked_at IS NULL').fetchall()[0][0]
    check('db-B1-users', users >= 1, f'active users: {users}')
    check('db-B2-tokens', toks >= 1, f'live api_tokens: {toks}')

    # C. chroma vector store — collections for R1/R2/R3 test KBs
    # Live store: repo-root ./chroma_db (backend vector.persist_dir default).
    # storage/chroma/chroma.sqlite3 is an empty decoy (0 collections).
    with connect_ro(ROOT / 'chroma_db' / 'chroma.sqlite3') as con:
        cols = [r[0] for r in con.execute('SELECT name FROM collections').fetchall()]
        r2_hit = [c for c in cols if '4d0b401b' in c]  # api-e2e-20261118-r2
        r1_hit = [c for c in cols if 'c286bb1c' in c]  # api-e2e-20261118
        r3_uuid = ''
        y3 = ROOT / 'storage' / 'tree-file-system' / 'api-e2e-20261118-r3' / '.knowledge-base.yml'
        if y3.exists():
            m = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',
                          y3.read_text(encoding='utf-8', errors='replace'))
            r3_uuid = m.group(1) if m else ''
        r3_hit = [c for c in cols if r3_uuid and r3_uuid in c]
        r2_emb = 0
        if r2_hit:
            r2_emb = con.execute(
                'SELECT COUNT(*) FROM embeddings e JOIN segments s ON e.segment_id = s.id '
                'JOIN collections c ON s.collection = c.id WHERE c.name = ?',
                (r2_hit[0],)).fetchall()[0][0]
    check('db-C1-chroma-r1-collection', bool(r1_hit), f'R1 KB vector collection: {r1_hit or "MISSING"}')
    check('db-C2-chroma-r2-collection', bool(r2_hit), f'R2 KB vector collection: {r2_hit or "MISSING"}')
    check('db-C3-chroma-r3-collection', bool(r3_hit) if r3_uuid else False,
          f'R3 KB uuid={r3_uuid or "n/a"} collection: {r3_hit or "MISSING (chain step pending?)"}')
    check('db-C4-chroma-r2-embeddings', r2_emb >= 1, f'R2 collection embedding rows: {r2_emb}')

    # D. tree storage — global index + per-KB yaml
    tfs = (ROOT / 'storage' / 'tree-file-system' / '.tree-fs.json').read_text(encoding='utf-8', errors='replace')
    check('db-D1-treefs-index', 'api-e2e-20261118-r2' in tfs and 'api-e2e-20261118-r3' in tfs,
          f'.tree-fs.json contains r2={"api-e2e-20261118-r2" in tfs} r3={"api-e2e-20261118-r3" in tfs}')
    y2 = (ROOT / 'storage' / 'tree-file-system' / 'api-e2e-20261118-r2' / '.knowledge-base.yml').read_text(encoding='utf-8', errors='replace')
    check('db-D2-kb-yaml-r2', 'R2轮对外API验收记录' in y2, 'r2 .knowledge-base.yml contains ingested doc entry')

    # E. claude SDK session JSONL — agent/chat lane persistence
    sdk_root = Path.home() / '.claude' / 'projects'
    here = Path(__file__).resolve().parent
    wanted = {}
    for f in ('t2r_result.json', 'r2sync_result.json'):
        p = here / f
        if p.exists():
            sid = json.loads(p.read_text(encoding='utf-8')).get('session_id')
            if sid:
                wanted[f] = sid
    found = {}
    if sdk_root.exists() and wanted:
        for tag, sid in wanted.items():
            hits = list(sdk_root.rglob(f'{sid}.jsonl'))
            found[tag] = {'sid': sid[:8], 'persisted': bool(hits), 'project_dir': hits[0].parent.name if hits else ''}
    check('db-E1-sdk-session-jsonl', bool(found) and all(v['persisted'] for v in found.values()),
          f'agent/chat harness sessions persisted as JSONL: {found or "no session ids available"}')

    out = Path(__file__).resolve().parent / 'r3_db_persistence.json'
    out.write_text(json.dumps(OUT, ensure_ascii=False, indent=1), encoding='utf-8')
    npass = sum(1 for x in OUT if x['ok'])
    print(f'[r3-db] done: {npass}/{len(OUT)} PASS -> {out.name}', flush=True)


if __name__ == '__main__':
    main()
