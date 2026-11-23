# W018 独立复核

受审产品为 `186c426ea550a6941ead417cd640a86c37017ba5`，起点为 `e5ea3a08ff6ddd8f406b55067761e5a69627a420`。未参与产品或正式测试实现的 reviewer 检查了两者的完整 diff，并从受审提交的 `git archive` 运行产品。首个样例/手算提交为 `fb6010a87d7bb0f88c84fa95eb4d0c7c79b80a0c`。该 YAML 的 SHA-256 在两次提交上均为 `fefb1bb72c15a131206f2885e1d9dc7ad98463aab676237a410a99d9c3d82890`。

**产品结论。** A1–A4 的配置绑定、精确投影和来源追溯通过独立检查。发现的 R1 已在受审提交关闭，当前产品必须修正项为 0。A5 的独立复核、工程验证与 PM 验收分别记录。

## 独立实跑

复现命令从仓库根目录运行。探针的可选位置参数可指定受审提交的归档根目录，便于直接对照产品来源。

```sh
python -B docs/tasks/W018/review_probe.py
python -B -m pytest -p no:cacheprovider -q tests/unit/test_w018_axes.py tests/unit/test_w018_model.py tests/contracts/test_w018_projection.py tests/contracts/test_w007_contracts.py::test_normalization_and_new_domain_keep_pure_dependency_boundaries tests/contracts/test_w005_contracts.py::test_importer_and_domain_dependency_direction
```

Python 3.12.14 上的[独立探针](review_probe.py)使用独立 GDS reader 读取 UNITS、layer/datatype、XY 与 BOUNDARY 字节偏移，将矩形铺成整数 DBU 单位方块。按源记录和格号逐项比较两个方向的索引与方块集合。预期来自文件、声明和整数算术。测试 helper 只负责在临时副本重绑输入和调用产品。另用独立文件副本手动更新 coordinate owner 和 closure，对非零原点、异源 effective 和稀疏预算进行了交叉检查。上面的 pytest 命令在 Python 3.10.22 上得到 36 passed。

| 检查 | 受审提交上的结果 |
| --- | --- |
| 类型和调用链 | W005 捕获 bundle 所选 coordinate owner，W008 从相同捕获认证。新 binder 先按 `projection` 选择闭合字段集，再产生 `TrackAxis`、`CellGrid` 或显式跳过。内核只接受解析后的轴与本地几何。查阅了配置、分派及 strip 适用性检查的完整路径。将一维 X 法向声明赋给 POLY，在非零原点与编号下界 −3 下，实际偏移 432 的垂直图形命中轨 −3。 |
| 完整覆盖 | 查到 15 项工艺层，共 40 条记录。主 GDS 的 18 条 FIN 分别对应中心 25…195 nm，每隔 10 nm；30 nm 的有符号偏差为 +5/−5。LI 与 M1 分别有 20/10 片，所属格及像素集合逐项相等，面积总和分别为 1110/1340 DBU²，加上 FIN 为 6050 DBU²。S2 附加重复记录后，每个来源都可由 12、12、4、4 DBU² 四个精确片段重建，独立保留 record ID 与偏移。 |
| 同格 CUT 来源 | 独立 GDS 解出的长 LI 和 CUT 位于字节偏移 182、246。专例的格 (4,1) 内有效覆盖为 [130,139) 与 [141,150) 乘 [20,24)，两片各 36 nm²，间隙 2 nm。逐方块核对 `drawn − CUT`，每片均能追溯到各自 region/piece 及同一 CUT。 |
| 缺项、错误、兼容 | 原 owner 仍读出 W008 40 条记录和 41 个旧索引片。新查询逐层报告缺声明；新版的显式跳过、缺声明及各自的空层可区分。缺 LI 的 Y 轴定位至 `/coordinate_projection/layers/LI/y_edges`，仍持有完整 W008。drawn 相等但 coordinate 捕获不同的 W009 被拒绝。 |
| 成本与边界 | 审查先累计 record/piece 贡献，再分配命中格和片段。使用 10³⁰ × 10³⁰ 的 LI 定义域得到同样的 48 个主图片段。预算 46 时替换格边枚举函数为立即抛错的探针，实际返回 `resource_limit`、总数 48、`value=None`。正式测试还覆盖 10¹⁸ 个命中格的满窗预估。 |
| 状态所有权 | W008/W009 的几何继续按源 ID 定位。新索引保存不可变片段，格、层、记录三类索引共享这些片段。直接检查 state 的 imports、来源检查、单位和 model ID；归一化层调用现有认证输入和只读构建器。旧消费者对 W008 分格与引用的使用路径保留。 |

## R1　合法有理数在模型身份计算时失败

冻结前的实现用通用十进制 wire 对派生中心做摘要。将 FIN 下边缘填为 `1 / 10^2200` nm，将宽度填为 `1 / (10^2200 + 1)` nm，各自满足字段文法。文件只有 5843 bytes，实际读取和 W008 认证成功。组合后的中心分母超过 4300 位十进制数字，Python 3.12.14 在 `domain.codec._wire` 中抛出整数转字符串的 `ValueError`，连同已具备双轴的 LI/M1 也无法取得结果。

修复仅作用于 W018 的模型身份，对各类轴和有理数分子分母作精确、带类型的十六进制编码。在受审归档重跑原始反例，得到完整 LI/M1 共 30 片及 18 条 `unsupported_strip` 记录，并验证相邻但不同的精确中心有不同模型身份。R1 已关闭。[持久回归](../../../tests/unit/test_w018_model.py)

## 工程证据与复用边界

核对受审归档的产品树 `bd179818623ec58271a57fb38d8035e8fd41d48f`、测试树 `a321832ecfae5f68b6ed4ccff2ac0ae8c3776869`、pyproject blob `197d03c3c59499d76f6ca28d6049229d192c1d2f`。W003/W004 fixture 子树与起点相同，均为 `c8b85527a7063f4d489f9af6d45fb61204389190`。针对执行矩阵冻结 manifest 的 310 个文件逐个比对字节 SHA-256。核查 3.10.22 与 3.12.14 两边已结束的 mypy、构建、干净安装依赖检查、wheel 字节比对和源码外 smoke 的退出码及日志摘要。每侧 mypy 检查 81 个源文件，smoke 均返回 15 层、40 条记录、48 片及三个可回查的 GDS 偏移。产品复核完成时，双版本全量 pytest 仍在执行。

复核覆盖 synthetic flat-rectangle 内核。生产 PDK、W016 无 tapcell 入口接入及 Stage 2 baseline 发布留给相应任务。源、样例、测试、依赖、捕获身份或实际合并行为变化时，按变化补跑定向检查；产品重新冻结时按仓库规则完成新版本工程矩阵。[验证复用规则](../../collaboration/rules.md#verification-reuse)
