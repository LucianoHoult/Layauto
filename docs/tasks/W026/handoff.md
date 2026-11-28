# W026 执行交接

开发起点为 `f8c06e75917e4fa111b63af179d8b5265218fcbd`，分支为 `codex/w026-connector-enclosure`。本包供 PM 在 Stage 5 集成时显式调用。方案、独立复核及运行入口分别见 [方案](plan.md)、[复核](review.md) 和 [示例](example.py)。

## 复现

从仓库根目录，用已安装项目测试依赖的 Python 3.12 执行。示例仅在临时目录准备文件，每个输入只发布一次。默认打印正常例、双违规例的版本及十条结论。加 `--all-witnesses` 可展开每个对象和来源。规则的声明来源见 `row.rule.source`。间距测量见 `row.pairs`；其他逐项证据见 `row.observations`。无法求值时查看 `row.issue` 和 `row.policy_action`。

```sh
PYTHONPATH=.:tests/contracts python -B docs/tasks/W026/example.py
python -B -m pytest -q tests/contracts/test_w026_*.py
python -B -m pytest -q tests/contracts/test_w024_boundaries.py tests/contracts/test_w024_context.py tests/contracts/test_w025_effective_li.py
python -B -m pytest -q tests/contracts/test_w010_geometry.py -k local_t05_semantics_are_explicitly_checked
python -B -m pytest -q tests/contracts/test_w022_layer_checks.py::test_complete_checks_bind_capture_frame_and_both_owners tests/contracts/test_w022_layer_checks.py::test_dropped_duplicate_and_substituted_frame_are_detected tests/contracts/test_w023_publication.py::test_snapshot_geometry_topology_identity_and_assurance
python -m mypy --strict layauto_v2/constraints layauto_v2/pipeline.py layauto_v2/state/layer_checks.py layauto_v2/state/local_connectivity.py layauto_v2/state/snapshot.py
```

## 实测依据

| 规则 | 对照与位置 |
| --- | --- |
| T01 | 正常框 [0,0,160,200]，M1 电源轨左边余量 0。新增 MARKER 跨至 X=161，Stage 2 初始化在对应 GDS 记录返回 OutsideFrame。 |
| T02 | 18 条 FIN 下边从 24 到 194 nm、宽 2、节距 10。删除最后一条后仍能发布，整包指出声明范围 [0,17] 的第 17 轨缺失。 |
| T03 | MN0、MP0 分别数到 5、7 条 FIN。C13 改变 target.cdl 第 3 行的 L，测得 4 nm、目标 5 nm。 |
| T04 | 本地体区四边、两域反型相交检查、各自的外部 tap/电源轨路径均有见证。错误轨声明在 Stage 2 terminal_relations 返回 BodyTargetRailMismatch，指向 body/context.json#/associations/0/expected_semantic_rail。 |
| T05 | VN/LI 原图偏移 2096/1648。正常余量 1 nm；右移后最小余量 −3 nm，仍有唯一物理边。外部 TN.ext 电源轨余量从 2 降到 1 nm 通过。降到 0 时在 Stage 2 terminal_relations 返回 BodyTapEnclosureFailure，指向 body/context.json#/shapes/4，无 head。额外 CUT 在实际 LI 内造成缺口，外框仍能包围。 |
| T06 | CUT 后 LI 的两个有效区域隔 1 nm，低于 2 nm，双方均可追回原 LI 和 CUT。 |
| T07 | C14 的 M1 记录偏移 2480/2544，正常 5 nm 等号通过，改动后 4 nm。与 VN 组合后分别复现 T05、T07 单项原因，其他八条保留各自结论。 |
| T08 | MN0.D 的声明改为 VDD，本地组件仍观察到 Y。B 端仍按独立外部路径取证。 |
| T09 | 核对原 GDS 记录、frame、source.cdl 语义、快照版本与 head 的零提交链。非零计数声明作为资料不相容处理；更改生命周期算子时 Stage 2 在 tech/physical.json#/operators/lifecycle~11 拒绝。实际导出回读属 Stage 6。 |
| T10 | 新增无标注 MARKER 按 preserve_disclose 保留，图中无导电节点。同名 A 赋给被 CUT 隔断的 LI，两岛和原 A 导体保留不同分量。 |

示例及合同均比较求值前后的完整仓库快照、输入 attempt、head、已发布快照和 sealed context 引用。正常检查保持 sealed_open。缺少声明、冲突声明和注入的执行错误各有定位，独立结果不被覆盖。Stage 4 选择、Stage 5 收口和 M2 修改传播由各自阶段执行。

## 运行记录

两例的实际输出保留了每条结论的代表性见证、来源摘要及受检引用。[示例结果](example-results.jsonl)

正常样本在 Python 3.12.14 上一次发布、一次打开，第 0 版十条均通过。该次输入准备 1.772 s，Stage 2 发布 117.558 s，打开 3.016 s，显式整包求值 0.129 s。与其他定向测试并发测量。正常受检快照摘要为 `bb24185cd25b408cea02c6695791fd8722dfb48bb2bcdbb23a52c3f85ed062d5`，head 摘要为 `f9b8b78e10bc1472e81f13fcee3a3281ff35287f73df796810e203eada55b21b`。每次重跑的标识由该次捕获生成。

上述示例在 `bb998483de34076b20bab48ddbde89e4bae9c85f` 的实现上实跑。最终实现 `017bf8d01ec2ffe21723cfc3b07f615b8664ee17` 为 T10 片段补充了原始几何和网络声明的位置；该增量已独立复核并在同一已发布上下文复验。W024/W025 的原距离算法和 W014 的已绑定外部审计按基线采信，W010/W022 抽出的共用函数和 W023 冻结输出按上列用例复验。双解释器全量、阶段收口与导出回读留给 PM 阶段集成。

本次新增合同共 17 项，按定向用例分组实跑并在修正后复验。四项外框、FIN、标注和异岛用例通过。三项器件/端子和一项多块包围用例通过。三项生命周期公开入口用例通过。整包、策略隔离与额外生命周期比较共六项使用修正后的实现通过，其中正常样本由会话级 fixture 共享。W010 声明消费三项、W022/W023 生产者三项通过。严格类型检查覆盖 16 个源文件，无诊断。pytest 的环境插件 anyio 报告 CallSpec2 弃用提示。

W024 只读依赖方向、上下文/版本错配、专项报告与 W025 有效 LI 间距合同共 25 项通过。本次新增及受影响测试合计 48 项。
