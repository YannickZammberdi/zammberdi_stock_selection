# 个股自动更新

- 名单：根目录 `watchlist.json`，初始为药明康德、福斯特、宁德时代，池外报告不更新。
- 每天悉尼时间 08:30 检查（自动适配 AEST/AEDT），另可手动运行 Actions「自动检查财报并更新个股」。GitHub 可能延迟定时任务。两个UTC定时入口中，仅当前时区对应的入口会继续检查。
- 仅在实际披露日早于今天、且最新财报期超过已覆盖期时调用模型；覆盖年报、中报、Q1、Q3四类正式财报。
- 不只检查昨天：漏跑后会补查，但同一家公司只更新到最新一期，不逐期补写。
- 默认 `opencode/deepseek-v4.1-flash-free`；免费模型失败、超时或产物未通过基础校验时，用官方 `deepseek/deepseek-flash` 重新生成。需配置仓库 secret `DEEPSEEK_API_KEY`（官方调用收费）；主模型可使用已有 `ZEN_API_KEY`。每个模型每份最多运行30分钟。无更新时不安装模型、不产生提交。
- 每个悉尼自然日最多尝试5份（失败也计数；同份的备用模型重试仍算一份），通过 `docs/history/auto_updates.json` 持久记录；剩余任务下次检查继续。
- 模型在临时克隆中运行，只取回指定HTML。通过基础结构校验后才写入正式报告，并运行 `sync_ghpages.py`、提交推送。
- 基础校验不是财务真实性审计；生成报告仍可能出错，请定期抽查。失败不推进覆盖期，下次检查会重试。
- 首次运行会补更池内已有的新财报。`covered_period` 是现有报告已纳入的财报截止期，不是分析日期；新增股票请如实填写（尚无报告用空字符串）。
- 手动更新报告时可保留 `<!-- COVERAGE period=YYYY-MM-DD -->` 标记并更新为真实覆盖期，避免重复自动生成。
- 定时任务须将 workflow 推送到默认分支后生效；公共仓库长期无活动时 GitHub 可能暂停定时任务。

本地只读检查：

Windows若缺少IANA时区数据库，先安装 `pip install tzdata`（GitHub Ubuntu runner自带）。

```sh
python scripts/auto_update_stocks.py
python -m unittest discover -s scripts -p 'test_auto_update_stocks.py'
```

`--run` 会调用模型、提交并推送，仅用于有Git写权限的CI环境。
