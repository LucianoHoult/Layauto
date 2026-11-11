# W012 A2 最小实施执行记录

独立执行 session，2026-11-11（Asia/Shanghai）。执行者 `/root`。

从干净 `/workspace/Layauto` 的 `work@2489b4609ae97d8211bf450d55cac9392492ac71` 开始，实际 ls-remote 核对 main 为该完整 SHA、实施分支为 `0213c346ac03b7b7282aae522c299155958ac8f6`。显式 fetch 后以 `--no-track` 恢复原实施分支；narrow refspec 导致首次 tracking ref 缺失、第二次自动 tracking 设置失败，均未变更源码或历史。PM 最新阶段明确为“可执行：A2两encoder最小私有typed pack，AI1–AI6”，方案父级 `71488d6034b40cb67970466b082298a8dc0d5eee`。只在此核验后开始产品修改。

已读根 AGENTS、README、协作规则、环境 local-setup/remote-development、current-work 与文档导航；目标树仅根 AGENTS。已读 W012 PM6、AI1–AI6、实施 prompt、A2 plan/independent-review/delivery/PM report/technical-check/receipt。已读架构 §2.2–2.3、§2.6、§3.7–3.8、§11.2/11.9/11.15 原文与实际两 codec、domain freeze/canonical/closed、lower codec 的 pack/unpack/encode/decode、W010/W011 builder/Result、W009 单次快照与 W011 异常历史合同。未重开 AP1–AP5 或泛化 writer 设计。

使用 cloud-environment-runtime 技能；本轮环境 ID `ccarenv_b64_Y2NhcmVudl81ZjI5Nzk0YzYxYzQ4MTkxYmExZmI2MzJiOTE3YTNkMQ`。ready 后观测 running、observations_current=true、network_policy=enforced；读取本机 network-policy，VPN=false。测量使用既有 `/workspace/.venvs/layauto/bin/python` 3.12.14，不将原环境旧测值当本轮 before。

唯一产品候选：两 codec 各新增 `_pack_for_encode`，逐字段使用原 `_SPEC`、原 delegate 次序与完整返回 bytes。原图 closed 检查在复制前，map/scalar 原位置 freeze、tuple 立即按序物化，操作自建 dict/tuple 交未变 canonical 完整冻结。仅切换 encode envelope 的调用；旧 `_pack`、decoder、constructor、两次认证、`_evaluate`、domain/lower codec 不变。未引入参考附件上限或 runtime 附件依赖。

协作：正式新增测试 `/root/formal_tests`、测量工具 `/root/measurement`、工程准备 `/root/engineering_prep` 各独立 detached worktree；集成负责人 `/root`。独立 reviewer `/root/independent_review` 未参与实现、正式测试或测量工具设计，先复核受影响方案一致性；初步无 blocker，最终结论由 reviewer 自写。

初次开发 typing 探针实际失败：`/workspace/.venvs/layauto/bin/python -m mypy` exit1，输出 `No module named mypy`。未声称 typing 通过；完整工程是否继续以有限筛选为门，工程准备在另外环境，不改变测量依赖。

W009 既有单次快照检查实际执行：`PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/layauto/bin/python -m pytest -p no:cacheprovider tests/contracts/test_w009_captured_decode_exceptions.py::test_public_collections_validate_and_store_one_snapshot -q`，exit0，8 passed in 0.30s。首次结果由工具返回保存于 session；后续正式开发回执另存，不将该事实冒记为双全量。

开发补记：两侧 source/test/config 冻结在 [freeze-screen](freeze-screen/freeze.json)，before 为本机 A1 main 的263项、after为候选提交 `c0a9a2e4c292255202a0ec82b6277cd8a8dd6b78` 的264项。两个 runtime 与新增82项正式测试以该提交绑定；全部原正式文件不变。新增测试在主树3.12和独立3.10均实际82 passed，双开发 typing 均54源文件通过，原输出见 development/。这些只是开发检查，不冒记最终矩阵。

首轮无路径 collection 实际收集1742项，比原正式范围额外包含3个 fixture_support unittest 和1个历史 gate-demo；输出和 collection-delta 保留。随后按原 A1 正式全量范围 `tests/unit tests/contracts` 实际收集1738项（原1656+新增82），原1656个 node ID 全保留；没有将 collection 当测试通过，也未执行历史gate演示。

