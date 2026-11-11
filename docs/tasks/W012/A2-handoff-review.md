# W012 A2 派发要求独立复核

复核日期：2026-11-11（UTC）。Reviewer：`/root/a2_handoff_independent_review`。

## 结论与适用范围

**复核通过；新增实质必须项0，派发元数据澄清项1已关闭，剩余必须项0。** 当前要求足以交独立执行 session 完成一次有限的兼容方案收敛及独立方案 review。它要求交付一个有收益与等价依据、可直接派发的最小方案，或有证据的 no-go 并建议回到 M1 网络标注；本结论不批准产品实施、新格式或减少公开认证，也不证明 A2 有可实现的收益。

本次只审 W012 顶部当前派发范围、A2 AP1–AP5 及 `A2-plan-prompt.md`。既有 P1/P2 与 A1 记录作为事实来源和历史要求读取，未重审其完整交付、重新验收 A1，亦未把 W012 或 M1 判为完成。M1 网络标注仍是后续功能主线，A2 不是其功能硬依赖。

## 受审身份与独立性

- Checkout：`/workspace/Layauto`；分支 `codex/w012-a2-serialization-plan`。
- `HEAD` 与本地 `main` 均为 `2489b4609ae97d8211bf450d55cac9392492ac71`；A1 实际 merge 为 `08dd232139918dc97b0a6d255aad237eb844686a`，产品/正式测试冻结为 `ca1f810c3c97376f71089d8b4054760ff198012f`。
- 初始工作区仅含已修改的 W012 task 和未跟踪的 A2 prompt。本 reviewer 仅新增本报告，不改 task、prompt、runtime、测试或其他材料；未 commit/push。
- 本 reviewer 未参与 A2 要求/prompt 起草、方案或参考工具设计，也未提出优化实现。另一个只读子 reviewer `/root/a2_handoff_independent_review/a1_identity_check` 独立核对了 A1 内容身份与既有数字；其未写文件、设计方案或运行产品路径。本 reviewer 随后独立复算了同一组身份、阶段中位和 profile exclusive 合计。

| 受审文件 | 初审 SHA-256 | 最终复核 SHA-256 |
| --- | --- | --- |
| `docs/tasks/W012-capture-wire-performance.md` | `f1319074e8d6cbd9a42f4a836a4b6d08b4260f3e8fb92cd96404a1711e5ccefa` | `4b73db46af8a023e8a0bb4dfc45cbe742a08d9e1d724b5381fb6c4e00d563cd3` |
| `docs/tasks/W012/A2-plan-prompt.md` | `ed30768fbafc992b69d8fa96694a18dcb5466a33df3d46c06cf24d52b31ebd3b` | 同初审，未改 |

报告不以自身 hash 作为受审身份。PM 后续补接收/阶段文字须与以上受审内容区分；若改变 AP1–AP5 或 prompt 的行为要求，应复核受影响部分。

## 实际读取与核对材料

- 根 `AGENTS.md`、`README.md`、`docs/README.md`、`docs/collaboration/rules.md`、`docs/environment/local-setup.md` 与 `remote-development.md`。路径搜索未发现本目标目录下的局部 `AGENTS.md`。
- `docs/architecture.md` 的 §2.2–2.3、§2.6 相关输入/中立合同及发布边界，§3.7–3.8 读取面、来源与递归冻结，§11.2、§11.9、§11.15 的 codec/模块/别名与持久身份边界。
- W012 当前 task、A2 prompt、原 `implementation-proposal.md`、A1 `performance-analysis.md`、`profile-summary.json` 的调用次数资料、原始 `profile/after-normal-readback-r1.profile.json`、对应 profile receipt、三个 `performance/after-normal-readback-r{1,2,3}.json`、`verification-r2/source-manifest.json` 与 `integration-receipt.json`。
- 实际 `domain/codec.py`、`domain/publication_codec.py`、`domain/regions.py` 的 closed graph 验证、`domain/local_connectivity.py` 的单次集合快照；实际 `normalization/channel_identity.py`、`channel_identity_codec.py`，并按调用链核查 `geometry_codec.py`、`local_connectivity_codec.py` 的 pack/encode/decode 接口。
- `tests/contracts/test_w011_exceptions.py`、`test_w011_contracts.py` 中二次认证/异常历史、错型等值、可变别名、完整字段与来源约束；`test_w009_captured_decode_exceptions.py` 的公开集合单次快照用例。只静态读取，未声称本次运行这些测试。

## 判断依据

