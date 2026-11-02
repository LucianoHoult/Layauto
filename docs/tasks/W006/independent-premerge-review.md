# W006 独立合并前复核

2026-11-02；角色：独立 reviewer。本会话主审 `/root` 及读取/捕获、Repository/domain、工程身份三个只读专项均未参与受审产品实现。本报告不是 PM 验收。

**结论：剩余必须修正项 1（P2，IPMR-01），阻止当前版本合并。** parser 的意外异常后，ToolRun 诊断冻结再次失败会丢掉原始异常及 cause chain。其余已检查路径未发现新增必须修正项；现有测试通过不能覆盖该组合反例。新增 finding 保持开放，交 PM 安排执行修复和独立复核。

## 1. 身份、恢复与实际范围

| 项目 | 本次核对结果 |
| --- | --- |
| 仓库 / 远端 | `/workspace/Layauto`；`origin=https://github.com/LucianoHoult/Layauto.git`，fetch/push 地址一致 |
| 初始 checkout | 干净的 `work@4db3aa81d6f01496a680bdcb264afe99cd80f3f3`，无 staged/unstaged/untracked 修改；不是交接中的 W006 分支 |
| main / review base | `4db3aa81d6f01496a680bdcb264afe99cd80f3f3`；实际远端 main 一致，且为受审 HEAD 祖先 |
| review branch / HEAD | `codex/w006-precontext-run-audit@cd1c847e74dc399ce32eeaf01c1ff5ab825c000d`；实际远端与用户交接完全一致 |
| 最终产品 / 回归 | `cc42ae62585755b0b914d4dbec43324941bfe7c6`；本次受测产品/测试与该提交一致 |
| 产品后的变化 | `cc42ae6… → cd1c847…` 共 104 个 docs 路径；执行/review/工程证据及 PM 接收记录。PM 回执的 99 对应其接收的 `628cc94383fa4c68bd44de51117ef06451ed3a9e`，统计端点不同 |

先检查本地身份与差异，再用 `git ls-remote` 核对两条远端完整 SHA，显式 fetch W006 并建立同名本地分支。初次 Git CLI 在默认网络沙箱中代理不可达，使用环境支持的网络权限后通过同一代理成功；未绕过网络策略。单分支 fetch 配置使 `switch --track` 未能建立 tracking，随后从已核对远端 ref 普通 `switch -c` 成功。没有 reset、force push 或覆盖既有修改。

实际 review 为 **base→交付 HEAD 的 diff，加受影响实现的完整控制流/上下游合同**：`pipeline.py`、`importers/reader.py`、新增 `domain/acquisition.py`、`domain/publication.py`、`publication_codec.py`、`tooling/fixture.py`、`repository/publication.py` 及相应测试/typing/说明。只写本报告、最小复现材料和任务 reviewer 追加记录；产品、fixture、PM 验收段、当前入口及历史 finding 原文保持原样。

已读根 AGENTS（未发现局部 AGENTS）、README、协作规则、当前入口、W006 全文与 interface-plan；核对 architecture §2.1–2.2、§2.6–2.7、§9.2、§11.2/11.4/11.10/11.13/11.15、§12.1/12.6–12.7 原文，W002 E6/E7/R4、W003 共享记录/失败/F1/F2 原合同与样张、W005 读取组件/后续组合归属。先按要求与实际代码建立专项判断，再核对 interface-review、code-review、PM 回执及其证据，未将历史“0 必修”作为本次结论。

## 2. Findings（按严重程度）

<a id="ipmr-01"></a>
### IPMR-01 — P2 / 必须修正：诊断冻结的第二个异常覆盖原始 parser 失败

**位置：** [pipeline.py](../../../layauto_v2/pipeline.py) 第 160–171 行，尤其第 167–168 行。首个 `except Exception` 已构造带原 cause chain 的 `StageFailure`；随后 `capture.freeze()` 的异常分支无条件覆盖同一个 `failure`。

**触发条件与最小输入：** 使用未改动的已验收 `tests/fixtures/w003_m1/site_config.yaml`，一个普通 `RunRequest`。在实际读取完成到 `parse_query` 时注入 `RuntimeError('original parser failure') from LookupError('original underlying cause')`；再让 `FixtureCapture.freeze()` 抛 `ValueError('secondary tool diagnostic freeze failure')`。这是 A7 要求的进程内双重故障注入，不需要坏 fixture、持久化 backend 或真实 EDA。

