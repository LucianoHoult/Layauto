# W012 A2 候选与有限筛选停止交接

2026-11-11（Asia/Shanghai）。**按 AI4 停止，候选和真实结果交 PM 取舍；不推荐进入最终工程或产品验收。** 本轮不是 A2 产品交付完成，也不是 W012/M1 完成。

## 身份与范围

- 实施分支 `codex/w012-a2-private-typed-pack`，恢复 PM 准备 `0213c346ac03b7b7282aae522c299155958ac8f6`；方案父级 `71488d6034b40cb67970466b082298a8dc0d5eee`。先实核远端、工作区与最新“可执行”阶段后修改产品。
- 本机 A1 before 为 main `2489b4609ae97d8211bf450d55cac9392492ac71`；候选产品/正式测试/配置冻结为 `c0a9a2e4c292255202a0ec82b6277cd8a8dd6b78`。263/264项完整 source/test/config 的 Git、磁盘、tar bytes 均核实，差异只有两个 codec 和新增正式测试。
- 两 codec 各新增私有 `_pack_for_encode`、只切换 encode envelope 调用。原 `_SPEC`/exact class/字段/delegate次序、原图 closed 检查、map/scalar即时freeze、tuple物化与完整nested bytes保持；原 `_pack`/decode/公开DTO/两次认证/`_evaluate`/canonical/domain/lower codec不改，无附件runtime依赖、上限、trusted/cache/memo。
- 原PM阶段/要求/current-work、fixture/答案、架构、生产body要求及原P1/A1/A2证据不改。task只新增标记的执行交接块，剔除该块后原完整字节相同。后补文档不是新受测产品。

## 实际检查

| 项 | 真实结果 / 原材料 |
| --- | --- |
| 新增正式测试 | 双3.10/3.12各82 passed；全 `_SPEC`/delegate、明确bytes/type、原accepted pack/canonical与真公开入口/decoder/异常见证，见[测试范围](testing.md)及`development/new-tests-*` |
| 受影响原回归 | 185 passed/2269.37s：W011异常53+合同44、W010合同80、W009单次快照8；原测试/旧finding未删或放宽，见[原命令](development/affected-r1.command.json) |
| 开发typing/节点 | 双strict typing54通过；正式collection1738，全部原1656 node IDs保留。首次缺mypy和初次1742全仓collection的修正/输出均保留，不将collection冒作通过 |
| 六条完整筛选 | 同机同3.12.14依赖、固定原URI/RunRequest/cache/roots/GC，各路before/after各1个fresh串行样本全部exit0。三对真正完整wire逐块相等，所有hash/ref/来源/值与readback边界保持，wire减幅0，见[回执](performance-attempt02/receipt-1.json) |
| 独立review | 未承担实现、正式测试或测量工具设计者完成代码/旧合同、正式证据、条件/实际wire及收益复核，建议STOP；新增必须项2均修正独立关闭、剩余0，原finding/失败保留。见[独立报告](independent-review.md)及其原探针/回执 |

## 性能与停止依据

以下只是有限筛选每侧每路1次，不能当最终三次矩阵或稳定收益证明。阶段总和先对实际阶段求和；不混入外层wall/profile。

| 路径 | 阶段总和 before → after | 峰值 KiB before → after | 完整wire B（不变） |
| --- | ---: | ---: | ---: |
| normal direct | 180.763609 → 169.770337s | 327444 → 325876 | 54,050,313 |
| normal readback | 284.589928 → 353.391652s | 711056 → 709204 | 136,471,701 |
| extraction_mismatch | 156.177652 → 150.496170s | 326396 → 326316 | 54,045,042 |

direct/mismatch总耗时少6.08%/3.64%，但readback整路多24.18%；direct decode多19.12%、mismatch W011 build多19.80%，峰值仅少0.02%–0.48%。未改的上游也有波动，不能将所有变化归因为删wrapper。收益混合且被退化抵消，不足支持继续当前候选；没有使用旧20%/50%硬门。所有build/encode/decode及其余阶段、各次/失败、完整hash与来源/功能证据见[完整分析](performance-analysis.md)、[机器汇总](screening-summary-attempt02.json)。

原工具失败 before-direct 已完成产品阶段，随后因错误URI后缀断言exit1，无成功JSON/wire，未用于成功对照。原源、原输出和诊断失败完整保留；I-R02修正为完整原preservation核对并先自检/独立复核，保持原相对URI，重冻工具后全六条重跑。汇总明确扫描原失败目录与新attempt；外层传播exit1不重复算另一产品失败。I-R01为封存自身输出的循环身份问题，原反例和真实隔离复跑也保留。

## 未执行、恢复与停止点

**最终双全量、构建、双干净安装源码外完整组合smoke、两侧各3次fresh性能矩阵均未执行，未获产品验收。** `engineering-preparation.md`及其环境/工具只是准备；未另跑profile、重开架构、扩owner或启动B/M1下一节点。不得将A1旧工程证据或本轮开发检查冒作新算法最终工程通过。

候选源码和当前证据足够让PM复核这个停止建议。下一步仅由PM决定是否不集成或另派受限工作，本执行停止；不自行验收、合main、删分支或改入口。提交采用 `LucianoHoult <LucianoHoult@users.noreply.github.com>`，最终Git/远端完整SHA由真实提交、推送核验和交接回复绑定，不为包含自身的文档制造循环hash。

完整恢复经过、失败及tool/source冻结见[执行记录](execution.md)。最终封存只核范围/身份/证据，不是产品验收；同次四生成输出由完成后独立检查与最终Git绑定。
