---
name: fund-report
description: 生成基金体检HTML报告（中澳通用，支付宝/RMB与ASX/AUD ETF均适用），按F1-F4框架组织，单页四节
---

# 基金体检报告（F1-F4）

## 用途

输入**基金名称/代码 + 市场（支付宝/RMB 或 ASX/AUD）**，输出一份单页基金体检HTML报告，覆盖 `F-fund-selection.md` 四维度：

| 区块 | 框架 | 内容 |
|------|------|------|
| F1 业绩 | F1 | 年化/夏普/最大回撤/波动率，3年为主 |
| F2 持仓 | F2 | 股债比/前十集中/换手/跟踪误差 |
| F3 费率与人 | F3 | 管理费/申购赎回/规模/经理任职 |
| F4 适配 | F4 | 与 VAS/IVV/现金的相关系数、回撤对冲 |

中澳通用：澳洲大概率买 **ETF**（`VAS/IVV`，`Stake` 交易），国内大概率在 **支付宝** 买（`景顺 001422` 等）。阈值取宽松者即过，详见 `stock-learning/materials/F-fund-selection.md`。

## 输入格式

用户给出基金名称/代码，市场未指定时按代码推断：

```
"看一下 001422"          → 市场=支付宝/RMB，基金=景顺长城安享回报 A
"VAS 怎么看"              → 市场=ASX/AUD，基金=VAS
"分析一下 IVV"            → 市场=ASX/AUD，基金=IVV
"001460 怎么样"           → 市场=支付宝，基金=天弘等
```

若为 ETF，直接判定为指数基金，走指数体检（`F2` 看跟踪误差，不考核漂移）。

## 输出文件

单页基金体检报告存入 `stock-learning/stocks-analysis/基金/{名称}_{代码}_基金报告.html`。

> 示例：`基金/景顺长城安享回报A_001422_基金报告.html`、`基金/VAS_VAS_基金报告.html`

## 参考框架

F1-F4 定义在 `stock-learning/materials/F-fund-selection.md`，分析前必须通读，报告结论与框架保持一致：

| 区块 | 框架文件 |
|------|---------|
| F1 业绩 | `F-fund-selection.md` §F1 |
| F2 持仓 | `F-fund-selection.md` §F2 |
| F3 费率与人 | `F-fund-selection.md` §F3 |
| F4 适配 | `F-fund-selection.md` §F4 |

指数基金（VAS/IVV）优先用 `F1+F3` 定性，主动基金跑满四维。评分 `F1 40 + F2 20 + F3 20 + F4 20 = 100`，`≥75` 可入池，`≥85` 优秀。

## 参考模板

复用 `stock-report-tab` 的 HTML 骨架（`max-width:800px`、`report-wrap`、`highlight-box` 等），但**单页四节**（不分 Tab），结构：

```
.report-wrap
  h1 + .subtitle + .meta
  .verdict（总分）
  F1 业绩（表格+结论框）
  F2 持仓（表格+结论框）
  F3 费率与人（表格+结论框）
  F4 适配（表格+结论框）
  综合结论（highlight-box，含 入池/观望/回避 + 跟踪指标）
  .footer
```

CSS/JS 与 `stock-report-tab` 模板一致。`meta` 中日期统一 `YYYY-MM-DD` 格式。

## 数据来源

优先级：
1. **websearch 实时搜索** — 业绩/持仓/费率/经理，优先 `天天基金/晨星中国`（RMB）与 `Morningstar AU / ASX 公告`（AUD）
2. **已生成报告** — `stock-learning/stocks-analysis/基金/` 下历史报告
3. **用户提供** — 用户给出的持仓/费率
4. **知识内已知数据** — 仅用于历史参考值，标注"历史参考"

必须拿到的基础数据（每只基）：近3年夏普/最大回撤、股债比/前十、费率/规模/经理任职、与 VAS/IVV 相关系数。缺失标"数据待补充"，不编造。

## 生成后检查（QC）

- [ ] 单页四节完整（F1/F2/F3/F4 标题齐全）
- [ ] `meta` 日期 `YYYY-MM-DD`，`F1` 以3年夏普/回撤为主，`F2` 季报后必看
- [ ] 总分 = F1(40)+F2(20)+F3(20)+F4(20)=100，`verdict` 颜色一致（≥85绿/≥75橙/<75红）
- [ ] 数据来源可追溯（天天基金/晨星/ASX 公告），无编造
- [ ] 中澳通用阈值已按 `F-fund-selection.md` 中澳差异速查表执行
