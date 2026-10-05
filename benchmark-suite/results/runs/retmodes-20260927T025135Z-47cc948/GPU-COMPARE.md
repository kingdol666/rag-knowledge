# 三模式检索 · CPU vs GPU 对比报告

- 生成：2026-09-27 02:58 UTC
- CPU 轮：`retmodes-20260926T202450Z-47cc948`（torch 2.10.0+cpu，逐段判决 Laya CPU 推理）
- GPU 轮：`retmodes-20260927T025135Z-47cc948`（**torch 2.14.0+cu130**，Laya 自动选 `cuda` — RTX 4070 Ti SUPER 16GB；设备选择零代码改动，Agent 默认 `device=None` 时自动优先 CUDA）

## 主对比矩阵

| 臂 | CPU 耗时 | GPU 耗时 | 提速 | 结果文档 CPU→GPU | 金标 | 门 |
|---|---:|---:|---:|---|:--:|:--:|
| A×q1 | 117.1s | 25.5s | **4.6×** | 17→17 | ✅ | ✅ |
| A×q2 | 124.5s | 24.3s | **5.1×** | 15→15 | ✅ | ✅ |
| B×q1 | 171.3s | 25.1s | **6.8×** | 23→23 | ✅ | ✅ |
| B×q2 | 89.3s | 10.1s | **8.8×** | 11→11 | ✅ | ✅ |
| C×q1 | 576.5s | 68.6s | **8.4×** | 36→36 | ✅ | ✅ |
| C×q2 | 541.7s | 64.2s | **8.4×** | 39→38 ⚠数值漂移 | ✅ | ✅ |
| **合计** | **1620s** | **218s** | **7.4×** | | | |

## 判决微观基准（单段 verdict）

- CPU（torch 2.10.0+cpu）：约 **2s/段**（2026-09-26 实测），547 段 ≈ 18 分钟
- GPU（torch 2.14.0+cu130）：加载 24.4s（模型上卡）+ 首段 12.1s（内核编译预热），热身后 **≈0.08s/段** —— 单段判决 **约 25×** 提速

## 结论

1. **GPU 加载成立且默认生效**：Laya `Agent(device=None)` 在 `torch.cuda.is_available()` 时自动选 CUDA——无需改任何业务代码；判决从分钟级坍缩到秒级，三模式全部受益。
2. **验证门 6/6 全过**：金标 6/6 命中、全部 `real_engine=true`、fail-closed 无击穿——GPU 数值路径未破坏召回正确性。
3. **一处数值漂移**：C×q2 结果文档 39→38（GPU 分数与 CPU 有轻微数值差，一个临界文档落到阈值外），金标不受影响；如需严格一致可加阈值容差或固定 CPU 判决。
4. **模式格局不变，绝对耗时全部进入交互级**：A ≈30s、B ≈10-28s、C ≈70s——原「C 最全但最慢」的取舍已被 GPU 大幅缓解，三模式均可进在线链路。

## 工件

- CPU 轮：`benchmark-suite\results\runs\retmodes-20260926T202450Z-47cc948`（THREE-MODE-REPORT.md + arm_*.json）
- GPU 轮：`benchmark-suite\results\runs\retmodes-20260927T025135Z-47cc948`（同结构）
- 复现：装 GPU torch（`pip install torch --index-url https://download.pytorch.org/whl/cu130`）后重跑 140 + 141 + 142
