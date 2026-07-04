---
name: l7-screening
description: 对A股/ASX指定行业进行完整分析（L7-L10），生成带Tab导航的HTML行业报告，含总结论/初筛/画像/竞争/周期五个Tab
---

# 行业分析框架（L7-L10）

## 用途

输入**市场 + 一个行业**，输出一份完整的行业分析HTML报告。报告含五个Tab：

| Tab | 对应框架 | 内容 |
|-----|---------|------|
| 总结论 | — | 行业速览 + 综合评分 + 核心结论 |
| L7 量化初筛 | L7 | 六道筛子过滤，候选池 + 观察池 |
| L8 行业画像 | L8 | 产业链 + 市场规模 + 生命周期 |
| L9 竞争格局 | L9 | 竞争格局 + 壁垒 + 驱动力拆解 |
| L10 周期时机 | L10 | 周期位置 + 估值 + 政策 + 买入清单 |

## 输入格式

用户给出行业名称和目标市场（未指定时默认为A股）。

```
"筛一下A股光伏"     → 市场=A股，行业=光伏
"ASX金矿看看"       → 市场=ASX，行业=金矿
"分析一下证券"      → 市场=A股，行业=证券
"锂矿现在能买吗"   → 市场=A股，行业=锂矿（含L10时机判断）
```

## 六道筛子速查（L7参考）

### ① 市值

| 市场 | 标准 |
|------|------|
| A股主板 | ≥50亿保留 |
| A股创业板/科创板 | ≥30亿保留 |
| ASX | ≥2亿AUD保留 |

### ② 营收

| 市场 | 标准 |
|------|------|
| A股主板 | ≥10亿保留 |
| A股创业板/科创板 | ≥3亿保留 |
| ASX | ≥1亿AUD保留 |

### ③ 毛利率

| 行业类型 | 标准 |
|---------|------|
| 制造业/科技/医药 | ≥15%保留 |
| 消费品牌 | ≥20%保留 |
| 金融/银行 | 跳过此筛 |
| 贸易/零售 | ≥10%保留 |
| ASX矿业 | 跳过此筛 |

### ④ ROE

| 标准 | 说明 |
|------|------|
| ≥8%保留 | 低于沪深300长期回报率 |
| 连续3年<5%剔除 | 长期低回报是资本堆积型 |
| ASX矿业/成长初期 | 放宽到≥5%或跳过 |

### ⑤ 负债率

| 行业类型 | 标准 |
|---------|------|
| 制造业/科技/消费 | ≤65%保留 |
| 金融/银行/保险 | 跳过此筛 |
| 地产 | ≤75%保留 |
| ASX公用事业 | ≤70%保留 |

### ⑥ 估值

| 指标 | 标准 |
|------|------|
| PE（盈利企业） | 历史分位≤70%保留 |
| PB（周期/金融） | 历史分位≤80%保留 |
| PS（亏损成长股） | ≤10x保留 |

### 行业类型调整速查

| 行业类型 | 跳过筛子 | 调整筛子 |
|---------|---------|---------|
| 银行/保险 | ③毛利率, ⑤负债率 | ⑥用PB |
| ASX矿业 | ③毛利率 | ④ROE放宽≥5%, ⑥用PB |
| 地产 | — | ⑤放宽≤75% |
| 周期股底部（亏损） | — | ⑥用PB替代PE |
| 亏损但高营收成长 | ④ROE | ⑥用PS≤10x |
| 上市不满3年 | — | ④用可用数据替代 |

## 输出文件

完整行业分析报告和后续L1-L6个股报告统一存入 `stock-learning/stocks-analysis/行业报告/`。

文件名格式：

```
{市场}——{行业名}——行业分析报告.html
{市场}——{行业名}——{股票简称}_{代码}_分析报告.html
```

示例：

```
stock-learning/stocks-analysis/行业报告/A股——证券——行业分析报告.html
stock-learning/stocks-analysis/行业报告/A股——证券——东方财富_300059_分析报告.html
stock-learning/stocks-analysis/行业报告/A股——光伏——行业分析报告.html
stock-learning/stocks-analysis/行业报告/ASX——金矿——行业分析报告.html
```

## 具体流程

1. **确认输入：** 市场（A股/ASX）+ 行业名称
2. **确认行业覆盖面：** 该行业大概多少只股票（通过历史对话或搜行业全景图）
3. **L7 初筛：** 按六道筛子逐轮过滤，标注淘汰原因，输出候选池
4. **L8 行业画像：** 产业链分析、市场规模、生命周期判断
5. **L9 竞争格局：** 市场结构、壁垒、驱动力拆解
6. **L10 时机判断：** 周期位置、估值分位、政策方向、买入清单
7. **写HTML留档：** 将完整结果写入 `行业报告/{市场}——{行业名}——行业分析报告.html`，含五个Tab
8. **判断下一步：** 建议跑哪只的L1-L6（按候选池优先级）

