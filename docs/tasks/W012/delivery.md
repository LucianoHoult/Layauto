# W012 P1/P2 执行交 PM

调查及具体方案已交付，独立review剩余必须项0；不是产品优化完成或PM验收。停止在PM接收，不实施优化、合main、改current-work或启动后续任务。

- 原分支：`codex/w012-capture-wire-performance`；PM准备 `f3698b7ffda3b0737a2eb61ca85dbf3b40bc89fe`，含W011最终验收的main起点 `0a3326aa363477724465886cd05874d0997fba3e`。
- 测量工具冻结 `cfaf85e195fcbedb99fbd26b19787afb0577862d`；完整调查/方案 `4aad0169c47f17c2c97bae541b6bc38bb6aaf489`；R01单行统计修复 `27280c4ef243a96578b78e9794ff52407be86eff`；独立review `9e769b134eed878b6383e91ac2ba8264e035518c`。最后只增加本交接与全附件清单；最终交付SHA由Git/远端实核给出，避免清单自包含hash循环。
- 项目提交身份：`LucianoHoult <LucianoHoult@users.noreply.github.com>`。推送前远端仍为上述PM准备/main起点，原分支dry-run权限已通过，不强推。

入口：[任务执行/review区](../W012-capture-wire-performance.md)、[冻结计划](measurement-plan.md)、[成本分析](cost-analysis.md)、[具体实施方案](implementation-proposal.md)、[独立review](independent-review.md)。原输出/失败/命令/环境/来源及工具均随目录保存，逐文件SHA256见 `delivery-manifest.json`。

PP1–PP5实际交付：先行身份/工具自检，三条无插桩完整构造/encode/decode，三条独立profile，以及限定的实际完整readback内存诊断均通过；执行396项证据完整性核对、独立review1521项核对通过（均非产品测试数量）。R01保留原finding和原失败stderr、修复及reviewer关闭；没有删除失败或覆盖性能样本。262源/100runtime未改，W011同源双1605/typing54/构建安装采信，未重跑小时级矩阵。

最重要的测量结果：原bytes去重不能独自解释GiB峰值；外层wire约99.9%为下层完整wire的hex按值展开；重复认证包含大量codec工作，不能叠加inclusive时间或删除公开验证。实际readback最终峰值7,319,108KiB出现在118,841,892字符的既有hex正则校验窗口，返回后RSS355,960KiB。原捕获、正常5/7、mismatch4对source5、完整crossing、局部图/T05/body和unsealed/checkpoint/无terminal保持。

推荐PM先接收调查与独立review，再决定兼容工作包A是否派发：等价有界hex校验、canonical/typed token临时表示优化，保持 `/1` 字节/hash和全部认证/异常合同。速度至少降20%、峰值至少降50%均仅为建议门，需实施后同条件三路实测，开发新增/受影响、最终冻结双全量验收。

可选新table wire B尚未批准，不能随A实施。方案已给同一结果旧decoder拒绝 `/2`、新wire hash改变、publication content_ref/readback迁移以及跨run同bytes不可合并关系的具体实例；PM/用户需决定默认入口、兼容期、身份算法和迁移范围。没有production/最大输入资源上界或新物理能力承诺。
