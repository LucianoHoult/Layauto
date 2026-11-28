# W027 交付与复现

最终受检实现与测试提交为 `86cafe8f06b622d22f80b4b8f35d4ec50beb7579`。起点 `b94c03e83fe16b7037a103e1c76e24e14a5a2f56`，交付分支 `codex/w027-no-change-closure`。适用范围为 synthetic 单 cell、whole-intent 和单进程仓库。阶段结束于 `stage5_closed`。Stage 6 可从 attempt 的 closure 引用读回 RunRecord 里的 `final_snapshot_ref`。

## 运行示例

从仓库根目录，在 Python 3.10+ 且已安装 `.[dev]` 的环境执行。每例在临时目录准备 W003/W004 实际文件，换入 W022 完整坐标并重绑工艺和 header。一次捕获、一次发布、一次目标判断；仅对规划放行的版本调用一次 W026。

```sh
PYTHONPATH=.:tests/contracts python -B docs/tasks/W027/example.py
PYTHONPATH=.:tests/contracts python -B docs/tasks/W027/example.py --all-evidence combined
```

默认输出包含正常、C13、两项目标同时改变、C16、C14、C15、双违规及缺 T07。每行通过仓库引用读出原 head、快照、关闭记录、目标与规则依据。可在同一进程用 README 中的 `run_stage5` 调用直接运行和重试。按原请求重放返回首次关闭的引用。文件中的 SHA-256 和位置用于核对对应输入，本次运行的内容引用可在当次仓库内解析。进程退出后保留的交付证据是示例输出。

## 定向验证命令

```sh
python -B -m pytest -q tests/unit/test_w027_*.py tests/contracts/test_w027_*.py
python -B -m pytest -q tests/unit/test_w006_publication.py tests/contracts/test_w006_*.py tests/contracts/test_w023_*.py
python -B -m pytest -q tests/unit/test_w024_spacing.py tests/unit/test_w025_spacing.py tests/contracts/test_w024_*.py tests/contracts/test_w025_*.py tests/contracts/test_w026_*.py
python -m mypy
```

下列命令构建发布包，在干净环境从 wheel 安装，先加载安装的库，再借用仓库内样本准备器。要求当前解释器已安装 build，并能获得项目运行依赖。

```sh
dest=$(mktemp -d)
python -m build --outdir "$dest/dist"
python -m venv "$dest/env"
"$dest/env/bin/python" -m pip install "$dest"/dist/*.whl pytest
"$dest/env/bin/python" -m pip check
"$dest/env/bin/python" -IB - "$PWD" <<'PY'
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import layauto_v2
from layauto_v2.pipeline import run_stage5
assert Path(layauto_v2.__file__).resolve().is_relative_to(sys.prefix)
root = Path(sys.argv[1]).resolve()
sys.path.extend((str(root), str(root / 'tests/contracts')))
from docs.tasks.W027.example import publish_sample, stage_sample
with TemporaryDirectory() as tmp:
    repo, req = publish_sample(stage_sample(Path(tmp), 'combined'), 'wheel-combined')
    closure = run_stage5(repo, req)
    assert repo.read(repo.load_attempt(req.run_id).closure_ref) == closure == run_stage5(repo, req)
    record = repo.read(closure.run_record_ref)
    failed = [r['id'] for r in repo.read(record.rule_ref).checks if r['status'] != 'pass']
    assert record.status == 'sealed_no_publication' and failed == ['T05.contact_enclosure', 'T07.m1_spacing']
    print(record.final_snapshot_ref.id, failed)
PY
```

## 仓库读回结果

[八个样例的实际输出](sample-results.jsonl)包含本次内容引用、输入 SHA-256、对象及位置、逐项规则状态和三段实测秒数。计时列中，目标判断含从仓库打开封存视图，规则列含 W026 调用和审计转换，关闭列含 CAS、编码及仓库根切换。各运行共用开发机，数字用于复现运行量级。

| 输入 | 判定和来源 | 目标 (s) | 规则 (s) | 关闭 (s) |
| --- | --- | ---: | ---: | ---: |
| normal | MN0/MP0 为 5/7，十条通过，原快照关闭为 no_change | 2.791 | 0.203 | 0.558 |
| c13 | MN0 长度从 4 nm 改为 5 nm，UnsupportedTargetAxis，双方 CDL 第 3 行 | 2.697 | 未调用 | 0.133 |
| multi | 另有 MP0 宽度从 2 nm 改为 3 nm，两项目标均可定位 | 3.011 | 未调用 | 0.249 |
| c16 | 零项语义差异，MN0 实测 4，双方 CDL 第 3 行均声明 5 | 2.785 | 未调用 | 0.173 |
| c14 | T07 实测 4 nm，要求 5 nm，GDS 偏移 2480/2544 | 1.299 | 0.077 | 0.285 |
| c15 | T05 四边余量为 5、20、−3、1 nm，要求至少 1 nm，GDS 偏移 2096/1648 | 1.253 | 0.087 | 0.262 |
| combined | 同一份 W026 整包记录 T05、T07 两处违规，其余八条通过 | 1.237 | 0.092 | 0.308 |
| missing_t07 | T07 的 MissingRule 指向规则目录 /rules，策略 indeterminate_then_reject，其余九条通过 | 1.236 | 0.076 | 0.220 |

