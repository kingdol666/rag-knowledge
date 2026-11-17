# -*- coding: utf-8 -*-
"""wikisource 抓取 round2：红楼梦用零填充回目（紅樓夢/第001回）；
请求间 sleep 防限速；429 指数退避重试。"""
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

BASE = Path(__file__).resolve().parent
ART = BASE.parent / "artifacts"
CORPUS = BASE.parents[2] / "corpus" / "multi-domain-docs-20261101"
API = ("https://zh.wikisource.org/w/api.php?action=query&redirects=1"
       "&prop=extracts&explaintext=1&format=json&formatversion=2&titles=")


def fetch_once(title: str) -> str:
    url = API + quote(title)
    p = subprocess.run(["curl", "-s", "-m", "60", "-A", "corpus-builder/1.0",
                        "-w", "\n%{http_code}", url], capture_output=True, timeout=90)
    out = p.stdout.decode("utf-8", "replace")
    body, _, code = out.rpartition("\n")
    if code.strip() == "429":
        raise RateLimited()
    if code.strip() != "200":
        raise ValueError(f"HTTP {code.strip()}")
    pages = (json.loads(body).get("query") or {}).get("pages") or [{}]
    return pages[0].get("extract", "")


class RateLimited(Exception):
    pass


def fetch(titles, rel, note):
    for t in titles:
        for attempt in range(3):
            try:
                text = fetch_once(t)
                if len(text) < 2000:
                    raise ValueError(f"extract {len(text)} chars")
                dest = CORPUS / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(text, encoding="utf-8")
                b = len(text.encode("utf-8"))
                print(f"OK   {note:22s} {b:>9,} B  ({t})")
                return {"note": note, "title": t, "ok": True, "bytes": b}
            except RateLimited:
                wait = 20 * (attempt + 1)
                print(f"..   {note} rate-limited, wait {wait}s")
                time.sleep(wait)
            except Exception as e:  # noqa: BLE001
                print(f"..   {note} {t} -> {str(e)[:80]}")
                break
        time.sleep(5)
    print(f"FAIL {note}")
    return {"note": note, "ok": False}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ART.mkdir(parents=True, exist_ok=True)
    items = [
        ([f"紅樓夢/第{n:03d}回" for n in (1, 2, 3, 4, 5)] + [f"红楼梦/第{n:03d}回" for n in (1,)],
         "literature-zh/hongloumeng_hui01.txt", "红楼梦第一回"),
        (["紅樓夢/第002回"], "literature-zh/hongloumeng_hui02.txt", "红楼梦第二回"),
        (["紅樓夢/第003回"], "literature-zh/hongloumeng_hui03.txt", "红楼梦第三回"),
        (["紅樓夢/第004回"], "literature-zh/hongloumeng_hui04.txt", "红楼梦第四回"),
        (["紅樓夢/第005回"], "literature-zh/hongloumeng_hui05.txt", "红楼梦第五回"),
        (["政府工作报告 (2024年)", "政府工作报告/二〇二四年", "政府工作报告/2024年"],
         "gov-zh/gov_work_report_2024.txt", "政府工作报告2024"),
        (["中华人民共和国国民经济和社会发展第十四个五年规划和2035年远景目标纲要",
          "中华人民共和国国民经济和社会发展第十四个五年规划和二〇三五年远景目标纲要"],
         "gov-zh/14th_five_year_plan.txt", "十四五规划纲要"),
        (["史記/卷007"], "history-zh/shiji_xiangyu_benji.txt", "史记项羽本纪"),
        (["史記/卷048"], "history-zh/shiji_chanshe_shijia.txt", "史记陈涉世家"),
    ]
    log = []
    for titles, rel, note in items:
        log.append(fetch(titles, rel, note))
        time.sleep(5)
    (ART / "wiki_log_round2.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for e in log if e.get("ok"))
    print(f"\n=== {ok}/{len(log)} fetched")


if __name__ == "__main__":
    main()