本轮独立 reviewer 发现交付工具必须项 A2-I-R01：初版 delivery checker 会在统一 wrapper 完成前 hash 自身 command/stdout，导致输出清单过时。原源保留为 `delivery_check-before-I-R01.py.txt`，原 scope-selfcheck 与 reviewer 反例保留。修正只明确排除并列出本次 result 和显式传入的 command/stdout/stderr 四个生成输出，最终由 Git 与独立完成后检查绑定，其他材料照常核 hash。独立 reviewer 已在隔离树运行完整修后 checker 并复核关闭；其原 finding/复现/关闭结论归独立报告。`scope-r01-fixed` 仅为修正自检快照，当时受影响回归仍在写其他输出；不能冒作最终封存。产品/正式测试/配置/性能工具均未变化。

受影响开发回归实际完成：`test_w011_exceptions.py` 53项、`test_w011_contracts.py` 44项、`test_w010_contracts.py` 80项及 W009 单次集合快照8项，共185 passed，pytest报告2269.37s，外层命令exit0/2269.814s，stderr为空。完整命令、实际相关源身份和原输出见 [affected-r1](development/affected-r1.command.json)。该范围包含 W011 预期错误后二次认证、nested Parameter/W007–W010故障、公开全记录重建/拒绝、来源/five-owner、typed equality/alias、W010字段/tag/跨hashseed与W009 ChangingList；不是最终双全量。该命令在新增测试集成前启动，执行的是明确列出的原文件；两runtime及这些被执行测试全程字节未变。新增82项另有双版本实际结果；筛选前264项已完整冻结。

首轮完整筛选真实失败（工具问题，产品未改）：本机 A1 before-normal-direct 已完成 W011 build64.421749s、encode3.270342s、decode85.335197s及恢复值全字段相等，之后新 probe 的 `ref.uri.endswith('/target.cdl')` 断言拒绝合法原字面 URI `target.cdl`。这是新增工具错误，不是产品异常；原 `performance/`、`development/performance-r1.*` 和冻结 `freeze-screen/` 原位保留，outer exit1。尚无成功 result JSON 或 wire 产物，所以不能把该次当成功 before 或复用为最终样本。输入 URI/原捕获/产品源码均保持，修正应核对完整 source/target preservation 与 parsed.completed 中原 EvidenceRecord，不能改 URI 迁就工具。工具作者轻量定位的首次 AttributeError 诊断及成功复查也保留于工具失败附件。独立 reviewer 将记录/复核本必须项 A2-I-R02；修后工具先自检和复核，再用新工具冻结、新 attempt 目录重跑全部六条，不覆盖原失败。

A2-I-R02 修后独立复核已关闭：实际正常/mismatch W005/W007完整 preservation 与原 completed 记录相等、相对 URI 保持、exact-class 交换来源负例拒绝及失败汇总/防覆写自检通过；独立 reviewer 又核新冻结 [freeze-screen-attempt02](freeze-screen-attempt02/freeze.json)，263/264项源码/测试/配置、35/五overlay输入、RunRequest与环境完全等于首冻结，只有probe/selfcheck/analyze三个工具hash变化，common/prepare/run不变。实际重试用全新 `performance-attempt02/` 和 `/workspace/work/w012-a2/wires-attempt02/`，全部六条fresh重跑；原失败不复用。跨attempt失败清单明确纳入原 `performance/`。原 finding、失败及独立关闭证据仍由 reviewer 保留。

完整 attempt02 六条 r1 及分析均实际 exit0，原命令/各次、全长 wire 比较和失败汇总保留。direct 总耗时改善6.0816%、readback退化24.1757%、mismatch改善3.6378%，峰值只改善0.4789/0.2605/0.0245%，wire减幅0。另direct decode +19.12%、mismatch W011 build +19.80%，所有退化原值保留。执行者按AI4推荐停止当前候选：没有显示值得继续的稳定净收益，不推荐进入最终工程/产品验收。具体见 performance-analysis.md；独立 reviewer 实核后自写其结论。最终双全量/构建/双干净安装源码外smoke、每侧3次性能矩阵均未启动，不能冒称最终工程或A2产品交付完成。源码/正式测试/配置仍为c0a9，未扩大owner或启动下一节点。
