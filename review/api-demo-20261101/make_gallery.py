# -*- coding: utf-8 -*-
"""生成"图库"测试素材：3 张含唯一事实的 PNG 卡片（OCR 友好：白底黑字、大字号）。

输出:
  gallery/01_aurora_borealis.png
  gallery/02_giant_sequoia.png
  gallery/03_golden_record.png
  gallery/gold.json   —— 金标事实 + 检索题 + 期望命中文档（判卷依据）

运行: uv run --no-sync --directory backend python review/api-demo-20261101/make_gallery.py
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent
OUT = BASE / "gallery"
OUT.mkdir(parents=True, exist_ok=True)

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",     # 微软雅黑
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
]

CARDS = [
    {
        "file": "01_aurora_borealis.png",
        "title": "北极光（Aurora Borealis）观测要点",
        "lines": [
            "1. 成因：太阳风携带的带电粒子，被地球磁场",
            "    导引至两极上空，与高层大气碰撞发光。",
            "2. 发光高度：约 100 至 500 公里。",
            "3. 绿色光：来自氧原子，波长 557.7 纳米，最常见。",
            "4. 红色光：来自高空的氧原子，波长 630 纳米。",
            "5. 蓝紫色：来自氮分子与氮离子。",
            "6. 最佳观测：高磁纬地区冬夜，如冰岛、挪威北部。",
        ],
        "description": "北极光观测要点卡片：太阳风带电粒子成因、100-500公里发光高度、氧原子557.7纳米绿光、氮分子蓝紫光。",
        "query": "北极光的绿色光主要来自哪种原子？发光高度范围大约是多少公里？",
        "gold_keywords": ["氧原子", "100", "太阳风"],
    },
    {
        "file": "02_giant_sequoia.png",
        "title": "巨杉与谢尔曼将军树（General Sherman）",
        "lines": [
            "1. 谢尔曼将军树：世界上现存体积最大的树木。",
            "2. 位置：美国加利福尼亚州内华达山脉巨杉国家公园。",
            "3. 高度约 83.8 米，底部直径约 11.1 米。",
            "4. 体积约 1487 立方米，估计树龄 2200 至 2700 年。",
            "5. 巨杉是世界上生长最快的针叶树之一。",
            "6. 树皮厚度可达 60 厘米，天然抗火灾与虫害。",
        ],
        "description": "巨杉与谢尔曼将军树卡片：世界体积最大树木、加州内华达山脉、83.8米高、1487立方米、树龄2200-2700年。",
        "query": "世界上现存体积最大的树是哪一棵？它位于什么地方？",
        "gold_keywords": ["谢尔曼", "加利福尼亚", "83.8"],
    },
    {
        "file": "03_golden_record.png",
        "title": "旅行者金唱片（Voyager Golden Record）",
        "lines": [
            "1. 1977 年随旅行者 1 号与 2 号探测器发射升空。",
            "2. 载体：镀金铜唱片，直径 30 厘米。",
            "3. 收录 115 张编码图像，约 90 分钟世界音乐。",
            "4. 含 55 种语言的问候语与地球的声音。",
            "5. 封面刻有播放方法与地球在银河系位置示意。",
            "6. 预期在星际空间中可保存超过 10 亿年。",
        ],
        "description": "旅行者金唱片卡片：1977年发射、镀金铜唱片直径30厘米、115张图像、90分钟音乐、55种语言问候。",
        "query": "旅行者号金唱片收录了多少张图像和大约多少分钟的音乐？",
        "gold_keywords": ["115", "90", "1977"],
    },
]


def load_font(size: int):
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    raise SystemExit(f"no CJK font found, tried: {FONT_CANDIDATES}")


def render(card: dict) -> Path:
    W = 1000
    title_font = load_font(42)
    body_font = load_font(33)
    LH = 52
    H = 120 + LH * (len(card["lines"]) + 1) + 60
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.text((40, 40), card["title"], fill="black", font=title_font)
    y = 120 + LH
    for line in card["lines"]:
        d.text((40, y), line, fill="black", font=body_font)
        y += LH
    out = OUT / card["file"]
    img.save(out, "PNG")
    return out


def main():
    written = []
    for card in CARDS:
        p = render(card)
        written.append(p.name)
        print(f"OK  {p}  ({p.stat().st_size} bytes)")
    gold = {
        "generated": "2026-11-01",
        "note": "图库演示素材：3 张 PNG，每张含唯一金标事实，供 OCR 解析→入库→图书管理员检索→删除全链路验证",
        "images": [
            {
                "file": c["file"],
                "doc_title": c["title"],
                "description": c["description"],
                "query": c["query"],
                "expect_doc": c["file"],
                "gold_keywords": c["gold_keywords"],
            }
            for c in CARDS
        ],
    }
    (OUT / "gold.json").write_text(
        json.dumps(gold, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"OK  {OUT / 'gold.json'}")
    print(f"files: {written}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