| 检查点 | 核对结果 |
| --- | --- |
| AP1 真实起点和热点 | 263 项 manifest 内容逐项匹配当前磁盘及 A1 冻结 Git blobs，其中 runtime 100 项；当前这组路径对冻结版本无 diff。三个 after 性能 receipt 与 after-profile receipt 的 source map 也等于该 manifest。manifest 自带的历史 `git_head=212554…` 未被当作冻结版本证明。阶段中位 51.427/66.115/2.616s 能从既有原数据复算。要求区分 wall、exclusive、cumulative 及未归因余量正确，没有把旧 P1 profile 或集成 after-only 检查冒作新的无插桩前后基准。 |
| AP2 可执行性和范围 | 交付要具体到 owner、入口、数据流、字段/token、快照算法和分步落点，并要求逐类区分可减少的序列化临时对象与必须保留的 DTO/重建/认证。writer/reader/memo 只选一个主候选；无需三包并行或无限增加调查。有限独立原型不得替换或 monkeypatch 完整产品入口。此处是在派发方案工作，无需当前要求文件先替执行者完成算法设计。 |
| build/decode 共同路径 | 实际 builder 调用 `_require_input`，公开 Result constructor 再次认证；`_require_input` 经下层完整 encode/decode，decode 的 `_unpack` 又进入公开 constructor，最终 canonical 重编码仍在。原 after-profile 的 `domain/codec.py` exclusive 合计在 W011 build/decode 分别约98.237/124.771s，说明共同序列化路径有调查价值；不能把这些插桩秒数当无插桩耗时或候选可节省秒数。仅外层 encode 的方案必须解释为何能影响前两条路径。 |
| AP3 完整性、身份与失败边界 | `/1` bytes、wire 大小、所有 hash/ref、公开签名、原 bytes、完整来源/run/owner、closed/exact scalar、排序/escape/rational/UTF-8、防御快照和单次集合快照均有明确要求。`record_digest/content_ref` 实际绑定完整编码，不能以 hash 相同代替角色认证。要求保留公开 DTO constructor、完整重建及第二次认证，和实际二次故障测试一致；临时序列化构造的减少须单列故障影响，不能用“不可变”泛称跳过验证或自行豁免原测试。原异常 object/cause/context/suppression 也在保留范围。 |
| AP4 收益和验证 | 要求实际共同路径/调用次数、未测假设、残余/退化和工程成本，禁止微基准充产品收益；兼容 wire 减幅为0，旧20%/50%不是硬门。未来完整三路逐字节及无插桩前后比较须固定 URI/RunRequest/cache/roots/GC。真正产品实施最终双全量/typing/构建/双安装仍明确；本次 runtime 不变可按身份采信 A1 既有工程证据。 |
| AP5 独立性和停止点 | 明确未参与方案/参考工具设计者 review，必须项修正后交 PM 停止。可交有依据最小方案或收益/等价不足的 no-go，不能泛泛后置、自动实施、合 main、扩成 B 或删认证。新公开格式/内容身份/迁移/架构行为另交具体材料，未在本次获批。 |

以上合同要求足够严格，但并未把所有内部 `FrozenMap`/pack 临时分配次数冻结成产品目标；执行者仍须说明每类拟减少对象为何只是纯序列化中间结果，并保留其涉及的既有公开验证和故障合同。这一责任不能由本次交接 review 预先豁免。

## Finding 与复核

| ID | 原问题、复现与影响 | 处置与复核 |
| --- | --- | --- |
| A2-HR01 | 初审 task 顶部“里程碑/依赖”仍写“本次先派发P1/P2调查”；“分工”泛称执行者提供“方案和实现”。用 `sed -n '5,19p' docs/tasks/W012-capture-wire-performance.md` 可定位。与当前只派发 A2 方案的元数据不一致，易混淆本轮工作和历史授权。要求澄清当前阶段，不扩展 AP 范围。 | PM 仅改这两项：明确 P1/P2、A1 已验收；本次只派发 A2 方案，非 M1 网络标注功能硬依赖；执行者仅提供 A2 方案/必要有限见证，产品实施另派。Reviewer 实读新两行并核最终 task SHA 为 `4b73db…`；prompt/AP1–AP5 未改。**已关闭。** |

未发现其他必须修改项；无待用户决定项由本次审查引入。

## 可复现轻量检查

命令在 `/workspace/Layauto` 执行；仅 Git/文件读取与 Python 标准库 JSON/hash/算术，不导入产品 runtime，不运行 benchmark。

