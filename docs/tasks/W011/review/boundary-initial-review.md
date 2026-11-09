# W011 公共合同与异常边界独立专项

Reviewer：`/root/code_review/boundary_review`，2026-11-09。未参与设计、实现或正式测试；只写本专项报告与独立证据。

本报告当前是初审 findings，尚不支持最终 A6/A8 通过。被审产品冻结为 `f49323311bd817f066cb3e2411cad45219764f04`（准备 base `81e01da1e5a6ce8e7132f3cebf8ee92bc237246f`）；执行者随后提交的修复需另行复核，不覆盖下面原发现。

已读根 AGENTS、协作/环境规则、W011 任务/方案/方案 review及架构 §3.8/11.15；检查 domain/channel_identity、derive aggregate、normalization 入口/codec 及实际 W007 子合同。无局部 AGENTS。初始 checkout 干净；探针使用 `/workspace/work/w011-review-boundary` 的 Git archive 冻结 runtime、原 fixture 和两项只用于独立临时输入变换的旧测试 helper。产品不依赖 helper。

## 原 findings

### CR-01（P2，必须修正）：中立 ChannelSeed 接受非法来源/opaque 字段形状

`ChannelSeed.__post_init__` 只核对 record/identity_provenance 的字段集合和少数 geometry/identity 值，没有验证 metadata_opaque 的数组/文字类型，也没有验证各 field_sources 是有效来源位置。由真实 W007 seed 构造后，分别替换 `metadata_opaque=7`、所有 `record.field_sources` 值为 `0`、所有 `identity_provenance.field_sources` 值为 `0`，新公开 constructor 与 W011 `encode_record→decode_record` 均接受。

这不是声称伪造 capture 已通过 W011 顶层认证：顶层会重新运行 W007并比较同源 seed。缺口位于对外承诺的中立 DTO/wire 表示自洽边界，允许缺少来源的 seed 被标成可重建合法对象。W007 `_seed` 要求合法 opaque 元数据及 provenance；任务 A6 要求 closed/immutable 来源和公开重建。修复应使中立值在不依赖 parser/normalization 的情况下明确验证这些已有字段形状，并保留合法同身份多 seed。

原探针：[boundary-probe-leaf.py](boundary-probe-leaf.py)，[stdout](boundary-leaf.stdout.txt)、[stderr](boundary-leaf.stderr.txt)。三例均 `constructor_accepted=true`、`decode_accepted=true`。

### CR-02（P2，必须修正）：新 semantic_record 嵌套解码转换意外异常

W011 codec 将 `ParameterComparison.declared` 等公开中立语义值交给旧 `normalization.codec` 的 `semantic_record` 子解码。旧 codec 的一般 constructor 分支捕获 TypeError/KeyError/AttributeError/UnicodeError 并生成新 ValueError，违反本任务对意外异常原对象及其既有链的要求。

独立探针从真实 source Parameter 创建合法 ParameterComparison wire，仅在 decoder 执行期间给 `Parameter.__post_init__` 注入携带原 cause/context、suppression=False 的异常。四类故障均被 W011 decode 抛为新的 ValueError，`same_object=false`、链不再相同、suppression=True；ValueError/KeyboardInterrupt 两个对照保持原对象/原链。问题是有效 wire 重建的意外故障，不是畸形 wire 期待拒绝的测试。

原探针：[boundary-probe-semantic-exception.py](boundary-probe-semantic-exception.py)，[stdout](boundary-semantic-exception.stdout.txt)、[stderr](boundary-semantic-exception.stderr.txt)。修复须保护 W011 对外暴露的新语义子记录完整重建路径，同时继续明确拒绝非法 wire；不能仅避开一个故障类型或测试 hook。

### CR-03（P2，必须修正）：W007 预期失败后的完成对象构造污染意外异常 context

实际复制输入并把 source CDL 的 NF=1 改为 NF=2、重绑真实来源后，W010 局部图仍成功，W011 正常控制得到 `UnsupportedFingerCount`。在 W011 调用的 W007 `component.NormalizationResult` 构造点注入既有 cause/context 的 TypeError，W011 builder 抛出同对象，但其 `__context__` 从原 LookupError 变为本次预期 `NormalizationError('finger_count is outside the selected source subset')`。

旧 `normalize` 在 `except NormalizationError` 内构造 error result；有 progress 时同样在 handler 内调用 facts `replace`。这已通过 W011 的实际同源组合成为本任务要求覆盖的 expected 后 completion 路径。最小方向为退出该 handler 后完成 facts/result 构造，保留原业务错误和 completed 事实，不重构 wire 或改变准入语义。第二条 identity/progress 路径的独立验证仍在运行，将追加原输出。

## 实际命令与限制

- `git archive f49323311bd817f066cb3e2411cad45219764f04 layauto_v2 tests/fixtures/w003_m1 tests/contracts/w005_cases.py tests/contracts/w007_cases.py | tar -x -C /workspace/work/w011-review-boundary` 固定被测源。
- 使用 `/workspace/work/w011-engineering/dev312/bin/python -B` 执行上述脚本，工作目录 `/workspace/Layauto`，输出重定向到同名 `.stdout.txt/.stderr.txt`；不安装依赖、不运行 EDA、不改原 fixture/答案。
- 本专项初审未运行双完整矩阵、strict typing、build/安装或最终资源测量，不能替代 A8 证据。正式新增回归仍由执行侧完成；后续修正复核在本报告追加，原 findings/输出保留。

### CR-03 第二条原路径补全

同一冻结版本的第二条实际输入将 iXref 的 Q17→MN0 改为 Q17→UNKNOWN 并重绑原捕获。W011 控制得到 `UnknownDeviceIdentity`；随后给 W007 error progress 的 `component.replace` 注入 TypeError，亦观察到原对象/cause保留但 context 被 `NormalizationError('xref names a device absent from source CDL')` 覆盖。原两条完整结果见 [boundary-expected-results.json](boundary-expected-results.json)，命令脚本 [boundary-probe-expected.py](boundary-probe-expected.py) 与 [stdout](boundary-expected.stdout.txt)/[stderr](boundary-expected.stderr.txt)。此原脚本 exit 0 表示探针正常收集两条失败事实，不表示被测异常合同通过。
