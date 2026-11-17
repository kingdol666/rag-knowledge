# -*- coding: utf-8 -*-
"""wikisource 中文长文抓取器（httpx 传输被 RST，改走 curl 子进程）。

每个条目尝试多个标题变体（简/繁/别名），取第一个 extract≥2000 字的命中。
仅 https、host 固定 zh.wikisource.org（字面量，无用户输入 URL）。
"""
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

BASE = Path(__file__).resolve().parent
CORPUS = BASE.parents[2] / "corpus" / "multi-domain-docs-20261101"
LOG = BASE / "artifacts" / "wiki_log.json"
API = ("https://zh.wikisource.org/w/api.php?action=query&redirects=1"
       "&prop=extracts&explaintext=1&format=json&formatversion=2&titles=")


def fetch(title: str, dest: Path, note: str) -> dict:
    url = API + quote(title)
    try:
        p = subprocess.run(["curl", "-s", "-m", "60", "-A", "corpus-builder/1.0",
                            "-w", "\n%{http_code}", url],
                           capture_output=True, timeout=90)
        out = p.stdout.decode("utf-8", "replace")
        body, _, code = out.rpartition("\n")
        if code.strip() != "200":
            raise ValueError(f"HTTP {code.strip()}")
        pages = (json.loads(body).get("query") or {}).get("pages") or [{}]
        text = pages[0].get("extract", "")
        if len(text) < 2000:
            raise ValueError(f"extract too short ({len(text)} chars)")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        print(f"OK   {note:24s} {len(text.encode('utf-8')):>9,} B  {dest.name}")
        return {"note": note, "title": title, "dest": str(dest), "ok": True,
                "bytes": len(text.encode("utf-8"))}
    except Exception as e:  # noqa: BLE001
        print(f"FAIL {note:24s} {e}")
        return {"note": note, "title": title, "ok": False, "error": str(e)[:160]}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    items = [
        (["紅樓夢/第一回", "红楼梦/第一回"], "literature-zh/hongloumeng_hui01.txt", "红楼梦第一回"),
        (["紅樓夢/第二回"], "literature-zh/hongloumeng_hui02.txt", "红楼梦第二回"),
        (["紅樓夢/第三回"], "literature-zh/hongloumeng_hui03.txt", "红楼梦第三回"),
        (["紅樓夢/第四回"], "literature-zh/hongloumeng_hui04.txt", "红楼梦第四回"),
        (["紅樓夢/第五回"], "literature-zh/hongloumeng_hui05.txt", "红楼梦第五回"),
        (["中华人民共和国个人信息保护法", "個人信息保護法"], "law-zh/pipl_full.txt", "个保法全文"),
        (["中华人民共和国数据安全法", "數據安全法"], "law-zh/dsl_full.txt", "数安法全文"),
        (["中华人民共和国网络安全法", "網絡安全法", "网络安全法"], "law-zh/csl_full.txt", "网安法全文"),
        (["政府工作报告 (2024年)", "政府工作报告/二〇二四年", "政府工作报告 (二〇二四年三月)",
          "政府工作报告/2024年"], "gov-zh/gov_work_report_2024.txt", "政府工作报告2024"),
        (["中华人民共和国国民经济和社会发展第十四个五年规划和2035年远景目标纲要",
          "中华人民共和国国民经济和社会发展第十四个五年规划和二〇三五年远景目标纲要"],
         "gov-zh/14th_five_year_plan.txt", "十四五规划纲要"),
        (["史記/卷007", "史记/卷007"], "history-zh/shiji_xiangyu_benji.txt", "史记项羽本纪"),
        (["史記/卷048", "史记/卷048"], "history-zh/shiji_chanshe_shijia.txt", "史记陈涉世家"),
    ]
    log = []
    for titles, rel, note in items:
        got = None
        for t in titles:
            got = fetch(t, CORPUS / rel, note)
            if got.get("ok"):
                break
        log.append(got)
    LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for e in log if e.get("ok"))
    print(f"\n=== {ok}/{len(log)} fetched")


if __name__ == "__main__":
    main()
