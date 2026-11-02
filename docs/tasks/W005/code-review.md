# W005 独立代码 review

Reviewer：`final_review` 子 agent；未编写本任务产品代码或测试，仅做只读检查、独立复现与复核。日期：2026-11-02。

## 版本、范围与结论

基线：`5b7205009b3ed7f8fe15e135e674654f2f544557`。最终代码复核版本：`ab7feddff83749b54c1866b1ad95fbc99fd787f1`，分支 `codex/w005-input-reading-binding`。该提交包含此前完整实现 `f29c84a` 及 R5 修复；后续执行记录和本 review 文档不改变被审代码。受审范围为新增中立 codec/evidence/results、输入读取和绑定、GDS/CDL/query parser、tech/schema、对应单元与组合测试、typing/build 配置和 README 使用边界。

已对照 AGENTS、协作规则、W005 A1–A7、接口 review、任务引用的架构条款与实际 fixture/profile/失败样本检查。**本次代码 review 的五项必须修正 finding 均已修复并独立复核，无剩余必须修正项。** 此结论交 PM 接收，不是 W005 最终验收、M1 闭环完成或生产准入。

接口 review 由另一 reviewer 独立完成；本次另查实际实现、实际文件读取及错误路径，没有用接口方案结论代替代码检查。初查时实现处于集成工作区，以下原始 finding 按其可复现操作保留；最后统一绑定上述已提交代码复核。

## Finding 与处置复核

| ID | 原始 finding、影响与最小复现 | 执行处置与 reviewer 复核 |
| --- | --- | --- |
| R1 | 可选 normalized cache 用 Python mapping 相等判断；`True == 1` 会把 integer→boolean 的类型漂移当相等。将缓存 `device_regions.records[0].field_sources.precision.sources[0].line_1based` 从 `1` 改为 `true`，普通 mapping 比较无法证明 schema 等价。 | 改为 exact canonical bytes 比较。独立实际文件复现返回 `NormalizedCacheMismatch`；合法 key 重排仍可读。持久回归 `test_cache_type_drift_is_not_hidden_by_python_bool_integer_equality`、`test_cache_key_order_is_not_semantic_drift` 通过。关闭。 |
| R2 | Body association 只检查 ID 存在，未校验内部引用字段的角色类型。对临时副本完整重绑后，将 `local_body` 指向已有 M1 rail `MN`、`external_body` 或 `tap` 指向 `MN.ext`、`local_rail` 指向 body `BN`，四种都曾返回 success。该问题属于 context 内部引用类型，不能推迟为跨 GDS 的物理匹配。 | 根据选定 drawn registry 验证 frame/body/tap/rail 的声明角色；未引入 GDS/CDL join。独立复现返回 `BodyReferenceTypeMismatch`，定位到 association 字段；既有 `body_wrong_type`（BTAP_N/P 物理兼容性）仍读取成功并留 Stage 2。四个持久参数化回归通过。关闭。 |
| R3 | `header.closure.canonical_encoding` 接受任意文本，实际始终按 compact UTF-8 JSON 算 digest。把声明改成 `UTF-16 with numeric-key coercion` 后仍返回 success，静默忽略了与身份计算不一致的编码声明。 | 将本版本支持的 closure 编码声明封闭校验。独立实际文件复现返回 `InvalidSchema` 并保留已读 header hash；`test_closure_digest_encoding_declaration_must_match_supported_contract` 通过。关闭。 |
| R4 | 支持的 Python 3.10/3.12 上，`Path.resolve()` 对 symlink loop 抛 `RuntimeError`，不在原 ValueError/OSError 分支内。site 或选定 tech 指向 `loop → loop` 时异常逃逸，未产生预期 typed 读取错误。 | 在 resolve 的窄边界转换已知 symlink-loop RuntimeError；无关 RuntimeError 仍传播。独立 site/selected 路径复现均得到 `InvalidInputPath`、无伪造 hash；两个持久回归通过。关闭。 |
| R5 | 可选 cache 的 `path.exists()` 在读取错误处理之外。实际将临时副本 `query/normalized` 目录 chmod `000`（执行 uid 1000）后，组件抛未捕获 PermissionError，丢失结构化失败交接。复现后恢复目录权限。 | `ab7fedd` 在可选存在性探测处窄捕获 OSError。独立重复实际 chmod 复现得到 `InputReadError`，source hash 为 null，已完成 query 等 9 份 evidence 保留。持久权限失败回归通过；缓存确实缺失仍合法。关闭。 |

另外两项初查建议在可运行集成版本前落实：嵌入 NUL/无效路径返回 typed error；`toy_gds_real8_nm/1` 不得重定义其固定 source nominal 1 nm/user 1 µm。Reviewer 在最终版本实际验证 NUL site/selected 路径和重绑 2 nm nominal 声明分别返回 `InvalidInputPath` 与 `UnitDeclarationConflict`，未将未执行的原版复现写成已验证事实。

## 独立验证证据

实际执行环境：Linux，Python 3.12.14；最低支持检查使用 Python 3.10.22。检查不调用 EDA，也不修改已验收 fixture。

