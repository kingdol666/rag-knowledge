# CIKM 配图风格指南（2026-09-24 调研，含官方条款与实图目检）

调研方法：① 官方站点逐页取证（cikm2026.diag.uniroma1.it，注意 cikm2026.org
域名不存在）；② ACM 官方制图规范（TAPS Image Specifications + 无障碍页）；
③ 目检 8 张真实 CIKM 2024/2025 论文配图（另有 21 张已验证直链存档于本目录
调研记录）。本文件供论文图 1-3 的后续维护与 camera-ready 使用。

## 一、官方硬性要求（逐条，含来源）

### CIKM 2026 Demo Track CFP（cikm2026.diag.uniroma1.it/demonstration-papers/）
- 页限（verbatim）: "Demo papers must be no more than 4 pages long including
  appendices and acknowledgments, plus unlimited pages for the GenAI Usage
  Disclosure section and references."
- 模板：ACM sigconf 双栏（PDF 经 EasyChair 提交）。
- 视频："Authors should also prepare a 3 minutes long demonstration video …
  A URL of the video … should be included in the paper."
- 单盲："single-blind … authors should include their names and affiliations"。
- 评审 rubric 硬清单：intended audience / innovative aspects / **what the
  audience will experience during the demo** / what functionality is
  supported / **user scenarios** / **interface and interaction options** /
  comparison with existing systems。
- 图/截图：demo 页**没有任何** figure/screenshot 条款（全文 grep 零命中）；
  仅 site-wide policies 页要求。
- 附加：审稿人提名制（不提名=desk reject）；至少一位作者现场展示。

### CIKM 2026 Policies（/policies-and-information/）
- alt text "strongly encouraged" for floats；
- "authors should follow the ACM Accessibility Recommendations for Publishing
  in Color and SIG ACCESS guidelines on describing figures"；
- GenAI Usage Disclosure 章节不计入页限（2026 文案）。

### ACM TAPS Image Specifications（authors.acm.org/proceedings/production-information/taps-image-specifications）
- 格式：SVG / PS / EPS / PDF / PNG / JPG / EMF / TIFF；VSD、GIF、BMP 不收。
- 分辨率：>300 dpi；黑白图用灰度提交。
- 矢量：EPS/PS/PDF 必须**字体内嵌或文字转曲**；黑字设 overprint；**去除多余白边**。
- 尺寸对齐版面：sigconf 单栏 20.5 picas（3.42 in）、双栏 42 picas（7 in）。
- 文件名仅限字母/数字/`-`/`_`。

### ACM 无障碍与颜色（author guidelines / describing-figures / SIGACCESS）
- 每张图必须有**描述**（`\Description`），≠caption、互补不重复；≤2000 字符；
  首句像标题 ≤125 字符；纯文本无标记；general→specific；术语与正文一致。
- 颜色：必须灰度可读；"It is NOT safe to encode information using only
  variations in color"；红绿色盲影响约 8% 男性；推荐 ColorBrewer / ACE 调色板。
- 复杂图（架构/流程图）描述要点：图类型、元素数、连线类型、起止点、逐条
  列出连接；复杂描述可放附录（SIGACCESS 指南）。

## 二、实际配图风格（2024/2025 真实论文目检结论）

目检样本：AppAgent-Pro（CIKM'25 demo）、RankArena（CIKM'25 demo）、
MARM（CIKM'25 applied）、DAS/Kuaishou（CIKM'25 applied）、MISS（CIKM'25）、
ST-LINK（CIKM'25 结果图）、AgentRE（CIKM'24）、一张旧式数据流图（反例）。

**当代 CIKM 风格共识（新图都在此列）：**
1. **扁平矢量**：无渐变、无投影、无 3D。旧式的立体圆柱+粗黑箭头+浏览器
   logo 风格（2010 年代）在近年 CIKM 中已基本绝迹，见到即显旧。
2. **柔和低饱和填充**（约 10–15% tint）+ 同色系细描边；或白底盒 + 彩色
   标题条/标签芯片。
3. **功能分区分块**：背景色带（在线=浅青 / 训练=浅黄）、或虚线竖直分隔
   （(1)(2)(3) 三栏）、或虚线分组框。
