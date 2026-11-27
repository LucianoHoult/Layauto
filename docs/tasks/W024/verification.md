# W024 执行证据与 PM 交接

## 版本与入口

开发基线为 `11506059006f7fb377732b4d0287e1f4fd72e057`。首个受审实现为 `29baffe2985ea01877080a00bff240e706251e1d`，修复复核发现后的受测产品为 `54554871c685cd06dae482ce95736ebb079c9c84`。两个提交都包含对应的产品代码和合同测试。任务记录与原始 reviewer 意见分别由执行与复核角色维护。[方案](plan.md) · [独立复核](review.md)

GitHub 的邮箱隐私保护拒绝了首次推送。交付使用同一作者在仓库历史中已有的 GitHub noreply 地址重建未推送提交。以下两组完整 Git tree 已逐一核对，相同的代码、测试、样本和配置承接原实跑结果。

| 版本 | 实跑提交 | 原分支上的对应提交 | 两者共同的完整 tree |
| --- | --- | --- | --- |
| 首次受审 | `29baffe2985ea01877080a00bff240e706251e1d` | `8c0f2fa3a84cd13996720ff5f9abc787d3901347` | `e49f7094df76608b2c3dffdb8c6097d18f0f66fc` |
| 修复交付 | `54554871c685cd06dae482ce95736ebb079c9c84` | `1828ec860b2bf5be71f56ed91bb9c68a8acc67bd` | `b9b198a2ce086d9d4a0a389a0021a514008b1a5f` |

在原分支上的修复提交另行实跑 13 项距离、依赖方向与上游拒绝检查，全部通过（1.05 秒），并重跑 94 个源文件的严格类型检查及两份报告的原始 GDS 对照。

调用 `open_constraint_context(repo, run_id, attempt.context_ref)`，再调用 `check_m1_spacing(context)`。结果的 `version` 保留检查 run 的 context、checkpoint、tool，以及所查 head、snapshot 和原版 checkpoint。对复用原 head 的新 run，可以分别沿这两组引用查工艺字节和原版几何。目录包含绑定工艺的整行声明和 mandatory policy。用 `report.for_rule('T07.m1_spacing')` 可直接查询单条结果、阈值和违规对。[运行入口](../../../layauto_v2/pipeline.py) · [检查器](../../../layauto_v2/constraints/engine.py)

## 两个文件样本

在临时副本应用原替换文件，显式选择 W022 完整坐标，重绑 header，以 400 片预算调用 W023 发布。临时目录已删除后才首次打开约束上下文。两个样本各有 4 条 M1、6 个无序对，原图中相关线端的 Y 范围均为 90 到 98 nm。所选 canonical DBU 为 1 nm。[正常 GDS](../../../tests/fixtures/w003_m1/source.gds) · [C14 GDS](../../../tests/fixtures/w003_m1/failures/count_correct_rule_wrong/source.gds) · [完整输出](evidence.json)

| 输入 | 偏移 2480 的矩形 DBU | 偏移 2544 的矩形 DBU | 最小距离平方 | T07 |
| --- | --- | --- | ---: | --- |
| 正常 | (50, 90, 75, 98) | (80, 90, 110, 98) | 25 nm² | 5 nm 达到阈值，6 对均通过 |
| C14 | (50, 90, 75, 98) | (79, 90, 110, 98) | 16 nm² | 4 nm，1 对违规 |

两次阈值都来自 `tech/rules.json#/rules/6/parameters/min_distance_nm`。绑定规则文件的 SHA-256 为 `40ce0b76abb28c07ab734734a19d61e1259bc5aee42a8cf2c02fabb9e4457480`。正常 GDS 的 SHA-256 为 `97cf8d88771ff97f2cf189f6ae6a2fdcce585fc14f93c93d0ecf32326b415429`，C14 为 `613e6cbb006ea0739d82bf55774755db7defbc7603435c14e8c04171724ae04f`。每个见证保留原记录 ID、URI、SHA-256、字节偏移和记录序号。同一偏移可在对应 GDS 中定位 BOUNDARY 和 XY。[规则原件](../../../tests/fixtures/w003_m1/tech/rules.json) · [所选物理算子](../../../tests/fixtures/w003_m1/tech/physical.json)

