---
name: gh-pages-sync
description: 刷新 docs/ 内的评分沿革表格、重建各级 index.html 表格数据、修正首页计数。docs 是唯一真身，本 skill 不做任何文件拷贝或删除
---

# GitHub Pages 索引刷新

## 架构前提（2026-10-13 起）

```
docs/          ← 唯一真身。报告 + history/scores.json + index.html，直接被 GitHub Pages 消费
stock-learning/ ← 只放学习资料（materials / notes / quizzes），不含任何报告
```

历史结构是「`stock-learning/stocks-analysis/` 生成 → 拷贝到 `docs/`」，该结构已在 2026-10-13 废除，原因是：

- 拷贝会产生滞后，Pages 不保证是最新版
- 双向可写导致漂移（实测 A股个股 16 份、ASX 个股 11 份、交易计划 6 份内容不一致）
- 「清理无源文件的旧报告」逻辑会误删（实测会删掉 13 份 ASX 行业报告与皖维高新交易计划，因为它们没有对应的源文件）

**因此：本 skill 不复制文件、不删除文件。** 报告写完直接就是最终态。

## 用途

对 `docs/` 做三项收尾，让 Pages 索引与实际文件一致：

1. **评分沿革注入/刷新** — 从每份报告的 meta 日期 + 总分 + 评分口径说明，读取或更新 `docs/history/scores.json`，并把「评分沿革」表格写回报告
2. **重建各级 index.html** — 按 `docs/` 中实际存在的文件重新生成表格数据
3. **修正首页计数** — `docs/index.html` 与 `docs/asx/index.html` 上的「N 份」

## 执行

直接跑脚本，不要手工改 index.html：

```bash
python scripts/sync_ghpages.py
```

脚本会依次完成：扫描 `docs/` → 刷新评分沿革 → 回写 `scores.json` → 重建
`stocks / asx.stocks / industry / asx.industry / plans / asx.plans / verify / asx.verify / funds / macro` 的
index.html → 更新首页计数。

脚本**不会**删除任何文件。输出中出现 `[skip] copy_files 已停用` 与
`[skip] prune_stale 已停用` 是正常的。

## 目录约定

| 报告类型 | A股 | ASX |
|---|---|---|
| 个股财务分析报告 | `docs/stocks/` | `docs/asx/stocks/` |
| 交易计划 | `docs/plans/` | `docs/asx/plans/` |
| 行业分析报告 | `docs/industry/` | `docs/asx/industry/` |
| C方案验证 | `docs/verify/` | `docs/asx/verify/` |
| 宏观环境报告 | `docs/macro/`（文件名 `A股_`/`ASX_` 前缀区分市场） | 同左 |
| 基金体检 | `docs/funds/`（中澳同池，按文件名判断） | 同左 |
| 评分历史 | `docs/history/scores.json` | 同左 |

**市场编码在目录里**，不再靠源目录层级推断。

## index.html 数据格式

除 `docs/macro/index.html` 为静态卡片外，其余 index.html 的表格数据都是内联 JS 数组
`const data = [ {..}, {..} ]`，由脚本生成。字段：

- `stocks` / `asx.stocks`：`name, code, type, score, fwd, rating, node, date, file`（`fwd`/`rating`/`node` 取自报告内的 `<!-- TRACK ... -->` 标记，无标记则空串，前端显示"—"）
- `industry` / `asx.industry`：`name, file`
- `plans` / `asx.plans`：`name, code, date, status, file`
- `verify` / `asx.verify`：`name, code, date, file`
- `funds`：`name, code, date, file`

排序默认按 `date` 倒序。**不要手工编辑这些数组**——跑脚本即可。

## 评分沿革机制

- 锚点：报告 verdict 框之后、综合诊断之前，保留 `<!-- HISTORY-TABLE -->` 注释
- 数据源：`docs/history/scores.json`，结构 `{version, updated, stocks: {代码: {name, code, series:[{d,s,t,n}]}}}`
  - `d` = 报告 meta 中的分析日期；`s` = 总分；`t` = L5 分类；`n` = 评分口径说明（≤40字）
- 同一天重复生成会**更新**该条记录，不会新增重复行
- 体系变化时（`t` 变了）自动生成「换评分体系（旧→新）」
- 注入是**幂等**的：脚本会先移除既有评分沿革表再重新写入，所以可以反复运行
  （2026-10-13 修复了旧实现「注入一次后 marker 消失、表格永久冻结」的 bug）

## 报告里必须有的字段

脚本靠这两个字段生成沿革，缺了就跳过：

```html
<p class="meta">分析日期：2026-10-13 | 数据来源：...</p>
<!-- 总分必须写成 "NN/100"，脚本用正则提取 -->
<tr style="font-weight:bold;background:#e8e8e8"><td>总分</td><td style="font-size:16px">89/100</td>...</tr>
<!-- 评分口径说明，≤40字，用于解释与上一版的差异 -->
<p class="score-note"><strong>评分口径说明：</strong><span>维持非周期股体系。ROE 按年化口径重估，因 H 股募资致净资产翻倍。</span></p>
<!-- 三轨标记（个股报告）：fwd=前瞻档 S/A/B/C/D，rating=Buy/Outperform/Neutral/Underperform/Sell，node=≤12字 -->
<!-- TRACK fwd=B rating=Neutral node=Q4存货去化 -->
```

## 排错

| 现象 | 原因 | 处理 |
|---|---|---|
| 评分沿革表没出现 | 报告缺 `总分` + 日期，或 `parse_score` 匹配不到 `NN/100` | 检查总分行写法 |
| 沿革表只有一行但改过多次 | 改的报告 `分析日期` 相同 → 视为同一版次覆盖 | 改 meta 日期，或改评分 |
| index 计数对不上 | 目录里有 `index.html` 以外的 html，或有手工新增 | 跑脚本重算，不要手改 |
| 想删某份报告 | 无源文件可依，脚本不会删 | 直接从 `docs/` 手工删除对应文件 |

## 注意

- 报告内容本身**不由本 skill 负责**，各生成类 skill 直接写入 `docs/` 对应目录即可
- `docs/history/scores.json` 是评分的历史账本，不要手工编辑，改报告后跑脚本
- 删报告时连同 `docs/history/scores.json` 里对应条目一起清，否则下次跑脚本会复活沿革行