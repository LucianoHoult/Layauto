# W023 执行验证

产品、测试、包配置与实际文件示例使用提交 `9f6fa09ce79c2b9c731c909b5a2e526a06e66c47`，tree 为 `5410ec3450c21bd55fedb1204bde59a506d48359`。开发主机为 Linux x86-64、glibc 2.41、CPython 3.12.14，pytest 9.2.0，mypy 2.4.1，PyYAML 6.0.3。独立安装的 wheel 使用同一解释器及 PyYAML 6.0.4。复核记录给出两次必须修正项的原版本、反例及补修后的结果。[任务](../W023-atomic-baseline-publication.md) · [独立实现复核](code-review.md)

## 正常文件与公开入口

在安装了 `.[dev]` 的仓库根目录运行。示例复制 W003/W004 的完整输入并保留正常 target 及四份 normalized cache，显式选取 W022 坐标文件，重新计算 header 闭包的实际字节摘要。W006 从 site 读取，不读取 fixture 的 oracle。示例按阶段计时；使用同一发布事务的 prepare 和 repository switch 分别计量，随后从公开入口重试并启动第二个 run。[示例](example.py) · [样本准备](../../../tests/contracts/w023_cases.py)

```sh
PYTHONPATH=.:tests/contracts python -B docs/tasks/W023/example.py
```

调用者保留 `Stage2Request.from_ready(ready, idempotency_key=..., fragment_budget=312)`，用 `publish_stage2(repository, request)` 发布或重试。读者从 `load_head(lineage_id)` 或 attempt 的 `context_ref` 出发，通过 `read(ref)` 解析 head、快照、事件、目标和本次 checkpoint。原版的查询、工艺包和 policy 可沿 checkpoint 的 tool/parse/evidence 引用读取。完整捕获的 query 缓存在 W006 审计里保留绝对路径，跨运行相容性使用缓存角色与实际摘要。绝对目录及 run ID 参与追溯，复跑时产生的仓库引用可不同。

以下调用从空仓库直接走 pipeline 公开入口，使用同样的正常文件副本。可在仓库根目录运行，也可在下文 wheel 安装后从临时目录运行，后者将 PYTHONPATH 指向仓库的 tests/contracts。

```sh
PYTHONPATH=.:tests/contracts python -B - <<'PYCODE'
from pathlib import Path
from tempfile import TemporaryDirectory
from layauto_v2.pipeline import publish_stage2
from layauto_v2.repository import PublicationRepository
from w023_cases import capture, sample

with TemporaryDirectory() as tmp:
    repo = PublicationRepository()
    ready, request = capture(repo, sample(Path(tmp)), 'normal-public')
    context = publish_stage2(repo, request)
    head = repo.read(context.head_ref)
    state = repo.read(head.snapshot_ref).state
    assert repo.read(context.target_ref).differences == ()
    tip, = (f for f in state['occupancy'] if (f['layer'], f['indices']) == ('M1', (2, 2)))
    assert tip['rect'] == (32, 48, 45, 58)
    assert state['geometry']['records'][tip['record_id']]['source']['byte_offset'] == 2352
    assert head.version == 0 and head.eco_commits == ()
    print(ready.attempt.revision, repo.load_attempt(ready.run_id).revision, context.head_ref.id, head.snapshot_ref.id)
PYCODE
```

## 合同与故障复现

```sh
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
python -B -m pytest -p no:cacheprovider -q --tb=short \
  tests/contracts/test_w023_publication.py tests/contracts/test_w023_boundaries.py

python -B -m pytest -p no:cacheprovider -q --tb=short \
  tests/unit/test_w006_publication.py tests/contracts/test_w006_pipeline.py \
  tests/contracts/test_w006_ipmr01.py tests/contracts/test_w006_review_regressions.py \
  tests/contracts/test_w006_boundaries.py tests/contracts/test_w021_initial_state.py \
  tests/contracts/test_w020_stage2.py::test_readback_rejects_foreign_attempt_for_same_run_id \
  tests/contracts/test_w008_geometry.py::test_domain_state_dependency_direction_and_no_hidden_occupancy_owner \
  tests/contracts/test_w007_contracts.py::test_normalization_and_new_domain_keep_pure_dependency_boundaries \
  tests/unit/test_analysis_api.py::test_no_body_end_to_end

python -m mypy
PYTHONPATH=.:tests/contracts python -B docs/tasks/W023/review_probe.py --check-origin
```