| 命令 / 检查 | 实际结果与身份 |
| --- | --- |
| `/workspace/work/w005-venv/bin/python -m pytest tests/unit tests/contracts -q` | `ab7fedd` 上 **237 passed in 23.26s**，reviewer 独立完整执行。此前集成工作区一次 234 passed 的结果不冒充此最终结果。 |
| `/workspace/work/w005-venv/bin/python -m mypy` | strict 检查 **13 source files**，无问题；目标解释器语法为 Python 3.10。 |
| Python 3.10 的 `tests/contracts/test_w005_inputs.py -q -k 'cache_type_drift or body_reference or fixed_source or closure_digest or symlink_loop or optional_cache_presence'` | **6 passed, 65 deselected**；其中 `body_reference` 未匹配实际测试名，另以 `-k context_internal_reference_roles` 实跑 **4 passed, 67 deselected**，不将未选中测试算作通过。 |
| 独立临时副本复现 | R1–R5 修复复核；dot-prefixed raw/request URI 一致重绑后读取成功；physical body wrong-type witness 保留到后续阶段。所有变更仅在临时副本。 |
| `git diff --check 5b7205009b3ed7f8fe15e135e674654f2f544557` | 通过。 |
| `git diff --name-only <base> -- tests/fixtures tests/support docs/architecture.md docs/current-work.md` | 空；原 fixture/答案、helper、架构和 PM 当前入口未被本实现改写。 |

执行者完整 Python 3.10 日志为 `pytest-310-final.txt`：最终 `ab7fedd` 上 **237 passed in 33.85s**；build-final 显示 sdist/wheel 构建成功，install-wheel 显示在新环境安装 wheel 及依赖，pip-check-wheel 无依赖冲突。本 reviewer 已读取这些 [verification](verification/) 日志，并逐项重算 `source-manifest.json` 的 22 个文件 hash，与工作区和受审提交均一致。

Reviewer 另直接检查最终 wheel 的产品文件与受审 manifest 相同，含 `py.typed`；wheel SHA-256 为 `f6d1bab300b425c54b07c26d54a5903d77ace08a9d2d2530a758fc19a3a0cf4d`。在源码目录外 `/workspace/work` 以新安装环境执行 `python -I /workspace/Layauto/docs/tasks/W005/verification/wheel_smoke.py /workspace/Layauto/tests/fixtures/w003_m1`，实际导入路径位于 `site-packages`，正常 40 shapes / 8 net regions 和重绑坏 raw 的 `MissingTerminator` 均通过。完整 3.10 套件和构建安装由执行者执行，reviewer 的上述复核和独立 smoke 与其区分记录。

## A1–A7 覆盖与限制

- A1：实际读取 site 选定文件，40 个 BOUNDARY 的 layer/bbox multiset 对照独立设计答案；两份 CDL 和四类 query 对照独立语义/缓存答案。测试在调用期间拦截 runtime 打开 expected/spec/oracle；目录内容 hash 前后不变。产品保留未注释几何。
- A2：REAL8 原 bytes 直接 exact-decode、整数 XY/完整 query vertices 和 CDL lexeme 保留；schema、duplicate/unknown/type/version/tag/nonfinite/limit 失败路径有测试。递归 alias mutation、exact wire 非法表示和跨进程 digest 均覆盖。原 decoded scale 与 nominal/delta 分离。
- A3/A4：实际应用 failure replacement/remove，并按对应原因拒绝；重绑坏语法、缓存删除/漂移、伪真 status、缺闭包/输入、body source/profile/引用等有定位错误。读取保留成功的前置 evidence；未知 LVS status 未升级 assurance。意外异常和 process interrupts 传播。
- A5：第二输入改变 top、器件/query 对象、raw 路径、记录/参数顺序和坐标，并完整重绑；另测额外未注释 BOUNDARY 与 query 单 tick 的 `1/20 nm` 变化。无 INV/Q17/40/5/7/raw 文件名或旧 hash 的运行时答案依赖。
- A6：domain 只含中立值/记录/codec；importer 不 import tooling/state/normalization/pipeline/legacy/tests.support，也不写文件或执行 EDA。格式代码为按声明子集重新实现，未复制 helper 作为产品实现。Body 仅解析和绑定，未产出 `body_complete`。
- A7：本 reviewer 已直接执行最终完整 3.12 测试、strict checker、3.10 定向修复回归，并独立核验 wheel 文件身份和源码目录外的安装后正常/失败读取。执行者完整 3.10/3.12、sdist/wheel 构建/干净安装证据已对照；未测试的 Python 版本/平台不可据此声称通过。

C08/C09/C10 的跨证据 cardinality/finger/reduction 准入、C13 的目标差异、C14–C16 与 body 物理/连接/rail 检查、C19/C20 的输出坐标转换仍交后续 Stage 2/admission/constraints/export。读取成功只表示事实保留。本次不含 pipeline attempt/terminal/RunRecord、layout state、真正的 body 几何匹配、Stage 6 导出、真实 Calibre/Virtuoso/PDK 或生产服务器验证。
