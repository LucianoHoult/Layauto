# W009 IPMR-01 独立修后复核

日期：2026-11-03 产品检查；2026-11-04 恢复与工程审计。Reviewer：`/root/ipmr01_independent_review`；未承担本轮方案、产品或正式测试实现。另由未参与修复的 `captured_boundary_audit` 检查捕获 DTO。Reviewer 仅写本报告、review 证据和任务 reviewer 段，不代写执行或 PM 结论。

**独立修后复核完成：IPMR-01 及本轮新增 FXR-01 均已关闭，剩余必须修正项 0，建议交 PM 核验接收。** 完整产品 diff、独立动态检查及最终工程身份/回执审计均已完成。本报告不构成 PM 验收、集成或后续任务授权。

## 受审版本与合同

- 基准：`cdf3d2d5d2aeb0c441221c8bb0b41d0b302d8afa`。
- 最终产品/正式测试：`73e38df8f932bbb5bd9caf074b442ad2f5c286e9`。
- 独立 worktree：`/workspace/work/w009-ipmr01-review`；分支 `codex/w009-ipmr01-independent-review`。先核对原 checkout `work@4df07e68…` 干净，再从冻结的 `8aa11ba…` 建树；活动检查结束后才 fast-forward 到最终产品，避免执行期间混用源码。

已读根 AGENTS/README、协作及 local/remote 环境规则、W009 原要求与 PM2、[本轮交接](ipmr01-fix-task.md)、[原独立报告](independent-premerge-review.md)、W007/W008 输入和公开合同，以及所引架构 Stage1/2、几何/occupancy/CUT/channel、domain/state 依赖与 exact 单位条款；恢复 tree 只有根 AGENTS。

实际检查基准到最终产品的 **11 文件完整 diff：8 个 runtime、3 个正式测试**，没有仅审最后一项修正。[版本审计](ipmr01-verification/review/version-scope.json)保存全部路径、118 个 runtime/contract/unit/config 文件身份及保护路径零差异。fixture/答案、legacy、架构、current-work、原独立报告/失败脚本及 W009 历史验证材料未改。

## 修复边界判断

`effective_codec → geometry_codec → LayoutDraft/BasePartition/BaseOccupancy` 的内部重建不再经 constructor broad catch。畸形 BOUNDARY 字段集合、未知层、坐标对等改由消费位置显式检查；正常数学及单位/来源重建仍走原路径。

本轮还提供了 W009 同链的具体可达见证：`NormalizationInput` 的请求选择和 `validate_parse`、`ReadbackBinding` 的 `content_ref`、捕获 `SourceFile` 的 hash 重建均可在合法完整结果 wire 中产生被旧边界改写的内部异常。对应修复限定于这些可达输入/捕获边界：semantic codec 仅额外放开 readback；publication codec 仅对 15 类捕获/readback DTO 使用构造器原异常。无关 terminal/failure 分支保留原边界，没有机械删除所有历史 catch。

`_validation` 用显式缺字段/类型/索引前置检查代替输入形状异常翻译；仅 native UTF-8 解码/编码的预期失败及原 typed `InputError` 保持有意翻译。执行侧追加发现的空白 `count_header.lexeme` 反例现先检查 split 结果非空，避免裸 `IndexError`；reviewer 独立沿完整 W009 result wire 复核该控制。

没有 wire schema、捕获认证、region/geometry 数学或不可变成功合同变更。effective geometry 数学算法、原 drawn/base 覆盖和 closed graph 实现未改；其历史复杂度、数学及有限规模证据按对应未改源码采信。新增 `_required` 等认证字段检查增加取用工作，本轮未重测完整认证的绝对时延或规模/性能曲线；旧有限穷举仍限原验证范围。

## 新增 finding：FXR-01（P2）— 公有集合校验与保存采用不同迭代

**原 finding（保留）：** 本轮初版 `EvidenceRecord.sources` 和 `ParseResult` 三类集合先 `any(values)` 校验，再 `tuple(values)` 保存。既有支持的 list 子类可首次迭代给出合法项、第二次给出 `None`。独立最小反例使 `EvidenceRecord` 成功保留 `sources == (None,)`，而 `ParseResult.sources` 产生裸 `AttributeError("'NoneType' object has no attribute 'uri'")`；旧版先快照后校验不会出现该退步。此问题属于本轮新增的共享 DTO 公有构造边界，普通 wire 标量矩阵不能覆盖它。