受测提交上，新增合同和模块边界 12 项通过（301.34 秒）。受影响检查 129 项通过（167.91 秒），包括 W006 仓库/codec、读入与失败终结、W020 异仓校验、W021 候选、模块依赖及既有单 cell 只读入口。mypy 对配置内的 88 个源文件检查通过。两组 pytest 串行执行。独立安装目录也从空仓库用公开 pipeline 入口跑通正常样本。[检查输出、安装身份及公开入口的运行引用](evidence/checks.txt)

| 输入或动作 | 从仓库核对的结果 |
| --- | --- |
| 两个独立 run 均在空 head 上完成准备，经屏障同时提交 | 仅增加一次 generation 和幂等回执，快照、事件、head 各一份。胜者 revision 2，落败者收到 HeadConflict，自身原 checkpoint 可读、attempt 保持 revision 1。 |
| initialize / seal_context 切换前故障、切换后丢失响应 | 切换前比较整份仓库观测相等。切换后从公开入口用原请求取回原上下文，无第二次写入。改同键预算返回 IdempotencyConflict；另键重复封存返回阶段冲突。 |
| 外来候选、相同请求在另一仓库、预算不一致、ready 的 evidence 或 value 被替换 | 在准备或提交处拒绝。无法解析或损坏的输入引用带 RefConflict。新 run 的 revision、head、内容及回执同时核对。 |
| 正常样本、额外 C13 + 二维 POLY | 正常样本无目标差异。C13 独立 lineage 读回当前 MN0 为 4n，目标 5n，保留 planner 义务。二维栅 36 片共 720 DBU²，普通占用可用，一维轨号不可用。 |
| 去掉 BTAP_N 坐标声明；在 GDS 追加越过外框的 MARKER | 分别定位到配置字段与原 GDS 记录。两次均保留输入审计与 revision 1，head 为空。 |
| 新 run 在另一绝对目录用相同输入或重新绑定的不同输入请求原 head | 相同时仅增加本 run 的 context 与 attempt 内容。将 M1 的 X 格数由 10 改为 12，或实际缩短 R04 的原始 query 多边形、撤下受影响的 normalized 缓存并重绑，两次均捕获成功，发布报 BindingConflict；原快照仍能回读。 |
| 快照读者沿真实格片查看物理和标注 | LI (1,3) 的 effective 格片为 (28,30)–(34,40) DBU，原图偏移 1648。沿 region → node → 三成员物理分量，另沿覆盖格片的 annotation → R04 / n_lo → VSS。未知导体区域仍标 suspect；MN0、MP0 的本地 B 端没有直接观测到 rail，外部 synthetic 关联分别为 VSS、VDD，LVS 为 not_run。 |

### W006 既有 wire 身份

在分支起点 `74b05f5dcfa5aa1513993460385510ebab22163f` 和受测产品提交分别运行以下命令。成功读入和失败终结两条路径合计 19 条内容，排序、加长度前缀后逐字节计算的 SHA-256 均为 `1e0656468ea09e373862f940eda7231c332b3145c5745dc01ef54860b15f2150`。

```sh
PYTHONPATH=.:tests/unit python -B - <<'PYCODE'
from hashlib import sha256
from test_w006_publication import audit_args, request
from layauto_v2.repository import PublicationRepository
from layauto_v2.domain.publication_codec import encode_record

repo = PublicationRepository()
for run, ready in [('ok', True), ('fail', False)]:
    repo.create_attempt(request(run))
    checkpoint = repo.record_audits(run, **audit_args(run, success=ready))
    if not ready:
        repo.finalize_precontext_failure(checkpoint.finalize_request)
items = [encode_record(repo.read(ref)) for ref in repo.snapshot().content_refs]
d = sha256()
for row in sorted(items):
    d.update(len(row).to_bytes(8, 'big') + row)
print(len(items), d.hexdigest())
PYCODE
```

## 构建及独立安装复跑

在仓库根目录执行。安装后切换到临时目录，PYTHONPATH 仅加入样本准备 helper，产品从 wheel 导入。

