# W010 合并前独立工程证据专项

2026-11-06；reviewer `/root/evidence_review`，未参与 W010 产品、正式测试或原工程矩阵实施。受审 HEAD `c4909ab679d0c0806200fcb132db8a5de1ad3e75`；main `3be0b98359038bab6c23980b55a48987cc71a369`；准备 `9758a157115cc22d91ce095ac2002209b9f210d3`；冻结产品/正式测试 `0f5029df935bc0acd106aad1bc2be81304d4f442`；执行交付 `ca39aedcb71fda02f77ffda1eb5d5dddc598226e`。

**本专项必须修正项 0；工程身份与守卫核验通过。** 本结论限于 A8 及交付身份，不替代主 reviewer 对产品行为、异常边界或合并条件的独立判断。

读取根 AGENTS、README、协作/本地及远端环境规则、W010 要求、执行、代码 review、PM 接收/JSON、工程和安装原回执，以及架构 §11.2–11.3、§11.14–11.15。没有局部 AGENTS。只新增本目录 `evidence-*`，未修改产品、正式测试、fixture、旧报告/证据、PM 或 current-work。

## 本次实跑

从仓库根执行：

```sh
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/layauto/bin/python -B docs/tasks/W010/independent-premerge-review/evidence-audit.py
```

[审计脚本](evidence-audit.py)最终 **45/45 检查通过、exit 0**；[原 stdout](evidence-audit.stdout.txt)、[原 stderr](evidence-audit.stderr.txt)、[命令/退出码/脚本身份](evidence-audit-run.json)及[逐项结果](evidence-result.json)保留。

- 实际读取、计算 Git/blob、当前文件、tar/wheel/sdist 字节及 SHA-256。252 个冻结 source/tests/config 在当前、冻结 Git 和完整归档逐项一致；归档成员无重复、路径集合完整。两个实包各 94 个 runtime 成员与源码一致，包成员无重复。包的整体 hash 与交付相同。
- 21 条历史工程命令各自 JSON 与总 receipt 一致，全部 exit 0；42 份原始输出 hash 一致。verification 78 项清单与实际文件集合完整对应。runner、smoke、source manifest 和 source snapshot 自身身份一致。
- **旧 delivery manifest 的 218 项按 `git show ca39aed…:<path>` 比对**，大小/hash 全部匹配；没有将 c4909ab 追加 PM 状态后的任务文件拿来错误否定旧交付。
- 本次分别在实际 main checkout 和审查 worktree 运行 `pytest --collect-only tests/unit tests/contracts -q`：**1149 / 1465 唯一 nodeid，原 1149 全保留、新增 316**。实际收集集合也与原双解释器 collection 相同。见 `evidence-{baseline,current}-collection.*`。
- 实际运行 W007 dependency guard 和 W010 domain/state direction guard：**2 passed / exit 0**。另从正式 guard AST 提取 W010 新 allowlist 表达式，检查 15 组具名/非具名文件、模块和符号正反例，均符合预期。例外只限 `local_connectivity.py` / `local_connectivity_codec.py` 的指定纯 DTO、builder/registry 和 `EffectiveDraft`；没有目录豁免。原 forbidden 集合和余下守卫未被移除。
- 整体 main→HEAD 为 254 条路径变更，准备→冻结为 15 条；冻结→HEAD 的 runtime、tests、pyproject、README diff 为空；交付→HEAD 仅 23 条文档/证据路径。完整 name-status 在 `evidence-result.json`。架构、协作/环境、fixtures、legacy 相对 main 无变更。

所有子进程禁写字节码、关闭 pytest cacheprovider，临时配置位于 `/tmp/w010-evidence-mpl`；实际检查环境是已有 Python 3.12.14 venv，不称为新建或干净安装。本专项没有重跑完整回归或 typing；主 reviewer 的本次完整实跑另记。

## 采信的历史执行与未验证范围

身份核验后，可采信原 R2 Python 3.10.22 / 3.12.14 各 **1465 passed**、各 strict mypy **48 source files**、新 wheel/sdist、双干净安装及源码外 `-I -B` direct/readback smoke。原无筛选命令、最终退出码和完整原 stdout 均在 receipt/verification 中，而不是根据空 stderr 推定通过；preflight/R1 partial 和失败未计作最终通过。

安装身份记录的两套 94 项 runtime 与本次实查源码/实包一致；安装报告给出的 artifact hash 与实际包一致，原孤立导入的 executable/package 均指向对应 site-packages。原 smoke 输出两条链均为 14/8/6/16、audit pass、attempt unchanged；脚本身份也闭合。3.10 旧 pip 的可选 direct_url hash 缺失沿用原事实，不补造。

**原测试树 `/workspace/work/w010-final-0f5029d/source` 和两套 `clean-310/clean-312` 安装树在本机均不存在。** 本次没有重新遍历这些树、重新导入它们、重新安装或观察历史进程运行；所采信的是上述原记录与既有独立审计所证明的历史事实。也未重跑性能、真实 PDK/EDA 或扩大生产性能范围。绝对 capture URI 可以进入完整 receipt 身份，因此不拿不同 checkout 的 receipt hash 作无条件相等要求。

## 资源核对及非阻塞建议

performance probe/runtime/config 内容身份与当前冻结产品一致；四个原始样本均 `max_pieces_per_region=1`。原始数值为：

| 样本 | 节点 | wire bytes（无 optional cache） | 公开 build 秒 | 进程累积 RSS KiB |
| --- | ---: | ---: | ---: | ---: |
| normal | 14 | 15,470,850 | 10.3056 | 926,272 |
| cut-islands | 3 | 12,579,736 | 6.6191 | 926,272 |
| extra 20 M1 | 34 | 17,086,974 | 13.9040 | 1,011,524 |
| extra 8 CONTACT | 14 | 16,096,466 | 12.1019 | 1,011,524 |

公开路径重复认证/重建、含 cache 正常 wire 22,789,218 bytes、约 988 MiB **累积** RSS、高片数/最大输入未测均已披露；没有证据支持把 core builder 时间当公开路径成本，也不据此新增生产性能准入门槛。

**E-N01（低、非阻塞文档精度建议）**：`execution.md:32` 的“四例 wire 约 15.47–17.09 MB”遗漏较小的 cut-islands，原 `performance.json` 实际为 12,579,736 bytes。最小复核：读取 `cases` 的 `result_wire_bytes`，取最小/最大。预期四例范围约 **12.58–17.09 MB**，实际摘要下限为 15.47；影响仅为范围文字，最大成本、正常成本与限制没有被低估，不影响 A8 或合并判断。建议 PM/执行在后续文档整理时澄清，本 reviewer 保留历史记录不直接改写。

本专项剩余必须修正项 **0**，非阻塞建议 **1**。是否建议 PM 集成由主 reviewer 汇总全部专项后决定。