**复现：** [double_exception.py](independent-premerge-verification/double_exception.py)，[实际输出](independent-premerge-verification/double-exception.txt)。仓库根执行：

```sh
/workspace/.venvs/layauto/bin/python -B \
  docs/tasks/W006/independent-premerge-verification/double_exception.py
```

当前受审版本退出 **1**，最后的合同断言失败。主审先用临时探针复现，Repository 专项又独立复跑确认，之后保存上述可移植脚本。脚本只读 fixture，patch 仅在本进程的 `with` 内生效。

**实际结果：** 返回 `PublicationUnavailable(operation='freeze_tool_run')`；顶层 `causes` 和 `pending_failure.causes` 都只有第二个 ValueError。`pending_parse=None`，原 RuntimeError/LookupError 在返回结果及 repository 中均不可查；仍保留 27 个 sources、8 个 completed evidence，checkpoint/terminal 均为 `None`。因此“未发布 terminal”的返回正确，但根因已丢失。

**预期与影响：** 同时保留原 stage failure 及二次诊断失败，调用者才能判断解析为何中断。原 failure 已在内存中建立，不能因后续诊断失败丢弃。此问题会把一次 parser/基础设施缺陷错误地只呈现为 ToolRun 冻结故障，破坏失败审计与修复定位；普通成功输入、单异常和原中断传播的已有通过结果不消除这个缺口。

**合同依据：** [W006](../W006-precontext-run-audit.md) 行为要求 7：“pipeline stage boundary 将意外程序/基础设施 Exception 转为 InternalStageFailure 并保留根因”；A7 明确要求多重错误、实际持有记录与 refs 的核对。另见 architecture §11.13 的显式 stage failure，以及 §2.7 / W003 的 best-effort 存储失败边界。这里不要求存储失败时仍保证 terminal，只要求保留已经取得的原始诊断。

**修正建议：** freeze 失败时保留已有 `failure`，仅当此前没有 failure 时构造冻结失败对应的 `InternalStageFailure`。`PublicationUnavailable.operation/message/causes` 可继续描述第二个冻结异常，`pending_failure` 保留原异常及完整 cause chain；继续保留 pending bytes/events/evidence，并如实返回无 checkpoint/terminal。等价的明确双层故障表示也可，但不可只留第二个错误。

**修复交接 / 独立关闭条件：** 执行者覆盖 parser Exception + cause chain 后 freeze 再失败，以及 acquisition Exception 后 freeze 再失败；确认两个错误均可解释、已有 facts 保留且无虚构 terminal。补查单独 freeze 失败、空消息/非法 Unicode/坏 `__str__`，并保持 `KeyboardInterrupt/SystemExit` 原对象继续传播。由后续独立 reviewer 对修复版本确认关闭；本会话不修改实现、不关闭该 finding。

**可后置建议：** 本轮没有另列后置建议。Stage 2–6、durability 等是既有后续归属，不计为本次缺陷或隐含新增任务。

## 3. A1–A8 与重点边界检查

| 要求 | 独立检查结论与证据 |
| --- | --- |
| A1 身份先行 | `prepare_inputs` 先 create，再启动 generator；InputParser 构造不读文件。正常/缺失/坏 site 的顺序 spy、create 失败不读不解析、create 响应丢失重试均通过。 |
| A2 声明与实际来源 | F1 caller 从实际文件自行构造 5+9+13 声明，再单独比样张；产品不读取 records/oracle/expected/spec。声明和捕获 hash 独立且 request 不回填；hash drift、未读声明、第二套合法命名/路径均有真实文件验证。四个 optional caches 属后发现事实。 |
| A3 unsealed 正常交接 | tooling 返回的同一个 SourceFile 被 send 给 parser；正常 31 份捕获与 Parse sources 相同。仅 InputsReady/unsealed、refs 可读回，无 canonical context、baseline/seal、成功 terminal。递归不可变、versioned codec、跨进程 canonical SHA-256 和 typed ref 守卫通过。 |
| A4 真实 F2 | 测试在临时副本应用原 missing_terminator 坏 header/raw、去掉对应缓存，再构造声明。实际错误为 MissingTerminator，保留定位/原 raw SHA 和 completed evidence；ToolRun→Parse→StageFailure→最小 failure RunRecord→closure→terminal reject 可沿同 run 查询。没有由提前 hash mismatch 代替解析错误，dummy_fixture 未冒称真实 EDA。 |
| A5 原子性与重试 | Repository 单锁、单 immutable root 发布 content/attempt/replay；same-key/same-digest 在当前 guards 前返回原结果。响应丢失、竞争/同 key 异 digest、读者不可见半发布及固定 failure checkpoint 已检查；terminal switch 前失败后改变磁盘文件，重试仍使用原 finalize 请求和捕获，不重读。 |
| A6 状态与关联 | 错 head/revision/run/ref/hash、terminal 后新 mutation、未支持 partial 均明确拒绝；未交付 seal/initialize/正常 close/finalize 方法，不以 stub 假成功放开 unsealed。范围仅当前 process-local 切片。 |
| A7 多重错误 | RunRecord freeze 的唯一无 RunRecord closure、terminal 未发布/丢响应读回、坏消息/空消息/Unicode、原中断传播的既有反例通过；**双 Exception 的诊断冻结组合不满足根因保留，见 IPMR-01**。 |
| A8 工程与保护 | 本次运行受影响 W006、Repository、W005 回归和 21 模块 typing；身份清单与产品提交一致。原双解释器/构建/安装证据按第 5 节采用。fixture/答案/生成 helper、架构、W003/W004 和 W005 既有附件未改，原读取能力没有通过弱化测试维持绿灯。 |

