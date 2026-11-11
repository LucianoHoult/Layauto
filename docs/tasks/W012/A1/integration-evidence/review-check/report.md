# W012 A1 PM 集成专项证据核验

结论：**新增必须项 0，剩余必须项 0**。最新独立 review 的111项正式原输出、150,728有限候选探针及结论0可按已核身份采信。实际合并提交的完整tree与交付相同；本专项未改仓库，未重跑产品、pytest、工程矩阵、性能测量或大wire。

核验由 `/root/a1_integration_check` 完成，辅助 `/root/a1_integration_check/review111_identity` 只读核111/探针/manifest。核验日期2026-11-11。遵照本次限定范围，未重复旧工程、产品、安装或性能专项。

- 最新交付 `1a1459e3179e7bd234e4971c1969a6a78f387fd2` 的直接parent为 `e4179dd42cc0de853df73bafd9140a363c8fa5be`。两者差异共72路径：71个新review报告/证据文件和W012任务reviewer区8行追加。移除该新review段后任务文件与e417原字节完全一致；PM段、current-work、README、docs导航、architecture、协作规则及AGENTS均未改动。
- 两份source-manifest均含263源/测试/配置及100runtime，内容清单相同。当前263文件SHA-256逐项等于manifest；263个Git blob身份及模式在 `ca1f810c3c97376f71089d8b4054760ff198012f`、`44a91c472fdeba5bb4b8a6071c0580313336c379`、`db07a16fb7cbbac030adae84a9eb88cc0c8aa650`、e417、1a及实际merge间逐项相同。首轮和r2两份source-snapshot tar各263个普通成员，逐成员SHA-256也等于该清单及当前文件。
- 67项review manifest逐项SHA-256和文件集合闭合；11份根命令的22份stdout/stderr身份及退出码闭合。正式回归原输出分别89 passed和22 passed，命令文件不重叠，22个独立收集node闭合，合计111。第三轮探针exit0，原stdout与result逐字节相同，独立重算候选150,728；三份探针源快照及原两轮checker失败均保留。两份真实codec快照逐字节等于对应main/e417 Git blob，交付1a的codec也相同，未以报告摘要替代身份检查。
- PM给出的实际main合并 `08dd232139918dc97b0a6d255aad237eb844686a` 已实核，两个parent依次为原main `0a3326aa363477724465886cd05874d0997fba3e` 和交付1a；完整tree `dc7f3ee70aa35a708abbea4a204f4b60810cbcd4` 与1a完全相同。核验时本地main指向该merge，当前263源一致，起止工作区clean。

本专项证据：[源/范围结果](source-scope-result.json)、[脚本](source_scope_check.py)、[原命令](source-scope.command.json)、[原stdout](source-scope.stdout.txt)、[原stderr](source-scope.stderr.txt)。111/探针细节见[辅助报告](probe-check/report.md)、[辅助结果](probe-check/result.json)及其原命令/输出。

限制：本次核验的是证据身份及实际合并等价。原大wire全长实比、原安装树实读、双全量/typing/构建安装和18次测量继续按不变源码及既有独立review采信；本专项没有新执行这些工作。有限synthetic候选不构成全生产输入域或最大输入保证，已披露私调恶意str子类的len副作用边界继续保留。实际合并版本的组合验证由PM另行执行及记录。

辅助checker首轮遇到PM已经完成合并的共享HEAD，固定1a HEAD断言因此失败；原脚本/命令/stderr保留在 `probe-check/attempt01.*` 和 `check-attempt01.py.txt`。按已核相同tree接受实际merge后第二轮exit0；该次checker恢复不属于产品finding。
