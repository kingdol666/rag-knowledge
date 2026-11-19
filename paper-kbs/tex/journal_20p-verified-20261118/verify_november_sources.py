#!/usr/bin/env python3
"""Offline November artifact verifier; run with Python -I -B.

With no options, check the shipped CSVs/records only. Use --repo-root PATH
for original files, or repeat --source NAME=PATH for individual originals.
--require-originals makes missing originals an error. --emit-records writes
only the deterministic, sanitized JSON to stdout (requires all originals).
No retrieval, database access, or filesystem writes are performed.
"""

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path
from typing import Any

PACKAGE = Path(__file__).resolve().parent
ART = 'review/experiment-redesign-20261101/artifacts/'
REPRO = ART + 'repro_20261117/'
R3 = 'review/api-harness-e2e-20261118/'
# Pinned raw-byte SHA256: original Windows bytes, then exact LF checkout bytes.
# Neither the input bytes nor the exported CSV are normalized before hashing.
SOURCES = {
    'traces': (REPRO + 's4_traces_repro_merged.json',
               '3d97cee2af3cffff8179fde59489efd72c3122e434aa49bfd63a285fa835a8cb',
               '14fccdd039ec636779315b91c273fd13f0c379cc1dc6106f92a9949dbdafdfb9'),
    'questions': (ART + 'provenance/questions.jsonl',
                  '7c552baab387f1fe0a54d08e9979025cb0e7bdf0a0dd7eafcf019efc984cca60',
                  '1c855b1d95d2f34623c5718b8588eb4ba205810017985764d8a4dd0c27422b67'),
    'stats': (REPRO + 's6_stats.json',
              'bd0c3278dd5a0b5ec600220a9afaaddd828606fe12373a4751495c5ddcc70c3c',
              '89985e6d70843411600d61e174d689cac7306961b9c54c5f1ad1c647274762bf'),
    'repro_report': (REPRO + 'REPRO-REPORT-20261117.md',
                     '1edaf277f6ac666b6026fddd8975e56d052e03fd612753d9ef932d9034db33d6',
                     '0e058a75d4fb379a36fb6d89b59e905942443fb5e5eacac280876945df1432fe'),
    'batch': ('review/e2e-master-20261117/batch_demo_results.json',
              'd927efe2812424f87854ee646b3433bfb143a21e15c6f5cbcfd5fa30b56fee68',
              '950fc663a5f4acdd23ee147e4bf991f6c449aa1d6c34d20659060725b467cdf6'),
    'r3_summary': (R3 + 'r3_summary.json',
                   'edaf1ee21836500718411076ff9002c80a1f1436078f4318ad8bf929bea15375',
                   '32516b50ab528e847ae70ac9fdb627440f62c32069e1d0beafff8659358e8f07'),
    'r3_rereads': (R3 + 'r3_readback_fix.json',
                   '47d88bb61bf987f695d700971e3740ba26f688d0ca0dfb42bb7576bfa5df8a68',
                   'a672ee0bab87eacd91054228fe51c1694feba2f1672ce6f72ec9f9440d00e669'),
    'r3_persistence': (R3 + 'r3_db_persistence.json',
                       '850f6a93a35d57944b4ef818380db4f353435c6d251cc32e19b1d68b3cd24faf',
                       '7ba7c4364edd6a527adcac54ceca5b2c1c1064344727b31eb3b52dd3dbc40bca'),
}
LATEST = 'supp_traces_rerun_20261117.csv'
FROZEN = 'supp_traces_frozen.csv'
PACKAGE_SHA = {
    LATEST: '83c3fa774b0c9951deb95d18374453a4c167eb1f199270c69d61b7aa108e9d95',
    FROZEN: '66b4a00d5d9dbd589d33c29fd3ec8cd194645f2b1ee5541f84c17050517fdd01',
}
FIELDS = ('run', 'arm', 'qid', 'gold_hit', 'is_refusal', 'refusal_ok',
          'bytes_ingested', 'tool_seconds', 'calls', 'route_slug',
          'route_correct', 'evidence_focus', 'first_hit_read_index')