路径专项另验证：absolute selections 在 `/tmp` cwd 仍绑定同 31 captures；不提供 selection manifest 仍可发现并审计输入；site symlink loop 在已有 attempt 下得到 InvalidInputPath→reject，不捏造 bytes/hash。URI 首次解析缓存、固定根目录和 event.path 绑定避免捕获后重新 resolve；未捕获的 `./source.cdl` 或 `link/../source.cdl` 可保守拒绝为 UnreadSelection，这是接口明示边界。中立 domain 无 IO，tooling/importers 互不依赖，repository 不依赖 importer/tooling/transactions，只有 pipeline 编排。

## 4. 本次实际运行

环境按仓库 `docs/environment/local-setup.md` 与 `remote-development.md` 执行：Linux x86_64 / glibc 2.41，CPython **3.12.14**；解释器 `/workspace/.venvs/layauto/bin/python`，pytest 9.2.0、mypy 2.4.1。复用已有专用 venv，补装 `.[dev]`；导入位置 `/workspace/Layauto/layauto_v2/`。这是 checkout editable 回归环境，不是干净 wheel 安装证据。

以下除说明外 cwd 为 `/workspace/Layauto`；`PY` 指上述解释器。

| 执行者 / 命令 | 实际结果 |
| --- | --- |
| 主审：`$PY -m pip install -e '.[dev]'`；`$PY -m pip check`；版本/导入路径检查 | 安装、依赖检查退出 0；No broken requirements found。pip 的 home cache 不可写提示不影响安装。 |
| 主审：`$PY -B -m pytest -p no:cacheprovider tests/contracts/test_w006_pipeline.py tests/contracts/test_w006_review_regressions.py tests/contracts/test_w006_boundaries.py -q` | **49 passed，66.87s，exit 0** |
| Repository 专项：`$PY -B -m pytest -p no:cacheprovider tests/unit/test_w006_publication.py tests/contracts/test_w006_boundaries.py -q` | **58 passed，1.08s，exit 0**；含与上一命令重复的 2 个 boundary tests，不把相加当独立用例数。 |
| 读取专项：`$PY -B -m pytest -p no:cacheprovider tests/unit/test_w005_config.py tests/unit/test_w005_formats.py tests/unit/test_w005_query.py tests/unit/test_w005_unicode.py tests/contracts/test_w005_contracts.py tests/contracts/test_w005_inputs.py tests/contracts/test_w005_unicode_inputs.py -q` | **284 passed，46.41s，exit 0**；原 W005 全部 7 个测试文件未改。 |
| 主审：`$PY -B -m mypy --cache-dir /workspace/work/w006-independent-review/mypy-cache` | **Success: no issues found in 21 source files，exit 0** |
| 读取专项：`$PY -B /workspace/work/w006-independent-review/capture/capture_probe.py` | 4 组路径/声明边界探针通过；场景和结果见第 3 节。 |
| 工程专项：`python -B /workspace/work/w006-independent-review/evidence/check_identity.py` | exit 0；逐项 SHA-256、Git 祖先/差异及历史命令结果核对，数量见第 5 节。此脚本使用宿主 Python 3.12.14 标准库，不作产品运行环境证据。 |
| 主审与 Repository 专项：临时双异常探针；主审：第 2 节保存的 `double_exception.py` | 临时探针两次确认原 cause 丢失；保存版合同断言 **exit 1**，为 IPMR-01 的预期复现失败，不列入“测试通过”。 |
| 主审：`git diff --check`，最终文档链接/修改归属/原段落保留核验 | 通过；交付只包含报告、复现和 reviewer 追加。 |