复现：[原脚本](ipmr01-verification/review/collection_snapshot.py)及[修前输出](ipmr01-verification/review/collection-snapshot-before.json)绑定 `8aa11ba…`；`5f9af59…` 的两个受影响模块相同。该结果已交执行者，未由 reviewer 改实现或测试。

**执行处置：** `73e38df…` 先检查容器 shape，再只取一次 tuple 快照，对同一快照校验并保存；保持 tuple/list 及原 list 子类支持。正式新增四入口 × valid-first/invalid-first 的 8 项回归，核对一次迭代及后续原容器变更不影响结果。

**独立复核：已关闭。** [修后同一脚本](ipmr01-verification/review/collection-snapshot-after.json)实际保存合法 SourceRef/SourceFile，无 `None` 或裸异常；专项另重跑原脚本和正式双向 **8 passed**，见[专项报告](ipmr01-verification/review/captured/report.md)及其原输出。既有支持范围、快照及明确拒绝恢复，无剩余 FXR-01 必须项。

## 独立实跑与工程身份

每项命令、解释器、cwd/HEAD、退出码与原始 stdout/stderr 均保存在 [review 目录](ipmr01-verification/review/)。最终独立环境为 Linux、Python3.12.14；使用 `/workspace/work/w009-ipmr01-env/py312/bin/python`，禁字节码和 pytest 缓存，临时路径另置 work。

| 最终受审源码上的独立检查 | 结果与证据 |
| --- | --- |
| 原 `exception_paths.py`，未修改脚本 | **99 cases / 99 same objects / identity_failures=[]**，实际检查 JSON，exit0/189.567s；[原输出](ipmr01-verification/review/exception-matrix.stdout.txt)、[命令回执](ipmr01-verification/review/exception-matrix.json) |
| 捕获/readback 15 类 DTO 畸形 wire | **1184** 变异：1143 明确 ValueError、41 为允许的 neutral canonical 替代值；unexpected_exceptions=[]。合法替代值再编码一致，不冒充捕获认证成功。另 9 类 SourceFile 内部异常 **9/9 同对象及既有 cause/context/suppress**；[专项](ipmr01-verification/review/captured/report.md) |
| malformed 捕获 receipt constructor 与完整 W009 result wire | **33 项明确 ValueError**，包含缺/多字段、错误 scalar/集合/来源/ref/metadata，以及空白 count header；[独立脚本](ipmr01-verification/review/receipt_controls.py)、[原输出](ipmr01-verification/review/receipt-controls.stdout.txt)、[回执](ipmr01-verification/review/receipt-controls.json) |
| FXR-01 公有集合原反例与正式回归 | 两入口原反例修后保留合法快照，四入口双向 **8 passed** 且只迭代一次；[专项身份](ipmr01-verification/review/captured/identity.json) |
| W008 公有 wire 畸形对照、真实 W005/W006 无 IO 组合及既有异常链 | **267 项明确 ValueError**；真实两路径构造相同草稿，40 个 drawn record/41 fragments 保持，禁 builder 文件/repository IO 后仍通过，attempt 不变，3 个 W009 入口 roundtrip；readback 四重建点 × 九类异常 **36/36 同对象及原 cause/context/suppress**。exit0/437.233s；[独立脚本](ipmr01-verification/review/probe.py)、[原输出](ipmr01-verification/review/independent-probe.stdout.txt)、[回执](ipmr01-verification/review/independent-probe.json) |
| 最终源码/完整 tar、新 wheel/sdist 和实际双安装树 | **245 源项、完整快照、两包各90 runtime、两实际安装各90 runtime** 全部匹配，独立读取 site-packages 与 direct_url metadata；[包/安装审计](ipmr01-verification/review/package-install-audit.json) |
| 最终正式回归与 typing 的独立回执审计 | Python3.12 完整 **1149 passed / 1069.07s**，Python3.10 受影响范围 **988 passed / 1465.64s**；双 strict mypy 各 **44 模块**、开发环境和两干净安装 pip check 均 exit0。属于执行者实跑、reviewer 核原输出与身份，非 reviewer 再跑全套；[完整工程审计](ipmr01-verification/review/engineering-audit.json) |

