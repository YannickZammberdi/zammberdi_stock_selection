# 个股自动更新

- 名单：根目录 `watchlist.json`，初始为药明康德、福斯特、宁德时代，池外报告不更新。
- 每天悉尼时间 08:30 检查（自动适配 AEST/AEDT），另可手动运行 Actions「自动检查财报并更新个股」。GitHub 可能延迟定时任务。两个UTC定时入口中，仅当前时区对应的入口会继续检查。
- 仅在实际披露日早于今天、且最新财报期超过已覆盖期时调用模型；覆盖年报、中报、Q1、Q3四类正式财报。
- 不只检查昨天：漏跑后会补查，但同一家公司只更新到最新一期，不逐期补写。
- 默认 `opencode/deepseek-v4.1-flash-free`（用已有 `ZEN_API_KEY`）。单份最多运行10分钟（`MODEL_TIMEOUT_SECONDS`）。免费模型超时/报错/产物未过校验时：当天还没用过付费备用就用 `deepseek/deepseek-flash` 重跑一次（记录 `paid_fallback`），否则只用免费模型再重试一次。付费备用每天最多 `fallback_daily_limit` 次（默认1），用完就等下次检查。无更新时不安装模型、不产生提交。
- 每个悉尼自然日最多尝试5份（失败也计数），通过 `docs/history/auto_updates.json` 持久记录；剩余任务下次检查继续。手动运行（Actions 里点 Run workflow，可填 `force_code` 强制重跑某只）不受每日上限约束，单次仍最多5份。

## 三段式流水线

`plan`（只检查，不调用模型）→ `update`（每只股票一个矩阵 job）→ `publish`（统一校验、写盘、同步索引、推送）。

- 每只股票独立 job：一只失败不影响其他，日志分开，可在 Actions 里单独重跑某一只；矩阵按 `max-parallel: 1` 顺序执行，保证付费备用额度在 job 之间可被可靠读取。
- 模型在临时克隆中运行（opencode 按 `$PWD` 定位工作目录，脚本已将其指向克隆），只取回指定HTML，产物作为 artifact 上传。
- **每份报告校验通过后立即提交推送**；索引同步或后续推送失败也不会丢已完成的报告，下次检查看到 `COVERAGE` 标记就会跳过，不会重新生成。
- 发布阶段失败时，直接点该次运行的 **Re-run failed jobs**：只重跑 `publish`，复用已上传的 artifact，不再调用模型。
- 基础校验不是财务真实性审计；生成报告仍可能出错，请定期抽查。失败不推进覆盖期，下次检查会重试。
- 首次运行会补更池内已有的新财报。`covered_period` 是现有报告已纳入的财报截止期，不是分析日期；新增股票请如实填写（尚无报告用空字符串）。
- 手动更新报告时可保留 `<!-- COVERAGE period=YYYY-MM-DD -->` 标记并更新为真实覆盖期，避免重复自动生成。标记空格格式异常时脚本会自动规范化；报告正文已写明同一财报期时也会自动补写该标记。
- 定时任务须将 workflow 推送到默认分支后生效；公共仓库长期无活动时 GitHub 可能暂停定时任务。

本地操作：

Windows 若缺少 IANA 时区数据库，先安装 `pip install tzdata`（GitHub Ubuntu runner 自带）。

```sh
python scripts/auto_update_stocks.py --plan                 # 只检查
python scripts/auto_update_stocks.py --generate-only --code 603806 --outdir results   # 需 REPORT_PERIOD/REPORT_PUBLISHED
python scripts/auto_update_stocks.py --publish results      # 需有 Git 写权限
python -m unittest discover -s scripts -p 'test_*.py'
```

## 邮件通知（暂时暂停）

邮件发送功能暂时停用，不影响定时检查、模型生成、同步索引或推送。相关脚本保留，之后可恢复。
