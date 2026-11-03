# W009 独立合并前复核：来源、组合和异常专项

日期：2026-11-03。Reviewer `/root/provenance_exceptions`，未参与 W009 原设计、实现或旧 review。受审 HEAD `88a7ae9d0330b7c7fddda0b07366c7a96552b65e`，完整比较 `4df07e68b05df4c57a8b8d44bc41e7e073938d3a..88a7ae9d0330b7c7fddda0b07366c7a96552b65e`；实现定位采用 `4975e565a33d9594782645b6ad0f944b78ee6ae8..5b1d9b5196a7c5181822c4dd0f1bd2f678475116`。本专项只写本目录，产品、正式测试、fixture、历史证据及 PM 段均未改。

**发现一项 P2 必须修正问题：W009 公开 draft/result decode 的嵌套 base 重建仍会翻译内部算法异常，CR-01 的关闭范围不完整。** 来源与算子专项的 26 项独立定向检查通过；IR-01 的实际角色/target/operator 检查成立。建议修正并复核下述问题后再进入集成。

## IPMR-01：嵌套 base 算法异常被当作畸形 wire

- 严重性：P2，合并前必须修正；对应 W009 行为 6/A6 及本轮明确要求的 CR-01 异常身份合同。
- 公开路径：`layauto_v2/normalization/effective_codec.py:67–74` 将嵌套 base/GeometryResult 交给 `geometry_codec.decode_record`。`geometry_codec.py:107–110` 对中立 constructor 包裹 `except (TypeError, KeyError, AttributeError, IndexError, UnicodeError)`，包括重建 `LayoutDraft`、`BasePartition`、`BaseOccupancy` 时发生的真实内部错误。该 catch 虽为历史代码，但当前 W009 的两个新公开 decode 路径都会经过它。
- 最小复现：[脚本](cr01_nested_base_minimal.py)、[本次原始结果](cr01-minimal-result.json)。在正常真实 W005→W008→W009 结果上先编码合法 draft/result；仅在 decode 时将 `state.occupancy._fragments` 暂时替换成抛出同一个 `TypeError` 实例的函数。无需修改 wire、产品或 fixture。
- 预期：`decode_record(valid_wire)` 抛出原 `TypeError` 对象，`observed is failure` 为真。
- 实际：两个入口均抛出新的 `ValueError('invalid geometry wire fields')`，`observed is failure` 为假，只有 `observed.__cause__ is failure` 为真。
- 影响：在合法 wire 的 W009 公开恢复过程中，base 重建的程序错误被错误分类成调用方 wire 问题；异常类型、对象身份和纯组件错误边界丢失。没有证据表明正常几何计算错误，本 finding 针对明确要求的失败语义。
- 修复建议：在 W009 使用的完整嵌套重建链上，将畸形输入的显式结构/字段拒绝与算法执行区分，使意外异常保持原对象；保留畸形 wire 的明确拒绝。补充 draft/result 上的嵌套 base 算法异常回归。可在本轮新边界实现适当复用，不要求借此扩展旧 W008 的其他能力或放宽原合同；reviewer 未改产品。

原 CR-01 在 W009 自身 `slab_difference` 路径的修正确实生效。旧测试 `test_w009_contracts.py:170` 仅在该 W009 算法注入；`:155` 的捕获解码注入也能传播。它们没有覆盖上述被复用的 base constructor 算法，故其通过不足以关闭完整嵌套路径。

[新的异常矩阵](exception_paths.py)及[原始结果](exception-paths.json)共 **99 项**，其中 **69 项保持原对象，30 项失败**：

| 入口 / 注入点 | 结果 |
| --- | --- |
| draft、result × W009 `slab_difference` / `canonical_cover` × 9 类异常 | 36/36 同对象 |
| draft、result × base `_fragments` / `_layers` / `_materialize` × TypeError、KeyError、AttributeError、IndexError、UnicodeError | 30/30 被替换成上述 ValueError |
| 同三类 base 算法 × RuntimeError、ValueError、KeyboardInterrupt、SystemExit | 24/24 同对象 |
| result 捕获 `geometry_input.parse_gds` × 9 类异常 | 9/9 同对象 |

中立 draft 不包含 `GeometryInput`，因此未对其注入捕获 parser；没有将未到达的注入点计为通过。异常矩阵中的 `BaseException` catch 只存在于 reviewer 观察脚本，用来记录中断对象；产品未修改。