4. **连线语法固定**：实线=数据/主流程、虚线=参数/异步/回退；细线
   (1–1.5px) 带**文字标签**（nearline / dump / load / infer / +10ms）。
5. **图内字体无衬线**（Helvetica/Arial/系统 sans），标签加粗纯黑；与正文
   Libertine 衬线形成对比。最小字 ~7pt 等效。
6. **多面板/多阶段显式编号**：(a)(b) 或 (1)(2)(3)，可配一句粗体小节名
   （如 "(2) Online Semantic IDs/Embs Inference"）。
7. **demo 轨允许"产品海报感"**：RankArena 的 hub-spoke 圆环+厚圆角卡片+
   emoji 图标、AppAgent-Pro 内嵌手机截图+卡通图标——demo 论文展示平台时
   装饰度明显高于 research 轨，这是 venue 接受的表达方式。
8. **结果图=matplotlib 保守风**：柔和 pastel 系列色（米/砖红/灰绿/紫红）、
   无网格线、boxed legend、2×2 子图共享坐标语义、色盲安全、同语义同色。
9. **截图**：系统类论文常嵌 1–2 张真实 UI 截图（demo 轨尤甚）——用于
   证明系统真实存在；但截图必须小而清晰，不抢版面。
10. **图注与描述**：citation 风格 "Figure N: …"，caption 自足（符号/缩写
    全解释），颜色/线型语义在 caption 里说明。

## 三、可执行 checklist（画新图或改图时逐条过）

- [ ] 矢量 PDF（或 SVG→PDF），字体全部嵌入/转曲，`get_fonts` 验证无匿名字体
- [ ] 无 raster 依赖；确有截图则 ≥300 dpi 并接受其在缩印后的清晰度
- [ ] 去除多余白边（mediabox/includegraphics 边界贴合内容）
- [ ] 宽度对齐：单栏 3.42 in 或双栏 7 in；字号换算后图内正文 ≥7pt
- [ ] 灰度打印测试：三色系在灰度下仍可区分（tint 明度差 ≥15%）
- [ ] 颜色永不唯一编码：色+文字标签/线型/形状至少双编码
- [ ] 线型语义全图统一（我们的约定：实线=直达、虚线=条件/回退）
- [ ] 多面板编号 (a)(b)/(1)(2)(3)；分区用浅色带或虚线分隔
- [ ] 图内 sans-serif + 加粗黑标签；避免 emoji 与装饰性 icon（research
      轨尤其；demo 轨克制使用）
- [ ] caption 自足 + `\Description` 互补（首句 ≤125 字符，≤2000 字符）
- [ ] 与全文其它图共享一套色语言（我们的 teal/slate/amber 家族）

## 四、我们论文三图对照（当前 build）

已符合：矢量 PDF+字体内嵌（三图 get_fonts 全 Arial 族）、mediabox 裁剪、
双栏全宽/0.92 宽对齐、灰度可读（浅 tint+深字）、线型双编码（solid=直达/
dashed=回退，与 DAS/MARM 的虚线约定一致）、多面板编号 (a)(b)、
`\Description` 全备且与 caption 互补、跨图色彩家族统一。

与 venue 观察的差异（有意为之，非缺陷）：
- 我们没有内嵌 UI 截图（AppAgent-Pro/RankArena 有）。demo rubric 强调
  "interface and interaction options"——视频承担了 UI 展示；若想更贴 demo
  轨惯例，可考虑在图 2 或 3 加一枚小控制台截图（需 ≥300dpi 且不抢版面）。
- 我们的图偏 research 轨的克制端（align MISS/TRIGON），装饰度低于
  RankArena 类"海报图"——两种都在 venue 接受范围内。

## 五、日程提醒（与配图无关但重要）

CIKM 2026 关键日期（AoE）：投稿 2026-06-06、通知 2026-08-07、
camera-ready 2026-08-23——按今日（2026-09-24）均已过。请确认实际投稿/
录用状态与目标（若为下一届或 workshop，页限条款需以新 CFP 为准）。