输出文件 SHA-256 为 `5ded700d8534668a6006a50f50de814a90c5a4ba7449d8db2cb373d28b4f3e41`。默认示例用相同的显示层分两批运行。正常样本有 12 项参数语义比较、20 项与两份 CDL 的参数测量对照、8 项端子物理关系。三个 Stage 4 拒绝样本的规则审计引用均为空。八例从仓库读出的 head 都为受检 head，ECO 链均为空。

## 核验范围

- **实现与独立复核。** [实施方案](plan.md)与[方案复核](plan-review.md)先于产品改动。代码复核发现规则行的汇总状态可能与细项证据矛盾。修复后，对真实双违规报告注入错误的通过状态，仍能从仓库读回 T05、T07 的阻止原因和对应 GDS 偏移。[独立复核、版本与复现](code-review.md)
- **身份与原子性。** 真实发布和复用覆盖了创建运行与检查运行不同、错 head、错快照及陈旧 revision。测试在一次仓库根切换的前后注入中断和响应丢失，分别核对原状态和已提交回执；同键改请求或改审计内容出现冲突。RunRecord 构造错误生成专门关闭变体，写入失败保持原状态。另有八个 W006/W023 旧编码样本，用起点的内容摘要重新验证。[边界测试](../../../tests/contracts/test_w027_boundaries.py) · [历史内容地址](../../../tests/unit/test_w027_wire_compatibility.py)
- **构建与安装。** 用最终受检提交的干净源码构建 sdist 和 wheel，在仓库外的独立环境安装，`pip check` 通过。实际导入路径位于该环境的 `site-packages`。wheel 从头发布组合样本并读回 T05/T07 两处违规；第二次同键请求返回原关闭记录。该次 wheel 的 SHA-256 为 `fcf1baf36d6ba8ea320d542b345583180f8b8f335f0f4876c20ddb633913b94a`，sdist 为 `372dfd1e2160c59fd08889b84afa41067decf460479757a5db321aec89207cb3`。
- **新增检查。** 在 Linux、CPython 3.12.14 上，W027 的 25 个不同测试均已分组实跑。10 个文件到仓库合同包含单项执行错误和缺少端子证据；3 个 Stage 4 合同含空差异表及零 FIN 反例；9 个关闭边界合同涵盖未封存及并发直接关闭；3 个单元合同核验规则报告矛盾及旧 wire。最终实现通过项目配置的严格 mypy，覆盖 109 个源文件。
- **修正后的复验。** 对规则冻结修复重跑了行状态矛盾单测及真实 C14/C15 错报通过的独立探针。对零 FIN 分类重跑物理缺证及语义差异对照。对并发补丁重跑线程直接关闭与管线竞争的用例。旧 W006 单测中对接口尚未存在的断言已随功能更新，并补测未封存 attempt 调用新的公开入口应无副作用。更新后的 W006 发布单测共 56 项通过。
- **受影响回归。** W006/W023 的 135 项、W024/W025 的 38 项、W026 的 20 项均已通过。W026 包括器件 6 项、图形和生命周期 8 项、整包/包围/策略 6 项。连同 W027 的 25 项，去重后的定向范围为 218 项。W024/W025 跑完后，其余 W026 用例分组完成，计数按测试节点去重。
- **验证复用与 PM 范围。** 上述检查在开发与交付过程中分批实跑。W006/W023 的捕获、初始化和旧记录编码，以及 W024–W026 原有物理算子，按起点及对应定向回归采信。涉及 W026 的共用识别函数单独跑过全部六项器件合同。对共享根切换的补丁复跑 W006 的发布合同和 W023 的竞争及响应丢失用例。示例采用相同的真实输入准备和显示层，修正后的错报通过、零 FIN 和重放竞争另有专项证据。依赖、输入、规则策略、发布编码或原子切换发生变化时须重跑对应合同。Python 3.10/3.12 双全量及阶段组合验收由 PM 在实际合并版执行。

执行环境为 Linux，CPython 3.12.14、pytest 9.2.0、mypy 2.4.1。测试输出中的一项弃用提示来自环境加载的 anyio pytest 插件。重试与恢复的边界为同一进程内的同一仓库实例。真实 ECO 属于 M2，导出及 terminal 属于 Stage 6。
