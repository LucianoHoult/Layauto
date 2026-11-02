# W005 独立合并前代码与合同复核

日期：2026-11-02。角色：新一轮独立 reviewer，未参与 W005 产品实现或原测试编写。主 reviewer 负责合同对照、当前环境验证、复现与结论；三个只读专项分别检查 GDS/CDL/中立合同、query/绑定、工程证据身份。专项不写仓库，由主 reviewer 汇总本报告。

## 结论

**当前不具备合并 main 条件：新增 1 项 P2 必须修正项 IPMR-01，尚未修复。** 它是可复现的输入错误边界与 canonical evidence 缺陷，附带同根因的测试缺口；不是证据不足或可选改进。未发现另外的必须修正项、单独的证据阻塞或需要新增的产品要求。

本次新环境完整组件测试 **237 passed**，strict mypy **13 source files 通过**，但现有测试未覆盖 IPMR-01。旧 review 的 R1–R5 关闭记录与 PM“分支技术接收通过”均保留为其当时事实，不替代本次判断。交 PM 安排修复及独立复核；本 session 不改实现、不代写验收、不合并 main。

## 实际版本与范围

| 项目 | 本次核实 |
| --- | --- |
| 仓库 / 分支 | `LucianoHoult/Layauto` / `codex/w005-input-reading-binding` |
| 实现前 base | `5b7205009b3ed7f8fe15e135e674654f2f544557` |
| 实际被审 head | `787a09e269062dd5c31df8ced627a6ecb799df57`；clone 后及完成审查时远端均为此 SHA |
| 实现交付 | `51d4d9d7b0d2715a5a2f3fe578615be4c59e74cb` |
| 发布等价产品提交 | `cf35d97478cd78aa7ad707d18c9e37ceda10eafb`，tree `70b905b98691ddcdf58726810ca875dc853069c2`；原受审 `ab7feddff83749b54c1866b1ad95fbc99fd787f1` 的映射见 [publication-map.json](verification/publication-map.json) |
| main 观察值 | `87fe5a5a87d0cbb1f97952f1485dac9a71416369`，只读核对，未合并或进行集成验收 |
| 实际 diff | base→交付 39 个路径；base→head 43 个路径。`787a09e` 只修改五个 PM 文档路径：`docs/README.md`、`docs/current-work.md`、`docs/roadmap.md`、W005 任务及新增 `pm-receipt.json`，不含产品/测试变化 |

启动时预置 `/workspace/Layauto` 是 `work` / `87fe5a5…`，staged、unstaged、untracked 为空，与指定任务版本不同。保留该 checkout，在 `/workspace/work/w005-premerge/repo` 独立 clone 指定分支后审查；新 checkout 初始也干净。未静默以旧版本代替 W005。检查到仅根 `AGENTS.md`，没有适用的局部追加规则。

读取了 AGENTS、README、协作规则、local-setup/remote-development、[W005 要求及 A1–A7](../W005-input-reading-binding.md)、其引用的 [architecture](../../architecture.md) §2.1–2.3、§3.1–3.2、§4.8、§5、§11.2/11.10/11.13–11.15、§12.1–12.8，以及 [W003/W004 输入合同](../W003/contracts.md)、实际 fixture/profile/raw/header/context/反例。检查实际 diff、三个 domain 文件、全部 importer/tech 实现、unit/contracts 测试、pyproject/README、接口与代码 review、verification 和 PM 回执。关键错误与来源要求回查原文，没有只依据完成表。

## IPMR-01 — P2：字符串转义可突破 typed 输入错误边界，并产生无法 canonical 编码的成功结果

**状态：开放，合并前必须修正。**

位置（行号绑定上述 head）：

