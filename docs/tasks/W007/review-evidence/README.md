# W007 独立 review 初审证据

由 `/root/code_review/dto_review` 编写并执行，主 reviewer `/root/code_review` 重跑核对并保存。产品基线为 `18546982984cbbbf1c29713c5b00193766fa9cd5`；环境 Linux / Python 3.12.14 / `/workspace/.venvs/layauto/bin/python`。记录仅证明所列组件行为，不代表 PM 验收或完整 M1。

| 脚本 | 初审实际输出 | 范围 |
| --- | --- | --- |
| [probe.py](probe.py) | [probe-output-initial.txt](probe-output-initial.txt) | CR-01 同 capture 参数/query 名称/geometry 错拼；CR-02 错网来源；CR-03 集合顺序；CR-05 NF=2 success 重标 |
| [relabel.py](relabel.py) | [relabel-output-initial.txt](relabel-output-initial.txt) | 真实 C10/no-reduction 与 swap-X 错误重标为 public success |
| [readback.py](readback.py) | [readback-output.txt](readback-output.txt) | 真实 W006 alias/readback、wire roundtrip、attempt 不推进、非法 sibling 拒绝 |

脚本实际执行时使用 `/workspace/Layauto` 绝对路径与 `PYTHONPATH=/workspace/Layauto:/workspace/Layauto/tests/contracts`。随 Git 保存的脚本仅增加从自身位置定位仓库的 bootstrap，并替换上述硬编码路径；探针逻辑未改变。原执行脚本和发布脚本的 SHA-256 分别保存在 [identity.json](identity.json)，输出是未修改的实际初审输出，不能当作修后输出。

重建初审：在独立 checkout 检出产品提交 `18546982984cbbbf1c29713c5b00193766fa9cd5`，从含本证据的提交复制本 `review-evidence` 目录到同一相对路径（不要 checkout 新产品）。使用含项目依赖的 Python 3.10+，于该 checkout 执行：

```sh
python -B docs/tasks/W007/review-evidence/probe.py
python -B docs/tasks/W007/review-evidence/relabel.py
python -B docs/tasks/W007/review-evidence/readback.py
```

`probe.py` 和 `relabel.py` 是原受审版本的问题探针：修复后应在非法构造处抛 ValueError，而不继续打印 success；它们不捕获每个拒绝后继续。逐项修后回归由测试与 review 复核记录给出。测试只复制 fixture 到临时目录或在内存替换 DTO，未改已验收输入。

补修复核 CR-01-FR1 的 [whitespace.py](whitespace.py) / [初始输出](whitespace-output-initial.txt) 实际运行于 `df977ff3da1c10ed53bfe52998dd6f4c8e148936`。命令：`python -B docs/tasks/W007/review-evidence/whitespace.py`；应保留 reader success 并得到 typed UnsupportedTerminalSwap，原输出记录了 ValueError 回归。该子项版本另列于 identity.json。

补修复核 CR-01-FR2 的 [seed_capture.py](seed_capture.py) / [初始输出](seed-capture-output-initial.txt) 实际运行于 `2f8a2d290927a21cf722cefd036e88967624be04`。命令：`python -B docs/tasks/W007/review-evidence/seed_capture.py`。两器件 geometry 与对应provenance整组互换，保留各自request identity/record ID，原版本错误success；修后应ValueError。

补修复核 CR-01-FR3 的 [seed_capture_metadata.py](seed_capture_metadata.py) / [初始输出](seed-capture-metadata-output-initial.txt) 实际运行于 `6712cbcf0e00395a32836122639c79a88c3813b6`。命令：`python -B docs/tasks/W007/review-evidence/seed_capture_metadata.py`。FR2 同样的 geometry/来源互换，再对调 responses metadata；原始 source bytes 与 request pointers 不改，仍错误 success。专项 reviewer 原探针与便携版仅 bootstrap/仓库定位不同。

`6712cbc` 候选的 125 项 W007 与原始 probes 复核记录保存在 [candidate-6712cbc/final-review.json](candidate-6712cbc/final-review.json)。这是 FR3 发现前的候选测试记录，不代表最终通过。

## 最终复核

最终产品/测试为 `0f879f01acbeac033173d0b6c6257c376bb9272a`。主 reviewer 实际运行 [run_final_review.py](run_final_review.py)，得到 148 项 W007 通过及原始 probes 的预期结果；精确命令、环境、输出与 SHA 保存在 [final-review.json](final-review.json)。该脚本生成 [final-probes/](final-probes/)：只将原探针的仓库定位层级和已审 FR3 内部模块 imports 更新，逻辑不变。原 `probe.py` / `relabel.py` 是逐步演示漏洞的脚本，修后分别在首次非法 CDL 归属、C10 success 构造处以 ValueError 停止，exit 1 是预期拒绝；逐项不停止的回归由 148 项测试覆盖。没有将 ImportError 视为通过。

执行者先发现的 ER-01 wire decoder 异常转换问题，在 `5c77f2533a1fb32b05aa6f864570fc7ee4482931` 由主 reviewer 复跑 `python -B -m pytest -p no:cacheprovider tests/contracts/test_w007_contracts.py -q -k captured_requests_decoder_unexpected`，结果 2 failed / 8 passed；[原输出](wire-decoder-output-initial.txt)保留。最终修正后 adapter/input wire/nested result wire 异常测试全通过。

主 reviewer 另实际运行 [audit_delivery.py](audit_delivery.py)，独立校验最终 Git blob/工作树清单、sdist/wheel 的完整 runtime 文件集合和字节 hash、13 项成功命令回执以及 14 个历史保护路径；结果保存在 [delivery-audit.json](delivery-audit.json)。本目录记录 reviewer 自己的检查和原始复现；执行者双解释器/build/install 完整日志另见 [verification](../verification/)，没有把执行者运行误记为 reviewer 重跑。