```sh
repo_root=$(pwd)
release_dir=$(mktemp -d)
python -m build --outdir "$release_dir/dist"
python -m venv "$release_dir/venv"
"$release_dir/venv/bin/python" -m pip install "$release_dir"/dist/*.whl
"$release_dir/venv/bin/python" -m pip check
cd "$release_dir"
PYTHONPATH="$repo_root/tests/contracts" "$release_dir/venv/bin/python" -B "$repo_root/docs/tasks/W023/example.py"
```

执行侧从上述产品提交的 git archive 构建 sdist 和 wheel，逐字节核对全部 132 个包文件在源码、wheel 和安装目录中的内容；本次 wheel 的 SHA-256 为 `6915c0ff4f2696241205adcacf2605bc1104b589c51e2999886f247f6b97e9c2`，sdist 为 `511cf6234d34cdb29e1e5c944757e0668bab0ca06aebecbb1aafaed064049d31`。解释器全量及实际合并组合检查归 PM。

## 首次完整读回的单次测量

使用独立安装的 wheel 和正常文件，已有捕获用时 1.3245 秒，W020/W021 组装用时 44.6967 秒。新增的逐层校验与冻结用时 1.2269 秒，原子发布 1.3107 秒，释放候选并回收后，按引用读回全部发布对象用时 0.3983 秒。各阶段共用一个进程，回读时候选的弱引用已失效。[实测原始输出、文件 SHA-256 与仓库引用](evidence/readback.json)

| 阶段结束时 | 当前 RSS（字节） | 进程累计峰值 RSS（字节） |
| --- | ---: | ---: |
| 捕获与输入审计 | 32,129,024 | 38,912,000 |
| 既有组装 | 109,481,984 | 415,895,552 |
| 校验和冻结 | 109,490,176 | 415,895,552 |
| root 切换 | 109,490,176 | 415,895,552 |
| 释放候选后完整读回 | 107,425,792 | 415,895,552 |

仓库持有的不可变编码内容从 2,088,782 字节增至 2,635,919 字节，发布增量 547,137 字节。该量按 root 中全部去重内容的字节串求和；Python 对象、索引及分配器开销体现在 RSS 中。进程峰值出现在既有组装阶段。这里的 RSS 差值是阶段边界观测，不能度量随后每次临时分配的峰值。

## 证据复用与补跑

沿用 W020–W022 已验收的捕获认证、分层重建、annotation 和物理图构建算法。相对本分支起点，W022 判定、W018 投影、原 GDS、正常 CDL 及完整坐标样本均未变更。W023 新测从仓库内容引用解析各项见证。变更 recipe、捕获或绑定、输入/依赖、codec、root 切换、层能力，或集成出现冲突时，重跑对应检查。范围为进程内原子发布和 synthetic 的 sealed_open 阶段交接。PM 在合并版运行 Python 3.10、3.12 全量及发布组合检查。[W022 集成证据](../W022-layer-initialization-checks.md#pm2-integration)

## 提交身份核对

首次推送被 GitHub 的邮箱隐私保护（GH007）拒绝。本轮提交改用仓库既有的 noreply 地址。以下每对提交的完整 Git tree 相等，包含源码、测试、示例与配置。独立复核按同一 tree 采信；正文复现命令指向可从远端取得的提交。

| 本地受审提交 | 分支可取提交 | Git tree |
| --- | --- | --- |
| `3ae18037ffddcce7e3b69cddfa85e24b4bf8a776` | `f28546777edc842018f7cea56992eecc33d6e758` | `4c14a4fbfd07292bf6c77f4a19c1054b97f9aec9` |
| `e9a2465889d1bc73d4f5caf7e8ccc695bba35b47` | `f1bcbda88b6b1b6b524ef50188072ab98356cb15` | `992472aaf087c2e90095ad637466dd9f208e3107` |
| `df600a23ab3e53a1d453cf2d53b3596b4c0e511c` | `8309595f205ed4a485ea7fd8f8681fe92e820e9d` | `95660be38ea4cc9a8614e2340bc7f5aacf2f1015` |
| `a5292825d0e829641b43bfbcb5fbacb2453f3ffd` | `9f6fa09ce79c2b9c731c909b5a2e526a06e66c47` | `5410ec3450c21bd55fedb1204bde59a506d48359` |
