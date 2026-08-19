---
name: gh-pages-sync
description: 将股票分析报告同步到docs目录并更新GitHub Pages表格索引，包括复制新文件、删除无对应源文件的旧文件、更新index.html的数据
---

# GitHub Pages 同步

## 用途

将 `stock-learning/stocks-analysis/` 下新生成/更新的报告同步到 `docs/`（GitHub Pages 根目录），并更新各 index.html 的表格数据。遵循**源文件为唯一真实来源**原则：以 `stock-learning/stocks-analysis/` 下实际存在的文件为准，缺乏源文件的旧报告将被清理，不存在的条目将从 index.html 中移除。

## 文件映射

| 源文件位置 | 目标目录 |
|---|---|
| `宏观报告/*.html` | `docs/macro/` |
| `行业报告/A股——*.html` | `docs/industry/` |
| `行业报告/ASX——*.html` | `docs/asx/industry/` |
| `A股/**/*.html` | `docs/stocks/` |
| `ASX/**/*.html` | `docs/asx/stocks/` |
| 交易计划 | 见下方「交易计划市场判断」 |
| `验证/*_C方案验证.html` | `docs/verify/` 或 `docs/asx/verify/`（见「验证市场判断」） |

> 交易计划的源文件位置**不固定**：可能在 `交易计划/` 子目录，也可能直接放在 `stock-learning/stocks-analysis/` 根目录。收集时用以下规则，不依赖路径：

**交易计划识别**：`stock-learning/stocks-analysis/` 下所有匹配 `*_交易计划.html` 的文件（含根目录和 `交易计划/` 子目录）。

**交易计划市场判断**（按优先级）：
1. 从文件名提取代码：取末尾 `_交易计划.html` 前的最后一段，如 `三友化工_600409_交易计划.html` → 代码 `600409`
2. 代码为 **6位纯数字** → A股 → `docs/plans/`
3. 代码含**字母**（如 MQG/CSL/BHP）→ ASX → `docs/asx/plans/`
4. 无法判断时，回退查 `stock-learning/stocks-analysis/index.md` 表格中的代码列归属市场；仍无法判断 → 询问用户，不猜测

**验证识别**：`stock-learning/stocks-analysis/验证/` 下所有匹配 `*_C方案验证.html` 的文件。

**验证市场判断**（与交易计划同规则）：取文件名 `_C方案验证.html` 前的最后一段为代码；代码为 **6位纯数字** → A股 → `docs/verify/`；代码含**字母** → ASX → `docs/asx/verify/`。

## 步骤

### 1. 收集源文件

遍历 `stock-learning/stocks-analysis/`（含根目录），按映射表收集所有 `.html` 文件，构建**源文件清单**（文件名 → 市场/类型）。

> 交易计划收集规则：`*_交易计划.html` 模式匹配，**根目录和 `交易计划/` 子目录都收**。

### 2. 同步副本文件

对每个源文件：
- 如果目标路径文件已存在且内容相同 → 跳过
- 如果目标路径文件不存在或内容不同 → 复制

> 交易计划目标目录按「交易计划市场判断」规则决定（`docs/plans/` 或 `docs/asx/plans/`）。

> 对于 A股 和 ASX 个股报告，复制时**平铺到目标目录**（不保留子目录层级），直接放在 `docs/stocks/` 或 `docs/asx/stocks/` 根目录下。

### 3. 清除无源文件的旧报告

检查 `docs/` 下各目标目录，按**反向映射**逐个比对：对每个目标文件，根据它所在的目标目录反推出应有的源文件位置，若对应源文件不存在则删除。

> 反向映射（目标目录 → 应有的源位置）：
>
> | 目标目录 | 应有的源文件 |
> |---|---|
> | `docs/macro/*.html` | `宏观报告/{同名文件}` |
> | `docs/industry/*.html` | `行业报告/{同名文件}`（文件名以 A股—— 开头） |
> | `docs/asx/industry/*.html` | `行业报告/{同名文件}`（文件名以 ASX—— 开头） |
> | `docs/stocks/*.html` | `A股/**/{同名文件}`（任意子目录） |
> | `docs/asx/stocks/*.html` | `ASX/**/{同名文件}`（任意子目录） |
> | `docs/plans/*.html` | 源为 `*_交易计划.html` 且市场判断为 A股 |
> | `docs/asx/plans/*.html` | 源为 `*_交易计划.html` 且市场判断为 ASX |
> | `docs/verify/*.html` | 源为 `验证/{同名文件}` 且市场判断为 A股 |
> | `docs/asx/verify/*.html` | 源为 `验证/{同名文件}` 且市场判断为 ASX |
>
> 比对前先收集一次源文件完整清单（步骤1的列表），反向匹配时在清单内查找，避免对已删除文件重复判断。
>
> **只删除报告 `.html` 文件，保留 `index.html`。**

> 匹配示例：`docs/stocks/三友化工_600409_分析报告.html` → 反查 `A股/**/` 下是否有同名文件；若 `A股` 下全部子目录都没有 → 删除。

### 4. 更新 index.html

对以下 index.html，用源文件的实际列表重新生成表格数据（`docs/macro/index.html` 为静态卡片，其余为 `const data = [...]` 数组）：

