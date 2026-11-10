# W012 P1/P2 独立复核

**调查与方案可交 PM 接收；新增必须修正项 1，已复核关闭 1，剩余 0。** 此结论不批准优化实施、不验收产品性能目标，也不代替 PM 验收。

Reviewer：`/root/independent_review`，未承担测量工具或实施方案设计。在独立 worktree `/workspace/w012-review` 只读检查原工具/合同和正在形成的证据，最终审阅范围为 PM 准备提交 `f3698b7ffda3b0737a2eb61ca85dbf3b40bc89fe` → 执行冻结 `4aad0169c47f17c2c97bae541b6bc38bb6aaf489`，再核对单行修复 `27280c4ef243a96578b78e9794ff52407be86eff`。受审文件完整 SHA256 见 [reviewed-manifest.json](review-evidence/reviewed-manifest.json)。仅写本报告、任务 review 区及独立检查证据。

## 实际复核

已阅读 AGENTS、README、协作/本地与远端环境规则、W012 派发、W011 PM2 和原资源/工程证据；回查架构 §2.2–2.3、§2.6、§3.7–3.8、§11.2/11.9/11.15，以及 W007–W011 的来源、readback、严格类型、codec 和异常合同。独立辅助专项 `/root/independent_review/contract_check` 只读复核同一合同，未设计方案、未改文件或运行重型组合。

实际运行 [独立轻量检查](review-evidence/check.py) **1521 项通过**，原命令/输出见 [command.json](review-evidence/command.json)、[stdout](review-evidence/stdout.txt)、[stderr](review-evidence/stderr.txt)，详细断言和重算值见 [result.json](review-evidence/result.json)。这些是身份、原输出完整性、统计和观测器自检，不是产品回归数量；没有重跑小时级矩阵或新建重型产品样本。

| 判据 | 独立核对及结论 |
| --- | --- |
| PP1 | PM 准备、main 起点 `0a3326aa363477724465886cd05874d0997fba3e`、W011 冻结 `e89bdaa6a091f56cfaf7862dced7232d34e22514` 三版本的262项逐 SHA256 相同，原 snapshot262项匹配，100 runtime 不变；原双1605及21命令原输出hash核对通过。固定overlay35项与原来源逐字节相同。输入URI、cache、RunRequest、GC/保留顺序、Python/资源、工具独立hash与先行轻量自检均可定位。 |
| PP2 | 三条 baseline 实为 fresh 进程且串行；完整 W005/W006→W008→W009→W010→W011 构造及公开 Result encode/decode 均通过。检查代码保留完整36项FIN集合和手写crossing见证、正常5/7、mismatch4对source5且一项差异/touch；原局部图/T05/body/来源、readback unsealed/checkpoint不变/无terminal均断言，完整恢复DTO相等。三条阶段总计独立重算91.921797/187.951635/88.230747s，wire及峰值与报告一致。 |
| PP3 | baseline没有启用hook/cProfile；profile分进程、同captures/完整wire，wrapper只读原有长度/类型，不额外encode/digest巨大对象。unique/content/logical bytes分开，census只读显式图且shallow不当RSS。重算外层hex占比99.8648%/99.9465%/99.8661%，这是下层wire按值展开，不是原raw bytes占比；W011 build两次认证及下层constructor次数匹配，cumulative不可相加。所有阶段domain.codec的disjoint self-time占比51.22%/51.47%/51.37%，不当无插桩函数耗时。额外readback内存诊断在六条后串行，同wire/captures，65次既有hex调用/5次刷新HWM；event34的118,841,892字符窗口达到该进程最终7,319,108KiB，返回后RSS355,960KiB，报告正确区分瞬时窗口与净驻留/分配。 |
| PP4 | 推荐先处理等价有界hex校验、再减少canonical/token中间表示，owner、完整字段/来源/类型/不可变和原二次认证异常合同明确。A保持 `/1` byte/hash/公开验证；速度20%和RSS50%均为有数据依据的可行性门建议，未声称已达成，三次同条件未来验证和退化报告明确。可选B的20MB/45MB/20MB尚无原型benchmark，已标建议；新格式、旧decoder拒绝、digest/content_ref和历史readback迁移的具体影响及用户决定门均列出，不能随A默认实施。 |
| PP5 | 本轮独立读代码、原输出、测量与方案，发现R01后由执行修正文案，reviewer再次重算关闭；其余必须项0。授权diff仅W012资料和任务执行/review区；runtime、正式测试、fixture/答案、架构、current-work未改。完成此交接后交PM，不自行实施/验收/合main/启动下任务。 |

## Findings 与复核

| ID / 性质 | 原 finding / 影响 | 执行处置 | Reviewer 复核 |
| --- | --- | --- | --- |
| R01 / 必须修正，已关闭 | `cost-analysis.md` 原文“每个外层222个bytes事件”与原profile不符：direct/readback各222，mismatch为217。独立检查在此失败，原[脚本](review-evidence/attempt01-check.py.txt)及[stderr](review-evidence/attempt01-stderr.txt)保留。wire字节量/hex字符量和比例本身正确，问题限于统计叙述。 | `27280c4ef243a96578b78e9794ff52407be86eff` 只改为“依次222 / 222 / 217”，不改测量/产品，不重跑重型组合。 | 逐读三份原profile并重算，实际222/222/217、对应53977248/136398636/53972674 hex字符。单行diff和最终独立检查通过，关闭。 |
| O01 / 可选建议，已处理 | 额外memory observer应先检查 `type(pattern) is str`，避免对外国pattern对象额外调用 `__ne__`。实际固定路径无此输入，初审未列为阻断。 | 执行在补测前加入原生pattern类型过滤，并重新自检；matcher计时也截在post-RSS读取之前。 | 最终代码及自检hash匹配；独立传入 `__ne__` 会抛错的外国pattern，原函数透传成功，原异常object/cause/context/suppression透传检查通过。 |

初审另提醒的“累计hex流量不可直接当最终wire占比”和“显式census不含repository内部、shallow不是RSS”均已在最终分析中明确，不保留未解决finding。

## 接收边界

已测单个完整Result及其恢复图的bytes payload为MB以内至约1.8MB量级，不能解释GiB峰值；此数不代表全进程所有保留roots。嵌套wire和反复认证确有实测成本，但没有授权删证据或绕过验证。`test_w011_exceptions.py:105–126` 的第二次认证失败历史仍是必须保护的现行合同，方案已列具体反例。新table格式必须先有版本/默认入口/兼容期/ref迁移决定，`hash相同`也不能替代URI、owner或run绑定。

本轮一次baseline/各条profile属于有限synthetic调查；时间有主机和插桩扰动，内存窗口只对readback补测，未测regex引擎内部逐项分配。未来A速度/RSS目标与B新格式目标仍需实施后的同条件完整三路实测、受影响回归及最终冻结双解释器全量/typing/包和干净安装。原W011负例按同源身份采信，本轮没有冒记实际重跑全部攻击路径或证明生产/最大输入上界。
