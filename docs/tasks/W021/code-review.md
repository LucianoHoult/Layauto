# W021 独立代码复核

基线为 `68dba6e2b137f789a906a6f3b9c29b1571b3f938`，分支最终受审产品提交为 `5c923caeb3bdd317b452504c60293c0cf217e898`，tree 为 `ae155bba3457f5cb53a6de0ee5a9b873715ae4e5`。独立检查了两者之间的 diff、W020 成功与失败入口、W018 对每个来源片的索引合同和 W021 定向测试。环境为 Linux、CPython 3.12.14。reviewer 仅写复核记录。

使用仓库既有的 noreply 邮箱重建提交后，reviewer 独立用 `git show -s --format="%H %P %T"` 核验了原探针受测提交 `c6c3127d6a221b18bcc5ec3066582065141ffb04` 和分支产品提交。两者父提交与 tree 完全相同，`git diff --exit-code c6c3127d6a221b18bcc5ec3066582065141ffb04 5c923caeb3bdd317b452504c60293c0cf217e898` 退出码为 0。源码、测试、工艺样例与配置按完整 tree 采信原复核结果。

**结论。** 方案复核条件已闭合，受审代码可提交 PM 验收。各层恢复数按原始记录或有效片逐项比较精确面积。W018 构造器已保证同一源的格片互不重叠且位于源内，允许该比较。显式跳过、缺声明、图形越界、无本地记录可以分别判断。缺栅轨声明的字段符合 W018 的 track 语法，归属所选 coordinate owner，单个 POLY 矩形不提供工艺周期。

**来源与共享。** 中立模块引用 domain/state，生产者仅接收完整组装。current/target 与差异取自已保存的 semantic_facts；局部图、标注、外部 body、坐标和 readback 保留原绑定。逐层构建只遍历现有索引、计算区域/片引用并创建小型汇总，没有重新解析捕获或序列化整个组件。合同测试用精确窗口与 annotation fragment 相交，截短 R04 后仍检查相同的物理边和分量。数据复用遵守上游 frozen DTO 的普通 Python 只读接口，未来发布时的正式事务验证仍属后续集成。

**独立反例。** 将 M1 的 x 方向缩至 3 格，删除 MARKER 的跳过声明，并为本地图形数为 0 的 CUT 提供有效二维声明。运行结果为 M1 恢复 2/4，另两条 outside_range 分别定位到 GDS 字节 2480、2544；MARKER 有缺声明诊断但无新增阻断，CUT 返回 no_local_records。直接构造候选、替换 current 和赋值字段均被拒绝，仓库快照逐项相等。

在受审提交的仓库根目录、安装项目依赖的 Python 环境复现：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests/contracts python - <<'PY'
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from w007_cases import ready_copy
from w018_cases import select_projection
from layauto_v2.domain.publication import RunRequest, InputsReady
from layauto_v2.pipeline import assemble_stage2, prepare_inputs
from layauto_v2.repository import PublicationRepository
from layauto_v2.normalization.initial_state import build_proposed_initial_state
from layauto_v2.state.mutation import ProposedInitialState

def variant(model):
    model['layers']['M1']['x_edges']['cells'] = 3
    del model['layers']['MARKER']
    model['layers']['CUT'] = model['layers']['LI']

with TemporaryDirectory() as temp:
    root = ready_copy(Path(temp))
    select_projection(root, mutate=variant)
    repo = PublicationRepository()
    ready = prepare_inputs(repo, RunRequest('probe', 'probe', 'create', str(root / 'site_config.yaml')))
    assert isinstance(ready, InputsReady)
    before = repo.snapshot()
    facts = assemble_stage2(repo, ready, fragment_budget=68)
    s = build_proposed_initial_state(facts)
    m1, marker, cut = [s.layers[n] for n in ('M1', 'MARKER', 'CUT')]
    assert m1.availability == 'incomplete'
    assert 0 < m1.drawn_reconstructed < m1.projection.record_count
    assert all(i.status == 'outside_range' for i in m1.diagnostics)
    assert marker.projection.projection == 'missing_declaration' and marker.gap is None
    assert cut.availability == 'no_local_records' and cut.gap is None
    assert not hasattr(s, '__dict__')
    for fn, error in ((ProposedInitialState, TypeError), (lambda: replace(s, current=s.current), TypeError),
                      (lambda: setattr(s, 'current', None), FrozenInstanceError)):
        try:
            fn()
        except error:
            pass
        else:
            raise AssertionError(fn)
    assert before == repo.snapshot()
    print('M1', m1.drawn_reconstructed, m1.projection.record_count, [i.source.record.source.byte_offset for i in m1.diagnostics])
    print('MARKER', marker.availability, marker.gap, 'CUT', cut.availability, cut.gap)
PY
```

本次实跑以上反例，另逐项核查 W021 对同名 cell、C13、截短覆盖、三节点分量、MARKER 与外部 body 的断言。其他受影响测试、typing、安装和测量按执行记录的源、配置与输入身份交接。修改 W018 的片覆盖不变量、W020 绑定、候选构造或分量关联时应重跑相应探针。双解释器全量依任务卡留至首次正式发布的集成提交。

## PM-01

独立复核通过，PM-01 可交 PM 重新验收。基线为 `892eb3ac891b6da2654d293b1c0f904afa37a8c4`，补修提交为 `1347a2be2509820cc37ba746436126016af31498`，补修 tree 为 `425645eeabe64a8ddf03769d02d4bfd30ca4f8fd`。逐行检查两提交间的 diff，唯一变更是 W007 既有合同测试中新增的四行登记。文件名、绝对模块名和符号集合按原逻辑共同匹配。两个模块的六个符号与 W021 生产者实际导入逐项一致。

独立实跑使用 Linux、CPython 3.12.14，在临时目录解包补修提交的 `layauto_v2`、`tests`、`pyproject.toml`，逐项执行下列原测试：

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /workspace/.venvs/layauto/bin/python -B -m pytest -p no:cacheprovider -vv --tb=short tests/contracts/test_w007_contracts.py::test_normalization_and_new_domain_keep_pure_dependency_boundaries
```

| 临时副本中的独立输入 | 实测结果 |
| --- | --- |
| 从基线恢复原 W007 测试文件 | 失败，violations 列出 initial_state.py 的 discrete_occupancy 与 mutation 两条依赖 |
| 恢复补修版 W007 测试文件 | 1 passed |
| 在 stage2.py 额外从 layauto_v2.state.mutation 导入 ProposedInitialState | 失败，定位 stage2.py 与 mutation |
| 在 initial_state.py 额外从 layauto_v2.state.discrete_occupancy 导入 OccupancyResult | 失败，定位 initial_state.py 与 discrete_occupancy |
| 在 initial_state.py 额外从 layauto_v2.repository 导入 PublicationRepository | 失败，定位 initial_state.py 与 repository |
| 在 initial_state.py 额外从 layauto_v2.transactions 导入 initialization | 失败，定位 initial_state.py 与 transactions |

每个额外导入均放入独立的 `if False:` 代码块，测试直接扫描导入语句的 AST。每次检查退出码 1、`assert violations == []` 以及违规文件与模块，再恢复文件执行下一例。补修前后的产品源码、fixture 与配置相同，原产品测试、构建和安装证据可按原受测身份采信。
