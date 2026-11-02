# W006 独立最终代码 review

主审：`/root/final_review`，未参与方案或实现。`/root/final_review/repository_review` 独立只读检查 repository/DTO/codec；主审检查 pipeline、acquisition/reader、请求来源与真实文件组合。此报告不是 PM 验收。

## R1 受审身份与范围（2026-11-02）

- 基线：`7320e5d6e819a422e0a446309eb039b1f05e7dd0`。
- 首轮产品/测试版本：`36161ca84f69de589a2733ad94d5c7a41a892cf3`，分支 `codex/w006-precontext-run-audit`。启动时工作区干净。
- 已读根 AGENTS、README、协作规则、current-work、环境文档、W006、接口方案与独立 review；依据 architecture §2.1–2.2/2.6–2.7、§9.2、§11.2/11.4/11.10/11.13/11.15、§12.1/12.6–12.7 及 W003 共享记录/F1/F2、W005 组件合同核对实际 diff。仅根 AGENTS 适用。
- 本轮只写本报告及 `review-verification/`，未修改产品、测试、fixture/答案、PM 状态、current-work；没有提交、合并或执行 EDA。

## R1 必须修正项

以下原 finding 保留；后续修正和关闭依据另记，不能用新增测试数覆盖反例。

| ID | 首轮反例与影响 | 依据及关闭条件 | 首轮状态 |
| --- | --- | --- | --- |
| CR-01 | `reader._Files.path` 每次重新 resolve URI。真实 `source.cdl` symlink 首次读取后改指另一个内容相同文件，header closure 随后重复读取同一 URI。`FixtureCapture.freeze()` 抛裸 `ValueError: duplicate acquisition source URI`；attempt 仍 unsealed，checkpoint/terminal 均无，已捕获审计未交回。脚本：[alias_during_capture.py](review-verification/alias_during_capture.py)，[原结果](review-verification/alias-during-capture-before.txt)。首轮相关位置：reader.py:35–59、pipeline.py:153–154。 | W006 same-bytes/真实获取与 A7；IR-02 的捕获时路径映射。冻结 URI 的第一次解析/捕获路径，后续依赖查重/读取复用同一身份；另保护 ToolRun 构造故障，不能丢掉原中断或已获取 facts。验证解析中途改 symlink，不能只测解析结束后修改。 | 必须修正 |
| CR-02 | 诊断直接 `str(exc)` 并要求 UTF-8。在 parser 抛 `SystemExit(BadMessage)`（`__str__` 再抛）或 `KeyboardInterrupt('\ud800')` 时，`prepare_inputs` 在进入 finally 前构造 StageFailure/causes，分别用 RuntimeError/UnicodeEncodeError 替换原中断。`finalize.freeze` 抛同类坏消息时，也无法进入唯一 freeze-failure closure。脚本：[interrupt_diagnostic.py](review-verification/interrupt_diagnostic.py)、[freeze_diagnostic.py](review-verification/freeze_diagnostic.py)；[原中断结果](review-verification/interrupt-diagnostic-before.txt)、[原冻结结果](review-verification/freeze-diagnostic-before.txt)。首轮位置：pipeline.py:145–151、domain/publication.py:187–199、repository/publication.py:343–348。 | W006 §7/A7 明确 best-effort 诊断不得取代原 KeyboardInterrupt/SystemExit，unexpected failure 保留根因；freeze 构造失败必须保留原故障并走专门 closure。安全快照 exception type/message/causes，处理格式化自身失败与无效 Unicode；原中断保护必须覆盖诊断构造，tooling 与 repository 同样核对。 | 必须修正 |
| CR-03 | `_binding_failure` 对 request 与已读 source 的 URI 使用 `posixpath.normpath`。真实 `link -> external/child` 时，声明 `link/../source.cdl` 实际选择 `external/source.cdl`，产品却仅读取根目录 `source.cdl`，仍返回 InputsReady。此声明 URI 从未被捕获；`..` 跨 symlink 的语义不能用词法折叠替代。脚本：[selection_dotdot.py](review-verification/selection_dotdot.py)，[原结果](review-verification/selection-dotdot-before.txt)。首轮位置：pipeline.py:45–50。 | W006 A2 的完整声明独立绑定及 IR-02 的“未捕获别名不能凭碰巧相等获准”。基于捕获时精确 URI/path 映射核验；未读别名可保守 UnreadSelection，不允许事后 resolve 或 `normpath` 为其制造读取事实。 | 必须修正 |