| 必需规则 | 正常 | C14 |
| --- | --- | --- |
| T01.frame | pending | pending |
| T02.fin_grid | pending | pending |
| T03.recognition | pending | pending |
| T04.body | pending | pending |
| T05.contact_enclosure | pending | pending |
| T06.li_spacing | pending | pending |
| T07.m1_spacing | pass | violation |
| T08.terminal_graph | pending | pending |
| T09.lifecycle | pending | pending |
| T10.coverage | pending | pending |

两份报告的 scope 均为 whole_cell，两次 attempt 均为 sealed_open。完整输出列出每行的版本、范围、参数、关系、assurance、evaluator 和缺上下文策略。报告中的仓库引用绑定了本次运行，复跑采用新临时目录时可得到新的内容引用，文件 SHA、矩形和距离可直接对照。

安装版在 CPython 3.12.14 和 PyYAML 6.0.4 下记录的单次增量如下。计时包括仓库读回与工艺字节解析，T07 单列，采集和发布已在计时前完成。[该次原始输出](evidence.json)

| 输入 | 首次建立上下文 | 单次 T07 |
| --- | ---: | ---: |
| 正常 | 1.103156 秒 | 0.302 毫秒 |
| C14 | 0.809640 秒 | 0.240 毫秒 |

## 缺项与边界

| 实际输入或动作 | 查询结果或拒绝位置 |
| --- | --- |
| 换工艺路径、把 T07 调到第 1 行，阈值改成 6 nm，同时更换 M1 格边 | 从 `tech/chosen-rules.json#/rules/0/parameters/min_distance_nm` 读到 6，同一对仍实测 5 nm，判违规 |
| 交换 T06 和 T07 的已知 evaluator | 两条结果均为 indeterminate。T07 定位到 `/rules/6/exact_evaluator_ref` |
| 把 T07 scope 改为仅已标注矩形，或把 spacing/1 改为曼哈顿距离 | indeterminate_then_reject，分别定位到 `/rules/6/scope` 与物理文件的 `/operators/spacing~11` |
| 删除整行 T07 | 所选目录显示实际 9 行，单查 T07 得到 MissingRule，定位到 `/rules` |
| 删除必需 relation_basis、移除阈值、选择未知 evaluator 或更改关系依据 | Stage 1 分别返回 MissingField、RuleDeclarationConflict、UnsupportedRuleVariant、RuleDeclarationConflict，保留源 URI、摘要与字段。运行没有可用的第 0 版 |
| evaluator 抛出 RuntimeError | error_then_reject，问题指向本行 evaluator。KeyboardInterrupt 向调用方传播 |
| 用 C14 输入复用正常 head，或把另一 run 的 context 用于查询 | 分别得到 W023 的 BindingConflict 和 Stage 3 的 ReadbackConflict。原快照可读 |
| 用正常版身份与 C14 几何手工拼成对象 | 公开检查入口拒绝该对象。同一反例见独立复核记录 |

几何边界覆盖 3–4–5 斜向等号、平方距离 18 nm²、非单位 DBU 缩放、重叠、重合记录、共边和点接触。每个样本还核对了查询前后仓库观测、phase 和 terminal 引用。[精确距离](../../../tests/unit/test_w024_spacing.py) · [文件、绑定和失败合同](../../../tests/contracts/test_w024_context.py) · [模块方向](../../../tests/contracts/test_w024_boundaries.py)

## 复跑

在仓库根目录，使用装有项目开发依赖的 Python 3.10+ 执行。示例输出中的两段计时分别覆盖首次读取已发布版本并建立上下文、在该上下文上单次 T07 求值，两段均从发布完成后起算。