[兼容证据独立审计](ipmr01-verification/review/compatibility-audit.json)另核对恢复版与最终版各90 runtime 同对应 Git 字节一致，命令确从不同包根导入并读取同一 fixture/URI spelling；W008 result、W009 draft/result 完整 wire/digest 与 semantic_digest 均相同。checkout 迁移引入的历史 absolute normalized-cache URI 差异不用于推断合法 wire 行为改变。

11月3日 R3 工程进程因环境断连中止，完整 pytest/typing 没有最终回执，不计为通过。11月4日恢复后，reviewer 重新核对全部245项源码与最终 Git/manifest 及已完成独立 probe 输出 hash，均未改变，见[恢复身份](ipmr01-verification/review/recovery-identity.json)。独立产品 probe 保留原检查日期和身份，不因断连重复执行。执行者将已完成且版本/输出身份重新核实的 R3 build/install/smoke 沿用，并归档断连时 partial 输出，仅补跑缺失的完整 pytest、typing 和 development pip checks；本报告不将沿用记录描述为跨日重建或重装。

最终[工程审计命令](ipmr01-verification/review/engineering-command.json)实际 exit0，核对总回执 `passed/errors=[]`、最终源身份未变、24份命令的 HEAD/finished_HEAD、manifest 和全部原始 stdout/stderr hash。16份11月3日完成的 build/install/smoke 回执及8份11月4日新跑的 environment/pytest/typing/development pip 回执逐一与总回执相同；开始时间与恢复点分界一致。14份断连归档逐一核 hash，旧 partial 不计完整通过，原 runner、smoke 和 resume script 实物 hash 亦一致。

Reviewer 同时重新实际遍历245项源码、完整 tar、包实物和当前两安装树，最终 manifest 为 `40a60ada56e2b560d1af88fec9c16e4d60a6b1384fb042f39202edfcaefefc2c`；全部源码等于受审 Git 字节。构建/干净安装由执行 runner 完成，reviewer 未冒称重新构建或重装。Python3.10 的 pip23 安装 metadata `direct_url.archive_info` 为空，URI 与安装 report 的 artifact SHA-256、包实物及全部90项安装字节共同绑定来源；未凭空补写 metadata hash。两套源码外 `-I -B` smoke 的实际输入与脚本已读，真实 W005/W006→W008→W009 正常、错误、codec、嵌套异常链均通过。

`pre-final/` 只保存 `8aa11ba…` 的 99/99 原矩阵、226 项正式回归及为切换冻结版本主动中止的旧独立 probe；不当作最终身份结果。`harness-initial/` 保留 reviewer 初版把合法 `Rect.x0=7` 误当必拒绝，以及把 pip23 可选 metadata hash 当必需字段的 harness 失败；后续使用确实非法的 None/集合/缺字段控制并核安装 report 实际 hash，不将 harness 问题记为产品 finding。`captured-before-final/` 的 1184 项旧 wire 专项亦保留原身份，最终已重新执行，不混作最终结果。

本次不改变原 IPMR-01、CR-01/CR-02、PM1/PM2 或原最小失败脚本。原最小脚本断言缺陷存在；修后不满足旧断言是预期现象，不能把它改成假通过。

## 限制与交 PM

Python3.10 本轮988项 scope 是全部 contracts 加 W006 publication unit，未重跑全部 parser unit；Python3.12完整1149项已覆盖 unit/contracts。几何数学算法及其历史复杂度/有限规模检查按未改源码采信；新增认证检查后的绝对耗时及生产性能未在本轮建立结论。真实 EDA/PDK、完整工艺坐标、connectivity/body/extraction、baseline/terminal 和后续任务均未由本次完成。

Reviewer 不自行验收、不合 main、不修改 PM 阶段或 current-work，不推送或启动 W010。最终交付由执行者集成 review 记录与证据后推送原 W009 分支，再由 PM 接收判断。