```sh
git branch --show-current
git rev-parse HEAD main
git status --porcelain=v1
sha256sum docs/tasks/W012-capture-wire-performance.md docs/tasks/W012/A2-plan-prompt.md
git diff --check
git diff ca1f810c3c97376f71089d8b4054760ff198012f HEAD -- README.md pyproject.toml docs/tasks/W003/examples/records.json layauto_v2 tests
```

最后一项无输出。受审 SHA 与前表一致，`git diff --check` 通过；新增本报告之前的工作区只有 task/prompt 两项。

```python
# python3 -B - <<'PY'（以下代码）
import hashlib, json, statistics, subprocess
from pathlib import Path
root = Path('docs/tasks/W012/A1')
files = json.loads((root/'verification-r2/source-manifest.json').read_text())['files']
frozen = 'ca1f810c3c97376f71089d8b4054760ff198012f'
for path, expected in files.items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected, path
    blob = subprocess.check_output(['git', 'show', f'{frozen}:{path}'])
    assert hashlib.sha256(blob).hexdigest() == expected, path
print('disk_and_frozen_source_matches', len(files), 'runtime',
      sum(p.startswith('layauto_v2/') for p in files))
samples = [json.loads((root/f'performance/after-normal-readback-r{i}.json').read_text())
           for i in (1, 2, 3)]
receipt = json.loads((root/'profile/after-normal-readback-r1.json').read_text())
assert all(v['source_identity']['files'] == files for v in samples + [receipt])
print('sample_and_profile_source_maps_match', len(samples) + 1)
for stage in ('W011_build', 'W011_result_decode', 'W011_result_encode'):
    print(stage, 'median_seconds',
          round(statistics.median(v['wall_seconds'][stage] for v in samples), 9))
profile = json.loads((root/'profile/after-normal-readback-r1.profile.json').read_text())
for stage in ('W011_build', 'W011_result_decode', 'W011_result_encode'):
    exclusive = sum(f['exclusive_seconds'] for f in profile[stage]['functions']
                    if f['file'].endswith('/layauto_v2/domain/codec.py'))
    print(stage, 'codec_exclusive_seconds', round(exclusive, 6))
```

实际原输出：

```text
disk_and_frozen_source_matches 263 runtime 100
sample_and_profile_source_maps_match 4
W011_build median_seconds 51.426606384
W011_result_decode median_seconds 66.114896278
W011_result_encode median_seconds 2.6164734
W011_build codec_exclusive_seconds 98.236572
W011_result_decode codec_exclusive_seconds 124.77135
W011_result_encode codec_exclusive_seconds 3.683182
```

## 限制与交接

本次未运行新算法、有限原型、正式回归、完整 readback、三路重型基准或小时级工程矩阵；未重比18份大 wire、重建固定 mismatch 输入或核原安装树。A1 既有证据只按同源材料作为本次方案派发起点采信。原 profile 的累计时间不可相加，未归因的尾部峰值余量仍未被重新定位；本报告没有把该余量归给某个候选。

执行 session 仍须从已提交推送且实际可访问的最新 A2 准备 head 恢复，先核远端完整 SHA/工作区，并按 AP1–AP5 交实际方案或 no-go 及独立 review。当前报告绑定上述未提交受审快照；是否更新阶段、发布交接及接收执行结果由 PM 维护。

## 发布补记局部复核

2026-11-11，PM 补记后的最终 task SHA-256 为 `78788308c8f6132c15064e13f15e020fb59926d195b4c3f297951479ba511f94`；prompt 仍为 `ed30768fbafc992b69d8fa96694a18dcb5466a33df3d46c06cf24d52b31ebd3b`。

Reviewer 实读顶部阶段、A2 标题、复核接收句及新增 PM5，确认“可执行”仅指 AP1–AP5 方案工作，保留方案/no-go、独立 review、交 PM 停止及禁止产品实施/B 的范围。用只读 Python 将前三处元数据恢复为原受审文本、移除新增 PM5 整块，重算 SHA 得 `4b73db46af8a023e8a0bb4dfc45cbe742a08d9e1d724b5381fb6c4e00d563cd3`，与上表一致；因此 AP1–AP5 及其余原有字节未改。未修改 task/prompt，也未新增产品或性能检查。

**发布补记复核通过，新增及剩余必须项均为0，原派发审查结论与限制继续适用。** 本段将最终 task 身份绑定到上述发布补记版本，不将 PM 接收元数据写成 A2 实施或收益验收。
