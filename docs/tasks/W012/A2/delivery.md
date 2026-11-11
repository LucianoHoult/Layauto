# A2 方案执行交 PM

日期：2026-11-11（Asia/Shanghai）。本次是独立执行 session 的方案交付，不是产品实施或 PM 验收。

## 恢复和交付身份

- 起点 main `2489b4609ae97d8211bf450d55cac9392492ac71`，实际 A1 merge `08dd232139918dc97b0a6d255aad237eb844686a`，受测源码/正式测试冻结 `ca1f810c3c97376f71089d8b4054760ff198012f`。
- 已实际核远端 A2 PM 准备提交 `842c5c1ea8f1d01bb3f04e4703f105e11f94158c` 并恢复原分支 `codex/w012-a2-serialization-plan`，初始工作区干净。
- 方案/有限工具受审提交 `cbf20807a85d8350928fc6a604612384cb2727fd`；原始文件内容及脚本身份见 [check-result.json](check-result.json)，独立review的受审范围及后续复核身份见 [independent-review.md](independent-review.md)。最终提交由Git及交接回复绑定，不给包含自身的交接文本制造循环hash。
- 沿用 `LucianoHoult <LucianoHoult@users.noreply.github.com>` 提交。原主机默认Git身份不是项目noreply，已仅对本仓库设置项目身份。无rebase/force-push/main合并，不创建新子项或公开codec。

## 可直接读取的结果

| AP | 交付与边界 |
| --- | --- |
| AP1 | [plan](plan.md) 的真实after wall/profile及调用链；263项对冻结/merge/PM准备/磁盘实核，9 after样本+profile同源；不相加cumulative、不把exclusive当无插桩可省秒数 |
| AP2 | 只推荐W010/W011两个closed encoder的操作私有typed pack；owner/入口/分支/字段/快照/步骤明确，旧_pack留给decoder；canonical/lower codec不改 |
| AP3 | [reference_pack](reference_pack.py)、[check](check.py)及原输出；完整字节结构归纳、6个小DTO原decoder对照、22个private subvalue及alias/closed/异常/UTF-8有限见证；不替换/monkeypatch完整runtime |
| AP4 | build/decode各路径作用、残余/退化/维护成本及完整未来验证计划；wire降幅0，不设新百分比门槛，不承诺产品/生产收益 |
| AP5 | 未参与方案/工具设计的独立reviewer在隔离worktree复核并保留其finding与结论；以其报告为准。交PM决定是否派发最小实施或回M1，不自动实施 |

## 本次实际检查

有限检查命令：`python3 -B docs/tasks/W012/A2/check.py`，实际解释器为 `/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3`。[命令回执](check.command.json)、[stdout](check.stdout.txt)、[stderr](check.stderr.txt)、[结果](check-result.json)可访问；exit0，无stderr。只用Python标准库及已存在的产品模块，无安装或网络数据依赖，没有测完整Result、微基准或产品收益。

小值调用次数证明被删的是临时序列化构造：SeedLocation freeze263→91、FrozenMap init151→43；ContactComponent290→91、169→41。完整wire相同；这些不是完整build/decode的减幅估计。原公开DTO、完整重建、所有来源/run/owner/bytes、第二次认证与异常历史是未来不可删合同。

交付范围/链接/证据身份检查见 [delivery_check.py](delivery_check.py)、[回执](delivery-check.command.json)、[原输出](delivery-check.stdout.txt)、[结果](delivery-check-result.json)。它只核任务新增执行段和新A2附件；原AP/PM/task文本及其他受保护路径不变，不是新的产品测试。reviewer自己的原探针/命令/结果由其报告定位。

本次runtime/正式测试/配置不变，采信同源A1已验收双1656/typing54/构建/双干净安装，未重复小时级矩阵或18条benchmark，也未声称重读旧约1.47GB wire/安装树。旧报告、工具、finding、输出全部保留；current-work/PM阶段/main均未改。

## 交接停止点

推荐最小兼容方案，产品收益大小未知，由未来同条件完整三路实际字节与无插桩比较决定是否值得集成。完整验证必须固定输入URI/RunRequest/cache/roots/GC；开发先新增/受影响，最终新冻结仍双全量/typing/构建/双干净安装。无法支持成本时交PM回M1网络标注，不自动扩reader/memo/B或删认证。

本轮独立review后仅提交推送原A2方案分支，并实际核远端完整SHA交PM。是否验收本方案、派发产品实施或回M1由PM维护；没有自行启动下一任务、改变公开格式/身份/迁移/架构或合main。