| 文件 | data 字段 | 源文件来源 |
|---|---|---|
| `docs/stocks/index.html` | name, code, type, score, date, file | 从 `A股/**/*.html` 解析 |
| `docs/industry/index.html` | name, type, score, date, file | `行业报告/A股——*.html` |
| `docs/plans/index.html` | name, code, date, status, file | 市场判断为 A股 的交易计划 |
| `docs/macro/index.html` | —（静态卡片） | `宏观报告/*.html` |
| `docs/asx/stocks/index.html` | name, code, type, score, date, file | `ASX/**/*.html` |
| `docs/asx/industry/index.html` | name, type, score, date, file | `行业报告/ASX——*.html` |
| `docs/asx/plans/index.html` | name, code, date, status, file | 市场判断为 ASX 的交易计划 |
| `docs/verify/index.html` | name, code, verdict, score, date, file | 市场判断为 A股 的验证报告 |
| `docs/asx/verify/index.html` | name, code, verdict, score, date, file | 市场判断为 ASX 的验证报告 |

#### 数据解析规则

解析时**优先从 HTML 实际内容提取**，回退才用文件名。具体选择器：

**个股报告**（A股和ASX）：
- 名称/代码：`<title>` 标签，格式 `{名称}({代码}) 分析报告`；回退用文件名 `{名称}_{代码}_分析报告.html`
- 日期：`.meta` 元素中匹配 `YYYY-MM-DD`（如 `分析日期:2026-07-09`）
- 评分：`.verdict` 框内文本或评分表总分行，匹配 `(\d+)/100` 提取数字
- L5分类：`.subtitle` 中 `L5分类:{值}`，或源路径 `{市场}/{分类}/{文件名}` 的目录名；回退从 `stock-learning/stocks-analysis/index.md` 表格查找

**行业报告**：
- 名称：文件名 `A股——{行业名}——行业分析报告.html`（行业名 = 第二个 `——` 之间的部分）
- 日期：`.meta` 元素中匹配 `YYYY-MM-DD`
- 评分：`.verdict` 框内或评分表总分行匹配 `(\d+)/100`
- 市场：文件名前缀 `A股——` / `ASX——`

**交易计划**：
- 名称/代码：`.sub` 或 `<title>`，格式 `{名称}({代码})`；回退用文件名 `{名称}_{代码}_交易计划.html`
- 日期：`.sub` 中匹配 `YYYY-MM-DD`
- 状态：`.sub` 中 `状态:<span class="tag ...">{值}</span>`；无该标记时默认 "计划中"

**C方案验证**：
- 名称/代码：`<title>`，格式 `{名称}({代码}) C方案验证`；回退用文件名 `{名称}_{代码}_C方案验证.html`
- 日期：`.meta` 中 `验证日期:YYYY-MM-DD`（注意报告里源报告日期可能出现更早，必须匹配 `验证日期` 字样，不能取第一个日期）
- 评分：匹配 `(\d+)/10`（10分制）
- 结论：匹配 `verdict-(ok|caution|bad)` 类名 → 言行一致/部分存疑/言行不一致

**宏观报告**：
- 文件名格式：`{市场}_宏观环境报告_{YYYY-MM-DD}.html`，市场/日期从文件名解析
- `docs/macro/index.html` 当前是**静态卡片**结构（非 data 数组）：直接按实际文件替换卡片列表，保持卡片样式与现有文件一致

> 提示：所有报告生成 skill 已在 QC 中约束 `YYYY-MM-DD` 日期格式和 `.meta`/`.sub` 结构，解析依赖这些约定。

#### 生成 data 数组

```javascript
const data = [
  // 按评分降序排列（个股/行业）或按日期降序排列（交易计划）
  {name:"...", code:"...", type:"...", score:..., date:"...", file:"..."},
];
```

> 保持与现有 index.html 中相同的 JavaScript 排序/渲染逻辑不变，只替换 `data` 数组（`docs/macro/index.html` 除外，它是静态卡片，见下方解析规则）。

## 注意事项

- 只操作 `stock-learning/stocks-analysis/` 和 `docs/` 下的文件，不修改其他目录
- 不要修改 index.html 中 `data` 数组以外的 JS/HTML 部分
- 确保 `docs/` 下目标目录存在（若不存在则创建）
- 如果某类报告完全为空，对应 index.html 保留空的 `data: []` 数组
- **市场归属只看源路径，不看文件名**：`A股/**` 归 `docs/stocks/`，`ASX/**` 归 `docs/asx/stocks/`。即使文件名含 ASX 字样，只要在 `A股/**` 下就按 A股 处理
- 交易计划**不依赖子目录路径**，用 `*_交易计划.html` 文件名模式识别，市场按代码格式判断（6位数字→A股，含字母→ASX）
- 验证报告市场判断与交易计划同规则（6位数字→A股，含字母→ASX）
- 对于 ASX 交易计划：如果 `docs/asx/plans/index.html` 当前是静态 "暂无交易计划" 页面，当有 ASX 交易计划需要同步时，参照 `docs/plans/index.html` 的结构改写为带表格的版本
- 验证章节 index（`docs/verify/index.html`、`docs/asx/verify/index.html`）为带 verdict 列的表格（tag-ok/tag-caution/tag-bad），只替换 `data` 数组

## 生成后检查（QC）

同步完成后逐项核对：
- [ ] `docs/` 下的文件数 = 源文件清单数（按映射表口径），无遗漏、无多余
- [ ] 每个目标文件与源文件内容一致（重新 diff 确认）
- [ ] 每个 index.html 的条目（`data` 数组或静态卡片）与 `docs/` 下实际文件一一对应，无死链、无多余条目
- [ ] 被清理的报告已从对应目录和 index.html 中一并移除
- [ ] index.html 中除 `data` 数组/卡片外无其他改动（用 git diff 确认）
- [ ] 若有新增目标目录，确认其已创建且 index.html 已同步生成
- [ ] 交易计划：源在根目录的 `*_交易计划.html`（如 `皖维高新_600063_交易计划.html`）已被收集并同步，未遗漏