上述临时脚本/日志位于 `/workspace/work/w006-independent-review/`，仅为本会话工作材料，不假定跨实例存在。关键缺陷复现脚本与原始输出已随本报告保存；测试命令及准确结果在此固定，不用本机临时路径冒充远端交付附件。

## 5. 已核对并采用的既有证据

本次重新计算 [最终 source manifest](verification/final/source-manifest.json) **214** 项、[tested-source](verification/final/tested-source-manifest.json) **88** 项、[fixture snapshot](verification/final/fixture-snapshot-manifest.json) **116** 项：均与产品 cc42ae6、交付 cd1c847 及工作区对应 bytes 一致。另核对 [工程证据 manifest](verification/final/engineering-evidence-manifest.json) **31** 项、[review identity](review-verification/identity.json) **16** 项、PM 两份日志及 probe 共 **3** 个 hash；11 项历史工程命令记录均 exit 0。接口方案 SHA-256 为 `5a1b9d986871d7ca4a6f10d83e37fb65e439255807fc18e3677b2866ae712b92`。

| 采用材料 | 结论与采用边界 |
| --- | --- |
| [最终 engineering receipt](verification/final/engineering-receipt.json)、[commands](verification/final/commands.txt) | Python 3.10.22 / 3.12.14 各 **389 passed**，两解释器 21 模块 strict typing；绑定最终产品，旧 `verification/r1/` 只证明 36161ca，不替代补修后版本。3.10 本次未运行。 |
| [build identity](verification/final/build-artifact-identity.json)、[build](verification/final/build.txt)、[install](verification/final/wheel-install.txt)、[smoke](verification/final/wheel-smoke.txt) | 已发表记录显示由最终源码构建 sdist→wheel、新 3.12 venv 安装/pip check、源码外正常交接和 F2 smoke 通过；方法及版本关系已核对。 |
| [旧 reviewer 工程身份核验](review-verification/engineering-identity-check.json) | 采用其原 wheel 74 项产品 bytes 与 Git 相同的核验。**本环境没有原 wheel；本次未重验原包字节、未重建、未做干净安装。** wheel SHA-256 仅引用原记录：`ca51366350ce95aba68df523ffaee653cd546a52ad8cfb0f61348bcfa430e8b0`；sdist：`9e802f092248b57d469bc5992f227ad3f55016f56d9c0e5c52a6ef30bc153724`。 |
| [PM receipt](pm-receipt.json) | PM 3.12 全套 389 项与 21 模块 typing 是既有接收事实，不替代本次 review；其原 wheel 不在场限制如实保留。 |

历史 findings 随后逐项对照当前实现和本次回归：IR-01 的稳定 failure checkpoint、IR-02 路径/捕获时身份、CR-01 解析中途 symlink、CR-02 原中断/坏消息/空消息、CR-03 未读 `..` 别名，原反例的关闭依据仍成立。IPMR-01 是此前未覆盖的 **普通 Exception＋诊断 freeze 第二次 Exception** 组合；不改写或删除历史 finding，不把旧“0 必修”扩展成当前无缺陷结论。

## 6. 边界与交回 PM

未运行真实 EDA/Calibre/Virtuoso/PDK、生产上传或 matched/live 验证；未重新生成 fixture、未运行 legacy；未实现或验证 Stage 2 语义/state/body/extraction、baseline/seal/no_change、Stage 5 ECO/完整 mode 矩阵、Stage 6 导出/正常 terminal 或完整 M1；不承诺持久化、跨进程、crash/OOM/断电恢复。本次未运行 Python 3.10、其他平台、构建或安装包 smoke；原交付也没有 Python 3.10 干净 wheel 安装证据。

本次 **剩余必须修正项 1**。建议 PM 接收 IPMR-01，安排在既有 W006 范围修复、补必要组合回归，再交独立 reviewer 按修复版本复核。本 session 保持 review 角色，只按授权提交/推送本报告、最小复现及任务 reviewer 追加记录至当前 W006 分支，并在交回回复核对远端完整 SHA；不代写验收、不合并 main、不删除分支、不启动下一任务。
