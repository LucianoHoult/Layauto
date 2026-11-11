# W012 A2 PM 收据与交付边界专项核验

2026-11-11 UTC。核验者 `/root/a2_plan_receipt_audit`。**本专项通过，新增必须项0、剩余必须项0；A2-R01关闭证据成立。** 可以采信这次方案交付的范围、身份及有限见证，结合另一专项的技术判断办理方案阶段接收。本报告不批准产品实施或证明性能收益。

本次在 `/workspace/Layauto` 只读核验，branch=`codex/w012-a2-serialization-plan`，HEAD=`71488d6034b40cb67970466b082298a8dc0d5eee`；本地main=`2489b4609ae97d8211bf450d55cac9392492ac71`，原派发base=`842c5c1ea8f1d01bb3f04e4703f105e11f94158c`，原方案受审commit=`cbf20807a85d8350928fc6a604612384cb2727fd`。起止工作区均干净，3239个tracked文件起止SHA-256逐项相同。没有修改repo文件、原输出、commit、push、产品实现或新子项；全部新产物在本报告目录。远端访问性由PM主核验负责，本专项未重复联网。

已读根AGENTS、README、协作规则、local-setup/remote-development、A2派发prompt与派发review、W012 AP1–AP5、实际plan/reference/check/delivery checker、独立review及其probe/R01工具和全部收据。路径搜索未发现本目标目录的局部AGENTS。读取并使用cloud runtime技能，当前环境状态running、observations_current=true、network_policy=enforced；没有安装或网络取数。

| 核验项 | 独立实际结果 |
| --- | --- |
| 263/100身份 | A1 manifest的263文件（100 runtime）逐项匹配当前磁盘及A1冻结`ca1f810…`、实际merge`08dd232…`、派发base、交付HEAD四组Git blobs；9份after性能receipt和1份after-profile receipt的source maps也完全匹配。未用manifest中的历史git_head替代内容证明。 |
| 真实diff范围 | base→HEAD恰为35 paths：task新增8行执行段，加34个新的A2附件。不存在runtime、正式测试、fixture、原P1/A1报告/工具/输出、架构、current-work或其他路径变动。独立按字节剔除唯一执行插入块后，task全部原字节等于base，因此AP/PM阶段及原要求均未改。 |
| 方案受审身份 | 当前plan/check/reference逐字节等于受审cbf提交；review表内plan、reference、check、check-result、command、stdout、delivery及修后delivery checker的SHA均匹配当前文件。原check.command的HEAD=base，表示当时未提交附件执行；result中的工具hash及后续cbf/最终Git将实际材料绑定，无需将它冒记成cbf上新执行。 |
| 真实有限检查 | 先读所有脚本写入点，再以runpy加载未修改原源，保留ROOT指向原repo，仅将工具HERE附件/输出目录重定向到外部复制目录；原main代码和产品模块未变。check exit0、stderr空，重跑生成的完整result及stdout与原件逐字节相同：6个小DTO、22个private subvalue及快照/closed/异常/UTF-8/bound见证成立。 |
| reviewer有限探针 | 同样重定向输出重跑review-probe，exit0、stderr空，34个private比较逐项等于原结果。原review-probe命令的script hash匹配，其8项原受审材料hash匹配cbf Git内容。 |
| R01处置闭合 | 原checker源和首次缺链接观测保留；原SHA=`596b202e…`，修后=`28d77077…`，与复核result吻合。复制未修改原复现脚本外部执行，实际exit1并定位`delivery-check.command.json`缺失；修后原复核脚本实际exit0，确认四生成输出未预造仍可过，普通缺链接仍被拒绝。原finding及关闭表未删。 |
| 完整交付checker | 将附件复制到外部目录，删去该副本四个未来输出，保留ROOT为repo后执行修后原main；实际exit0、stderr空，四产物真实生成，scope及material map等于原最终seal。额外A1链接仅通过外部只读symlink定位，不修改原目录。 |
| final seal与Git | final seal的35-path scope等于真实diff，27个material hashes全部匹配当前文件；8个前缀`delivery-check*`的首次/最终命令/结果/stdout/stderr不自hash，但均逐字节等于最终HEAD blobs。最终Git封存闭合，不存在必须预造通过结果才能运行的循环。 |

首次完整seal原四产物已保留。其历史material map当前只有`independent-review.md`一项hash变化，原因是后来追加最终局部复核；最终刷新seal已绑定新的review内容，不能将首次历史seal误当最终材料map。final seal及command中的`head_at_check/git_head=cbf…`也如实保留，最终收据、报告与后补task插入段由`71488d6…`绑定，并非另一个受测产品版本。

独立review的记录说明reviewer未参与方案/参考工具设计，初审在隔离detached cbf worktree，后补交付材料单独局部复核。原probe输出、R01失败复现、修正验证和最终局部复核均可访问且内容一致，故可按项目协作规则采信其独立review；本专项无法从Git材料重建原会话的全部执行历史，不将文档声明提升为额外的取证结论。

同源A1工程证据只按既有验收采信。本次实读integration及verification-r2 receipt，重新hash核对其中21条既有命令的stdout/stderr，全部匹配、exit0；双1656、typing双54及source manifest身份相符。没有重跑双全量、构建、安装、完整Result/build/readback或18条benchmark，没有重新实读旧安装树或重比约1.47GB大wire。A1原始完整矩阵/安装/wire结论的适用范围与原独立验收相同。

实际复算readback阶段中位build=51.426606384s、decode=66.114896278s、最终encode=2.616473400s，after-profile文件SHA=`51e1b4db…`与原receipt/check一致。它们是继承的旧after事实；本轮有限构造计数不构成完整产品收益、峰值改进或生产上界证据。是否足以另派两owner最小实施，结合独立技术专项判断；真正实施仍需完整三路同条件逐字节/无插桩前后比较与新的冻结工程矩阵。wire降幅必须为0，AP5停止点及不自动扩reader/memo/B或删认证仍有效。

可复现主命令为`python3 -B /workspace/work/w012-a2-pm/receipt-audit/audit.py`，实际Python3.12.14；成功运行UTC `07:02:08`–`07:02:12`，exit0、stderr空。机器结果见[result.json](result.json)，工具源见[audit.py](audit.py)，命令与原输出见[command.json](command.json)、[stdout.txt](stdout.txt)、[stderr.txt](stderr.txt)。各重跑细节和原产物在`finite-rerun/`、`probe-rerun/`、`delivery-rerun/`及`r01-rerun/`。

审计脚本首次把初次seal的历史变化错误预期为task+review两项，实际只有review一项，导致本地audit断言失败；已修正这一审计预期，未更改被审材料，失败源与命令/输出保留为`audit-attempt01.py.txt`和`attempt01.*`。这不是交付finding。