## 来源、算子、纯组合及畸形 wire

[独立 probe](provenance_probe.py)不导入正式测试 helper、expected/spec/oracle。它从真实 reader、repository 和公开组件入口构造以下 **26 项检查**，[原始结果](provenance-results.json)全部通过：

- W005→W008→W009，在构建期间禁用文件 IO；raw drawn/base 为原对象，原 semantic 编码、geometry 编码、completed、body 证据保持，physical/drawn/formats 分别关联同一 tech 捕获的 source role 3/1/4，unit ref 一致。reader acquisition 另设答案路径禁止访问守卫。
- 真实 W006 `prepare_inputs`→caller readback→W008→W009，在组合期间禁用文件及 repository read；结果草稿与直接链相等，原 attempt 保持、phase 为 unsealed、无 terminal。另一 run 的 ready 与原记录混用被拒绝。
- 中立草稿可携带自洽的 foreign physical owner，但不能进入 capture-bound success；该分层符合合同。
- 同时篡改 parse.value 和 completed 的 physical 算子 payload，保持原 source bytes：直接 GeometryInput 和 W009 嵌套 result wire 均以 `GeometryInputError` 拒绝。
- 12 类实际 owner bytes 变体，在临时副本修改并按实际 bytes 重绑 header：`effective_active_operator` 由既有 W005 schema 先定位拒绝；其余 11 类由 W009 定位拒绝，包括 channel/S-D/gate/差集/terminal 算子、OD/POLY/LI/CUT 四层错误 role，以及 CUT 错 target/operator。CUT 改 role 时移除只准 cut role 使用的字段，确保真正到达 W009 而不被先前语法失败遮蔽。所有错误保留完整 completed；没有把先前 schema 边界冒称新组件检查。
- draft/result 各 4 类畸形 wire：未知字段、缺字段、scalar 携带容器、无效嵌套 geometry bytes 均明确以 ValueError（含 JSONDecodeError 子类）拒绝。

源码审阅确认 `effective._physical` 取同一认证 GeometryResult 的完整 physical payload 和精确 source role；成功 aggregate 比较完整 base/physical，W008 `GeometryInput._verify` 重新解析全部捕获 owner，成组 payload 不能替换原 bytes。新 builder 不读取 query/CDL 名称来制造几何，没有 IO、发布或 attempt 推进。算子校验先定位四个层名再检查实际角色，不按 cut role 先过滤，IR-01 的遗漏风险已关闭。

## 本次执行与限制

使用既有 `/workspace/.venvs/layauto/bin/python`，Linux Python **3.12.14**；以 `PYTHONPATH=/workspace/work/w009-review` 确保导入本 worktree。三条命令均加 `PYTHONDONTWRITEBYTECODE=1` 和 `-B`，退出码均为 0，stderr 均为空：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/work/w009-review /workspace/.venvs/layauto/bin/python -B docs/tasks/W009/independent-premerge-review/provenance-exceptions/exception_paths.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/work/w009-review /workspace/.venvs/layauto/bin/python -B docs/tasks/W009/independent-premerge-review/provenance-exceptions/cr01_nested_base_minimal.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/work/w009-review /workspace/.venvs/layauto/bin/python -B docs/tasks/W009/independent-premerge-review/provenance-exceptions/provenance_probe.py
```

stdout 分别保存上述 JSON，stderr 分别保存 `exception-paths.stderr.txt`、`cr01-minimal.stderr.txt`、`provenance.stderr.txt`。异常及来源完整结果包含受审源码 SHA-256；数学和性能不由本专项重新背书。专项未重跑完整回归、typing、3.10、构建、干净安装或真实 EDA，也未重新观察历史安装树；这些工作由主 reviewer 的执行/证据专项分别报告。

读取依据包括根规范和环境规则、W009 任务/方案/原 review/执行/PM1、架构 §2.2–2.3、§3.1/3.4–3.6、§4.5–4.8、§5.6–5.9、§11.2–11.3/11.14–11.15、§12.3/12.5、W008 输入/几何/占用公开合同、W003 contracts 和 MR-045/046/052/054/056。旧 MR 的 body/网格说明按各自历史版本理解，当前样本采用 W004 修订后的 owner/context。未将后置的完整工艺坐标、connectivity、canonical device/net join、FIN/body、baseline/Stage6 或 U06 缺外部上下文问题列为本轮缺陷；当前 synthetic body_context 必填保持。
