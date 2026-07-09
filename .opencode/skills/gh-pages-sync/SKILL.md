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
| `行业报告/A股——*.html` | `docs/industry/` |
| `行业报告/ASX——*.html` | `docs/asx/industry/` |
| `A股/**/*.html` | `docs/stocks/` |
| `ASX/**/*.html` | `docs/asx/stocks/` |
| `交易计划/**/*.html` | 股票代码6位数字 → `docs/plans/`（A股）/ `docs/asx/plans/`（ASX） |

> 交易计划判断规则：文件路径含 `交易计划/`，若文件名含 ASX 股票代码（字母）则归入 `docs/asx/plans/`，否则归入 `docs/plans/`。

## 步骤

### 1. 收集源文件

遍历 `stock-learning/stocks-analysis/`，按映射表收集所有 `.html` 文件的列表。

### 2. 同步副本文件

对每个源文件：
- 如果目标路径文件已存在且内容相同 → 跳过
- 如果目标路径文件不存在或内容不同 → 复制

> 对于 A股 和 ASX 个股报告，复制时**平铺到目标目录**（不保留子目录层级），直接放在 `docs/stocks/` 或 `docs/asx/stocks/` 根目录下。

### 3. 清除无源文件的旧报告

检查 `docs/` 下各目录（`stocks/`、`industry/`、`plans/` 及 `asx/` 对应子目录），移除在 `stock-learning/stocks-analysis/` 中找不到对应源文件的 `.html` 文件。

> 匹配规则：以文件名（不含路径）为准，在源文件列表中查找相同文件名。

### 4. 更新 index.html

对以下 6 个 index.html，用源文件的实际列表重新生成 `const data = [...]` 数组：

| 文件 | data 字段 | 源文件来源 |
|---|---|---|
| `docs/stocks/index.html` | name, code, type, score, date, file | 从 `A股/**/*.html` 文件名中解析 |
| `docs/industry/index.html` | name, type, score, date, file | `行业报告/A股——*.html` |
| `docs/plans/index.html` | name, code, date, status, file | `交易计划/*.html` A股部分 |
| `docs/asx/stocks/index.html` | name, code, type, score, date, file | `ASX/**/*.html` |
| `docs/asx/industry/index.html` | name, type, score, date, file | `行业报告/ASX——*.html` |
| `docs/asx/plans/index.html` | name, code, date, status, file | `交易计划/*.html` ASX部分 |

#### 数据解析规则

**个股报告**（A股和ASX）：
- 从 HTML 文件内容提取信息：读取 `<title>` 标签，或查找页面中嵌入的元数据（如评分、分类、日期等）
- 回退策略：如果无法从 HTML 解析评分/分类，则从文件名模式解析
- 文件名格式一般为 `{名称}_{代码}_分析报告.html`
- 分类标签：从 HTML 中 class 为 `col-tag` 或 `tag-*` 的元素提取
- 代码：从 `stock-learning/stocks-analysis/index.md` 中的表格查找，或从文件名提取

**行业报告**：
- 文件名格式：`A股——{行业名}——行业分析报告.html` 或 `ASX——{行业名}——行业分析报告.html`
- 从 HTML 文件内容提取评分、分类、日期
- 回退：从 `stock-learning/stocks-analysis/index.md` 表格中查找

**交易计划**：
- 文件名格式：`{名称}_{代码}_交易计划.html`
- 日期：从交易计划 HTML 中提取
- 状态：默认为 "计划中"

#### 生成 data 数组

```javascript
const data = [
  // 按评分降序排列（个股/行业）或按日期降序排列（交易计划）
  {name:"...", code:"...", type:"...", score:..., date:"...", file:"..."},
];
```

> 保持与现有 index.html 中相同的 JavaScript 排序/渲染逻辑不变，只替换 `data` 数组。

## 注意事项

- 只操作 `stock-learning/stocks-analysis/` 和 `docs/` 下的文件，不修改其他目录
- 不要修改 index.html 中 `data` 数组以外的 JS/HTML 部分
- 确保 `docs/` 下目标目录存在（若不存在则创建）
- 如果某类报告完全为空，对应 index.html 保留空的 `data: []` 数组
- ASX 个股报告在 `docs/asx/stocks/` 中用原名即可（注意某些文件名含有 ASX 字样，但路径已经区分了市场）
- 对于 ASX 交易计划：如果 `docs/asx/plans/index.html` 当前是静态 "暂无交易计划" 页面，当有 ASX 交易计划需要同步时，参照 `docs/plans/index.html` 的结构改写为带表格的版本
