# W006 IPMR-01 局部补修独立复核

2026-11-02；reviewer：`/root/ipmr01_fix_review`。未参与本轮产品或回归实现；只写本报告、独立复核证据与任务 reviewer 追加记录，不代写 PM 验收。

**IPMR-01 在 `f19ac0448a5d0111f799660bd7be043ebfd16e41` 上经独立复核关闭，剩余必须修正项 0。** 原 stage failure 与二次 ToolRun 冻结诊断分别保留；未发布状态、内存证据与原中断传播保持。结论仅覆盖 PM2 授权的局部补修及其相关边界，交 PM 重新接收，不表示 W006 已验收、main 已集成或完整 M1 通过。

## 身份与方法

| 项目 | 本次实际检查 |
| --- | --- |
| 仓库 / 分支 | `/workspace/Layauto`；`codex/w006-precontext-run-audit` |
| 补修 base | PM2 交接 `e8fec97b918938a5b431eb8ad38c2d63ed67e9d2` |
| 补修产品 / 回归 head | `f19ac0448a5d0111f799660bd7be043ebfd16e41` |
| 原问题身份 | [独立合并前报告](independent-premerge-review.md#ipmr-01)及[原复现](independent-premerge-verification/double_exception.py)保留；原产品 `cc42ae62585755b0b914d4dbec43324941bfe7c6`，review 交付 `ccd157fe1a3dee4267d4f0b119a4eda53cfdcf9f` |
| 实际产品 diff | `pipeline.py` 一个异常分支增加条件保护；新增 `tests/contracts/test_w006_ipmr01.py`，16 个参数化用例。没有 schema、输入定义、fixture、答案或旧测试修改 |
| 启动工作区 | 产品和测试已提交；执行者的 `ipmr01-verification/` 尚未跟踪，属并行生成证据，未覆盖其内容。仅根 AGENTS 适用 |

已读 AGENTS、README、协作与环境文档、W006 行为 7/A7、PM2、原 finding/复现和 interface-plan；对照 architecture §2.7/§11.13 及 W003 failure/shared-record 原合同，先审实际控制流，再运行原反例和必要独立探针，最后核对执行工程证据。未凭执行者“通过”摘要自行关闭。

## Finding 关闭判断

| 检查 | 独立结论 |
| --- | --- |
| 原 cause chain | `pipeline.py` 第 164–174 行仅在 `failure is None` 时构造冻结错误对应的 StageFailure。已有 parser/acquisition failure 不再被覆盖；传入 `_unavailable` 的 `pending_failure` 保留原 type/message/cause 快照。 |
| 二次诊断 | `_unavailable` 的 `operation/message/causes` 仍由此次 freeze 异常产生，与 `pending_failure` 分列；不把第二层原因藏进原 message，也不重新读取原异常来改写已冻结快照。 |
| 首次故障就是 freeze | 没有原 failure 时仍构造 InternalStageFailure；成功 Parse 的 sources/completed 与 pending parse 保留，没有把这种情况错误当作已有 parser failure。空消息、surrogate、坏 `__str__` 仍使用既有安全格式化。 |
| 已捕获 facts 与发布状态 | 实际 sources 的 bytes/hash、read events、completed evidence/backlinks 均保留。ToolRun 本身构造失败时 `pending_tool=None`，不伪造 audit refs、checkpoint、RunRecord、closure 或 terminal；attempt 保持 unsealed revision 0。没有改走 repository 的 `run_record_freeze_failure` 专门分支。 |
| 原中断 | 既有 finally 在诊断前固定原 KeyboardInterrupt/SystemExit，补修未改变此保护。新增与旧回归覆盖 parser/read 两处中断以及诊断坏消息，原对象继续传播。 |

原 `double_exception.py` 本次返回 exit **0**：`pending_failure.causes` 为 RuntimeError→LookupError；顶层 `causes` 为 secondary ValueError，仍有 27 个 sources、8 个 completed evidence，checkpoint/terminal 均为 None。[实际输出](ipmr01-verification/reviewer/original-repro.txt)与[命令记录](ipmr01-verification/reviewer/original-repro.result.json)绑定修复提交。

另外独立构造的[诊断快照探针](ipmr01-verification/reviewer/diagnostic_snapshot_probe.py)覆盖 parser/read 两处：先产生带 cause 的 stage Exception；freeze 时改变原异常消息对象，让二次异常的 `__str__` 抛 KeyboardInterrupt，并让诊断 readback 抛 OSError。两种情况下原 cause 快照仍为首次捕获文本，二次错误安全显示为 `<unprintable exception>`，返回 PublicationUnavailable 且无虚构发布；可进行 wire roundtrip。[两组结果](ipmr01-verification/reviewer/diagnostic-snapshot.txt)均通过。这是本次 reviewer 自行增加的组合检查，未改产品或 fixture。

**处置：IPMR-01 关闭；无新增必须修正项或后置建议。** 原 finding、原失败输出及 PM2 记录保留，不用新结论覆盖其历史事实。

## Reviewer 亲自运行与核验

环境：Linux x86_64，CPython 3.12.14；`/workspace/.venvs/layauto/bin/python`，复用 checkout editable venv，导入受审源码。以下 cwd 均为 `/workspace/Layauto`；`PY` 指该解释器。逐命令 cwd/head/退出码及日志 hash 见 [identity.json](ipmr01-verification/reviewer/identity.json)。

| 命令 / 核验 | 实际结果 |
| --- | --- |
| `$PY -B docs/tasks/W006/independent-premerge-verification/double_exception.py` | exit 0；原反例转为合同预期 |
| `$PY -B -m pytest -p no:cacheprovider tests/contracts/test_w006_ipmr01.py tests/contracts/test_w006_review_regressions.py -q` | **33 passed，22.29s，exit 0**；[日志](ipmr01-verification/reviewer/targeted-tests.txt) |
| `$PY -B docs/tasks/W006/ipmr01-verification/reviewer/diagnostic_snapshot_probe.py` | parser/read 两组独立组合通过，exit 0 |
| `$PY -B docs/tasks/W006/ipmr01-verification/reviewer/package_identity_probe.py /workspace/work/w006-ipmr01/engineering/dist` | 先核对初始 216 项；补齐测试样张依赖后再次核对 **217** 项 snapshot/Git/工作区 bytes 一致。新 wheel 与 sdist 各 **74** 个产品文件均与提交相同，含 py.typed；wheel 无 tests/legacy/docs runtime。[最终直接核验](ipmr01-verification/reviewer/package-identity-final.txt) |
| 工程日志与保护路径身份 | **47** 项工程证据 hash、**19** 项主线程执行证据 hash、**29** 份命令输出 hash、**4** 项关键产品/测试/配置/原复现身份相符。架构、fixture/support、原 finding/复现、domain/repository/tooling/importers 相对 PM2 未改。E5 和[执行回执](ipmr01-verification/receipt.json)的表述与实际证据一致，无须更正。 |

本次 reviewer **直接读取了本次新构建包的实际 bytes**；不是采用旧 ca513… wheel 证明修复。新 wheel SHA-256：`8b71ed7438c1c95e1987d13d08c4dce23d21fc80e91d86a339d260b83ef5e064`；新 sdist：`31dc9826729e5488c867bb3451dd62c8b234663b461a958c30afc884aa033d63`。包是临时运行产物，跨实例不保证本地路径仍在；随 Git 保存的清单、日志和脚本固定了本次身份与可重建方式。

## 核对并采用的本次执行证据

下列由执行者或工程专项运行；本 reviewer 检查方法、命令、环境、版本和结果，不记为 reviewer 亲自重跑。

| 证据 | 采用结论 |
| --- | --- |
| [3.12 全套](ipmr01-verification/pytest312.txt)、[typing](ipmr01-verification/mypy312.txt) | f19ac04 的 **405 passed，134.53s**；strict typing 21 source files 无错误。覆盖 W005 原读取回归、正常/F2及新旧 W006 错误组合。 |
| [3.10 首轮](ipmr01-verification/engineering/pytest310.txt)、[样张补入后的定向复跑](ipmr01-verification/engineering/pytest310-f1-retest.txt)、[typing](ipmr01-verification/engineering/mypy310.txt) | CPython 3.10.22：首轮 121 项中 **120 passed / 1 failed**，失败原因是独立 snapshot 漏导出 F1 测试依赖 `docs/tasks/W003/examples/records.json`。从同一 f19 提交补入原 bytes 后，该项 **1 passed**；合计 121 个不同受影响用例通过，**不是一次 121 项全绿**。产品、测试、fixture 未变化；21 模块 typing 通过。 |
| [工程回执](ipmr01-verification/engineering/engineering-receipt.json)、[构建](ipmr01-verification/engineering/build.txt)、[安装](ipmr01-verification/engineering/wheel-install.txt) | 最终源码独立 snapshot 构建 sdist→wheel，全新 3.12 venv 安装并 pip check 通过。F1 样张补入只修测试环境，包内 74 项产品身份不变，无需据此重建包。初始与补齐后 manifest、失败日志都保留。 |
| [源码外正常/F2 smoke](ipmr01-verification/engineering/wheel-normal-f2-smoke.txt)、[IPMR-01 smoke](ipmr01-verification/engineering/wheel-ipmr01-smoke.txt) | `-I` 下导入来自新 venv 的 site-packages。正常仍为 unsealed InputsReady；真实 F2 为 MissingTerminator→reject；parser/acquisition 双异常均保留两层原因、捕获证据且无 terminal。 |

3.10 样张遗漏在本次工程验证内已纠正；执行记录明确保留首轮失败和补跑范围，没有更改 fixture/答案、放宽断言或将原始 exit 1 改写成 exit 0。原双解释器 389 项和旧 wheel 只保留旧版本事实，不作为新修复证据。

## 复核边界

本 reviewer 未重跑 3.12 全套、3.10 测试/typing、构建/安装或 wheel smoke，按上表采用本次执行证据并直接核对新包内容。未执行 Python 3.10 干净 wheel 安装、其他平台/解释器、真实 EDA/PDK/生产、fixture 生成、legacy、durable/跨进程恢复或 Stage 2–6 完整组合。局部修复不新增这些承诺，也不改变正常输入仅 unsealed 交接的边界。

IPMR-01 已达到 PM2 的独立关闭条件，**剩余必须修正项 0**。后续由 PM 核对本修复及文档交付版本，决定重新接收、集成与最终验收；本 reviewer 不合并 main、不修改 PM 段或当前入口、不启动下一任务。
