---
name: macro-report
description: 生成大盘宏观环境HTML分析报告，含A股/ASX的L0-A1/A2/B1/B2综合判断与结论
---

# 宏观环境报告模板

## 用途

为用户生成一份带Tab导航的宏观环境HTML报告，报告包含：
- A股宏观环境综合判断（L0-A1 + L0-A2）
- ASX宏观环境综合判断（L0-B1 + L0-B2）
- 对当前市场给出明确结论（现在是进攻还是防守、仓位多少合适）

## 参考框架

L0 宏观框架定义在 `stock-learning/materials/`，分析前必须通读对应文件，报告结论与框架保持一致：

| 模块 | 框架文件 |
|------|---------|
| A股宏观象限（tab-a1） | `stock-learning/materials/L0-A1-china-macro-cycle.md` |
| A股政策资金（tab-a2） | `stock-learning/materials/L0-A2-policy-capital.md` |
| ASX大宗利率（tab-b1） | `stock-learning/materials/L0-B1-australia-macro.md` |
| ASX全球联动（tab-b2） | `stock-learning/materials/L0-B2-global-linkage.md` |

## 参考模板

参考 `stock-learning/stocks-analysis/宏观报告/A股_宏观环境报告_2026-07-09.html` 的HTML结构和CSS样式（Tab导航+verdict框）。

## 输出路径

`stock-learning/stocks-analysis/宏观报告/{市场}_宏观环境报告_{YYYY-MM-DD}.html`

> 示例：`stock-learning/stocks-analysis/宏观报告/A股_宏观环境报告_2026-07-09.html`

## 报告结构

### 页面布局

```
body (bg:#f5f5f5, padding:0)
  .report-wrap (max-width:900px, margin:0 auto, bg:#fff)
    h1 + .subtitle + .meta
    .tab-bar (sticky top, 5个tab)
    .tab-content#tab-summary  → 总结论
    .tab-content#tab-a1       → A股宏观象限
    .tab-content#tab-a2       → A股政策资金
    .tab-content#tab-b1       → ASX大宗商品+利率
    .tab-content#tab-b2       → ASX全球联动
    .footer (生成日期)
```

### Tab导航

| 按钮 | data-tab | 内容 |
|------|----------|------|
| 总结论 | summary | 整体判断 + 评分 + verdict + 当前策略建议 |
| A股 宏观象限 | a1 | 经济象限判断（PMI/社融/CPI/PPI/国债收益率）+ 趋势 |
| A股 政策资金 | a2 | 货币政策/财政政策/产业政策/北向/两融/新发基金 + 评分表 |
| ASX 大宗利率 | b1 | RBA利率走向 + 铁矿石/金价/锂价 + AUDUSD + 中国经济联动 |
| ASX 全球联动 | b2 | 美联储利率 + 美债收益率 + 美元指数 + ASX200技术面 + VIX |

### CSS准则

与个股报告css完全一致的风格，但tab button增加为5个并排。

- .tab-bar 的 flex-wrap: nowrap，按钮字体缩小到13px确保5个tab在一行

### 总结论（tab-summary）的结构

```
h2 当前市场环境总判断

[verdict 框]
  绿色（verdict-ok）  ： 全力做多，环境极度友好
  橙色（verdict-caution）： 中性偏多/偏空，精选个股
  红色（verdict-bad）  ： 休息或轻仓

h3 A股综合评分：x/6
  评分表（类似个股报告的评分表）：
  维度 | 评分 | 说明
  宏观象限 | +1/0/-1 | 一句话解释
  货币政策 | +1/0/-1 | 一句话解释
  财政政策 | +1/0/-1 | 一句话解释
  产业政策 | +1/0/-1 | 一句话解释
  资金面   | +1/0/-1 | 一句话解释
  情绪/技术 | +1/0/-1 | 一句话解释
  总分     | x/6    | 结论

h3 ASX综合判断
  四个维度各一句话 + 整体看法

h3 操作建议
  仓位建议：重仓(>80%) / 正常(50-80%) / 轻仓(20-50%) / 回避(<20%)
  风格建议：成长 / 周期 / 防御 / 均衡
  关键风险：1~3条当前最需要关注的风险点
```

### JS交互

与个股报告完全一致的Tab切换逻辑，仅把tab数量改为5个。

```javascript
var btns = document.querySelectorAll('.tab-btn:not(.disabled)');
var contents = document.querySelectorAll('.tab-content');
btns.forEach(function(btn) {
  btn.addEventListener('click', function() {
    btns.forEach(function(b) { b.classList.remove('active'); });
    contents.forEach(function(c) { c.classList.remove('active'); });
    btn.classList.add('active');
    var tab = btn.getAttribute('data-tab');
    document.getElementById('tab-' + tab).classList.add('active');
  });
});
```

## 数据来源

**获取顺序（优先级从高到低）：**
1. **websearch 实时搜索** — 优先用 `websearch` 获取最新宏观数据（PMI/社融/LPR/利率/大宗价格等），记录来源和日期
2. **用户提供** — 用户消息中给出的宏观跟踪表或已知信息
3. **知识内已知数据** — 仅用于无法搜索到的历史参考值，必须标注"历史参考"

每次生成报告时，需要确认以下数据是否齐全：

**A股部分需要确认：**
- PMI（近3个月数据）
- 社融（当月同比多增/少增）
- CPI/PPI
- 十年期国债收益率
- LPR最新利率
- 北向资金月累计
- 是否有近期重要政策信号

**ASX部分需要确认：**
- RBA最新利率
- 铁矿石价格趋势
- 金价趋势
- AUDUSD
- 美联储最新利率
- 10年期美债收益率
- ASX200技术面

## 数据录入

对每一项数据，先尝试 websearch 获取最新值；搜索不到再询问用户或标注缺失。

如果某项数据无法获取（websearch 失败且用户未提供），报告对应区域标注"数据待补充"并用灰色字体。**不要编造数据。**

## 更新日志

每次生成时在 `.footer` 或报告末尾追加一行更新记录：

```
更新：{YYYY-MM-DD} | 数据完整度：A股 n/7 · ASX n/6 | 数据来源：websearch/用户提供
```

## 生成后检查（QC）

生成完成后逐项核对：
- [ ] 5个tab结构完整，按钮文字与`data-tab`对应
- [ ] meta/更新日志中的日期为 `YYYY-MM-DD` 格式
- [ ] 每个数据点有来源：websearch（标注日期）或"数据待补充"灰色标注
- [ ] 无编造数据：所有数字能追溯到搜索来源或用户输入
- [ ] verdict 框与评分一致（总分≥4绿 / 2-3橙 / ≤1红）
- [ ] 数据待补充项有明确提示，不占verdict评分