ARMS = ('A0', 'A0f', 'A0h', 'PD', 'A1b', 'A2', 'A3')
PROBES = {'R1', 'R2', 'R3', 'R4'}
RECORD = 'november_source_checks.json'
RECORD_SHA = ('c61d64a7477b24f357c5032267ddaf3167d94622670ea19311dd0fdf09180ddf',
              '608553fe5192cfc3c64046378b0b9983ca43387766587a6e78de2c29cb615a6b')


class CheckError(ValueError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise CheckError(message)


def read_pinned(path: Path, name: str, *pins: str) -> tuple[bytes, str]:
    try:
        data = path.read_bytes()
    except OSError:
        raise CheckError(f'{name}: unable to read input') from None
    digest = hashlib.sha256(data).hexdigest()
    require(digest in pins, f'{name}: SHA256 mismatch ({digest})')
    return data, digest


def export(traces: dict[str, list[dict[str, Any]]]) -> bytes:
    """Mirror the archived exporter, including row order and empty cells."""
    require(tuple(traces) == ARMS, 'raw traces: unexpected arm order or set')
    out = io.StringIO(newline='')
    writer = csv.writer(out, lineterminator='\r\n')
    writer.writerow(FIELDS)
    for arm, rows in traces.items():
        require(len(rows) == 76, 'raw traces: expected 76 rows per arm')
        for row in rows:
            require(row['arm'] == arm, 'raw traces: inconsistent arm label')
            writer.writerow((
                'rerun-20261117', arm, row.get('qid', ''),
                bool(row.get('gold_hit')), bool(row.get('is_refusal')),
                None if row.get('refusal_ok') is None else bool(row['refusal_ok']),
                row.get('bytes_ingested', ''), row.get('tool_seconds', ''),
                row.get('calls', ''), row.get('route_slug', ''),
                None if row.get('route_correct') is None else bool(row['route_correct']),
                row.get('evidence_focus', ''), row.get('first_hit_read_index'),
            ))
    return out.getvalue().encode('utf-8')


def read_csv(data: bytes) -> dict[str, dict[str, dict[str, str]]]:
    reader = csv.DictReader(io.StringIO(data.decode('utf-8'), newline=''))
    require(tuple(reader.fieldnames or ()) == FIELDS, 'CSV: unexpected export fields')
    arms: dict[str, dict[str, dict[str, str]]] = {}
    for row in reader:
        require(None not in row and None not in row.values(), 'CSV: malformed row')
        by_id = arms.setdefault(row['arm'], {})
        qid = row['qid']
        require(bool(qid) and qid not in by_id, 'CSV: missing or duplicate arm/qid')
        require(row['is_refusal'] == str(qid in PROBES) and
                row['gold_hit'] in ('True', 'False'), 'CSV: invalid flags')
        by_id[qid] = row
    return arms


def latest_metrics(arms: dict[str, dict[str, dict[str, str]]]) -> dict[str, Any]:
    require(tuple(arms) == ARMS, 'latest CSV: unexpected arm order or set')
    require(all(len(rows) == 76 and rows.keys() == arms['A0'].keys()
                for rows in arms.values()) and PROBES <= arms['A0'].keys(),
            'latest CSV: expected matching sets of 72 gold and 4 probes')
    by_arm = {}
    for arm, rows in arms.items():
        gold = [row for qid, row in rows.items() if qid not in PROBES]
        n = len(gold)
        avg_bytes = sum(int(row['bytes_ingested']) for row in gold) / n
        by_arm[arm] = {
            'gold_hits': sum(row['gold_hit'] == 'True' for row in gold),
            'mean_text_bytes': round(avg_bytes),
            'mean_text_kB': round(avg_bytes / 1000, 1),
            'mean_tool_seconds': round(sum(float(row['tool_seconds']) for row in gold) / n, 1),
        }
    return {'rows': sum(map(len, arms.values())), 'export_fields': list(FIELDS),
            'gold_questions_per_arm': 72, 'ood_probes_per_arm': 4, 'gold_only': by_arm}


def overlap_check(data: bytes, campaigns: dict[str, dict[str, dict[str, dict[str, str]]]],
                  traces: dict[str, list[dict[str, Any]]] | None) -> dict[str, Any]:
    questions = {}
    kinds: dict[str, set[str]] = {'gold': set(), 'refusal': set(), 'cross': set()}
    overlap = set()
    for line in data.decode('utf-8').splitlines():
        row = json.loads(line)
        qid, kind, text = row['id'], row['kind'], row['question']
        require(qid not in questions and isinstance(text, str), 'question list: invalid entry')
        questions[qid] = text
        kinds[kind].add(qid)
        if kind == 'gold':
            target = row['gold_evidence']
            require(isinstance(target, str) and bool(target), 'question list: empty gold target')
            if target.lower() in text.lower():
                overlap.add(qid)
    gold = kinds['gold']
    require(len(gold) == 72 and kinds['refusal'] == PROBES and kinds['cross'] == {'X1', 'X2'},
            'question list: unexpected cohort')
    if traces is not None:
        require(all(row['query'] == questions[row['qid']] for rows in traces.values()
                    for row in rows), 'raw traces: query text differs from exact question list')
    non_overlap = gold - overlap
    require((len(overlap), len(non_overlap)) == (29, 43), 'question list: unexpected overlap split')
    result: dict[str, Any] = {'rule': 'nonempty lowercase target is a contiguous lowercase question substring',
                              'overlap_n': len(overlap), 'non_overlap_n': len(non_overlap),
                              'excluded_probe_n': 4, 'excluded_cross_domain_n': 2}
    for campaign, arms in campaigns.items():
        strata = {}
        for arm, rows in arms.items():
            require(rows.keys() == gold | PROBES, 'calibration: CSV question set differs from source')
            strata[arm] = {
                'overlap_hits': sum(rows[qid]['gold_hit'] == 'True' for qid in overlap),
                'non_overlap_hits': sum(rows[qid]['gold_hit'] == 'True' for qid in non_overlap),
            }
        result[campaign] = strata
    return result


def check_stats(data: bytes, metrics: dict[str, Any]) -> None:
    archived = json.loads(data)['per_arm']
    require(set(archived) == set(ARMS), 'archived stats: unexpected arm set')
    for arm, row in metrics['gold_only'].items():
        old = archived[arm]
        require((old['n_total'], old['n_gold'], old['n_probe'], old['gold_hits'],
                 old['avg_bytes_gold'], old['avg_tool_s_gold']) ==
                (76, 72, 4, row['gold_hits'], row['mean_text_bytes'], row['mean_tool_seconds']),
                f'archived stats: {arm} count, budget or time mismatch')


def normalized(items: list[dict[str, Any]], labels: tuple[str, ...],
               statuses: bool = False) -> dict[str, Any]:
    require(len(items) == len(labels), 'check records: unexpected item count')
    checks = {}
    for label, item in zip(labels, items):
        ok = item['ok']
        require(type(ok) is bool, 'check records: invalid outcome')
        value = {'ok': ok}
        if statuses:
            matches = re.findall(r'\bstatus\s*=\s*(200|400)\b', item['detail'])
            require(len(matches) == 1, 'check records: missing or ambiguous HTTP status')
            value['http_status'] = int(matches[0])
        checks[label] = value
    return {'passed': sum(item['ok'] for item in checks.values()),
            'total': len(checks), 'checks': checks}


def batch_check(data: bytes) -> dict[str, Any]:
    src = json.loads(data)
    steps, summary = src['steps'], src['summary']
    parse = steps['batch_parse']
    require(parse['ok'] is True and (parse['total'], parse['successful'], parse['failed']) == (3, 3, 0)
            and len(parse['results']) == 3 and all(item['success'] is True for item in parse['results'])
            and len(steps['direct']) == 2, 'batch: acquisition totals mismatch')
    labels = ('collection_created', 'batch_parsed', 'pdf_1_saved', 'pdf_2_saved', 'pdf_3_saved',
              'pdf_1_rank1', 'pdf_2_rank1', 'pdf_3_rank1', 'markdown_1_ingested',
              'markdown_2_ingested', 'markdown_1_rank1', 'markdown_2_rank1',
              'collection_totals', 'rag_1', 'rag_2', 'rag_3')
    items = summary['checks']
    result = normalized(items, labels)
    require((result['passed'], summary['passed'], summary['failed']) == (16, 16, 0),
            'batch: check totals mismatch')
    ranks = (('retrieve parsed doc:', (5, 6, 7)), ('retrieve direct doc:', (10, 11)))
    for prefix, indices in ranks:
        require(tuple(i for i, item in enumerate(items) if item['name'].startswith(prefix)) == indices
                and all(items[i]['detail'].startswith('top1=') for i in indices),
                'batch: rank-one probe records mismatch')
    result.update(pdf_parsed=3, markdown_ingested=2, rank1_probes_passed=5,
                  batch_wall_seconds=parse['wall_s'], sse_events=parse['event_count'])
    return result


def r3_initial(data: bytes) -> dict[str, Any]:
    rows = json.loads(data)
    chain_labels = ('create_collection', 'create_document', 'reindex', 'vector_response_assertion',
                    'keyword_hit', 'catalog_visible')
    chain = normalized(rows['chain']['items'], chain_labels, statuses=True)
    contract_labels = tuple(f'C{i:02}' for i in range(1, 12)) + ('readback_snake', 'readback_camel')
    items = rows['contract']['items']
    contract = normalized(items, contract_labels, statuses=True)
    for name, group, count, total in (('chain', chain, 6, 6), ('contract', contract, 11, 13)):
        require((group['passed'], group['total'], rows[name]['pass'], rows[name]['total']) ==
                (count, total, count, total), 'R3: archived group totals mismatch')
    require(all(item['ok'] for item in list(contract['checks'].values())[:11]),
            'R3: unexpected initial failure')
    for suffix, item in zip(('snake', 'camel'), items[-2:]):
        require(item['id'] == f'doc-4.2-readback-{suffix}' and
                contract['checks'][f'readback_{suffix}'] == {'ok': False, 'http_status': 400},
                'R3: initial readback failure not preserved')
    return {'chain_nov18': chain, 'contract_initial_nov18': contract}


def r3_rereads(data: bytes) -> dict[str, Any]:
    rows = json.loads(data)
    result = normalized(rows, ('readback_snake', 'readback_camel'), statuses=True)
    for suffix, row in zip(('snake', 'camel'), rows):
        require(row['id'] == f'doc-4.2-readback-{suffix}-rerun' and
                result['checks'][f'readback_{suffix}'] == {'ok': True, 'http_status': 200},
                'R3: reread result mismatch')
    return result


def r3_persistence(data: bytes) -> dict[str, Any]:
    rows = json.loads(data)
    # Ordinals only: no private check names, details, locations, or counts of stored data.
    result = normalized(rows, tuple(f'P{i:02}' for i in range(1, 12)))
    require(result['passed'] == 11, 'R3: persistence check totals mismatch')
    return result


def resolve_sources(args: argparse.Namespace) -> dict[str, Path]:
    supplied = {}
    for spec in args.source:
        name, sep, value = spec.partition('=')
        require(bool(sep and value and name in SOURCES and name not in supplied),
                'invalid or duplicate --source; see --help for names')
        supplied[name] = Path(value)
    if args.repo_root is not None:
        require(args.repo_root.is_dir(), '--repo-root is not a directory')
        for name, (relative, *_) in SOURCES.items():
            path = args.repo_root / relative
            if name not in supplied and path.is_file():
                supplied[name] = path
    return supplied


def verify(args: argparse.Namespace) -> None:
    paths = resolve_sources(args)
    missing = sorted(SOURCES.keys() - paths.keys())
    if args.require_originals or args.emit_records:
        require(not missing, 'missing original sources: ' + ', '.join(missing))
    inputs = {}
    digests = {}
    for name, path in paths.items():
        inputs[name], digests[name] = read_pinned(path, name, *SOURCES[name][1:])
    data_dir = PACKAGE / 'experiment_data'
    latest_data, _ = read_pinned(data_dir / LATEST, LATEST, PACKAGE_SHA[LATEST])
    frozen_data, _ = read_pinned(data_dir / FROZEN, FROZEN, PACKAGE_SHA[FROZEN])
    raw = None
    if 'traces' in inputs:
        raw = json.loads(inputs['traces'])
        regenerated = export(raw)
        require(regenerated == latest_data, 'rerun export: data differs from shipped CSV bytes')
        latest_data = regenerated
    latest, frozen = read_csv(latest_data), read_csv(frozen_data)
    record = {
        'schema_version': 1,
        'original_sha256': {name: entry[1] for name, entry in SOURCES.items()},
        'retrieval_nov17': latest_metrics(latest),
    }
    if 'questions' in inputs:
        record['target_overlap'] = overlap_check(inputs['questions'], {'nov17': latest,
                                                 'frozen': {arm: frozen[arm] for arm in ('A0', 'A0h')}}, raw)
    if 'stats' in inputs:
        check_stats(inputs['stats'], record['retrieval_nov17'])
    if 'repro_report' in inputs:
        report = inputs['repro_report'].decode('utf-8')
        require('first A3 attempt hung' in report and 'retry WITHOUT --prepare-a3' in report,
                'rerun incident: report does not identify both attempts')
        record['a3_nov17_attempts'] = ['initial_rebuild_hung', 'retry_reused_existing_libraries_and_completed']
    if 'batch' in inputs:
        record['batch_nov17'] = batch_check(inputs['batch'])
    if 'r3_summary' in inputs:
        record.update(r3_initial(inputs['r3_summary']))
    if 'r3_rereads' in inputs:
        record['contract_rereads_nov18'] = r3_rereads(inputs['r3_rereads'])
    if 'r3_persistence' in inputs:
        record['persistence_nov18'] = r3_persistence(inputs['r3_persistence'])
    if args.emit_records:
        print(json.dumps(record, indent=2))
        return
    shipped_data, _ = read_pinned(data_dir / RECORD, RECORD, *RECORD_SHA)
    shipped = json.loads(shipped_data)
    for key, value in record.items():
        require(shipped[key] == value, f'package-side check record mismatch: {key}')
    print(f'PASS: package CSV hashes and {record["retrieval_nov17"]["rows"]} latest rows; '
          f'{"exact raw-to-CSV export matched" if raw is not None else "raw export not checked"}.')
    for name, digest in sorted(digests.items()):
        print(f'  SHA256 {digest}  {SOURCES[name][0]}')
    if missing:
        print('Original sources not checked: ' + ', '.join(missing))
    else:
        print('PASS: all original sources and recomputed normalized records match.')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--repo-root', type=Path, help='repository root containing review/')
    parser.add_argument('--source', action='append', default=[], metavar='NAME=PATH',
                        help='explicit source override; names: ' + ', '.join(SOURCES))
    parser.add_argument('--require-originals', action='store_true', help='fail if any original is unavailable')
    parser.add_argument('--emit-records', action='store_true', help='emit sanitized snapshot JSON instead of comparing it')
    try:
        verify(parser.parse_args())
    except CheckError as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    except (KeyError, TypeError, ValueError, AttributeError, OSError, csv.Error):
        # Parser exceptions may contain source text or private paths.
        print('FAIL: malformed source or package record', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
