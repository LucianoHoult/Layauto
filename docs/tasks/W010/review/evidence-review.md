# W010 A8 独立工程证据复核

Reviewer `/root/code_review/evidence_review`，未参与产品、正式测试或原工程矩阵实施。受审 base 为 `9758a157115cc22d91ce095ac2002209b9f210d3`，head 为 `0f5029df935bc0acd106aad1bc2be81304d4f442`。本专项只检查工程证据及实际包/安装，不代替数学、公开合同或总代码 review。

**新增必须修正项 0。** [独立审计脚本](evidence-audit.py)在仓库根目录执行 `python -B docs/tasks/W010/review/evidence-audit.py`，结果为 **68/68 passed**，见[完整结果](evidence-audit.json)。未修改产品、正式测试、verification 原证据、PM 段或 current-work。

| 独立检查 | 实际结果 |
| --- | --- |
| 被测身份 | 252 个 source/tests/config 文件逐字节等于冻结 Git head、当前 checkout、原实际测试 source 树和 tar 的恰好 252 个唯一成员；source manifest、tar、receipt 和 evidence manifest 的 SHA-256 均等于交接身份 |
| 原始工程回执 | 21 条命令的单独 JSON 与总 receipt 一致，42 份 stdout/stderr 的实际 bytes/hash 均吻合，全部 exit 0；verification 共 79 个文件，包括 manifest 本身，manifest 的 78 个条目与其余文件集合/bytes 完全一致 |
| 双解释器完整回归 | 原输出分别为 Python 3.10.22 的 `1465 passed in 3615.88s`、3.12.14 的 `1465 passed in 2614.99s`；原命令均为无筛选的 `pytest -p no:cacheprovider tests/unit tests/contracts -q`，没有 skipped/deselected |
| 原能力保留 | 基线修正快照的 244 项与 base Git 全部一致；两份最终 collection 都有恰好 1465 个唯一 nodeid、包含同一原始 1149 个 nodeid并新增 316 个。tests 下 35 个既有 Python 文件仅具名 W007 dependency guard 文件改变，旧 test function 名无遗漏；16 处保护路径在 base→head 的实际 diff 为空 |
| typing/依赖 | 双原输出均为 strict mypy `Success: no issues found in 48 source files`；pyproject 的 Python 3.10/strict 与新增模块覆盖明确。开发和安装环境的 pip check 原输出通过 |
| 新包实物 | wheel `f77c718aa292d8c15c37206a1543462e29888dc65e38e61cc830856f75c60232`、sdist `49b5fdd10ee7aca6f349dfcaea1d42292dfd647a6d05a9aa695d180d85d25d5b` 的实际字节与回执相同；两包各 94 项 runtime Python/py.typed 与源码完全一致，包内成员无重复；wheel 声明 `Requires-Python: >=3.10` |
| 两套实际安装 | 独立读取 `/workspace/work/w010-final-0f5029d/clean-{310,312}` 的实际安装树，各 94 项 runtime 与源码及两包完全一致。原 pip 报告给出 3.10=本次 sdist、3.12=本次 wheel 的 URL 与精确 artifact hash；venv 均禁用系统 site-packages |
| 原安装组合 smoke | 原命令从 checkout/snapshot 外 cwd 以 `-I -B` 执行，实际导入来自对应 site-packages；direct/readback 均为 14 nodes、8 edges、6 components、16 个 pass audit，attempt 保持不变。脚本真实执行 W005/W006→W008→W009→W010、禁 IO、公开 roundtrip 和漏节点拒绝，没有导入 test/support、spec/oracle/expected 作为运行输入 |
| Reviewer 实际导入 | 本专项分别重新调用两个实际安装的 `python -I -B`，从 `/workspace` 导入包并读取版本；均 exit 0，确认当前解释器及实际 site-packages 来源。完整 argv/stdout/stderr 存于独立结果 |
| 有限资源证据 | `performance_probe.py` 与 performance.json 的 probe/runtime 身份仍等于当前产品。4 个样本含正常、cut-islands、额外 20 个 M1 和 8 条重复 CONTACT；公开构建/codec 的重复认证成本、约 15–17 MB wire、约 988 MiB 累积 RSS 高水位和全部 max-pieces=1 的限制均明确披露 |

证据采用边界：本专项实际重新检查 Git/所有清单/归档/包/安装 bytes、原始命令输出和两套安装导入；双完整回归、typing、构建、安装及原完整组合 smoke 采用已经独立认证的执行记录，没有冒称重新运行。原 R1 guard 失败与 preflight 漏样张/中断的 partial 保留历史身份，未计入最终通过。

3.10 的旧 pip 将安装树 `direct_url.json` 的 `archive_info` 留空；实际 URL 与本次 sdist 一致，原 `install-310-report.json` 明确保存该 sdist 的 SHA-256，实际 artifact 和完整安装 runtime bytes 也逐项吻合。因此本报告以这些可直接核验的材料认定包来源，不虚构 direct_url 内存在的 hash。

本结果支持 A8 的既定 synthetic/local scope，不证明极端规模、多片压力性能、真实 PDK/EDA 或完整 Stage2/M1 准入。PM 验收与集成决定仍归 PM。