```sh
PYTHONPATH=.:tests/contracts python -B docs/tasks/W024/example.py > /tmp/w024-example.json
python -B docs/tasks/W024/review_probe.py /tmp/w024-example.json
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
python -B -m pytest -p no:cacheprovider -q \
  tests/unit/test_w024_spacing.py tests/contracts/test_w024_boundaries.py tests/contracts/test_w024_context.py \
  tests/unit/test_w005_config.py tests/contracts/test_w006_boundaries.py \
  tests/contracts/test_w010_geometry.py::test_same_layer_exact_hand_cases_independent_arrangement \
  tests/contracts/test_w023_boundaries.py \
  tests/contracts/test_w023_publication.py::test_snapshot_geometry_topology_identity_and_assurance \
  tests/contracts/test_w023_publication.py::test_new_run_seals_own_checkpoint_and_replays \
  tests/contracts/test_w023_publication.py::test_existing_head_rejects_rebound_input
python -m mypy
```

## 交付验证环境与范围

独立工作区从首次受审实现 `29baffe2985ea01877080a00bff240e706251e1d` 实跑下列定向范围，108 项通过，用时 687.77 秒。独立复核在该版本上另行复现了跨版反例。修复提交在既有跨版用例中加入该反例，因此用例数相同。在修复提交的独立干净工作区重跑同一组 108 项，全部通过，用时 681.15 秒。

执行检查使用 Linux x86_64、CPython 3.12.14、PyYAML 6.0.3、pytest 9.2.0、mypy 2.4.1。两次提交都通过严格类型检查，覆盖配置中的 94 个源文件。受测产品目录的 Git tree 为 `3a52767a555fc821eb9e7d2072b65b7404194035`，测试目录为 `4fa0e9de292da5726922172e0c6e10692a12d255`，`pyproject.toml` 的 Git blob 为 `79a228fe620eef6ee1ad520f821817c40a7761f6`。上列 pytest 命令按行输出的 108 个 node ID（每行末尾 LF）合并后的 SHA-256 为 `b47b02b8119f00c6f08aa7888aaabb2caa174a1cdc99e7a6572bf00e41764aa1`。

| 定向范围 | 用例数 | 选择依据 |
| --- | ---: | --- |
| W024 文件合同、精确距离、依赖方向 | 24 | 新公开入口、规则值、引用、缺项和运行异常 |
| W005 工艺配置 | 68 | 绑定 owner、声明和上游拒绝沿用原合同 |
| W006、W023 模块方向 | 3 | 封存读取与 pipeline 的模块依赖 |
| W010 同层接触 | 9 | T07 复用的精确接触算子 |
| W023 发布读回、复用和重绑 | 4 | Stage 3 的 head、snapshot 和 run 来源 |

从受测产品提交导出包源码，在仓库外用 build 1.6.1、setuptools 84.2.1 和 wheel 0.48.0 构建 sdist 和 wheel。wheel 的 SHA-256 为 `5608168d7848a0ac365b33f59a51fdb954857d413f4bb7a8a5fd7fb794fbb971`，sdist 为 `2c0d3fc26ebf57167bd278c5739e640ed04ea86e182048993d1ec87f559acab1`。在新虚拟环境中安装 wheel，`pip check` 通过。受测 checkout、sdist、wheel、安装目录中的 134 个包文件逐字节相同。在仓库外运行同一示例，产品导入自安装目录，所装运行依赖为 PyYAML 6.0.4、NumPy 2.5.5 和 Matplotlib 3.11.2。保留的 JSON 文件 SHA-256 为 `c78b52bfc52dc95af906bc9d87a0576f6935456597df95bd6e6076eec86a077e`。[安装版输出](evidence.json)

W023 的 Stage 2 发布、仓库、快照编码及两份原始样本沿用起点身份。该阶段双解释器全量的范围、环境与结果见 [W023 PM2](../W023-atomic-baseline-publication.md#pm2-integration)。W024 交付覆盖所选 synthetic 工艺和第 0 版只读查询。其它九条规则求值、整轮 no_change 以及终态由后续任务承担。实际合并若改变相关代码、工艺或样本身份，需补跑受影响合同及两份文件样例。
