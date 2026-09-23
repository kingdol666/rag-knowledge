#!/usr/bin/env python3
"""fig1_hero.html 遮挡/连线程序化校验:
A. 所有文字行盒完整落在画布内
B. 文字完整落在所属容器内 (stage/chip/drawer/metric/head)
C. 流程线条采样点不得穿过任何文字行盒 (同 SVG 内部的刻度文字除外)
D. 箭头落点必须命中目标元素
E. 文字行盒两两不得重叠
用法: python verify_fig1_hero.py"""
import json, sys
from playwright.sync_api import sync_playwright

HTML = r"D:/codes/ClaudeGPT/rag_project/rag-knowledge/paper_demo/figures/fig1_hero.html"

JS = r"""
() => {
  const fig = document.getElementById('fig');
  const fr = fig.getBoundingClientRect();
  const issues = [];

  // ---- collect text line rects ----
  const texts = [];  // {rects:[{x,y,w,h}], svg: bool, info: str}
  const walker = document.createTreeWalker(fig, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    const t = node.textContent;
    if (!t || !t.trim()) continue;
    const range = document.createRange();
    range.selectNodeContents(node);
    const svgOwner = !!node.ownerSVGElement;
    const info = (t.trim().slice(0, 32));
    const rects = [];
    for (const r of range.getClientRects()) {
      if (r.width < 1 || r.height < 1) continue;
      rects.push({x:r.x, y:r.y, w:r.width, h:r.height});
    }
    if (rects.length) texts.push({rects, svgOwner, info});
  }

  const hit = (p, r, pad=0) => p.x >= r.x-pad && p.x <= r.x+r.w+pad && p.y >= r.y-pad && p.y <= r.y+r.h+pad;
  const inter = (a, b) => Math.max(0, Math.min(a.x+a.w, b.x+b.w) - Math.max(a.x, b.x)) *
                         Math.max(0, Math.min(a.y+a.h, b.y+b.h) - Math.max(a.y, b.y));

  // ---- A: inside canvas ----
  for (const t of texts) for (const r of t.rects) {
    if (r.x < fr.x-0.5 || r.y < fr.y-0.5 || r.x+r.w > fr.x+fr.width+0.5 || r.y+r.h > fr.y+fr.height+0.5)
      issues.push({check:'A-canvas', sev:'major', what:`text "${t.info}" outside canvas`, at:r});
  }

  // ---- B: text inside its container ----
  const containers = [...fig.querySelectorAll('.stage,.gainchip,.redchip,.citechip,.drawer,.metric,.panel .head')];
  for (const c of containers) {
    const cr = c.getBoundingClientRect();
    const w = document.createTreeWalker(c, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = w.nextNode())) {
      if (!n.textContent.trim()) continue;
      const range = document.createRange(); range.selectNodeContents(n);
      for (const r of range.getClientRects()) {
        if (r.width < 1) continue;
        const rr = {x:r.x, y:r.y, w:r.width, h:r.height};
        if (rr.x < cr.x-1.5 || rr.y < cr.y-1.5 || rr.x+rr.w > cr.x+cr.width+1.5 || rr.y+rr.h > cr.y+cr.height+1.5)
          issues.push({check:'B-container', sev:'major', what:`text "${n.textContent.trim().slice(0,32)}" overflows container`, at:rr, box:{x:cr.x,y:cr.y,w:cr.width,h:cr.height}});
      }
    }
  }

  // ---- C: connector sampling vs text ----
  const svgs = [...fig.querySelectorAll('svg')];
  for (const svg of svgs) {
    const sr = svg.getBoundingClientRect();
    if (sr.width === 0) continue;
    const own = [];
    { const w = document.createTreeWalker(svg, NodeFilter.SHOW_TEXT);
      let n; while ((n = w.nextNode())) { const range = document.createRange(); range.selectNodeContents(n);
        for (const r of range.getClientRects()) if (r.width>1) own.push({x:r.x,y:r.y,w:r.width,h:r.height}); } }
    const skip = p => own.some(r => hit(p, r, 2));
    for (const el of svg.querySelectorAll('path,line,polyline')) {
      const cl = el.getAttribute('class') || '';
      if (!el.getAttribute('stroke') && !cl.includes('flowline')) continue;
      let len = 0, isPath = false;
      try { len = el.getTotalLength(); isPath = true; } catch(e) {}
      const pts = [];
      if (isPath && len > 0) {
        for (let d = 0; d <= len; d += 5) { const p = el.getPointAtLength(d);
          pts.push({x:sr.x+p.x, y:sr.y+p.y}); }
      } else {
        const x1=+el.getAttribute('x1'), y1=+el.getAttribute('y1'), x2=+el.getAttribute('x2'), y2=+el.getAttribute('y2');
        if (Number.isNaN(x1)) continue;
        const n = Math.max(2, Math.ceil(Math.hypot(x2-x1, y2-y1)/5));
        for (let i = 0; i <= n; i++) pts.push({x:sr.x+x1+(x2-x1)*i/n, y:sr.y+y1+(y2-y1)*i/n});
      }
      for (const p of pts) {
        if (skip(p)) continue;
        for (const t of texts) { if (t.svgOwner) continue;
          for (const r of t.rects) if (hit(p, r, 0.5))
            issues.push({check:'C-line-vs-text', sev:'major', what:`connector passes through text "${t.info}"`, at:p});
        }
      }
    }
  }

  // ---- D: arrow landing semantics ----
  const byText = (sel, txt) => [...fig.querySelectorAll(sel)].find(e => e.textContent.includes(txt));
  const near = (p, target, tol=8) => p.x >= target.x-tol && p.x <= target.x+target.w+tol && p.y >= target.y-tol && p.y <= target.y+target.h+tol;
  const tipOf = svg => { const sr = svg.getBoundingClientRect();
    const poly = svg.querySelector('polygon'); const pts = poly.getAttribute('points').trim().split(/\s+/).map(s=>s.split(',').map(Number));
    const tip = pts.reduce((a,b)=> (b[1]<a[1]||(b[1]===a[1]&&b[0]>a[0]))?b:a);
    return {x:sr.x+tip[0], y:sr.y+tip[1]}; };

  // left panel arrows: tip should touch next stage left edge
  const L = {q: byText('.stage','Query'), s: byText('.stage','embedding index'), k: byText('.stage','Top-k'), a: byText('.stage','LLM')};
  const leftArrows = [...fig.querySelectorAll('.panel.rag > svg')].filter(s=>s.querySelector('polygon') && s.getAttribute('width')==='48');
  const ltargets = [L.s, L.k, L.a].map(e=>e.getBoundingClientRect());
  leftArrows.forEach((s,i)=>{ const t = tipOf(s);
    if (!near(t, {x:ltargets[i].x, y:ltargets[i].y, w:0, h:ltargets[i].h}, 6))
      issues.push({check:'D-landing', sev:'major', what:`left arrow ${i} tip not on target`, at:t}); });

  // right panel arrows
  const R = {q: byText('.stage','Query'), r: byText('.stage','Domain'), v: byText('.stage','Vector-first'), g: byText('.stage','Content'), a: byText('.stage','Grounded')};
  const rightArrows = [...fig.querySelectorAll('.panel.kb > svg')].filter(s=>s.querySelector('polygon') && s.getAttribute('width')==='21');
  const rtargets = [R.r, R.v, R.g, R.a].map(e=>e.getBoundingClientRect());
  rightArrows.forEach((s,i)=>{ const t = tipOf(s);
    if (!near(t, {x:rtargets[i].x, y:rtargets[i].y, w:0, h:rtargets[i].h}, 6))
      issues.push({check:'D-landing', sev:'major', what:`right arrow ${i} tip not on target`, at:t}); });

  // router -> cabinet
  const cab = fig.querySelector('.cabinet').getBoundingClientRect();
  const rarrow = [...fig.querySelectorAll('.panel.kb > svg')].find(s=>s.getAttribute('width')==='24' && s.querySelector('polygon') && !s.querySelector('path'));
  { const t = tipOf(rarrow);
    if (!(t.x >= cab.x && t.x <= cab.x+cab.w && Math.abs(t.y - cab.y) <= 8))
      issues.push({check:'D-landing', sev:'major', what:'router arrow tip not on cabinet top', at:t}); }

  // gate connector -> diamond top vertex
  const dias = [...fig.querySelectorAll('.panel.kb > svg')].filter(s=>s.querySelector('rect[transform]'));
  const dia = dias[0].getBoundingClientRect();
  const gcon = [...fig.querySelectorAll('.panel.kb > svg')].find(s=>{ const l=s.querySelector('line'); return l && s.querySelector('polygon') && Math.abs(+l.getAttribute('x1') - +l.getAttribute('x2')) < 1; });
  { const t = tipOf(gcon);
    const topV = {x:dia.x+dia.w/2, y:dia.y};
    if (Math.hypot(t.x-topV.x, t.y-topV.y) > 10)
      issues.push({check:'D-landing', sev:'major', what:'gate connector tip not at diamond top vertex', at:t}); }

  // pass branch -> grounded answer bottom
  { const svgs2 = [...fig.querySelectorAll('.panel.kb > svg')].filter(s=>s.querySelector('path') && s.getAttribute('width')==='140');
    const pass = svgs2[0]; const t = tipOf(pass);
    const a = R.a.getBoundingClientRect();
    if (!(t.x >= a.x-4 && t.x <= a.x+a.w+4 && Math.abs(t.y - (a.y+a.h)) <= 8))
      issues.push({check:'D-landing', sev:'major', what:'pass branch tip not at grounded-answer bottom', at:t}); }

  // fail loop -> points up into vector-first recall
  { const svgs2 = [...fig.querySelectorAll('.panel.kb > svg')].filter(s=>s.querySelector('path') && s.getAttribute('width')==='240');
    const loop = svgs2[0]; const t = tipOf(loop);
    const v = R.v.getBoundingClientRect();
    if (!(t.x >= v.x && t.x <= v.x+v.w && t.y > v.y+v.h && t.y - (v.y+v.h) < 40))
      issues.push({check:'D-landing', sev:'major', what:'fail loop tip not below vector-first recall', at:t}); }

  // ---- E: text-vs-text overlap ----
  const flat = [];
  texts.forEach(t => t.rects.forEach(r => flat.push({...r, info:t.info})));
  for (let i = 0; i < flat.length; i++) for (let j = i+1; j < flat.length; j++) {
    if (inter(flat[i], flat[j]) > 4) issues.push({check:'E-text-overlap', sev:'major', what:`"${flat[i].info}" overlaps "${flat[j].info}"`, at:flat[i]});
  }

  // ---- VS arcs stay in the gutter ----
  const gutter = {x:1100, y:fr.y, w:200, h:fr.height};
  for (const svg of svgs) { if (!(svg.getAttribute('class')||'').includes('vsflow')) continue;
    const sr = svg.getBoundingClientRect();
    const arc = svg.querySelector('path'); const len = arc.getTotalLength();
    for (let d = 0; d <= len; d += 4) { const p = arc.getPointAtLength(d); const q = {x:sr.x+p.x, y:sr.y+p.y};
      if (q.x < gutter.x || q.x > gutter.x+gutter.w) issues.push({check:'F-vs-arcs', sev:'minor', what:'VS arc leaves the gutter', at:q}); } }

  return {textCount: texts.length, issues};
}
"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width":2400, "height":1060})
    pg.goto("file:///" + HTML.replace("\\", "/").lstrip("/") + "#static")
    pg.wait_for_timeout(900)
    res = pg.evaluate(JS)
    b.close()

print(json.dumps(res, ensure_ascii=False, indent=1))
print("TOTAL ISSUES:", len(res["issues"]))
sys.exit(0 if not res["issues"] else 1)
