# W007 最终验证回执

最终被测产品与测试提交：`0f879f01acbeac033173d0b6c6257c376bb9272a`。本目录根下的命令回执、日志和 packages 对应该版本；[candidate-6712cbc](candidate-6712cbc/README.md) 是必须保留的历史候选，不能代替最终验证。[environment.json](environment.json) 是实施前环境，[environment-final.json](environment-final.json) 是最终四套环境。

[receipt.json](receipt.json) 汇总实际命令、cwd、时间、退出码、日志及身份。每条命令的同名 JSON/TXT 保留原始回执/输出；不依赖执行 session 的临时目录恢复结论。虚拟环境及命令中的绝对路径是实际执行位置，换机时需按项目环境规则重建。

Review 的 [wire 异常修正前 pytest 输出](../review-evidence/wire-decoder-output-initial.txt) 保留原生行尾空格和末尾空行，未为通过空白格式检查改写原始证据；最终暂存内容的 `git diff --cached --check` 仅排除此原始日志后通过。

| 验证 | 最终结果 |
| --- | --- |
| Python 3.12.14 / 3.10.22 全部 unit/contracts | 分别 553 passed / 256.34s、553 passed / 342.94s；原 405 项及新 148 项，含 W005/W006/IPMR-01 |
| 两解释器 strict mypy | 各 33 source files，无问题 |
| 新 sdist / wheel | 构建成功；各 83 个 runtime 文件与被测清单一致 |
| 两套新 venv 安装及源码外 smoke | 均成功；真实 W005 正常/C08/C13、W006 InputsReady/readback、wire 与 no-IO 检查 |
| 四套环境 pip check | 全部成功 |
| 既有输入/实现/记录保护 | [14 处保护路径](protected-paths.json) 的 Git 对象与 PM 交接一致，工作树无差异 |

运行 smoke 时将 [wheel_smoke.py](wheel_smoke.py) 复制到源码树外，再使用两套只安装 wheel 的新环境运行；`PYTHONPATH` 不指向源码，实际 import 路径见 wheel-smoke 日志。脚本只从 fixture 复制输入，剔除 expected/oracle/spec/answers 等，不 import 测试 helper。fixture 为 `tests/fixtures/w003_m1`，profile 为 `synthetic_static_fin_context_no_change_v2`；派生反例仅在临时副本改动并按既有合同重绑来源。

[source-manifest.json](source-manifest.json) 的 101 项覆盖 runtime、unit/contracts 测试与构建/typing 配置，content SHA-256 为 `f051ae0fecab66a1104e0aa609cc8450c1cf480a99384113027dc5a6f40976a9`。文档/执行/review 记录不纳入该清单，避免循环身份；最终交付仅在该被测版本后追加这些记录。[package-identity.json](package-identity.json) 保存包及清单 SHA，实际包一同存于 [packages](packages/)。独立 reviewer 的核验见 [delivery-audit.json](../review-evidence/delivery-audit.json)。

没有验证真实 EDA/PDK、完整几何/坐标/occupancy/physical connectivity/body/extraction、baseline/seal、整轮 no_change/terminal、ECO 或 Stage 6；均未在本切片实现。组件语义相等不表示 extraction equality 或整轮成功。此回执是执行证据，不是 PM 验收。
