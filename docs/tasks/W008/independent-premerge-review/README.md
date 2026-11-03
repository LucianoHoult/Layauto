# 本轮独立复核附件

本目录只保存 2026-11-03 独立合并前复核的新材料。所审 HEAD 为
`131f66dfadd77b5fb9073db999d6939051c3addf`；产品交付为
`aced62b0adda35fe7bcd8284a7354badc5b03649`。结论见
[父报告](../independent-premerge-review.md)。`review-receipt.json` 绑定源身份、
命令回执及新附件字节；Git 提供最终完整报告交付身份。

| 目录 | 内容 |
| --- | --- |
| `recovery/` | 独立 checkout、真实 Git 对象/远端/工作区恢复回执 |
| `validation/` | 本轮新环境安装输出、环境/版本、完整 730 项 pytest、strict mypy、pip check、scope/import 核对及其实际命令/原始输出/hash |
| `input/` | 24 项独立角色、alias、真实 readback/noIO、原 CR-01 正确拒绝和异常探针；脚本/输出/回执/说明 |
| `geometry/` | 600 组数学分区、21,314 点、逐 record 二进制/面积/重叠验证、4 次真实派生输入及中立信任边界探针 |
| `evidence/` | 新的 29 项只读证据审计，核对 235/84/13 清单、包实物及历史采用边界 |

原路径反映实际执行环境；复制时保留脚本/输出/回执原字节，未改写历史路径。
`runner-output.txt` 是 geometry runner 的外层输出；其内层两个原始输出和
`receipt.json` 是主要证据。纯标准库证据审计使用主机 Python3.12.14，产品
测试/探针使用本轮新建 Python3.12.14 venv。旧 Mac 全矩阵和安装树未在本次
重新运行或访问，采用依据见 `evidence/summary.md`。

## 重放

先读脚本的 HEAD/路径假设。`evidence/audit.py` 明确要求所审 `131f66df…`，
应使用该提交的独立 checkout；后续报告提交不应改成该脚本的默认受审对象。
所有会生成输出的 runner 应先复制到新的临时目录再执行，不能在本目录原地
重放并覆盖证据。原 PM 审计另绑定 `baad534…`，本轮没有原地执行它。

例如在一个干净、位于 `131f66df…` 的 checkout 中，先设置显式路径：

```sh
REVIEW_REPO=/absolute/path/to/reviewed-checkout
REVIEW_PYTHON=/absolute/path/to/dedicated-venv/bin/python
REVIEW_SCRATCH=/absolute/path/to/new-empty-scratch
```

新环境用 Python3.10+ 创建，按 `pyproject.toml` 安装 `.[dev]`。然后从仓库根
目录执行下列产品检查；mypy cache 和所有新输出放到上述 scratch 中：

```sh
cd "$REVIEW_REPO"
PYTHONDONTWRITEBYTECODE=1 "$REVIEW_PYTHON" -B -m pytest tests/unit tests/contracts -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 "$REVIEW_PYTHON" -B -m mypy --cache-dir "$REVIEW_SCRATCH/mypy-cache"
"$REVIEW_PYTHON" -B -m pip check
```

将本目录复制到 `$REVIEW_SCRATCH/evidence-copy` 后可运行：

```sh
cd "$REVIEW_REPO"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests/contracts "$REVIEW_PYTHON" -B "$REVIEW_SCRATCH/evidence-copy/input/probe.py"
"$REVIEW_PYTHON" -B "$REVIEW_SCRATCH/evidence-copy/geometry/run_probes.py" "$REVIEW_REPO" "$REVIEW_PYTHON"
"$REVIEW_PYTHON" -B "$REVIEW_SCRATCH/evidence-copy/evidence/run.py" "$REVIEW_REPO"
```

各 runner 的参数以脚本实际定义为准。`input/probe.py` 的攻击构造借用既有
fixture-copy/rebinding 工具，没有加载 expected/spec/oracle；数学/二进制探针
不调用现有测试 helper 或产品算法生成期望。所有派生输入只在临时副本生成，
不更改已验收 fixture/答案。