## 行业分析HTML模板

> 📐 **格式参考：** 实际产出效果见 `stock-learning/stocks-analysis/行业报告/A股——光伏——行业分析报告.html`（含进度条/彩色标签/卡片式产业链/编号卖出信号等完整样式）

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{市场}——{行业名} 行业分析报告</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:-apple-system,'Microsoft YaHei',sans-serif;background:#f5f5f5;padding:0;color:#333}
  .report-wrap{max-width:800px;margin:0 auto;background:#fff}
  h1{font-size:22px;margin:0;padding:28px 0 4px;text-align:center}
  h2{font-size:18px;margin:28px 0 12px;border-bottom:2px solid #1a1a1a;padding-bottom:4px}
  h3{font-size:15px;margin:18px 0 8px}
  .subtitle{color:#666;font-size:13px;text-align:center;margin-bottom:4px}
  .meta{color:#999;font-size:12px;text-align:center;margin-bottom:20px;padding-bottom:12px;border-bottom:1px solid #e0e0e0}
  .tab-bar{position:sticky;top:0;z-index:10;background:#fff;display:flex;flex-wrap:wrap;border-bottom:2px solid #ddd;gap:0}
  .tab-btn{padding:10px 14px;cursor:pointer;border:none;background:none;font-size:13px;color:#666;border-bottom:2px solid transparent;margin-bottom:-2px;transition:all .2s}
  .tab-btn:hover{color:#333;background:#f9f9f9}
  .tab-btn.active{color:#1a1a1a;font-weight:700;border-bottom-color:#1a1a1a}
  .tab-content{display:none}
  .tab-content.active{display:block}
  .tab-inner{padding:0 12px}
  table{width:100%;border-collapse:collapse;margin:10px 0 18px;font-size:13px}
  th{background:#f5f5f5;padding:8px 6px;text-align:left;border-bottom:2px solid #ddd;white-space:nowrap;font-weight:600}
  td{padding:7px 6px;border-bottom:1px solid #eee}
  tr:nth-child(even) td{background:#fafafa}
  .summary-box{background:#fffde7;border-left:4px solid #f9a825;padding:12px 16px;margin:14px 0;border-radius:0 4px 4px 0;font-size:13px}
  .highlight-box{background:#e3f2fd;border-left:4px solid #1e88e5;padding:12px 16px;margin:14px 0;border-radius:0 4px 4px 0;font-size:13px}
  .danger-box{background:#ffebee;border-left:4px solid #e53935;padding:12px 16px;margin:14px 0;border-radius:0 4px 4px 0;font-size:13px}
  .verdict{text-align:center;padding:20px;margin:16px 0;border-radius:8px;font-size:18px;font-weight:700}
  .verdict-ok{background:#e8f5e9;border:2px solid #4caf50;color:#2e7d32}
  .verdict-caution{background:#fff3e0;border:2px solid #ff9800;color:#e65100}
  .verdict-bad{background:#ffebee;border:2px solid #e53935;color:#c62828}
  .score{font-size:36px;display:block;margin-bottom:4px}
  .pass{color:#2e7d32;font-weight:700}
  .skip{color:#666;font-style:italic}
  .tag{display:inline-block;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:700}
  .tag-red{background:#ffebee;color:#c62828}
  .tag-green{background:#e8f5e9;color:#2e7d32}
  .tag-yellow{background:#fff8e1;color:#f57f17}
  .footer{font-size:11px;color:#aaa;text-align:center;padding:24px 0 8px;border-top:1px solid #eee;margin-top:30px}
  .card{background:#fafafa;border:1px solid #e0e0e0;border-radius:6px;padding:14px;margin:10px 0;font-size:13px}
  .flex{display:flex;flex-wrap:wrap;gap:8px}
  /* --- 美化增强样式 --- */
  .tbl-wrap{border:1px solid #e0e0e0;border-radius:6px;overflow:hidden;margin:10px 0 18px}
  .tbl-wrap table{margin:0}
  .tbl-wrap th{background:#f5f5f5;padding:9px 8px;border-bottom:1px solid #ddd;font-weight:600;font-size:12px}
  .tbl-wrap td{padding:8px;border-bottom:1px solid #f0f0f0;font-size:13px}
  .tbl-wrap tr:last-child td{border-bottom:none}
  .tbl-wrap td,.tbl-wrap th{vertical-align:middle}
  .bar-wrap{display:inline-flex;align-items:center;width:60px;height:16px;vertical-align:middle}
  .bar-bg{background:#eee;border-radius:4px;height:8px;width:100%;overflow:hidden}
  .bar{display:block;height:8px;border-radius:4px}
  .score-cell{font-weight:700;font-size:15px;text-align:center;white-space:nowrap}
  .col-tag{display:inline-block;padding:1px 6px;border-radius:3px;font-size:11px;font-weight:600}
  .col-win{background:#e8f5e9;color:#2e7d32}
  .col-lose{background:#ffebee;color:#c62828}
  .col-warn{background:#fff3e0;color:#e65100}
  .col-info{background:#e3f2fd;color:#1565c0}
</style>
</head>
<body>
<div class="report-wrap">

<h1>{市场}——{行业名} 行业分析报告</h1>
<div class="subtitle">L5分类：{周期/成长/防御/价值/混合周期} ｜ 上市公司：~{N}只 ｜ 总市值：~{市值}亿</div>
<div class="meta">生成日期：{YYYY-MM-DD}</div>

<div class="tab-bar">
  <button class="tab-btn active" data-tab="summary">总结论</button>
  <button class="tab-btn" data-tab="l7">L7 量化初筛</button>
  <button class="tab-btn" data-tab="l8">L8 行业画像</button>
  <button class="tab-btn" data-tab="l9">L9 竞争格局</button>
  <button class="tab-btn" data-tab="l10">L10 周期时机</button>
</div>

<!-- ═══════════════════════════════════════════════════
     总结论 Tab
     ═══════════════════════════════════════════════════ -->
<div class="tab-content active" id="tab-summary">
<div class="tab-inner">

<h2>行业速览</h2>
<div class="tbl-wrap">
<table>
<tr><th style="width:30%">项目</th><th>内容</th></tr>
<tr><td>行业名称</td><td><strong>{行业名}</strong></td></tr>
<tr><td>市场</td><td>{A股/ASX}</td></tr>
<tr><td>L5分类</td><td><span class="col-tag col-{win/lose/warn/info}">{周期/成长/防御/价值/混合周期}</span> {补充说明}</td></tr>
<tr><td>上市公司</td><td>~{N}只，其中符合L7筛选条件<span class="col-tag col-win">{候选数}只</span></td></tr>
<tr><td>行业总市值</td><td>~{市值}亿</td></tr>
<tr><td>产业链利润核心</td><td><span class="col-tag col-{win/warn/info}">{利润最厚环节}</span>{补充说明}</td></tr>
<tr><td>生命周期阶段</td><td><span class="col-tag col-{warn/info/lose}">{导入/成长/洗牌/成熟/衰退}期</span>{补充说明}</td></tr>
<tr><td>当前周期位置</td><td><span class="col-tag col-{win/lose}">{繁荣/复苏/衰退/萧条}</span>{补充说明}</td></tr>
</table>
</div>

<h2>综合评分</h2>
<div class="tbl-wrap">
<table>
<tr><th>维度</th><th style="width:60px">得分</th><th>进度</th><th>说明</th></tr>
<tr>
  <td>行业规模与空间</td>
  <td class="score-cell">{N}/20</td>
  <td><span class="bar-wrap"><span class="bar-bg"><span class="bar" style="width:{N*5}%;background:#4caf50"></span></span></span></td>
  <td style="font-size:12px;color:#555">{说明}</td>
</tr>
<tr>
  <td>产业链位置</td>
  <td class="score-cell">{N}/15</td>
  <td><span class="bar-wrap"><span class="bar-bg"><span class="bar" style="width:{N*6.7}%;background:{≥8?4caf50:ff9800}"></span></span></span></td>
  <td style="font-size:12px;color:#555">{说明}</td>
</tr>
<tr>
  <td>竞争格局</td>
  <td class="score-cell">{N}/20</td>
  <td><span class="bar-wrap"><span class="bar-bg"><span class="bar" style="width:{N*5}%;background:#ff9800"></span></span></span></td>
  <td style="font-size:12px;color:#555">{说明}</td>
</tr>
<tr>
  <td>增长驱动力</td>
  <td class="score-cell">{N}/15</td>
  <td><span class="bar-wrap"><span class="bar-bg"><span class="bar" style="width:{N*6.7}%;background:#ff9800"></span></span></span></td>
  <td style="font-size:12px;color:#555">{说明}</td>
</tr>
<tr>
  <td>周期位置</td>
  <td class="score-cell">{N}/15</td>
  <td><span class="bar-wrap"><span class="bar-bg"><span class="bar" style="width:{N*6.7}%;background:#4caf50"></span></span></span></td>
  <td style="font-size:12px;color:#555">{说明}</td>
</tr>
<tr>
  <td>政策环境</td>
  <td class="score-cell">{N}/15</td>
  <td><span class="bar-wrap"><span class="bar-bg"><span class="bar" style="width:{N*6.7}%;background:#4caf50"></span></span></span></td>
  <td style="font-size:12px;color:#555">{说明}</td>
</tr>
<tr style="background:#fafafa">
  <td style="font-weight:700;font-size:14px">总分</td>
  <td style="font-weight:700;font-size:16px;color:{≥60?2e7d32:e65100}">{N}/100</td>
  <td><span class="bar-wrap"><span class="bar-bg"><span class="bar" style="width:{N}%;background:{≥60?4caf50:ff9800}"></span></span></span></td>
  <td style="font-size:12px;color:#555;font-weight:600">{优秀/一般/回避}</td>
</tr>
</table>
</div>

<div class="verdict verdict-{ok/caution/bad}">
  <span class="score">{N}</span>
  {优秀 / 一般 / 回避}
</div>

<div class="summary-box">
  <strong>核心结论</strong><br>
  {这行业值不值得研究、用什么框架分析、当前能不能买}
</div>

<div class="highlight-box">
  <strong>行业公式</strong><br>
  收入 = {量因子} × {价因子}<br>
  关键指标：{3-5个核心跟踪指标}
</div>

</div>
</div>

<!-- ═══════════════════════════════════════════════════
     L7 Tab
     ═══════════════════════════════════════════════════ -->
<div class="tab-content" id="tab-l7">
<div class="tab-inner">

<h2>筛子调整说明</h2>
<div class="tbl-wrap">
<table>
<tr><th style="width:12%">筛子</th><th style="width:35%">标准</th><th>调整说明</th></tr>
<tr><td>①<span class="col-tag col-info">市值</span></td><td>{标准}</td><td>{调整说明}</td></tr>
<tr><td>②<span class="col-tag col-info">营收</span></td><td>{标准}</td><td>{调整说明}</td></tr>
<tr><td>③<span class="col-tag col-{跳过?info:lose}">毛利率</span></td><td>{标准}</td><td><span class="col-tag col-info">{跳过?跳过此筛:调整说明}</span></td></tr>
<tr><td>④<span class="col-tag col-{跳过?info:warn}">ROE</span></td><td>{标准}</td><td>{调整说明}</td></tr>
<tr><td>⑤<span class="col-tag col-{跳过?info:info}">负债率</span></td><td>{标准}</td><td><span class="col-tag col-info">{跳过?跳过此筛:调整说明}</span></td></tr>
<tr><td>⑥<span class="col-tag col-info">估值</span></td><td>{标准}</td><td>{调整说明}</td></tr>
</table>
</div>

<h2>候选池（{N}只）</h2>
<div class="tbl-wrap">
<table>
<tr><th>股票</th><th>环节</th><th>市值</th><th>毛利率</th><th>ROE</th><th>负债率</th><th>PE/PB分位</th><th>通过</th></tr>
<!-- 核心候选（前5只高亮加粗） -->
<tr>
  <td><strong>{股票名} {代码}</strong></td>
  <td><span class="col-tag col-{win/warn/info}">{环节}</span></td>
  <td style="font-weight:600">{市值}</td>
  <td><span class="col-tag col-{≥15?win:lose}">{毛利率}</span></td>
  <td><span class="col-tag col-{≥8?win:lose}">{ROE}</span></td>
  <td>{负债率}</td>
  <td>{分位}</td>
  <td class="pass">{N}/6</td>
</tr>
<!-- 次要候选（灰底） -->
<tr style="background:#fafafa">
  <td>{股票名} {代码}</td>
  <td><span class="col-tag col-{win/warn/info}">{环节}</span></td>
  <td>{市值}</td>
  <td>{毛利率}</td>
  <td>{ROE}</td>
  <td>{负债率}</td>
  <td>{分位}</td>
  <td class="pass">{N}/6</td>
</tr>
</table>
</div>

<h2>观察池</h2>
<div class="tbl-wrap">
<table>
<tr><th>股票</th><th>卡在哪筛</th><th>备注</th></tr>
<tr>
  <td><strong>{股票名}</strong></td>
  <td><span class="col-tag col-lose">{卡住筛子}</span></td>
  <td>{触发条件}</td>
</tr>
</table>
</div>

<h2>筛除记录</h2>
<div class="tbl-wrap">
<table>
<tr><th>筛子</th><th style="width:60px">筛除数</th><th>知名示例</th></tr>
<tr><td>①市值</td><td style="text-align:center">{N}</td><td>{公司名}</td></tr>
<tr><td>②营收</td><td style="text-align:center">{N}</td><td>{公司名}</td></tr>
<tr><td>③毛利率 <span class="col-tag col-{最严?lose:info}">{最严?最严:跳过}</span></td><td style="text-align:center">{N}</td><td>{公司名}</td></tr>
<tr><td>④ROE <span class="col-tag col-warn">{唯一筛除?唯一筛除:''}</span></td><td style="text-align:center">{N}</td><td>{公司名}</td></tr>
<tr><td>⑤负债率 <span class="col-tag col-info">{跳过?跳过:''}</span></td><td style="text-align:center">{N}</td><td>{公司名}</td></tr>
<tr><td>⑥估值</td><td style="text-align:center">{N}</td><td>{公司名}</td></tr>
<tr style="background:#fffde7"><td><strong>剩余</strong></td><td style="text-align:center;font-weight:700;color:#2e7d32"><strong>{N}</strong></td><td>—</td></tr>
</table>
</div>

<div class="highlight-box">
  <strong>L7筛选结论</strong><br>
  {筛选力度如何、是否需要加第七筛（如市占率趋势）、哪些特别值得关注}
</div>

</div>
</div>

<!-- ═══════════════════════════════════════════════════
     L8 Tab
     ═══════════════════════════════════════════════════ -->
<div class="tab-content" id="tab-l8">
<div class="tab-inner">

<h2>产业链</h2>
<div class="card" style="font-size:13px;line-height:1.7">

<div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:12px">

<!-- 上游 -->
<div style="flex:1;min-width:{上游占比};background:#f5f5f5;border-radius:6px;padding:10px">
  <div style="font-weight:700;text-align:center;margin-bottom:6px;color:{色};font-size:14px">上游原材料</div>
  <div style="border-top:1px solid #ddd;padding-top:6px">
    <!-- 上游环节：色块 + 代表公司 + 箭头指向 -->
    <div style="margin-bottom:6px;background:{色浅};border-radius:4px;padding:6px 8px;text-align:center;font-weight:600;font-size:13px">{环节名}</div>
    <div style="text-align:center;font-size:11px;color:#666">{公司列表}</div>
    <div style="margin:10px 0;text-align:center;color:#999;font-size:18px">↓</div>
    <div style="margin-bottom:6px;background:{色浅};border-radius:4px;padding:6px 8px;text-align:center;font-weight:600;font-size:13px">{环节名}</div>
    <div style="text-align:center;font-size:11px;color:#666">{公司列表}</div>
  </div>
</div>

<!-- 中游 -->
<div style="flex:2;min-width:280px;background:#f5f5f5;border-radius:6px;padding:10px">
  <div style="font-weight:700;text-align:center;margin-bottom:6px;color:#1565c0;font-size:14px">中游制造</div>
  <div style="border-top:1px solid #ddd;padding-top:6px">
    <!-- 主链环节：横向流程箭头，红底为亏损 -->
    <div style="display:flex;gap:6px;margin-bottom:10px;flex-wrap:wrap">
      <div style="flex:1;min-width:60px;background:#ffebee;border-radius:4px;padding:6px 4px;text-align:center">
        <div style="font-weight:700;font-size:12px">{环节}</div>
        <div style="font-size:10px;color:#666">{公司}</div>
      </div>
      <div style="font-size:20px;color:#999;line-height:36px">→</div>
      <div style="flex:1;min-width:60px;background:#ffebee;border-radius:4px;padding:6px 4px;text-align:center">
        <div style="font-weight:700;font-size:12px">{环节}</div>
        <div style="font-size:10px;color:#666">{公司}</div>
      </div>
    </div>
    <div style="text-align:center;font-size:11px;color:#c62828;margin-bottom:10px">▲ 亏损提示</div>

    <!-- 辅材 / 设备 / 其他分支：flex色块排列 -->
    <div style="margin:6px 0 4px;font-weight:600;font-size:12px;color:#1565c0">{分支标题}</div>
    <div style="display:flex;gap:6px;flex-wrap:wrap">
      <div style="flex:1;background:#fff3e0;border-radius:4px;padding:6px 8px;text-align:center;font-size:12px">{名称}</div>
    </div>
  </div>
</div>

<!-- 下游 -->
<div style="flex:1;min-width:160px;background:#f5f5f5;border-radius:6px;padding:10px">
  <div style="font-weight:700;text-align:center;margin-bottom:6px;color:#c62828;font-size:14px">下游应用</div>
  <div style="border-top:1px solid #ddd;padding-top:6px">
    <div style="margin-bottom:6px;background:#ffebee;border-radius:4px;padding:10px 8px;text-align:center;font-weight:600;font-size:13px">{环节}</div>
    <div style="text-align:center;font-size:11px;color:#666">{公司}</div>
    <div style="margin:10px 0;text-align:center;color:#999;font-size:18px">↓</div>
    <div style="margin-bottom:6px;background:#f5f5f5;border:1px solid #ccc;border-radius:4px;padding:10px 8px;text-align:center;font-weight:600;font-size:13px">终端用户</div>
    <div style="text-align:center;font-size:11px;color:#666">{用户类型}</div>
  </div>
</div>

</div>

<div style="background:#fffde7;border-left:3px solid #f9a825;padding:8px 12px;font-size:12px;border-radius:0 4px 4px 0">
  <strong>利润最厚环节：</strong>{说明}
  <br><span style="color:#999">{备注}</span>
</div>

</div>

<div class="tbl-wrap">
<table>
<tr><th>环节</th><th>代表公司</th><th>毛利率</th><th>集中度</th><th>议价能力</th></tr>
<tr>
  <td><span class="col-tag col-{win/lose/warn}">{环节}</span></td>
  <td>{公司}</td>
  <td><span class="col-tag col-{win/lose/warn}">{毛利率}</span></td>
  <td>{集中度}</td>
  <td><span class="col-tag col-{强?win:中?warn:lose}">{议价能力}</span></td>
</tr>
</table>
</div>

<h2>市场规模</h2>
<div class="tbl-wrap">
<table>
<tr><th style="width:30%">指标</th><th style="width:25%">数值</th><th>说明</th></tr>
<tr><td><strong>TAM</strong>（总可触达市场）</td><td><span class="col-tag col-info">{N}</span></td><td>{说明}</td></tr>
<tr><td><strong>当前渗透率</strong></td><td>{N}%</td><td>{说明}</td></tr>
<tr><td><strong>近年增速</strong>（3年CAGR）</td><td><span class="col-tag col-{高?win:中?warn:lose}">{N}%</span></td><td>{说明}</td></tr>
</table>
</div>

<h2>生命周期</h2>
<div class="summary-box">
  <strong><span class="col-tag col-{warn/info/lose}">{导入/成长/洗牌/成熟/衰退}期</span></strong><br>
  {判断依据}
</div>

<h2>增长驱动力</h2>
<div class="tbl-wrap">
<table>
<tr><th>驱动力</th><th>类型</th><th>可持续性</th><th>量化指标</th></tr>
<tr>
  <td>{驱动力}</td>
  <td><span class="col-tag col-{结构?win:周期?lose:warn}">{结构/周期}</span></td>
  <td><span class="col-tag col-{长?win:中?warn:lose}">{长/中/短}</span></td>
  <td>{量化方式}</td>
</tr>
</table>
</div>

</div>
</div>

<!-- ═══════════════════════════════════════════════════
     L9 Tab
     ═══════════════════════════════════════════════════ -->
<div class="tab-content" id="tab-l9">
<div class="tab-inner">

<h2>市场结构</h2>
<div class="tbl-wrap">
<table>
<tr><th style="width:25%">维度</th><th>判断</th></tr>
<tr>
  <td>市场结构类型</td>
  <td><span class="col-tag col-{完全竞争?lose:垄断竞争?warn:寡头垄断?win:win}">{完全竞争/垄断竞争/寡头垄断/完全垄断}</span></td>
</tr>
<tr>
  <td>CR3</td><td>{说明}</td>
</tr>
<tr>
  <td>格局象限</td>
  <td><span class="col-tag col-{价格战?lose:百花齐放?warn:赢家通吃?win:win}">{格局}</span></td>
</tr>
<tr>
  <td>新进入者威胁</td>
  <td><span class="col-tag col-{大?lose:中?warn:win}">{大/中/小}</span></td>
</tr>
</table>
</div>

<h2>竞争壁垒</h2>
<div class="tbl-wrap">
<table>
<tr><th>壁垒类型</th><th>强度</th><th>可持续性</th><th>具体表现</th></tr>
<tr>
  <td>{壁垒}</td>
  <td><span class="col-tag col-{强?win:中?warn:lose}">{强/中/弱}</span></td>
  <td><span class="col-tag col-{长?win:中?warn:lose}">{长/中/短}</span></td>
  <td>{说明}</td>
</tr>
</table>
</div>

<div class="summary-box">
  <strong>定价权测试</strong><br>
  🔹 龙头能涨价吗？<span class="col-tag col-{能?win:lose}">{能/不能}</span> 理由：{说明}<br>
  🔹 毛利率趋势：{稳定/上升/下降}<br>
  🔹 ROE趋势：{稳定/上升/下降}
</div>

<h2>驱动力拆解</h2>
<div class="highlight-box">
  <strong>行业收入公式</strong><br>
  收入 = {量因子} × {价因子}<br><br>
  当前组合：<span style="color:{量↑?#2e7d32:#c62828};font-weight:700">量 {↑/↓}</span> ＋ <span style="color:{价↑?#2e7d32:#c62828};font-weight:700">价 {↑/↓}</span> ＝ <span class="col-tag col-{warn/win/lose}">{量价齐升/以价换量/涨价撑收入/量价齐跌}</span>
</div>

<div class="tbl-wrap">
<table>
<tr><th>驱动因子</th><th>最新值</th><th>历史区间</th><th>当前分位</th></tr>
<tr>
  <td>{因子}</td>
  <td><span class="col-tag col-{高?win:低?lose:warn}">{值}</span></td>
  <td>{低-高}</td>
  <td><span class="col-tag col-{高?win:低?lose:warn}">{N}%</span></td>
</tr>
</table>
</div>

<h2>成本结构</h2>
<div class="summary-box">
  🔹 <strong>类型：</strong><span class="col-tag col-{重?lose:info}">{重资产/轻资产}</span>{补充}<br>
  🔹 <strong>成本敏感性：</strong>{说明}<br>
  🔹 <strong>盈亏平衡点：</strong>{说明}
</div>

<h2>竞争格局总结</h2>
<div class="highlight-box">
  {这个行业谁在赚钱、靠什么赚钱、龙头的护城河能维持多久}
</div>

</div>
</div>

<!-- ═══════════════════════════════════════════════════
     L10 Tab
     ═══════════════════════════════════════════════════ -->
<div class="tab-content" id="tab-l10">
<div class="tab-inner">

<h2>周期位置</h2>
<div class="tbl-wrap">
<table>
<tr><th style="width:25%">维度</th><th>判断</th></tr>
<tr>
  <td>库存周期阶段</td>
  <td><span class="col-tag col-{复苏/繁荣?win:win:lose}">{复苏/繁荣/衰退/萧条}</span>{补充}</td>
</tr>
<tr>
  <td>产能利用率</td>
  <td><span class="col-tag col-{高?win:低?lose:warn}">{N}%</span>（历史区间：{N}-{N}%）</td>
</tr>
<tr>
  <td>产品/服务价格分位</td>
  <td><span class="col-tag col-{高?win:低?lose:warn}">{N}%</span></td>
</tr>
<tr>
  <td>行业盈利状态</td>
  <td><span class="col-tag col-{盈利?win:亏损?lose:warn}">{状态}</span></td>
</tr>
</table>
</div>

<div class="danger-box">
  <strong>⚠ PE悖论检查</strong><br>
  当前行业PE：{N}x ｜ PB：{N}x<br>
  PE分位：{N}% ｜ PB分位：{N}%<br>
  {提示}
</div>

<h2>估值水平</h2>
<div class="tbl-wrap">
<table>
<tr><th>估值指标</th><th>行业当前</th><th>历史中位数</th><th>80%分位</th><th>20%分位</th></tr>
<tr>
  <td><strong>PE</strong></td>
  <td><span class="col-tag col-{低?lose:中?warn:win}">{N}</span></td>
  <td>{N}</td><td>{N}</td><td>{N}</td>
</tr>
<tr>
  <td><strong>PB</strong></td>
  <td><span class="col-tag col-{低?lose:中?warn:win}">{N}</span></td>
  <td>{N}</td><td>{N}</td><td>{N}</td>
</tr>
</table>
</div>

<h2>政策环境</h2>
<div class="summary-box">
  🔹 <strong>政策方向：</strong><span class="col-tag col-{利好?win:利空?lose:warn}">{利好/中性/利空}</span><br>
  🔹 <strong>关键政策：</strong><br>
  &emsp;• {政策1}<br>
  &emsp;• {政策2}<br>
  🔹 <strong>政策周期位置：</strong><span class="col-tag col-{宽松?win:收紧?lose:warn}">{宽松期/中性期/收紧期}</span>
</div>

<h2>买入清单</h2>
<div class="tbl-wrap">
<table>
<tr><th style="width:28%">条件</th><th style="width:16%">结果</th><th>备注</th></tr>
<tr>
  <td>周期位置：不在繁荣顶点</td>
  <td style="text-align:center"><span class="col-tag col-{满足?win:不满足?lose:warn}">{✅/❌/⚠️}</span></td>
  <td>{说明}</td>
</tr>
<tr>
  <td>估值：PB/PE在历史偏低分位</td>
  <td style="text-align:center"><span class="col-tag col-win">✅</span></td>
  <td>{说明}</td>
</tr>
<tr>
  <td>政策：不是收紧期</td>
  <td style="text-align:center"><span class="col-tag col-{满足?win:lose}">{✅/❌}</span></td>
  <td>{说明}</td>
</tr>
<tr>
  <td>格局：龙头壁垒稳固</td>
  <td style="text-align:center"><span class="col-tag col-{满足?win:warn}">{✅/⚠️}</span></td>
  <td>{说明}</td>
</tr>
<tr>
  <td>增长：有可见驱动力</td>
  <td style="text-align:center"><span class="col-tag col-win">✅</span></td>
  <td>{说明}</td>
</tr>
</table>
</div>

<div class="highlight-box">
  <div style="font-size:16px;font-weight:700;margin-bottom:8px">综合判断：<span class="col-tag col-{买入?win:等待?warn:lose}" style="font-size:15px">{可以买入 / 等待 / 回避}</span></div>
  <div style="margin-bottom:6px">{一句话总结}</div>
  <table style="font-size:12px;margin:6px 0;border:none;background:transparent">
    <tr><td style="border:none;padding:3px 6px;background:transparent;width:90px;font-weight:600">预期回报</td><td style="border:none;padding:3px 6px;background:transparent">{估值修复/业绩增长/股息}</td></tr>
    <tr><td style="border:none;padding:3px 6px;background:transparent;font-weight:600">仓位建议</td><td style="border:none;padding:3px 6px;background:transparent"><span class="col-tag col-warn">{建议}</span></td></tr>
    <tr><td style="border:none;padding:3px 6px;background:transparent;font-weight:600">跟踪指标</td><td style="border:none;padding:3px 6px;background:transparent">{指标}</td></tr>
  </table>
  <div style="margin-top:8px;padding:8px;background:#e8f5e9;border-radius:4px;font-size:12px">
    <strong>买入策略：</strong><br>
    <span class="col-tag col-win">{类别}</span>：{策略}<br>
    <span class="col-tag col-win">{类别}</span>：{策略}
  </div>
</div>

<h2>卖出信号</h2>
<div class="danger-box">
  <strong>出现以下信号考虑卖出：</strong><br>
  <div style="margin-top:6px">
    <span style="display:inline-block;background:#ffebee;border-radius:50%;width:20px;height:20px;text-align:center;line-height:20px;color:#c62828;font-weight:700;margin-right:6px">1</span>
    {卖出信号1}<br>
    <span style="display:inline-block;background:#ffebee;border-radius:50%;width:20px;height:20px;text-align:center;line-height:20px;color:#c62828;font-weight:700;margin-right:6px;margin-top:4px">2</span>
    {卖出信号2}<br>
    <span style="display:inline-block;background:#ffebee;border-radius:50%;width:20px;height:20px;text-align:center;line-height:20px;color:#c62828;font-weight:700;margin-right:6px;margin-top:4px">3</span>
    {卖出信号3}<br>
    <span style="display:inline-block;background:#ffebee;border-radius:50%;width:20px;height:20px;text-align:center;line-height:20px;color:#c62828;font-weight:700;margin-right:6px;margin-top:4px">4</span>
    {卖出信号4}
  </div>
</div>

</div>
</div>

<div class="footer">Generated by Industry Analysis · L7-L10 Framework · Stock Selection</div>

</div>

<script>
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
</script>
</body>
</html>
```

> ⚠ 如果用户只给了行业名没给市场，默认A股。如果行业太大（>200只），收紧阈值或优先用ASX 300/A股沪深300成分股作为筛选起点。
>
> ⚠ 生成报告时严格按照上方的CSS和HTML结构，保持`col-tag`彩色标签、`tbl-wrap`圆角表格、`bar-wrap`进度条、卡片式产业链、编号卖出信号等样式的一致性。实际模板变量用花括号`{变量}`标记，生成时替换为具体内容。

## 参考文档

- `materials/L7-screening.md` — L7六道筛子完整说明
- `materials/L8-industry-profile.md` — L8行业画像与产业链
- `materials/L9-competition-drivers.md` — L9竞争格局与驱动力
- `materials/L10-cycle-policy-timing.md` — L10周期政策与时机
- `notes/N7-screening.md` — 实战案例：A股光伏行业109→10的全流程
- `stock-learning/stocks-analysis/A股行业全景图.md` — A股行业分布
- `stock-learning/stocks-analysis/ASX行业全景图.md` — ASX行业分布
- `stocks-analysis/行业报告/{市场}——{行业名}——行业分析报告.html` — 行业分析报告
- `stocks-analysis/行业报告/{市场}——{行业名}——{股票简称}_{代码}_分析报告.html` — L1-L6个股报告
