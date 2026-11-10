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

## CR-04：聚合公开构造接受与 codec 不一致的错型旧叶（P2，必须修正）

在独立冻结 `f49323311bd817f066cb3e2411cad45219764f04` 上追加轻量实证。先正常构造 `FinEvaluation(width_nm=Fraction(2))`，深拷贝后用 `object.__setattr__` 将宽度改为原生 `int(2)`；伪造叶仍与合法原叶相等。随后正常调用公开 `ChannelMeasurement(..., evaluations=(forged,), count=1, ...)` 构造成功，返回对象保留 `int` 宽度；对该公开聚合进行 W011 codec 重建则抛出 `ValueError('channel values require exact Fraction scalars')`。直接调用 `FinEvaluation(width_nm=2)` 对照正确拒绝。

这证明聚合的 closed-graph 检查和 Python 等值判断未替代对子级公开契约的重建校验。攻击前提明确包括 `object.__setattr__` 绕过叶自身构造；这里没有声称错误类型可由合法叶构造获得，也没有声称已经穿透完整 captured Result。W011 的闭合 DTO 和完整公开重建要求仍应拒绝这种错型旧叶。主评审将协调对完整 Draft/Result 的扩展回归。

命令：`/workspace/work/w011-engineering/dev312/bin/python /workspace/work/w011-review-boundary/probe_equality.py`，exit 0（探针完成，结果是发现拒绝边界不一致）。原脚本和输出见 `boundary-probe-equality.py`、`boundary-equality.stdout.txt`、`boundary-equality.stderr.txt`。未改产品、正式测试或 fixture。

## 修复候选 975852d 独立复核（阶段性）

冻结 `975852d3b9ea946aca24f727071cf26a7dce8bc7` 的 runtime/fixture 到新的 `/workspace/work/w011-review-boundary-fixed`，未复用已变动 checkout 导入路径，原证据保留。

- **CR-01 已闭合（本候选）**：原三类 provenance/metadata 畸形字段均在公开构造处 `ValueError` 拒绝；正常真实 W007 seed 的 W011 wire roundtrip 继续通过。
- **CR-02 已闭合（本候选）**：同一 ParameterComparison wire 的六类异常注入全部保留同对象、原 cause、原 context、suppression=False，包括原失败的 TypeError/KeyError/AttributeError/UnicodeError。另从真实正常 source/target/identity 获取 16 种中立 exemplar，正常 codec roundtrip 全部成功；384 个字段形状变换中，369 个明确 ValueError，15 个合法可选/自由文字中立变化接受，没有新 TypeError/KeyError/AttributeError 等形状泄漏。这个矩阵用于区分应拒绝的 wire 形状与应原样传播的意外故障，不替代捕获真实性验证。
- **CR-03 复核进行中**：原两个实际 captured 错误路径正在串行执行；未提前宣称闭合。
- **CR-04 待修**：975852d 不包含该项修复。

证据为 `boundary-recheck-probe_leaf.py`、`boundary-recheck-probe_semantic_exception.py`、`boundary-recheck-probe_malformed.py` 与相应 stdout/stderr；源文件 hash、实际命令及环境限制见 `boundary-recheck-leaf-receipt.json`。畸形 wire 小矩阵用时 21.16 秒、峰值 RSS 25,464 KiB。共同环境 cgroup 4 CPU / 16 GiB，有其他正式测试并行；本阶段未启动完整 W011 result codec 重建，不声明最终全矩阵/安装/A8 通过。

### 实际 expected completion 复核补全

**CR-03 已闭合（975852d 候选）**：两条原始实际捕获路径控制仍分别得到 `UnsupportedFingerCount` 和 `UnknownDeviceIdentity`，注入结果都保持同一个 TypeError、原 cause、原 LookupError context、suppression=False。完整 stdout 与 JSON 保留于 `boundary-recheck-expected.stdout.txt` 和 `boundary-recheck-expected-results.json`；脚本 `boundary-recheck-probe_expected.py`，exit 0。

