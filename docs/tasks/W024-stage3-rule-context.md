# W024 从第 0 版建立约束上下文，核验第一条金属间距规则

## 任务要求（PM）

**W024 已验收，PM-01 已关闭。** [PR #91](https://github.com/LucianoHoult/Layauto/pull/91) 已合入 main，结果见[PM2 集成验收](#pm2-integration)。执行分支 `codex/w024-stage3-rule-context`。输入是 [W023](W023-atomic-baseline-publication.md#pm2-integration) 已发布的 synthetic 第 0 版和已封存的上下文。目标是从该版直接回答“这条规则检查什么、实测多少、结果来自哪些图形和哪份工艺文件”。执行 session 交付产品代码，独立 reviewer 复核方案及实现，PM 验收。

[架构 §2.4、§8.1–8.8、§11](../architecture.md) 规定约束引擎读取 Stage 2 的几何、占用、坐标和连通。工艺包提供规则和适用条件。域、索引及用于检查的缓存可重建。当前阶段读入规则目录，并实现其中的 `T07.m1_spacing`。其它规则的执行、候选变化的传播与回滚、全目标判定、Stage 5 收口及 Stage 6 导出后续接续。

### 两个可手算的输入

使用 W003/W004 已验收的正常样本和 [C14](../../tests/fixtures/w003_m1/failures/count_correct_rule_wrong/geometry_change.json)。对临时副本应用现有替换文件，再经 tech bundle 显式选择 W022 完整坐标并重绑 header。发布后以仓库引用为入口。[PM 输入及读回探针](W023/pm_integration.py) · [规则原件](../../tests/fixtures/w003_m1/tech/rules.json)

| 输入 | 从原图得到的判据 | T07 的预期结果 |
| --- | --- | --- |
| 正常 | 4 条 M1 形成 6 个无序对。最近两条在 Y=90…98 nm 上重叠，前一条终止于 X=75，后一条始于 X=80，GDS 偏移 2480、2544。 | 实际间距 5 nm，所选规则要求至少 5 nm，等号通过。 |
| C14 | 相同的两个偏移，后一条左端改为 X=79。源与目标电路的语义仍相同。 | 实际间距 4 nm，该对违反 T07。可从结果反查规则、阈值、两条源记录及本次 snapshot。 |

PM 在实际 W023 合并版用 400 片预算发布两份临时输入。正常版得到 312 片，C14 得到 313 片。读回两版的原始矩形后，各自的 6 对中最小距离平方为 25、16 DBU²，本包 1 DBU 等于 1 nm。两次使用相同规则阈值。此处是验收用独立测量，产品规则入口由本任务实现。

### 验收项

| 项 | 可观察结果 |
| --- | --- |
| A1 已发布输入 | 从正常运行的 context、head、snapshot 及同次或相容的已封存证据创建只读检查上下文。原输入目录已移走、原候选已释放时也能读取。新 run 复用原 head 时能正确定位本次 run 和所检查的版。交叉混用不相容的引用，或缺少必要引用，须能定位拒绝原因。查询前后 repository head、attempt 和既有内容相同。 |
| A2 规则目录 | 从该次绑定的实际 `tech/rules.json` 读取规则、全 cell 范围和 mandatory policy。对本包 10 条必需规则标识 ID、版本、来源、适用对象、参数、关系及缺上下文策略，使下游能区分已实测、尚待求值及已发现的缺项。规则声明的 evaluator 需与执行能力匹配。规则全集和来源可回查。 |
| A3 精确检查 | 从版本中的 M1 精确矩形及单位实算上表两例，返回来源、测量、阈值及具体结论。格边可用于找候选对，格子相邻无法代替线端真实距离。实际同层接触的处理依据所选工艺的几何/接触语义；本条规则没有按网名豁免。另用斜向距离、相同网标但物理分离或换一套格边的定向例，独立核实至少一个容易误判的边界。 |
| A4 缺项与责任 | 缺必要字段、未知 evaluator、关系依据不符等按已绑定 policy 给出可定位状态，沿用上游已明确的拒绝。区分数据无法判断和检查器运行异常。展示 T07 通过时，其它尚待执行的规则仍可见。C14 的单条规则失败可直接查询，运行仍在 sealed_open，原第 0 版仍可读。整轮 `no_change` 和 terminal 结论由后续阶段给出。 |
| A5 交付 | 提供可从文件运行的例子，列明所检查的版本、规则来源与几何见证。记录从已发布版本首次建立上下文和执行 T07 的增量耗时。新增/受影响测试覆盖正常、违反、缺项、跨版本和模块方向。交独立 reviewer 按 GDS 原记录复算一组结果。 |

## 实施与验证

先看 W023 的发布仓库、快照及已绑定的审计记录，查看 `layauto_v2/constraints/` 和既有精确几何能力。提出运行入口、数据归属、规则状态及失败样张后做独立方案复核，再实施。规则包、阈值、层及单位随所选输入绑定。固定 fixture、oracle 和辅助验证程序仅供测试构造和独立对照。

开发、交付与 review 均按[验证分工](../collaboration/rules.md#verification-reuse)运行新增及受影响范围。W023 已承担 Stage 2 阶段双版本全量。后续完整 mandatory 与无修改闭合由 PM 另排集成回归。

## 方案、实施与复核

执行者记录具体方案、受测提交、定向命令和已知限制。独立 reviewer 记录原始发现和复核结论。由 PM 维护任务阶段、验收结果和 main 集成状态。

## 执行 session 启动指令

> 在 `codex/w024-stage3-rule-context` 执行 W024 A1–A5。从已发布第 0 版和绑定工艺建立只读约束上下文，列清本包 10 条规则，先实算 T07。用正常与 C14 的真实文件证明相同两条 M1 在 5 nm 时通过、4 nm 时违反，报告能追到规则和两条原图。先独立复核方案，再实现并跑新增及受影响测试。交独立代码复核后，将实现、样例和证据推回原分支交 PM。

## 执行交付

[受审方案](W024/plan.md) · [独立复核与原始发现](W024/review.md) · [可复跑示例](W024/example.py)

从仓库根目录运行以下命令。示例先用实际文件发布两个第 0 版，移除临时输入后，通过本次 run 的封存引用读取工艺并执行 T07。JSON 给出全部规则的原声明和状态、snapshot、阈值字段、最近一对的两个原始记录位置，以及首次加载和求值各自的耗时。

```sh
PYTHONPATH=.:tests/contracts python -B docs/tasks/W024/example.py
```

[PM 交接与定向验证](W024/verification.md) · [两版完整报告](W024/evidence.json) · [从原始 GDS 独立复算](W024/review_probe.py)

原分支上的产品提交为 `1828ec860b2bf5be71f56ed91bb9c68a8acc67bd`，其完整 Git tree 与受测修复版 `54554871c685cd06dae482ce95736ebb079c9c84` 一致。开发版与修复后的交付版分别通过 108 项新增及受影响检查，严格类型检查覆盖 94 个源文件。独立 reviewer 已从两份 GDS 原记录复算全部 12 个距离与逐对状态，并复核跨版本混用问题的修复。执行交付提交 PM 验收。

<a id="pm1-receipt"></a>

## PM1 验收与补修

**2026-11-27，PM-01（P2）阻止合并。** 核对远端交付 `22b985d25d5181411fdc097d15967c57e2b6c454`。在此提交的 Python 3.12.14 环境中，PM 用仓库已有的 GDS 字节探针复算了两份样本各 6 对距离。阈值均为 5 nm。正常版最近 5 nm，C14 最近 4 nm 且仅一对违反。Python 3.10.22 另跑精确距离与依赖边界共 9 项，通过。交付版的产品、测试和包配置与已复核的产品提交 `1828ec860b2bf5be71f56ed91bb9c68a8acc67bd` 一致。执行侧的 108 项定向检查、94 个源文件的严格类型检查和安装证据见[执行记录](W024/verification.md)。

**问题属于 A1 的必要引用和版号追溯。** 新运行复用已有 head 时，结果的 `version.original_checkpoint_ref` 对外提供原版的输入记录。两次运行均成功封存后，如果这条记录丢失，使用原运行打开上下文会准确报错，使用复用运行却仍能打开，T07 报告通过并返回已无法读取的原版引用。正常数据中的几何计算已核实。现象限于本次模拟的仓库记录缺失。[检查入口](../../layauto_v2/pipeline.py) · [可复跑的 PM 探针](W024/pm01_checkpoint.py)

探针使用真实样本文件先建立第 0 版，再以新 run 复用，删除临时输入后才开始查询。两者最初均通过，共用 head/snapshot，各自的 checkpoint 不同。随后沿用 W023 的仓库故障注入方式，在隔离的内存仓库中仅移除建版 run 的 checkpoint，其余内容及引用完整。PM 实跑结果如下。

| 读取对象 | 在同一个模拟故障下的实际结果 |
| --- | --- |
| 仓库直接读取原版 checkpoint | `RefConflict`，指出完整缺失引用 |
| 原运行打开 Stage 3 上下文 | 同一 `RefConflict`、同一引用 |
| 复用运行打开 Stage 3 上下文 | 成功；T07 给出 6 对、最小 5 nm、通过，报告仍引用缺失记录 |

本次缺失引用为 `checkpoint:creator:3681781083ff053577cd10700447dc348c132a0cd0606ce76553cf2ba1b0cc12`。两次查询后仓库 root 和 head 保持原样。重新捕获时完整引用可随临时目录变化。以下命令从仓库根目录执行，最后一条在本交付提交结束于 `AssertionError: missing original checkpoint accepted by ['reuse']`。

```sh
python -B docs/tasks/W024/review_probe.py docs/tasks/W024/evidence.json
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest -p no:cacheprovider -q tests/unit/test_w024_spacing.py tests/contracts/test_w024_boundaries.py
PYTHONPATH=.:tests/contracts python -B docs/tasks/W024/pm01_checkpoint.py
```

**补修验收。** 在打开已封存的检查上下文时，确保返回给调用方的原版 checkpoint 可以按所给引用通过仓库校验；对与本次相同的引用复用已有读取。正常建版和正常复用继续使用各自的运行资料，保留原版来源。原版 checkpoint 缺失或内容摘要不符时，能在打开上下文时定位该引用，仓库保持只读。新增一项针对原版损坏的独立对照，与上述缺失及正常样本一同核实。按[验证分工](../collaboration/rules.md#verification-reuse)跑新增和受影响检查，交独立 reviewer 复核，再推回 W024 原分支申请 PM 重新验收。

## PM-01 执行补修与复验

起点为 `58698b964bf685a9830ded54490de0e00de709a0`。先运行 PM 的原探针，两次健康查询均为 5 nm。移除 `checkpoint:creator:7c697a1a882ac5c20a88b522407f040b0ade40d682e980869eacee870b999f26` 后，首次建版 run 报出该引用，复用 run 仍返回通过。探针以 `AssertionError: missing original checkpoint accepted by ['reuse']` 退出。

修复提交为 `c3112971a85fd14645fbda996d1574bdb79d70b4`。Stage 3 打开入口已读取本次封存的 checkpoint。若快照引用的是另一条原版 checkpoint，入口在返回报告前再用仓库的 `read` 核实该原版记录。相同引用沿用本次读取。仓库校验记录字节的 SHA-256 和内容引用中的类型、run、摘要，缺失及损坏沿用带完整引用的 `RefConflict`。工艺 owner 仍从检查 run 自己的采集记录解析。[入口修正](https://github.com/LucianoHoult/Layauto/commit/c3112971a85fd14645fbda996d1574bdb79d70b4)

在仓库根目录使用项目开发环境复跑。第一条为 PM 的缺失探针，第二条为独立 reviewer 的损坏对照。定向合同覆盖真实文件发布与复用、内容读取次数、损坏定位、源几何、跨版、只读和模块依赖。

```sh
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
PYTHONPATH=.:tests/contracts python -B docs/tasks/W024/pm01_checkpoint.py
PYTHONPATH=.:tests/contracts python -B docs/tasks/W024/pm01_review_probe.py
python -B -m pytest -q --tb=short -p no:cacheprovider \
  tests/contracts/test_w024_context.py::test_open_reads_each_distinct_checkpoint_once \
  tests/contracts/test_w024_context.py::test_open_rejects_unreadable_original_checkpoint \
  tests/contracts/test_w024_context.py::test_rule_book_and_raw_gds_witnesses \
  tests/contracts/test_w024_context.py::test_reuse_crossed_missing_and_immutable_refs \
  tests/contracts/test_w024_context.py::test_changed_gds_cannot_reuse_normal_head \
  tests/contracts/test_w024_boundaries.py tests/unit/test_w024_spacing.py
python -B -m pytest -q --tb=short -p no:cacheprovider \
  tests/contracts/test_w023_publication.py::test_new_run_seals_own_checkpoint_and_replays \
  tests/contracts/test_w023_publication.py::test_bad_stored_digest_refuses_seal_without_changing_root
python -m mypy
python -B docs/tasks/W024/review_probe.py docs/tasks/W024/evidence.json
```

修复版重跑 PM 原探针，记录完整时两种运行各查 6 对，最近间距均为 5 nm。移除原版记录后，直接读取、建版 run 和复用 run 均得到 `RefConflict`，三者准确指出同一条缺失引用 `checkpoint:creator:9aee242f2066aa5ab07c4b8afe5bb1bc1920f7625ad9487fa0ab12aafeee91ca`。复用 run 自己的 checkpoint 仍可读取，各次查询均保持相应的仓库 root 和 head。每次复跑的临时输入目录不同，完整 checkpoint 摘要随之变化。

独立 reviewer 在原引用下换入另一条合法 checkpoint 的字节。原版内容被替换时，建版与复用均在打开时报告原版引用的摘要冲突。反向只替换复用记录，建版仍为 5 nm，复用定位到自身的损坏引用。完整记录时，建版读取一个 checkpoint 一次，复用对两个不同引用各读一次。三组对照前后均核对 root、head 和 attempt。[独立复核记录](W024/pm01-review.md) · [可复跑的损坏对照](W024/pm01_review_probe.py)

在上述修复提交上，CPython 3.12.14、pytest 9.2.0、PyYAML 6.0.3 实跑 Stage 3 的 18 项定向检查（159.44 秒）和 W023 发布复用的 3 项检查（158.37 秒），合计 21 项全部通过。mypy 2.4.1 对 94 个源文件检查通过。原始 GDS 探针对既有正常与 C14 报告的 12 对距离复算通过，最近分别为 5 nm 和 4 nm。其余几何与工艺合同沿用原 W024 交付，合并若改变读取入口、仓库校验或样本，再补跑相应对照。本次修复和复核证据交 PM 重新验收。

<a id="pm2-integration"></a>

## PM2 集成验收

**2026-11-27，W024 A1–A5 验收通过，PM-01 关闭。** 远端交付为 `3fa275f72afee6429ebccf8ac846157ee84df29d`，修复产品为 `c3112971a85fd14645fbda996d1574bdb79d70b4`。PM 核对二者的产品、测试和打包配置无差异，并核查了打开上下文时对两个 checkpoint 引用的处理。在交付提交上，原缺失探针的健康对照两次均为 5 nm。删除原版记录后，首次建版与复用均得到 `RefConflict`，两者都定位本次缺失的 `checkpoint:creator:2cde8b7039febcb45cb871c31aa70b0bbb18227eac60b221537cd7b39863acbd`。[原始问题和验收条件](#pm1-receipt) · [执行与独立复核](W024/pm01-review.md)

[PR #91](https://github.com/LucianoHoult/Layauto/pull/91) 的实际合并提交为 `90dcd50817a087214bd27090094fb1b41497a5b8`。其双亲依次为 `1150605`、`3fa275f`；整棵 Git 树 `a2a9be4410bc7c2ba17f7c61771e92b5602e34cb` 与交付提交相同。PM 在该集成提交使用 Linux、Python 3.12.14 串行实跑以下两个组合探针。

```sh
PYTHONPATH=.:tests/contracts python -B docs/tasks/W024/review_probe.py docs/tasks/W024/evidence.json --published
PYTHONPATH=.:tests/contracts python -B docs/tasks/W024/pm01_review_probe.py
```

| 组合 | 实测 |
| --- | --- |
| 文件 → 第 0 版 → 已封存上下文 → T07 | 对正常和 C14 重新捕获、发布、打开后求值。逐对对上两份 GDS 原字节计算的 12 个距离平方和状态。最近一对的偏移均为 2480 / 2544。正常为 5 nm、零违规；C14 为 4 nm、仅一对违规。跨用 C14 图形和正常版本身份被入口拒绝，查询保持只读。 |
| 健康与损坏的两个 checkpoint | 健康时建版的同一引用读一次，复用对不同引用各读一次，均为 5 nm。用另一运行的合法字节替换建版记录时，两边均报建版引用的摘要冲突。反向只替换复用记录时，建版保持通过，复用定位自身的引用。三组对照中，仓库 root、head 和两个运行的 attempt 保持一致。 |

执行侧修复后的 21 项受影响检查、94 个源文件的类型检查按受测源码和测试身份采信。原交付的 108 项检查及安装示例对应补修前的产品，支持其覆盖的几何、单位、工艺和未改入口行为；补修后的 checkpoint 路径由上表核验。本节点在 synthetic 单进程仓库验证第 0 版的 T07，10 条必需规则中其余 9 条仍待求值。双解释器全量按[验证分工](../collaboration/rules.md#verification-reuse)留到完整 mandatory 与无修改闭合的阶段集成。[下一任务 W025](W025-effective-li-spacing.md)