三项均在原授权实现范围内，无新增用户预期或额外审批要求。

## R1 已核对的成立部分

- create attempt 在 acquisition/parser 前，缺失/坏 site 也有运行身份；create 失败不继续 IO。
- F1 caller 独立从实际输入选择构造 27 项，产品不读取 sample records/oracle；四个 optional cache 是后发现的审计事实。真实 F2 使用匹配坏 header/raw，MissingTerminator 未被提前 hash drift 代替。
- coroutine 把 tooling 返回的 SourceFile 交回 importer；Parse 单向关联 ToolRun，tool 仅描述 fixture 读取。正常出口仅 unsealed InputsReady，无成功 terminal、baseline 或 canonical context。
- repository 单锁/不可变 composite root 统一管理 content、attempt pointer 与幂等；重放检查先于 revision/phase guard。失败 checkpoint 固定 finalize 请求，terminal 发布失败重试不重新获取输入。
- 既有 schema/codecs、run/ref/hash 关联守卫、只提供本切片方法以及同 root 发布 RunRecord/closure/terminal 的主路径符合要求。专项独立执行的 46 项单元测试和新增四模块 strict typing通过；上述 CR-02 是这些正常消息注入测试未覆盖的失败分支。

## 验证与限制

开发解释器 `/workspace/work/w006/venv/bin/python`（Python 3.12.14）。四个独立反例均在首轮产品版本实测；只使用临时 fixture 副本或中立 repository DTO，未修改已验收输入。代表性正常/F1/F2/次序/响应丢失/并发回归结果及修复复核在后续段落记录。

完整 Python 3.10/3.12 矩阵、sdist/wheel、干净安装由执行验证记录提供；本 review 会核对其受测版本与证据，但不把日志采用写成主审亲自重跑。未验证真实 EDA/PDK、其他平台、durability、Stage2–6 或完整 M1；这些未完成范围不能由本切片 review 消除。

## R2 修正复核中的追加发现

执行修正版 `3a597742b72d29971f56b9e47e1bf7147ec068f3` 已使四个原始复现转为预期行为：解析中途 symlink 切换仍复用首次 bytes；未捕获 `..` 别名不再 InputsReady；坏消息的原中断同对象传播；RunRecord 冻结坏消息走唯一专门 closure。

CR-02 仍有一个复核遗漏：新 `safe_exception_message(RuntimeError())` 返回空字符串，pipeline 构造 `StageFailure` 或 `PublicationUnavailable` 又以“message 必须非空”抛 ValueError。无参数异常是普通合法 Python 异常，不能让诊断再次失败。独立脚本 [empty_diagnostic.py](review-verification/empty_diagnostic.py) 及 [3a59774 结果](review-verification/empty-diagnostic-r2-before.txt) 记录 parser 与 create.before_switch 两处；repository freeze 分支这例已正确 fallback，不重复记为其缺陷。此项并入 CR-02，要求非空的安全消息 fallback 后再关闭。

## R3 最终产品修正复核

最终受审产品/测试版本：`cc42ae62585755b0b914d4dbec43324941bfe7c6`。独立核对工作区产品与该提交逐文件相同；[identity.json](review-verification/identity.json) 保存准确版本及 SHA-256，fixture、support、W003/W004/W005历史记录与 legacy 相对任务基线无变更。

| Finding | 独立关闭依据 | 结论 |
| --- | --- | --- |
| CR-01 | `_Files.path` 缓存 URI 的首次解析路径；原解析中途 symlink 反例现在只读取 source-first 与 target，返回 unsealed InputsReady，有 checkpoint 且无 terminal。[复核结果](review-verification/alias-during-capture-after.txt)。ToolRun 构造故障的新回归确认返回非 terminal 的 PublicationUnavailable，保留 pending bytes/events/evidence 与 InternalStageFailure，原中断不被替换。 | 关闭 |
| CR-02 | 安全 exception type/message/causes 快照容纳格式化自身失败、surrogate 和空消息；外层 finally 在诊断前固定原中断。原两种中断均同对象重抛且 best-effort 链可查；冻结坏消息均为唯一 run_record_freeze_failure closure，原 failure ref 保留。空消息 parser→terminal reject、create publication→PublicationUnavailable、freeze→专门 closure 均符合边界。[中断](review-verification/interrupt-diagnostic-after.txt)、[冻结](review-verification/freeze-diagnostic-after.txt)、[空消息](review-verification/empty-diagnostic-after.txt)。 | 含 R2 追加反例一并关闭 |
| CR-03 | 绑定仅使用捕获时 URI、冻结根目录下精确路径字符串及 event.path，不再 normpath/事后 resolve。原 link/../source.cdl 声明现在形成明确 UnreadSelection → terminal reject，定位仍是未捕获声明，无假 hash。[复核结果](review-verification/selection-dotdot-after.txt)。 | 关闭 |

