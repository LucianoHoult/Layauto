# W010 PM 接收：交付证据专项

日期：2026-11-06。PM 委派的只读核验者 `/root/w010_pm_evidence`。对象为分支 `codex/w010-local-contact-connectivity@ca39aedcb71fda02f77ffda1eb5d5dddc598226e`，产品/正式测试冻结提交 `0f5029df935bc0acd106aad1bc2be81304d4f442`，准备基线 `9758a157115cc22d91ce095ac2002209b9f210d3`。

**本专项核验通过，未发现必须修正项。** 本专项只支持交付内容和证据身份核验，不替代原独立代码 review、PM 最终验收或合并决定。

## 本次实际核验

读取根 AGENTS、README、协作/环境规则、W010 原要求、执行交接、独立代码/工程 review 及相应机器回执，实际运行 `audit.py`：

- 最终252项源码/测试/配置等于冻结产品 Git、交付 Git 和当前文件；94项 runtime 与当前源码全等。源清单 SHA-256 为 `cef29336dba1bf572fd30227f354365d4a4d780e721d089b70095589d0f55889`。
- 完整源码 tar 恰含252个唯一普通成员，逐字节与清单一致；整体 SHA-256 与执行回执一致。
- verification manifest 的78项文件与目录实际文件集合及 hash 完全一致；总 receipt 和 runner/smoke 自身身份匹配。21条命令各自 JSON 与总 receipt 一致，exit0，42份原始 stdout/stderr hash 匹配。
- 原始两套输出均为完整1465项且无 failed/skipped/deselected；两份 collection 各1465个唯一 nodeid，包含相同原1149项并新增316项。原基线修正清单与准备 Git 一致；双 typing 原输出均为48源模块通过。
- wheel/sdist 实物的整体 hash、无重复成员及各94项 runtime 逐字节匹配。wheel SHA-256 为 `f77c718aa292d8c15c37206a1543462e29888dc65e38e61cc830856f75c60232`，sdist 为 `49b5fdd10ee7aca6f349dfcaea1d42292dfd647a6d05a9aa695d180d85d25d5b`。
- 两套安装身份记录的94项 runtime、直接 artifact URL/安装 report hash、实际 site-packages 来源、源码外 cwd 和 `-I -B` smoke 相互一致；direct/readback 均记录14节点/8边/6分量/16个通过 audit，attempt不变。3.10可选 direct_url metadata hash 留空的事实按原review保留，未补造字段。
- 最终 review 身份清单的21份报告/probe/原输出及任务 reviewer 区 hash 匹配；main/math/boundary附加回执的实物 hash 亦匹配。220条故障保真、166项畸形拒绝及原数学/主组合结果均归原独立review的实际执行，不冒称本专项重跑。
- 交付清单218项文件的大小及 hash 全匹配，performance probe/source 身份匹配；16处保护路径相对准备基线无变更。全部原测试函数名保留，旧测试仅 W007 具名纯依赖守卫改变；其代码正确性仍归原代码review及PM代码核验。
- preflight 的缺测试样张/harness失败、partial和R1旧守卫失败/主动中断按其原身份保留。最终工程结论仅采用R2冻结源码下的21条命令，未用旧partial或完成部分包流程替代完整回归通过。

## 实跑与采信边界

本次实际运行的是标准库只读内容审计，exit0、stderr空；完整结果见 [audit-result.json](audit-result.json)，逻辑见 [audit.py](audit.py)。命令：

```sh
cd /workspace/Layauto
PYTHONDONTWRITEBYTECODE=1 python3 -B /workspace/work/w010-pm/evidence/audit.py > /workspace/work/w010-pm/evidence/audit-result.json 2> /workspace/work/w010-pm/evidence/audit.stderr.txt
```

脚本固定核对交付HEAD；后续PM文档提交后应从上述交付checkout复验，不能把HEAD守卫失败误判成源码不一致。

原实际测试源码树和两套实际安装目录均不在当前主机。本次实际读取了源/归档/包及历史记录，**没有重新遍历原测试树或安装树、重新导入原安装、pytest、typing、build、install或smoke**。这些历史执行事实按版本与原独立review的实际树/导入审计采信；hash一致不等于本机重新观察历史命令执行。

本专项未修改仓库、产品、测试、fixture、任务或Git状态，未提交/推送/合并。完整数学/公开接口动态核验归主PM与其代码专项；有限证据不证明生产性能、真实PDK/EDA或完整Stage2/M1闭环。