先尝试 `/usr/bin/time -v` 收集资源，但该可执行文件不存在（exit 127，未执行探针），失败输出也保留为 `boundary-recheck-expected-time-tool.stderr.txt`；随后直接 Python 执行成功。期间实际 builder RSS 一次采样 131,964 KiB，只作为采样而非峰值；未再启动重型全 result codec。

### CR-04 原轻量样本复核

冻结后续 `88fefa7c550993ed0d53d4ae073419a36a7b200b`，原轻量 `FinEvaluation(width_nm=int2)` 伪造样本在 `ChannelMeasurement` 公开构造处已 `ValueError` 拒绝；直接非法 leaf 对照继续拒绝。证据 `boundary-members-probe_equality.py` 和 `boundary-members-equality.stdout.txt`。这关闭原具体样本；顶层 `ChannelIdentityResult.issues/completed` 仍仅 closed-graph + Python 等值比较的 SourceRef 整数位置等值问题，已通知主评审扩展检查，尚不将整个 CR-04 宣称全部闭合。

以上候选、源 hash、实际命令、失败尝试、证据 hash 与资源限制见 `boundary-recheck-completion-receipt.json`。

## CR-06：同一派生声明来源位置存在互相矛盾的内容，中立聚合仍接受（P2，必须修正）

冻结 `c37eecf844e27787b478bccddfdb8fdaba18bc06`。从实际 read→W007 normalize 取 seed，将 `record.field_sources.derived_layer.sources[1].lexeme.target_layer` 从 `POLY` 改成 `METAL`；同一来源在 geometry_kind、quality 中的副本同步修改，共 3 处。该来源仍为 `tech/derived.json`、SHA `0806468843e018c9dda461dc7c6c583773f63453392143ce6b6a92259a7ec1d9`、JSON pointer `/derived_registry/0`。传入聚合的真实 derived EvidenceRecord 保持完全相同 URI/SHA，指针对应 payload row 仍为 `target_layer=POLY`。

叶 `ChannelSeed` 允许这种输入。接着真实构建 W008→W009→W010 局部图，将其 `.value`、真实 W007 source、上述 seeds 和真实 derived owner 传入公开 `build_channel_identity_draft`。聚合接受，`issues=[]`，计数仍 `[5, 7]`。`_seed_operands` 对 registry lexeme 只交叉检查 id/quality；`_owners` 按 id 独立消费传入 owner row，没有检查两份已声明为同来源位置的 row 内容一致性。

这是中立聚合已有证据互相矛盾，区别于需要读取捕获字节才能判断的 authenticity。**并非**要求中立层新增 parser/IO 或仅因来源路径不同就拒绝，也未声称 captured 顶层可接受这份 seed；捕获层会重新生成 seed。修复应核对已有 registry 来源/声明对应关系，不新增 FIN 或工艺规则语义。

脚本与输出为 `boundary-owner-probe_owner.py`、`boundary-owner-owner.stdout.txt`/stderr。初次 harness 将 GeometryInput.parse.completed 误写为 GeometryInput.completed，exit 1；失败脚本/输出亦保留为 attempt1，修正 harness 后 exit 0。执行 14.70 秒，峰值 RSS 660,112 KiB；未构建 W011 captured Result、未做全 codec。源 hash、实际命令、环境与限制见 `boundary-owner-receipt.json`。

### CR-04 追加：to_value 投影未覆盖完整 Draft 来源字段

同一 `c37eecf844e27787b478bccddfdb8fdaba18bc06` 的独立 probe 进一步证明，顶层 Result 的 `same_draft` 不能单靠 `canonical_bytes(value.to_value())` 代替完整 DTO 验证。对正常实际中立草稿做 deepcopy，将 source MN0 的 `finger_count` Parameter.source.line 从 3 改为 999（通过 `object.__setattr__` 修改该 Parameter 的 source，保留原 field_evidence.line=3）。两个 Draft 的 dataclass equality 为 False，但 `canonical_bytes(forged.to_value()) == canonical_bytes(control.to_value())` 为 True。直接公开 Draft 构造重建仍正确抛出 `ValueError('field evidence location disagrees with source reference')`。

