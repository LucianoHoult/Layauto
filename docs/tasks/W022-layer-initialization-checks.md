# W022 核对第 0 版发布前的逐层几何与占用

## 任务要求（PM）

**本轮交付运行代码。** 从 W021 的 `ProposedInitialState` 出发，对本次捕获的每个本地层回答三个问题：哪些原始几何应保留、哪些占用应能从原图或有效区域重建、各项是否有足够依据进入后续发布步骤。下游能直接读取通过的检查及带来源的缺项。任务属于 M1 的 Stage 2，执行分支为 `codex/w022-layer-initialization-checks`，产品基线为 W021 实际集成提交 `565412819167cea6165486e5ee4b4319c6aca52f`。[W021 验收](W021-proposed-initial-state.md#pm2-integration) · [架构 §2.3](../architecture.md#23-stage-2事实归一化与-layout-state-构建) · [逐层生命周期](../architecture.md#94-policy-controlled-geometry-finalization) · [初始化事务](../architecture.md#118-transactions)

### 输入与手算依据

保留原 W003/W004 fixture 和 W018 配置。用临时输入副本，经原有 tech bundle 显式选择坐标文件并重绑 query header。以下两份坐标各有用途。

| 输入 | 预期与来源 |
| --- | --- |
| [W018 原样例](W018/layer-discretization.example.yaml) | 15 层中的 FIN、LI、M1 有坐标；BOUNDARY、MARKER 显式跳过投影；其余 10 层缺声明。POLY 仍有一条原图，能核对位置，无法初始化栅轨。 |
| [W022 完整 synthetic 正例](W022/layer-discretization.synthetic.yaml) | 沿用 W018 已有的 5 项声明。POLY 采用既有垂直栅测试的绝对轨道，保持 W018 的全局原点 (0,0)，令 -3 号轨中心为 60 nm、测试节距为 9 nm。另 9 层各自显式选用与 LI 相同的测试格边。假设只用于本正例。生产参数由工艺配置提供。[原 POLY 定向见证](../../tests/contracts/test_w018_projection.py) |

完整样例沿用 W018 schema，SHA-256 为 `cd25a045187c22d23040ea45363043b33b497d6318890a73a15782b293346009`。PM 已从实际读取的 GDS 走 W008 几何、W009 有效区域与 W018 投影，得到 15 层、40 条 drawn 记录。38 条需投影的原图获得 220 个 drawn 片，另有 92 个 effective 片；两条显式跳过投影的原图仍保留。PM 对照[手工样本](../../tests/fixtures/w003_m1/spec.json)按半开格边独立重算了 220 个 drawn 片。形状的层名在示例中用于定位，算法依据各层的显式声明选择。

PM 也从实际合并版走完 W006 读取、W020 组装及 W021 候选构建。显式片数预算 312 时，候选返回 10 层已重建、2 层显式跳过、3 层无本地图形。POLY 的 -3 号轨回到 GDS 偏移 432，M1 末格仍为 130 DBU²。组装前后仓库快照相等。这个结果验证 W022 正例的输入和上游入口；逐层保真校验本身由执行者交付。

复用 W018 的临时输入流程时，在 `PYTHONPATH=.:tests/contracts` 的仓库根目录可用下段准备输入。随后按 W021 示例对 `root / 'site_config.yaml'` 调用完整入口。本样例的 312 是实测片数，产品继续使用调用方给定的预算。

```python
from pathlib import Path
from shutil import copyfile
from w005_cases import copy_input, rebind
from w018_cases import COORDINATE_URI, select_projection

root = copy_input(temp_dir)  # 调用方创建的临时目录，类型为 Path
select_projection(root)
copyfile(Path("docs/tasks/W022/layer-discretization.synthetic.yaml"), root / COORDINATE_URI)
rebind(root)
```

### 验收项

| 项目 | 可复跑结果 |
| --- | --- |
| A1 按层核验并保留依据 | 从完整运行输入走 W020 → W021 → 本次检查。输出与同次候选、原始证据、坐标及比较器绑定。对每个本地层分别给出生命周期、原图与有效片的检查范围、结论及来源；可区分显式跳过投影、无本地图形、缺声明和重建失败。成功或失败时，原候选和仓库状态均可核对。 |
| A2 几何保真与固定外框 | 按本包的 [drawn 声明](../../tests/fixtures/w003_m1/tech/drawn.json)、[几何比较器](../../tests/fixtures/w003_m1/tech/formats.json)及 [lifecycle/1](../../tests/fixtures/w003_m1/tech/physical.json) 执行。10 层 preserve_drawn 按顶层身份、stream 元素、图层/用途映射、精确矩形与记录重数核对来源；5 层 frame_static 还须绑定实际 BOUNDARY 和适用的外框条件。正例 MARKER 保留、框为 (0,0)–(160,200) DBU。用独立样张证明丢一条重复记录、错绑外框或缺少必要算子/比较器会被检出。该工艺包声明的生命周期仅有上述两种。 |
| A3 工艺坐标和占用 | 按配置中的 1D、2D、显式跳过分派。在完整样例逐源验证投影片位于各自来源内、无丢失、可重建；可复用 W018/W021 已证明的不变量。保留格片到 GDS 记录、effective region/piece 的反查。验证 POLY 的 -3 号轨、M1 末格的 130 DBU²；用 W018 的 CUT 专例复核同格两片各 36 nm²、中间仍有空隙。 |
| A4 对照输入与失败 | 对照原 W018 样例和完整样例。POLY 缺声明时，指出受阻的是栅轨初始化，并保留该层已能核对的原图与生命周期。缩小 M1 网格覆盖范围时，定位越界的原记录。按既有层职责区分必须投影和显式免投影，避免通过删除必需声明获得整体通过。无效工艺字段若已由上游拒绝，保留其原始来源与拒绝阶段。混用其他捕获的证据须被拒绝，或由单一输入的接口排除。 |
| A5 发布交接 | 提供一条从真实文件运行检查的命令、成功与受阻样张，以及一份后续初始化事务可直接消费的只读结果。注明剩余发布条件。保留未知区域、外部 synthetic body 的证据范围和独立 target；目标有差异不会改写当前几何或产生 ECO。记录首次校验的增量耗时和输出体积。 |

## 执行与复核

先用两个输入展示同一层的预期结果，列明每项比较的独立依据。避免用候选与自身比较来证明保真；既有捕获中的源记录和已证的构造不变量可以复用。让独立 reviewer 核对来源、层策略和失败语义后实施。实现遵守中立候选与事务的依赖方向。调用期间沿用已取得的事实，优先复用已验证的算子和投影结果。若需要新生产工艺值或改变对外输入含义，用具体例子交 PM 决定。

开发与交付跑新增及受影响合同，包括涉及的模块边界。独立 reviewer 复算一个几何正例及一个拒绝例。双解释器全量安排在**首次原子发布第 0 版**的实际集成节点。W022 交付逐层校验；后续发布任务负责将快照、初始化事件和 head 一次写入并封存上下文。[验证分工](../collaboration/rules.md#verification-reuse)

## 交接记录

当前由 PM 派发。执行者追加方案、受测版本、命令、结果及限制，独立 reviewer 追加发现和修正复核，PM 验收集成。

## 执行 session 启动指令

> 在 `codex/w022-layer-initialization-checks` 执行 W022 A1–A5。从完整运行构建 W021 候选，再按显式工艺声明逐层核验原图保真、固定外框，以及占用片段能否重建。对照原 W018 配置与 W022 完整合成样例，证明 POLY 缺声明能定位、补声明后可核对，M1 末格和 CUT 同格两片都保留精确覆盖。给出可直接供后续初始化事务读取的校验结果。先独立复核方案，再实现、定向验证及独立代码复核。将代码、复现命令、证据与完整 SHA 推回原分支，交 PM 验收。
