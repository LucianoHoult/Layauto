# W020 独立代码与交付复核

复核任务卡 A1–A5，依据[架构 §2.3](../../architecture.md#23-stage-2事实归一化与-layout-state-构建)。起点 `fd629b1a0afc7b8dedb3ea0da52c86c574a7b210`；受审候选 `5fcf7e057734cf3faa63a43e4c448a5ef9797d43`。已核其实际 diff、测试、示例与文档。候选的运行代码和配置与探针受测提交 `0ec047899c14d33307faebda173fb970ce5568f2` 相同。环境为 Linux、CPython 3.12.14。复核中只修改本记录。

## 受测版本与分支恢复

按仓库的 noreply 邮箱重建提交后，独立复核了两组版本。分别用 `git rev-parse <提交>^{tree}` 取到下列相同 tree，两次 `git diff --exit-code <原提交> <分支提交>` 均以 0 退出。运行代码、测试、配置与样例逐文件相同，原证据适用于右侧提交。

| 用途 | 原受测提交 | 分支恢复提交 | 双方相同的 tree |
| --- | --- | --- | --- |
| 运行代码 | `0ec047899c14d33307faebda173fb970ce5568f2` | `2ef3662032332533046b4c294e4a3d3e5e9ea5e7` | `3cc598c112d2c3cb0150e9ad5abbfde57068b564` |
| 受审候选 | `5fcf7e057734cf3faa63a43e4c448a5ef9797d43` | `e95ce132eee16dd8599fee1013a5c030491160ff` | `81570b2fac513a1518cdddebda1da5c58b25decd` |

## 核查与独立实跑

- **来源与调用顺序。** 仓库回读当前 attempt 与 checkpoint，检查 ready 的 parse、tool、evidence 引用及 ready_value。W007/W008 复核捕获内容后，组装沿同一份 geometry、effective 和 local graph 构造投影与标注。源码中无文件重读、状态发布和跨运行缓存。原组件问题及预算不足分别保留在异常与结果内。W014 的诊断草稿随错误返回，成功路径才给出完整组装。
- **几何与来源。** 首次与候选复跑的逐层样本报告逐字节相同（25,801 字节，SHA-256 `26d9dac2282b50d3d47bf17dd192b1bf754bd317421a2f7168123d088e825dcd`）。逐项读取 45 个带 URI 和 SHA-256 的来源，复核实际文件摘要、已有 JSON/YAML 指针、原始文本行/词位和 GDS 记录头。独立按 GDS 大端记录长度读取 BOUNDARY 与 int32 XY。偏移 1648 对应 LI 矩形 (28,30)–(34,55)；两条物理边经偏移 1840 的 CONTACT 和偏移 2096 的 VIA0，连接器矩形为 (29,40)–(33,44) 和 (29,50)–(33,54)，两侧均有 16 DBU² 的正面积交集。M1 原矩形 (0,48)–(45,58) 位于偏移 2352，截取格 (2,2) 的面积为 130 DBU²。报告还给出关联节点、分量、标注目标、R04 源顶点和 `nXref.temp` 第 11 行。
- **同一请求、不同捕获。** 在同一绝对 site 路径与相同的 run ID、lineage、幂等键下，先后用两个仓库读取。仅缩短 R04 在 Y 方向的直接标注，变更来自真实文件。实测两份 checkpoint digest 的前 12 位为 `15e0ec68e129` 与 `b2da1d679d5c`。双向交换 ready 均在 attempt 检查处得到带 run ID 的 `ReadbackConflict`。各自正常组装后，两个仓库的 snapshot 与组装前逐项相等。
- **截短标注。** 对修改后的捕获先组装，直接标注已缩至 Y=[50,55) nm。查询 Y=[30,40) 的 LI 格得到 `direct annotation covering the selected effective fragment: expected one, found 0`。随后从原捕获组装，同一处返回 VSS。两份结果的完整物理边元组、物理分量元组各自相等，所选分量均为 `656bd9b055f519897cb4f4e86da8a0f713eea6022d6a46cc6dec00fa814de16d`。
- **目标与发布边界。** 检查有交错读取的合同测试及 W003 输入。正常样本两个器件的几何 FIN 数为 5/7；`unsupported_target` 同样为 5/7，差异保留 MN0 的 `resize:channel_length`、源与目标 CDL 第 3 行及精确参数值。逐层示例区分记录数、缺声明、显式跳过、按记录/有效片精确并集重建。未标注 MARKER、本地 B 端未知网络、外部 synthetic body 各自保留。六类事实与下一步所需验收输入见[发布缺口](readiness.md)。

下面的探针在项目根目录、已装项目依赖的环境重跑。两个临时捕获共享同一个请求，缩短的 query 形状保留原 xref、GDS、工艺和 cell 身份。

```sh
PYTHONPATH=.:tests/contracts:docs/tasks/W020 python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from w005_cases import copy_input, without_cache, rebind
from w018_cases import select_projection
from layauto_v2.domain.publication import InputsReady, RunRequest
from layauto_v2.pipeline import prepare_inputs, assemble_stage2
from layauto_v2.repository import PublicationRepository, RepositoryConflict
from trace import conductor_trace

with TemporaryDirectory() as temp:
    root = copy_input(Path(temp))
    without_cache(root)
    select_projection(root)
    request = RunRequest('same-id', 'same-lineage', 'same-key', str(root / 'site_config.yaml'))
    a, b = PublicationRepository(), PublicationRepository()
    ra = prepare_inputs(a, request)
    path = root / 'query/raw/net_shapes_n_lo.txt'
    raw = path.read_bytes()
    path.write_bytes(raw.replace(b'600 560\n', b'1000 560\n').replace(b'600 680\n', b'1000 680\n'))
    rebind(root)
    rb = prepare_inputs(b, request)
    assert isinstance(ra, InputsReady) and isinstance(rb, InputsReady)
    assert ra.attempt.request == rb.attempt.request and ra.checkpoint_ref != rb.checkpoint_ref
    before = (a.snapshot(), b.snapshot())
    for repo, foreign in ((a, rb), (b, ra)):
        try:
            assemble_stage2(repo, foreign, fragment_budget=68)
        except RepositoryConflict as error:
            assert error.code == 'ReadbackConflict'
        else:
            raise AssertionError('accepted a foreign capture')
    partial = assemble_stage2(b, rb, fragment_budget=68)
    original = assemble_stage2(a, ra, fragment_budget=68)
    x, y = partial.terminals.input.value, original.terminals.input.value
    assert (x.edges, x.components) == (y.edges, y.components)
    try:
        conductor_trace(partial)
    except ValueError as error:
        assert 'direct annotation covering' in str(error)
    else:
        raise AssertionError('assigned a network without local coverage')
    assert conductor_trace(original)['annotation']['net_name'] == 'VSS'
    assert (a.snapshot(), b.snapshot()) == before
PY
```

## 已关闭的发现

| 编号 | 原问题、处置与复核 |
| --- | --- |
| CR-01 | 初版 A1 测试访问了 `TargetCircuit.selected_cell`。该字段属于 source，target 通过 `cells` 保存 cell。执行者改为在独立 target 的 cell 列表核验身份。已检查候选代码；在候选定向日志中核对 `test_each_interleaved_assembly_resolves_only_its_captured_inputs` 为 PASSED。 |
| CR-02 | 初版 `example.py` 遇到 pre-context 拒绝后读取 `PipelineResult.status`，掩盖了实际拒绝。对 `w005_cases.copy_input` 做临时测试替换，仅在复制后移除 `source.gds`；以 `example.run(parent, 'original')` 实跑，修前得到 `AttributeError`，修后得到 `RuntimeError w020-original: input rejected, closure closure:w020-original:…`，可由 run 和 closure 回查。已核修正。 |


## 结论与证据适用范围

独立代码复核通过，两项发现已关闭，可交 PM 按任务卡验收。

本次独立实跑包含以上双仓探针、局部标注的正反例、报告来源和 GDS 原字节复算以及 CR-02 回验。运行代码、W003 输入、W018 配置与旧合同实现在受测提交与候选之间逐文件相同。示例的输入拒绝分支单独复测，当前示例文件 SHA-256 为 `2230256f19d4df082d24f864d4165686c809e8d9f97cf3a23b2342c696e54b68`。

按[验证分工](../../collaboration/rules.md#verification-reuse)采信本次执行者的受影响合同、类型、构建与安装证据，汇总归[任务卡](../W020-stage2-baseline-readiness.md)。W019 阶段双版本全量的范围以 [W019 集成记录](../W019-single-cell-occupancy-query.md#pm2-integration)为准。W020 的双版本全量由 PM 在阶段集成版本运行。合并改变编排、投影/算子、fixture、报告生成或证据身份时补对应探针。当前证据覆盖受限 synthetic 样本的事实组装。