原因是摘要 binding 含 source 语义和原 preservation，而只有实测轴 Parameter 的完整来源进入 comparison；NF/M 来源未进入此投影。Result 当前只校验其 closed graph，再用这个摘要投影比较，却未重建 caller 提供的 Draft。此扩展不声称没有运行的 full Result probe 已执行；独立证据明确证明当前用于信任 caller Draft 的比较量遗漏了真实字段，并给出公开重建拒绝对照。主评审/执行者已收到应重建完整 supplied Draft 的修复要求。

探针 `boundary-projection-probe_projection.py` 复用 owner probe 中真实 local/source/control；完整输出 `boundary-projection-projection.stdout.txt`，执行 15.54 秒、峰值 RSS 677,928 KiB、exit 0。原始对象绕过前提与未运行 full Result/codec 限制见 `boundary-projection-receipt.json`。CR-04 保持待完整闭合。

## 8917d38 专项最终代码复核

最终专项冻结对象为 **`8917d38d916c914bfa785cb116982f3f299b38de`**。下面只结论本专项 A6 代码与独立探针，不替代主评审对完整 Result、原有/新增全量矩阵、strict typing、构建、双干净安装组合 smoke 或 A8 交付的判断。

| 必须项 | 独立复核状态与证据 |
| --- | --- |
| CR-01 seed metadata/provenance 形状 | 本候选原三类非法字段全部 ValueError 拒绝，合法真实 seed roundtrip 通过。 |
| CR-02 semantic_record 意外异常链 | 本候选六类原注入故障全部保持同对象、原 cause/context、suppression=False；16 种合法中立记录 roundtrip 和 384 个形状变换控制结果保持 369 次 ValueError、15 次合法可选/自由文字接受、0 次非 ValueError 形状泄漏。 |
| CR-03 expected 后 completion | 975852d 两条实际路径独立复核已闭合；本候选 component.py/codec.py 与该已测版本字节相同。新 Result 分支只在有 Draft 时重建，原 semantic error 两路径仍保留 None Draft；正式全量执行侧覆盖后续整体链。 |
| CR-04 等值旧叶与完整 Draft | 本候选原 FinEvaluation 整数宽度旧叶在公开 ChannelMeasurement 构造处拒绝；NF source.line=999 草稿在公开 Draft 重建处拒绝。静态核实 Result 现已先 `replace(self.value)` 进入完整公开重建，再比较完整 Draft wire，未再把摘要投影当完整 DTO。顶层 actual Result 的完成事实/未测来源故障实证由主独立 reviewer 补充，本专项不冒认已执行。 |
| CR-06 同源派生声明矛盾 | 本候选真实 W010 local + W007 source/seeds 的原 METAL/POLY 同定位矛盾在公开 neutral Draft 处 ValueError 拒绝；正常 control 仍成功。闭合。 |

本专项已报告的代码缺口均有对应修正，未发现新增未处理代码必须项。CR-04 全 Result 行为闭合依赖主评审实际探针的最终记录；A8 独立工程交付复核由主评审继续处理。所有原 findings、接受输出、失败 harness、阶段版本复核均保留，未覆盖原证据。

最终脚本/输出见 `boundary-final-*`，全部本次命令正常 exit 0；源/fixture 身份、实际命令、资源、原路径可复用条件与未测范围见 `boundary-final-receipt.json`。本次真实 neutral builder+来源投影对照 14.43 秒、峰值 679,076 KiB；轻量形状矩阵 6.74 秒、25,468 KiB。共享环境 cgroup 4 CPU / 16 GiB。本专项没有产品/正式测试/fixture/PM/current-work 修改，也未提交或推送。