- [`layauto_v2/importers/config.py:77–81`](../../../layauto_v2/importers/config.py#L77-L81)：字符串直接返回 `n.value`，没有处理 PyYAML 接纳的 surrogate code points。
- [`layauto_v2/importers/reader.py:335–336`](../../../layauto_v2/importers/reader.py#L335-L336)：缓存比较直接调用 `canonical_bytes(cache)`；外层第 342 行只转换 `InputError`。
- [`layauto_v2/domain/codec.py:75–77`](../../../layauto_v2/domain/codec.py#L75-L77)：`ensure_ascii=False` 后 UTF-8 编码，遇 surrogate 抛 `UnicodeEncodeError`。

**违反的既有要求。** W005“输入、结果与范围”第 4 项要求提供的 normalized 缓存比较并拒绝漂移，第 6 项要求预期输入错误返回带来源、hash、定位和已完成依据的中立结果；A2 要求可稳定编码/digest 的 exact evidence，A3 要求缓存漂移错误可定位。架构 §2.2 的 schema-canonical evidence、§12.1 的 validated immutable DTO 和 §12.6 的 typed `EvidenceIssue` / `ParseResult` 同样适用。非法输入造成的已知编码错误不属于应传播的程序员意外异常。

**复现操作。** 从被审 checkout 根目录、安装好 README 的开发依赖后运行以下脚本。它只修改仓库外临时副本，不改已验收 fixture/golden；缓存不在 header closure 中，缓存用例无需重绑。两个 site 用例都重新绑定实际 site bytes 与 closure digest，排除了 hash 不一致的干扰。

```sh
python -B - <<'PY'
import hashlib
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from layauto_v2.domain.codec import digest
from layauto_v2.importers import read_inputs

fixture = Path('tests/fixtures/w003_m1').resolve()
with TemporaryDirectory(prefix='w005-review-') as tmp:
    for case in ('cache', 'escaped_note', 'literal_note'):
        root = Path(tmp) / case
        shutil.copytree(fixture, root)
        if case == 'cache':
            path = root / 'query/normalized/device_regions.yaml'
            data = json.loads(path.read_text(encoding='utf-8'))
            data['schema_version'] = chr(0xD800)
            path.write_text(json.dumps(data) + '\n', encoding='utf-8')
        else:
            path = root / 'site_config.yaml'
            data = json.loads(path.read_text(encoding='utf-8'))
            data['note'] = 'example ' + chr(0x1F600)
            path.write_text(json.dumps(data, ensure_ascii=(case == 'escaped_note')) + '\n', encoding='utf-8')
            header_path = root / 'query/header.json'
            header = json.loads(header_path.read_text(encoding='utf-8'))
            for entry in header['closure']['entries']:
                if entry['uri'] == 'site_config.yaml':
                    entry['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            closure = json.dumps(header['closure']['entries'], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
            header['closure']['sha256'] = hashlib.sha256(closure).hexdigest()
            header_path.write_text(json.dumps(header) + '\n', encoding='utf-8')
        try:
            result = read_inputs(root / 'site_config.yaml')
            print(case, 'status=', result.status, 'issues=', [x.code for x in result.issues])
            if result.value is not None:
                print(case, 'note=', ascii(result.value['config']['note']))
                digest(result.value)
                print(case, 'digest_ok')
        except UnicodeEncodeError as exc:
            print(case, type(exc).__name__, str(exc))
PY
```

**本次实际结果**（主 reviewer 实跑，两个专项另外独立复现缓存错误）：

```text
cache UnicodeEncodeError 'utf-8' codec can't encode character '\ud800' in position 27729: surrogates not allowed
escaped_note status= success issues= []
escaped_note note= 'example \ud83d\ude00'
escaped_note UnicodeEncodeError 'utf-8' codec can't encode characters in position 2101-2102: surrogates not allowed
literal_note status= success issues= []
literal_note note= 'example \U0001f600'
literal_note digest_ok
```

缓存文件的 bytes 是合法 UTF-8/ASCII；孤立 surrogate 是转义后的非法字符串内容。`read_inputs` 在完成 query 后抛裸异常，没有返回 `ParseResult`，调用者拿不到已读缓存 hash 与九份已完成组件 evidence。第二用例则来自标准 `json.dumps` 对合法 U+1F600 的转义：loader 留下两个 surrogate，返回 `success`，随后中立 codec 无法编码。第三用例是同一字符的直接 UTF-8 表示，成功且可 digest，证明问题在转义/字符串规范化边界，不是新增几何或格式能力。

**预期与影响。** 非法字符串/缓存应得到有来源、定位与实际 bytes hash 的 typed error，并保留 completed evidence；不得逃逸为未分类异常。成功接纳的字符串应是可进入 canonical codec 的值；合法 JSON surrogate pair 应与其 Unicode 字符等价。当前缺陷既中断错误交接，又可能把不可编码内容交给后续 evidence 消费者。普通 fixture 通过不能覆盖这一输入变体；无需真实 EDA 或 Stage 2 才能触发。

**最小修复建议。** 在 safe document 的字符串边界（包括 key）处理有效 JSON surrogate pair，并对孤立/非法 surrogate 产生定位 `InputError`，使 loader 接纳值与 codec 可编码值保持一致；也可在必要的编码边界窄转换已知输入编码失败，但仅包住缓存比较不足以解决成功配置值的问题。不要以全局 `except Exception` 吞掉程序错误。补充公共 API 的缓存错误回归和转义/直接 UTF-8 等价的配置→digest 回归，断言错误来源/hash/completed 仍保留。此处仅提出修复方向，未改实现或测试。

## 本次运行与覆盖判断

按仓库环境说明创建新的 `/workspace/work/w005-premerge/venv`，没有沿用其他 session 的环境。Linux x86_64 / glibc 2.41；CPython 3.12.14、pytest 9.2.0、mypy 2.4.1、PyYAML 6.0.3、types-PyYAML 6.0.12.20261030、build 1.6.1。

| 本轮实际执行 | 结果 |
| --- | --- |
| `python3 -m venv /workspace/work/w005-premerge/venv`；在该环境 `python -m pip install -e '.[all,dev]'` | 安装成功；`python -m pip check` 无依赖冲突，导入指向独立被审 checkout |
| `python -B -m pytest -p no:cacheprovider tests/unit tests/contracts -q` | **237 passed in 23.67s**，被测 head 为 `787a09e…`，产品文件与发布受审版相同 |
| `python -m mypy`（`MYPY_CACHE_DIR` 指向仓库外） | **Success: no issues found in 13 source files**；strict 与目标 Python 3.10 设置来自 pyproject |
| 上述 IPMR-01 三用例 | 两种失败机制复现，直接 UTF-8 对照成功；两个专项另复现缓存裸异常 |
| GDS/CDL 专项外部探针 | 固定 seed 的 400 次 GDS bytes 变异：398 typed errors / 2 合法结果；400 次 CDL bytes 变异：345 typed errors / 55 合法结果。另对 400 个 REAL8 与独立精确公式比较、signed INT32 XY 极值、多 top/空 top/CRLF/tab/参数重排及 codec roundtrip 检查通过；有限探针不代表格式穷尽证明 |
| Query 专项外部探针 | 九份 raw 逐行前缀截断及删除，共 252 次公开 API 调用；实际改副本、重绑 raw hash、移除缓存，全部为 typed error，无未预期异常或错误接受 |
| `git diff --check <base> HEAD`，fixture/support/architecture diff 与工作区检查 | 通过；已验收输入、答案、support 和架构相对 base 无变化 |

组件测试与代码对照支持以下判断：

| 要求 | 独立检查后的结论 |
| --- | --- |
| A1 | 真实文件读取、40 个 BOUNDARY（含未注释 MARKER）、完整 source/target CDL、2/4/2/8 query records 和只读 context 有依据；独立答案只在测试使用，实际输入目录前后 hash 测试通过 |
| A2 | XY/REAL8/lexeme/Fraction、完整 query polygon/provenance、schema/owner/registry/单位模型、不可变与跨进程 digest 的现有检查通过；**字符串 canonical 边界有 IPMR-01 缺口** |
| A3/A4 | hash/closure/top/profile/status、坏 raw 与缓存删除/漂移、C01–C07/C11/C12/C17/C18/C21/C22及 body 读取/绑定分界已检查；**缓存转义错误没有满足 typed 失败合同** |
| A5 | 第二合法输入的 top/器件/query identity/raw 路径/记录参数顺序/坐标变换和额外未注释图形测试通过；未发现固定 INV/Q17/40/5/7/旧 hash 的产品答案依赖 |
| A6 | importer/domain/tech 职责与依赖边界保持；无运行时 oracle、legacy/support、EDA、状态构造或输出写入。未把格式内关联扩成跨 GDS/CDL 的 Stage 2 join |
| A7 | 本轮完整组件测试和 strict typing 通过；最低解释器及构建/干净安装证据按下节身份核验后采用，未冒称本轮重跑全部矩阵 |

## 采用的既有证据及身份限制

- [source-manifest.json](verification/source-manifest.json) 的 22 个文件，在 `cf35d974…`、`51d4d9d…`、`787a09e…` 三个版本均逐项 hash 相同；[receipt.json](verification/receipt.json) 的 13 个 evidence hash 全部重算匹配。publication-map 的 14 个发布提交 tree 均匹配，父链从指定 base 正确接续。E1 正文重建 hash 与 [interface-review](interface-review.md) 的 `293b6934179252909e7eb253ede5464d18e82268335cbcb6611036967ace354a` 相同。
- [pytest-310-final.txt](verification/pytest-310-final.txt) 为 CPython 3.10.22 上最终 **237 passed in 33.85s**，原身份由 receipt 与 [code-review](code-review.md) 关联到 `ab7fedd…` / 发布等价 `cf35d974…`。旧 3.10/3.12 的 236 项日志保留历史身份；最终 3.12 的 237 项另有旧独立 review、PM 和本次实跑支撑。
- [构建日志](verification/build-final.txt) 显示隔离 PEP517 sdist→wheel 成功，含 `py.typed`；[安装日志](verification/install-wheel.txt)、[pip check](verification/pip-check-wheel.txt)、[smoke](verification/wheel-smoke.txt) 支持新环境完整依赖安装及源码目录外验证。实际审阅 [wheel_smoke.py](verification/wheel_smoke.py)：检查 site-packages 导入、正常 40/8 结果、临时副本重绑坏 raw 后 `MissingTerminator`。
- [pm-receipt.json](pm-receipt.json) 记录从 `51d4d9d…` archive 独立重建、新 3.12 安装环境、源码目录外 `-I -B` smoke，且明确新 wheel 不冒充原 wheel。本轮核对方法与结果，没有发现需要机械重跑全矩阵的具体矛盾。
- 本 clone 无原 14 个未发布 commit 对象，也未取得原执行者 wheel。本轮直接证明发布树、manifest、当前文件及证据 hash；旧→新仅邮箱元数据差异和原 wheel 内容一致性采用原独立 reviewer 的已刊核验事实，不声称本轮直接比过那些不可用对象。这是已披露的证据采用边界，未单独构成新阻塞。

## 未验证范围与交回 PM

本次不运行真实 Calibre/Virtuoso/PDK、生产上传、无关 legacy 回归或全量 fixture 生成。未新建 Python 3.10 环境或重复 wheel 构建安装，也未测试其他平台/解释器。探针只在仓库外副本执行；可携带复现见本报告，不把短期临时目录当跨 session 必需证据。

W005 仍只是读取组件：正式 pipeline 的 attempt/RunRecord/terminal、Stage 2 状态和跨格式/空间/body 物理判断、Stage 6 导出及完整 M1 未由本轮验证。C08/C09/C10 留 Stage 2 准入，C13 留目标解释/规划，C14–C16 与 body 物理反例留提取/规则，C19/C20 留输出转换；不因这些后置义务新增 W005 finding。

**交回 PM：安排 IPMR-01 修复，在新提交上补充上述回归并独立复核，再恢复合并判断。** 本轮只新增本报告并在 W005 reviewer 区域追加结论；原 review、执行、PM 记录及任务阶段均保留。报告不构成 PM 验收记录，也不授权合并或启动下一任务。
