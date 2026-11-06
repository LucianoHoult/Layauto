# W010 PM 分支接收

日期：2026-11-06。核验对象 `codex/w010-local-contact-connectivity@ca39aedcb71fda02f77ffda1eb5d5dddc598226e`；冻结产品/正式测试 `0f5029df935bc0acd106aad1bc2be81304d4f442`，准备起点 `9758a157115cc22d91ce095ac2002209b9f210d3`。main仍为 `3be0b98359038bab6c23980b55a48987cc71a369`。

**分支技术接收通过，本次未发现新增必须修正项；阶段待验收。** 尚未进行另一个独立session的合并前复核及main集成组合验证，不宣称W010最终验收。

## 要求、实现及review核对

PM核对原W010要求、[方案review](plan-review.md)、[执行交接](execution.md)、[代码review](code-review.md)及实际产品/测试/配置diff；没有只依据交接摘要验收。实现新增中立contact/edge/component/audit、纯state草稿、认证适配与closed codec；旧依赖守卫仅扩展具名纯模块/符号白名单。原fixture/答案、上游运行时、main和历史证据未由执行改变。

| 要求 | 本次核验 |
| --- | --- |
| A1 来源与组合 | PM重跑原独立主probe，实际direct和W006 readback→W008→W009→W010均为14节点/8边/6分量/16侧audit，通过无IO、完整input/completed/body与unsealed attempt保留、异rules source及漏edge/假audit拒绝。新增rules绑定相同捕获payload与固定source role，公开输入在编码复制前检查原对象图并完整重建认证。 |
| A2–A5 几何与图 | 同层正面积/正长度边、独立region计数、重复connector来源/audit、孤立BODY、special三分量和via_enclosure边保留/违例分离按任务核对。PM正式定向回归覆盖关键公开路径，另委派独立有限几何/有理阈值集合判据，见[几何专项](pm-evidence/geometry/report.md)。 |
| A6 公共合同与错误 | 公有draft从完整effective输入重建nodes/edges/components/audits；captured result另认证完整输入及rules。不以编码相等替代原图检查。PM定向回归含集合快照、伪造拓扑/audit及expected policy error之后再次认证的原异常链保真；原更广nested故障矩阵按最终身份与独立代码review采信。 |
| A7 scope | local图无net/device标签输入、无via-as-wire、无S/D器件边或外部body union。graph success可伴局部enclosure violation，未消费operator及外部BTAP/完整规则等deferred范围显式。当前不等于全部T05、完整Stage2/M1或生产准入。 |
| A8 工程身份 | 当前252项源/测试/配置、完整tar、两包各94runtime、21条命令/42份输出及原1149 nodeid保留/新增316、review与交付清单经实际内容审计；见[证据专项](pm-evidence/evidence/report.md)。修前guard/harness失败与中断材料不计最终通过。 |

## 本次实跑与采用的证据

- Python3.12定向正式回归：**50 passed / 233.81s**，其余266项W010用例本次未选。覆盖手算接触/包围、special、via违例、端点歧义/重复connector、多片、rules绑定、伪造图/audit、集合快照及错误路径异常链。外部anyio插件有1条pytest弃用提示，原文保留。
- 原独立主probe重跑：**通过 / 58.346s**，实际direct/readback各14/8/6/16，无IO/来源伪造/完整性检查通过；这是重跑既有独立probe，不冒称PM新编。
- Strict mypy：**48模块通过 / 2.045s**。
- PM新增独立几何probe：**12,288接触、5,120有理包围、8,704等覆盖分解比较**全部通过（512掩码，含大整数平移）。
- PM证据内容审计：**通过**，252源/完整归档、两包94runtime、21条命令42原输出、原1149保留/新增316及review/交付身份一致。

本机使用既有Linux Python3.12.14 PM环境，pytest9.2.0、mypy2.4.1、PyYAML6.0.3，不是干净安装。实际命令、HEAD、范围、环境、耗时、退出码及原stdout/stderr hash保存在[机器回执](pm-receipt.json)和`pm-evidence/`；未重复双解释器完整1465项或原220项大wire故障矩阵。

原Python3.10.22/3.12.14各1465项、双typing48、新包与双全新安装/源码外`-I -B`真实组合smoke，按最终源码/包/命令输出身份和原独立审计采信。原两个实际安装目录及旧实际测试树在当前主机不存在，PM没有重新遍历、重建/重装或运行这些历史环境；hash一致不等同重新观察历史执行。3.10旧pip的可选direct_url hash缺失仍保留原事实，来源以实际install report/URL、包和安装字节独立审计支持。

最终source manifest SHA-256 `cef29336dba1bf572fd30227f354365d4a4d780e721d089b70095589d0f55889`。本次仅追加PM文档/证据，原252项受测源、产品、正式测试、配置和历史清单保持；任务文件追加PM状态不改写旧交付manifest或报告。

## 下一步与限制

沿用独立session分工，下一步单独做合并前复核，再进入main集成与组合验证并记录最终验收。本次PM专项不冒称新的独立premerge session已经完成，未合main或启动下一任务。

仍在M1局部物理事实构建部分。完整工艺坐标/有效region occupancy、外部body/U06、FIN/器件及语义join、query空间标注、其余mandatory/lifecycle、原子baseline/seal/no_change/terminal/Stage6和真实EDA/PDK继续后置。

执行已披露完整公开路径的重复认证/重建、正常含cache wire约22.8MB、有限共享host资源高水位等成本；全部性能样例max-pieces=1，未测最大输入或大量多片/孔洞压力。PM不从有限正确性判据推出生产性能或全部整数输入保证。
