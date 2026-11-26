# W021 把同次运行的事实整理成不可变的初始状态候选

## 任务要求（PM）

**W021 已验收并合入 main。** PM-01 已关闭。[实际合并版核验](#pm2-integration) · [原始问题与复现](#pm1-receipt)

W021 是 M1、Stage 2 的产品开发任务。起点是已通过 [PR #83](https://github.com/LucianoHoult/Layauto/pull/83) 集成的 W020，产品提交为 `6cd6b14d41b9f4bc32b64ca62d0be6a731d98391`。执行分支为 `codex/w021-proposed-initial-state`，由独立执行 session 实施、独立 reviewer 复核、PM 验收。

**交付一个后续初始化事务能直接消费的只读候选对象，及其逐项缺口。** 从一次 W020 完整运行组装的事实产生一个 `ProposedInitialState`。下游能读到起始几何、电路现状、占用、网络标注及物理连通，也能单独取得不可变的目标引用。来源相同、内容可复算、缺项可定位。依据为[架构 §2.3](../architecture.md#23-stage-2事实归一化与-layout-state-构建)、[状态职责](../architecture.md#113-state)、[初始化事务的输入](../architecture.md#118-transactions)与 [W020 发布缺口](W020/readiness.md)。

| 验收项 | 可观察结果 |
| --- | --- |
| A1 候选与所有权 | 在中立的 `state/mutation.py` 定义候选合同，由 normalization 从同一次认证的组装结果构建。持有或引用可解析的冻结数据，明确单位、坐标、工艺、来源与绑定。current 来自 source，target/intent 作为独立上下文引用。下游从候选查询数据时无需重新读文件、执行整条归一化或解析示例 JSON。 |
| A2 准确和未知均可查 | 通过候选回查 W020 的 LI 格 (1,3) 的 60 DBU²、三节点物理分量与 R04/VSS；同时查得 M1 的 130 DBU² 末格、无标注的 MARKER、本地 B 网络未知与外部 synthetic body 关联。缩短 R04 后，该格失去直接覆盖，边和分量保持。保留未覆盖区域的证据范围和适用保守策略。 |
| A3 层和缺项可定位 | 从现有声明计算每层几何记录、投影与初始化依据。至少区分可重建的 FIN/LI/M1、显式跳过投影仍保留几何的 BOUNDARY/MARKER、有几何但缺声明的 POLY，以及本次无本地记录的层。分别给出几何生命周期和占用可用性。用 POLY 说明需要哪些字段、由谁提供、阻断哪个操作。只有既有合同要求的缺项才阻断对应能力；当前一条栅形给不出栅距，不填入推算值。 |
| A4 身份、差异与发布边界 | 同一捕获重复构建得到等价内容和可核对的绑定。两份同名 cell 使用不同输入时，候选只解引用本次来源；按接口形式验证错配被拒或无法构造。C13 目标长度 4n → 5n 和双方字段位置仍可读，current 值保持 4n。尝试从调用方修改候选时原内容保持。成功或失败均可核对原 attempt、checkpoint、终态指针。 |
| A5 交接 | 交付最小 Python 调用、定向合同、受测版本与独立复核。说明事务如何取用候选、逐层初始化还需验证什么。用同一捕获记录组装耗时和新增候选构建耗时、首次构建峰值及输出体积，检查有无重复认证或复制大 wire。 |

## 执行与验证

先给出中立类型、生产方与消费方的依赖方向，并用一个有事实和一个有缺项的样张说明字段含义。由未参与设计的 reviewer 核查来源、只读性和职责后实施。中立类型不依赖 normalization、repository 或 transactions 的具体实现。重用已有几何和证据对象或可解析的引用，保留 geometry 与 connectivity 的所有权。正式发布时的 CAS、初始化事件、sealed context 及 Stage 3–6 留到对应任务实施。[架构模块边界](../architecture.md#1115-模块依赖方向与边界测试)

沿用固定 fixture 的临时副本与已有逐层配置，不把测试假设升为生产工艺值。若正式发布所需层的参数缺乏依据，记录缺项和已有输入能验证的范围；只在确需新增输入语义或改变使用预期时带样张交 PM。开发和交付跑新增及受影响项，按实际修改做类型检查和安装冒烟。下一次双版本全量安排在 Stage 2 首次正式发布第 0 版的集成提交上。[验证分工](../collaboration/rules.md#verification-reuse)

## 执行、复核与 PM 验收

执行和独立复核记录见下文。最终验收见 [PM2](#pm2-integration)。

## 执行 session 启动指令

> 在 `codex/w021-proposed-initial-state` 执行 W021。用 W020 同一次运行的事实构建不可变的初始状态候选，让下游直接读取已知事实、独立目标及按层定位的缺项。用 LI/VSS 追溯、POLY 缺轨道参数、缩短 query 标注及 C13 目标长度差异验证。先独立复核方案，再实现并做独立代码复核；运行新增和受影响项。将代码、复现命令、证据与完整 SHA 推回原分支交 PM。本轮止于候选对象，正式发布第 0 版另行集成。

## 执行交付

基线 `68dba6e2b137f789a906a6f3b9c29b1571b3f938`，受测产品提交 `5c923caeb3bdd317b452504c60293c0cf217e898`，tree `ae155bba3457f5cb53a6de0ee5a9b873715ae4e5`。先由独立 reviewer 复核样张和依赖方向，再实现。独立代码复核另见下列记录。当前交 PM 验收。[方案](W021/plan.md) · [方案复核](W021/plan-review.md) · [代码复核](W021/code-review.md)

### 事务调用与证据

```python
from layauto_v2.normalization.initial_state import build_proposed_initial_state
from layauto_v2.pipeline import assemble_stage2

facts = assemble_stage2(repository, ready, fragment_budget=68)  # W003 逐层样例
candidate = build_proposed_initial_state(facts)
current = candidate.current
intent = candidate.target_context
li = candidate.occupancy.in_cell("LI", 1, 3, view="effective")
poly = candidate.layers["POLY"]
```

Pipeline 可将这个对象传给未来的初始化事务。事务只需引用 `state.mutation.ProposedInitialState`。候选从一份成功的 W020 组装结果读取现有单位、工艺、输入 SHA 和 readback 引用。目标及 typed differences 在独立的 `target_context`。正常 Python 读写接口沿用上游 frozen DTO 的不可变约定。占用与本地连通共用相同 effective 和 layout 对象，未增加第二份几何或 wire。[合同测试](../../tests/contracts/test_w021_initial_state.py) · [实现](../../layauto_v2/normalization/initial_state.py)

| 验收项 | 观测 |
| --- | --- |
| A1、A4 | 同一绝对路径、请求和 cell，两个仓库分别捕获原样和缩短 R04 加 C13 的输入。移开文件树后从各自 checkpoint 组装。双向交换 ready 均触发 ReadbackConflict。每份候选重建相等，替换 target、写 layer 表和嵌套 readback 均失败。MN0 current 的 L=4n，target L=5n，差异回到各自 CDL 第 3 行及文件哈希。成功与错配前后仓库快照相等，attempt 仍为 unsealed、revision 1，未写终态。W020 预算与算子失败路径也已重跑。 |
| A2 | LI (1,3) 的 60 DBU² 格片经有效 region、节点、三成员分量和 target 连到覆盖该片的 R04/n_lo/VSS。把 R04 的下边从 30 调到 50 nm 后，整格落入 unknown 片，保留 suspect_conductor 策略；边和分量逐项相同。M1 (2,2) 为 130 DBU²。MARKER 保留且没有网络目标，规则包 T10 对未知非导体要求 preserve_disclose。两个 B 端保留本地分量、空本地网络以及分别指向 VSS/VDD 的外部 synthetic 关系，LVS 为 not_run。 |
| A3 | 15 个层各自保留 drawn policy、声明位置、原图数、分源重建数及诊断。FIN/LI/M1 分别重建 18/3/4 条原图，LI 另重建 3 个有效片。BOUNDARY/MARKER 显式跳过投影，生命周期分别为 frame_static/preserve_drawn。CUT 等层计数为零。POLY 的一条 gate 在偏移 432，工艺包的 coordinate owner 缺该层条目；栅轨初始化须取得 index_axis、节距、首中心依据及编号范围，具体字段可读 `poly.gap.required_fields`。可从现有原图检查栅宽、位置及相交，栅距仍待工艺方声明。 |
| A5 | Linux、CPython 3.12.14 的干净 wheel 环境，单次 C13/W018 捕获组装 55.907 秒，首次增量构建 6.90 毫秒。仅在构建候选时开启 tracemalloc，新增驻留 6,784 字节，临时分配在内的峰值 10,553 字节。全进程峰值 RSS 265,838,592 字节。示例输出 JSON 为 4,735 字节，内容是诊断摘要。构造路径复用 semantic_facts、annotation、graph 和索引，逐源计数与小型片引用参与计算。 |

后续发布前，按选定能力核对每层要求和来源。投影层核对原图与有效片的精确覆盖及逐源诊断。frame_static 层须核 frame/boundary 签名，preserve_drawn 层核原图重数、身份与等价性；若选择 derived，需版本化算子、依赖及比较器。保留未覆盖区与关联证据的范围，再由事务完成原子发布。[逐层实测输出](W021/evidence/first-build.json) · [完整调用](W021/example.py)

### 复现与验证范围

在受测提交的仓库根目录执行。开发包版本见[环境记录](W021/evidence/dev-packages.txt)。

```sh
python -m venv /tmp/w21dev
. /tmp/w21dev/bin/activate
python -m pip install '.[dev]' wheel setuptools
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1
python -m pytest -p no:cacheprovider -q tests/contracts/test_w021_initial_state.py
python -m pytest -p no:cacheprovider -q tests/contracts/test_w020_stage2.py
python -m pytest -p no:cacheprovider -q tests/contracts/test_w018_projection.py -k 'sample_identity or direct_physical_parameters_on_vertical_poly_strip or cut_islands_same_cell or negative_origin'
python -m mypy
python -m mypy layauto_v2/state/mutation.py layauto_v2/normalization/initial_state.py
python -m build --no-isolation -o /tmp/w21dist
python -m venv /tmp/w21wheel
/tmp/w21wheel/bin/pip install /tmp/w21dist/*.whl
/tmp/w21wheel/bin/pip check
/tmp/w21wheel/bin/python -I docs/tasks/W021/example.py
```

实跑 W021 **4 passed**、W020 **10 passed**、W018 投影专项 **4 passed**，mypy 配置范围 84 文件和两处改动的显式检查均通过。sdist 与从 sdist 构建的 wheel 成功，干净安装 pip check 和隔离模式下完整调用通过。受测 wheel SHA-256 为 `ac1e5f8824e447b14340b0d0fba3b55fa504a39e7e904a1fab2be0f748097f05`。本轮按身份沿用 W020 未修改生产者与 W018 固定样本。若生产者、候选、输入、依赖或集成行为变更，补跑受影响范围。双解释器全量留到 Stage 2 首次正式发布的集成提交。

<a id="pm1-receipt"></a>

## PM1 接收与补修

2026-11-25，PM 接收原分支交付 `ee072dd5a09c05e226f951d8d535473851206221`，核对产品提交 `5c923caeb3bdd317b452504c60293c0cf217e898` 及受审 tree `ae155bba3457f5cb53a6de0ee5a9b873715ae4e5`。交付版的产品、测试、配置及示例与该产品提交相同。剩余必须修正项 1（P2），待独立定向复核后再合并。

**PM-01　验证范围漏掉了一条受影响的既有架构合同。** W007 的检查遍历 normalization 下的所有 Python 模块，按文件、模块及符号逐项限定允许访问的 state 类型。W021 的生产者 `normalization/initial_state.py` 新增了下表两条导入。它们符合任务卡 A1 的依赖方向，但当前检查未登记，因此实际运行失败。[产品导入](../../layauto_v2/normalization/initial_state.py) · [已有依赖检查](../../tests/contracts/test_w007_contracts.py) · [架构 §11.8](../architecture.md#118-transactions)

| 模块 | W021 使用的只读类型 |
| --- | --- |
| `layauto_v2.state.discrete_occupancy` | `DiscreteOccupancy`、`ProjectionDiagnostic` |
| `layauto_v2.state.mutation` | `LayerInitialization`、`ProjectionGap`、`ProposedInitialState`、`TargetContext` |

在仓库根目录使用本项目 Python 环境复现：

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest -p no:cacheprovider -q --tb=short tests/contracts/test_w007_contracts.py::test_normalization_and_new_domain_keep_pure_dependency_boundaries
```

| PM 实跑，Linux / CPython 3.12.14 | 结果 |
| --- | --- |
| 上一版 main `68dba6e` 与 W021 交付版运行同一条 W007 检查 | 基线通过；W021 失败，`assert violations == []` 报告上表两处模块。 |
| W021 的 4 项新合同 | 4 项通过。含 LI 的 60 DBU²、R04 截短后直接标注变为 unknown 且物理分量和边相等、POLY 缺坐标参数、C13 目标 4n → 5n 以及两份捕获互换失败。 |
| W005、W006、W008、W013 的相邻依赖方向检查 | 4 项通过，分别为 `test_importer_and_domain_dependency_direction`、`test_dependency_direction_and_no_builtin_hash_as_content_identity`、`test_domain_state_dependency_direction_and_no_hidden_occupancy_owner` 和 `test_new_modules_keep_declared_dependency_and_no_io_boundaries`。 |
| 临时隔离副本中的修正试验 | 仅为 `initial_state.py` 登记表中 6 个类型后，原测试通过。再分别尝试额外导入同模块的 `build_discrete_occupancy` 或 repository 的 `PublicationRepository`，原测试均按预期失败。试验没有改动交付版本。 |

执行侧 18 项定向结果、typing、构建及安装证据按上述产品身份采信。下一次双版本全量仍在 Stage 2 首次正式发布第 0 版的集成节点。

**原执行 session 补修指令**

> 在 `codex/w021-proposed-initial-state` 接续本节 PM-01。先复现 W007 依赖检查失败，再按既有按文件、模块和符号登记的方式，为 W021 生产者补齐上表六个类型。保持仓库和事务等依赖的原有限制。用原测试验证，另在临时副本验证额外导入仍被拒；请独立 reviewer 核查改动和反例。若改动仅限检查及证据，产品回归、构建、安装按原受测身份采信。将补修、命令、结果与完整 SHA 推回原分支，交 PM 重新验收。

### PM-01 补修交付

起点 `892eb3ac891b6da2654d293b1c0f904afa37a8c4`，补修提交 `1347a2be2509820cc37ba746436126016af31498`。在 W007 已有的 `component_seams` 表中为 `initial_state.py` 增加上表两个模块、六个符号。相对起点，该提交仅改动 `tests/contracts/test_w007_contracts.py` 的四行登记。[补修 diff](https://github.com/LucianoHoult/Layauto/commit/1347a2be2509820cc37ba746436126016af31498)

| 实跑版本或临时改动 | W007 原测试结果 |
| --- | --- |
| 起点，未修改 | 1 failed。依赖检查在 `assert violations == []` 报告 initial_state.py 的 discrete_occupancy、mutation 两处导入。 |
| 补修提交 | 1 passed。 |
| 补修副本增加同模块的 build_discrete_occupancy | 1 failed。唯一违规来自 initial_state.py 的 layauto_v2.state.discrete_occupancy 导入。 |
| 另一补修副本增加 PublicationRepository | 1 failed。唯一违规来自 initial_state.py 的 layauto_v2.repository 导入。 |

Linux、CPython 3.12.14、pytest 9.2.0。在起点与补修提交的仓库根目录分别运行 PM1 节的原命令。临时反例可在补修提交根目录用相同环境复现，以下每轮均复制干净的产品与测试，检查原断言和违规文件、模块。

```sh
python - <<'PY'
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

node = 'tests/contracts/test_w007_contracts.py::test_normalization_and_new_domain_keep_pure_dependency_boundaries'
for module, symbol in [('layauto_v2.state.discrete_occupancy', 'build_discrete_occupancy'),
                       ('layauto_v2.repository', 'PublicationRepository')]:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name in ('layauto_v2', 'tests'):
            shutil.copytree(name, root / name)
        shutil.copy2('pyproject.toml', root)
        source = root / 'layauto_v2/normalization/initial_state.py'
        with source.open('a') as output:
            print(f'\nfrom {module} import {symbol}', file=output)
        result = subprocess.run([sys.executable, '-B', '-m', 'pytest', '-p', 'no:cacheprovider',
                                 '-q', '--tb=short', node], cwd=root, capture_output=True, text=True,
                                env={**os.environ, 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'})
        print(symbol, result.stdout)
        assert result.returncode == 1 and '1 failed' in result.stdout
        assert 'assert violations == []' in result.stdout and str(source) in result.stdout
        assert module in result.stdout
PY
```

产品、输入、配置与 W021 受测提交相同，原 18 项定向测试、typing、构建和安装证据按 PM1 记录采信。本次新增证据覆盖漏跑的 W007 合同及负例，交 PM 重新验收。[独立补修复核](W021/code-review.md#pm-01)

<a id="pm2-integration"></a>

## PM2 补修接收与集成核验

**2026-11-26，W021 A1–A5 在 W003/W004 synthetic 范围验收，PM-01 关闭。** [PR #85](https://github.com/LucianoHoult/Layauto/pull/85) 已合入 main，实际产品提交为 `565412819167cea6165486e5ee4b4319c6aca52f`。交付版 `ad8f1af99698c64c7d2f3c62f13eb96133759b5d`、PR 的合并候选和实际合并版的完整 tree 均为 `fc297794bbd41858585a86d333b8e32e8d35da2c`。

| 核验 | PM 实测或采信依据 |
| --- | --- |
| 补修内容与边界 | `1347a2be2509820cc37ba746436126016af31498` 只在既有测试中为 `initial_state.py` 增加四行，按模块登记六个只读类型。交接补记只涉及文档。产品、配置、固定 fixture、W021 示例和 W021 正式合同与原受测产品 `5c923ca` 相同。 |
| 交付版定向复跑 | Linux、Python 3.12.14。原先失败的 W007 依赖检查和相邻的 W008、W013 模块边界检查共 3 项通过。在三份逐次还原的临时变体中，同模块的额外函数、其他文件导入已登记的类型、生产者导入 repository 均被原测试定位拒绝。原失败记录见 [PM1](#pm1-receipt)。 |
| 实际合并版组合验证 | 从实际合并提交运行下方命令，5 项通过（107.56 秒）。W021 合同使用真实文件并交叉核对两份同名捕获，覆盖 LI/VSS、R04 截短后的 unknown 和不变的物理边及分量、M1 末格、缺声明的 POLY、外部 body 范围，以及 MN0 的 4n → 5n 差异。候选构建前后仓库快照相等。 |
| 证据复用与范围 | 原 18 项新增及受影响合同、类型检查、构建、干净安装按原产品身份采信。[补修独立复核](W021/code-review.md#pm-01) 保留基线、修正、反例。双解释器全量仍安排在首次正式发布第 0 版的集成节点。真实 PDK、生产 LVS 另按其节点验收。 |

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest -p no:cacheprovider -q tests/contracts/test_w007_contracts.py::test_normalization_and_new_domain_keep_pure_dependency_boundaries tests/contracts/test_w021_initial_state.py
```

下一项 [W022](W022-layer-initialization-checks.md) 使用本候选做逐层初始化校验，之后由初始化事务原子发布第 0 版。
