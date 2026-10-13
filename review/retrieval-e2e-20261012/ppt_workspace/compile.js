/**
 * compile.js — assemble HTML slides into OUTPUT.pptx
 * Run with cwd = ppt_workspace, NODE_PATH = ./node_modules
 * (NODE_PATH lets the external html2pptx.js resolve playwright/sharp)
 */
const pptxgen = require('pptxgenjs');
const path = require('path');
const _mod = require('C:/Users/87287/.claude/skills/huashu-slides/scripts/html2pptx.js');
const html2pptx = typeof _mod === 'function' ? _mod : _mod.html2pptx;

const WORKSPACE = __dirname;
const SLIDES_DIR = path.join(WORKSPACE, 'slides');

const IMAGE_MAP = {
  'img-hero': path.join(WORKSPACE, 'garden-gpt-image-2', 'image', 'p01_cover.png'),
  'img-finding': path.join(WORKSPACE, 'garden-gpt-image-2', 'image', 'p03_finding.png'),
};

(async () => {
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_WIDE'; // 960pt x 540pt (13.33" x 7.5")
  pptx.author = 'RAG Knowledge Platform';
  pptx.title = '三种检索模式端到端实测 Benchmark 2026-10-12';

  const files = ['slide-01.html', 'slide-02.html', 'slide-03.html'];
  let hits = 0;
  let placeholdersSeen = 0;

  for (const f of files) {
    const htmlPath = path.join(SLIDES_DIR, f);
    console.log(`processing ${f} ...`);
    const { slide, placeholders } = await html2pptx(htmlPath, pptx);
    for (const p of placeholders) {
      placeholdersSeen++;
      const img = IMAGE_MAP[p.id];
      if (img) {
        slide.addImage({ path: img, x: p.x, y: p.y, w: p.w, h: p.h });
        hits++;
        console.log(`  placeholder "${p.id}" -> ${path.basename(img)} @ (${p.x.toFixed(2)}, ${p.y.toFixed(2)}) ${p.w.toFixed(2)}x${p.h.toFixed(2)} in`);
      } else {
        console.warn(`  WARNING: no image mapped for placeholder "${p.id}"`);
      }
    }
  }

  const out = path.join(WORKSPACE, 'OUTPUT.pptx');
  await pptx.writeFile({ fileName: out });
  console.log(`written ${out}`);
  console.log(`IMAGE_MAP hits: ${hits}/${placeholdersSeen} placeholders`);
})().catch((e) => {
  console.error('COMPILE FAILED:', e.message);
  process.exit(1);
});