主审实际复跑（均为 Python 3.12.14，代码版本以 identity.json 为准）：

- 五个独立复现脚本，结果如上。
- `python -B -m pytest -p no:cacheprovider tests/contracts/test_w006_review_regressions.py tests/unit/test_w006_publication.py -q`：**73 passed**，21.14s，见 [修复回归](review-verification/fix-review-tests.txt)。
- `python -m mypy`：**21 source files，无错误**，见 [typing](review-verification/fix-review-mypy.txt)。
- `python -B -m pytest -p no:cacheprovider tests/contracts/test_w006_pipeline.py -q -k 'attempt_is_created or f1_full or f2_real or second_legal or same_captured_bytes or failed_terminal_publication or response_loss_retains or concurrent_same_request'`：**12 passed / 18 deselected**，26.99s，见 [代表组合](review-verification/representative-after.txt)。首次对应结果为 [12 passed](review-verification/representative-before.txt)，不将其冒记为修正后证据。

**CR-01、CR-02、CR-03 均经独立复核关闭，剩余必须修正项 0。** 工程矩阵与安装证据的最终版本核对单列后续接收段；本结论不代替 PM 验收，不宣称完整 M1、真实工具或持久化恢复。

## R4 工程证据版本核对与最终结论

已读取最终 [engineering-receipt.json](verification/final/engineering-receipt.json)、各命令退出码、解释器/导入路径、源码清单及构建/安装/源码外 smoke 日志。它们绑定 `cc42ae62585755b0b914d4dbec43324941bfe7c6`；`verification/r1/` 的旧记录仅证明首轮 `36161ca`，不覆盖修正代码。

| 采用的执行证据 | 实际结果与边界 |
| --- | --- |
| [Python 3.10.22 全量](verification/final/pytest-310.txt)、[typing](verification/final/mypy-310.txt) | 389 passed；21 source files 无错误。环境记录确认导入来自该提交导出的源码快照。 |
| [Python 3.12.14 全量](verification/final/pytest312.txt)、[typing](verification/final/mypy312.txt) | 389 passed；21 source files 无错误。覆盖 W005 全量及本次新增单元/合同/真实文件错误组合。 |
| [build](verification/final/build.txt)、[包身份](verification/final/build-artifact-identity.json) | 新 sdist/wheel 成功，wheel 从 sdist 构建；74 项产品文件及 py.typed 包内容匹配提交，无 legacy/tests/docs runtime 内容。 |
| [干净 wheel 安装](verification/final/wheel-install.txt)、[源码外 smoke](verification/final/wheel-smoke.txt) | Python 3.12 新 venv 的 site-packages 导入；27 项声明、正常 unsealed InputsReady、replay/codec/refs 与真实 F2 MissingTerminator → reject 均验证。pip check 无破损依赖。 |

主审没有把上述执行日志写成亲自重跑：本次额外独立逐项核对了 tested-source-manifest 的 **88 项源码/测试/配置 bytes** 及 wheel 内 **74 项产品 bytes** 与 Git 提交相同，见 [engineering-identity-check.json](review-verification/engineering-identity-check.json)。wheel SHA-256 为 `ca51366350ce95aba68df523ffaee653cd546a52ad8cfb0f61348bcfa430e8b0`。

A1–A8 的本切片交付、失败/恢复义务和工程证据已核对，**最终技术 review 通过，剩余必须修正项 0，可交 PM 接收**。尚未执行 Python 3.10 干净 wheel smoke、CI服务、其他平台/解释器、legacy、真实 EDA/PDK/生产、durability及 Stage2–6完整组合；这些限制与任务范围一致。此结论不自行验收 W006，不合并 main，也不启动下一任务。
