# W012 A2 最小实施派发要求独立复核

2026-11-11（UTC）；Reviewer：`/root/a2_implementation_handoff_review`。

**派发要求复核通过，新增及剩余必须项0。** AI1–AI6 与实施 prompt 准确承接已审两 owner 私有 typed pack；本结论不验收产品、收益或 M1，不重新批准方案外的优化。

本次仅审任务顶部实施范围、AI1–AI6 与 [实施 prompt](A2-implementation-prompt.md)；未参与这些要求、原方案或测量工具的起草/设计，未派生子 reviewer。仅新增本报告，不改 task/prompt，不 commit/push。

## 受审身份

- Checkout：`/workspace/work/layauto-w012-a2-implementation-prep`；branch：`codex/w012-a2-private-typed-pack`。
- HEAD/base：`71488d6034b40cb67970466b082298a8dc0d5eee`；本地 main：`2489b4609ae97d8211bf450d55cac9392492ac71`。
- 初始工作区只有已修改 task 与未跟踪 prompt，无 staged 改动；不是已发布的最终准备提交。

| 材料 | 初审 SHA-256 |
| --- | --- |
| `docs/tasks/W012-capture-wire-performance.md` | `febbb46164a3363cf7da91265fca19baf16fc9a75d3363e7cfe8e754771ee65c` |
| `A2-implementation-prompt.md` | `7cbd8821fcd0821826fae3ca24888bbf2081ad608f5fa6d2ad11df9fb2973876` |
| `A2/plan.md` | `b5a30b7263140ce87320210694d48cefe76f1b66df81bfc28d133778136a7a7e` |
| `A2/independent-review.md` | `11bd1e33e3a97911eb888fcb7c35e6f63a0bff84e4eafbd429df527c968084b5` |

AI1–AI6 六行按文件顺序以 LF 连接并保留末尾 LF 的 SHA-256：`293d046dff50a597dc955f9e06af5ca7c3b1eb583f788d769d63725802c02c2d`。报告不要求包含自身最终 hash。

## 实际读取与核对

- 根 AGENTS、README、docs 导航、协作规则；local-setup/remote-development 的适用环境和交接条款。未发现目标下或仓库外祖先的额外 AGENTS。
- 架构 §2.2–2.3、§2.6、§3.7–3.8、§11.2/11.9/11.15 的相关原文节选；本次不改产品合同。
- 当前 task diff、AI1–AI6、完整实施 prompt；[原方案](A2/plan.md)、[方案独立 review](A2/independent-review.md)、[方案交付](A2/delivery.md)及[原方案派发 review](A2-handoff-review.md)的范围/停止点。
- current-work、docs 导航和 roadmap 的 W012 恢复/阶段段落；PM 正在独立更新这些元数据，最终身份另记。

| 检查点 | 实际核对结论 |
| --- | --- |
| 两 owner/落点 | AI1 与 prompt 6 仅允许 local_connectivity_codec/channel_identity_codec 各自私有 helper 和 encode envelope 的 pack 表达式；原 `_SPEC`、exact class、字段/delegate 次序不变，无公共 codec 或泛化框架。 |
| 快照与表示 | 原图 closed 检查先于复制；map/scalar 原位置立即 freeze，tuple 按序物化，owned 树不逃逸/缓存；canonical 全树 freeze、`_wire`/JSON/UTF-8 不变。附件节点/深度/叶/整数上限明确不进入产品。 |
| 认证/异常 | AI2、AI3 与 prompt 6–8 保留旧 `_pack` 供 decoder、`_unpack`/decode、公开 DTO、完整来源重建、第二次认证及 `_evaluate`；异常 object/cause/context/suppression、closed/exact/别名与单次集合快照有明确要求。依赖拟删构造的公开故障须恢复或带反例交 PM。 |
| 字节/身份 | 要求完整 `/1` wire 逐字节、全部 hash/ref/签名及 source/run/owner/原 bytes 不变；相同 hash 不替代认证，wire 降幅为0。未授权新格式/行为、trusted/memo 或改变 fixture/答案。 |
| 开发到筛选 | AI3→AI4：先新增/受影响回归，再同机同解释器/依赖固定 URI/RunRequest/cache/roots/GC，三路各一组 fresh 成对完整公开 build/encode/decode；原 mismatch 按35项/五 overlay 重建，正常5/7、4对5及 readback/attempt 边界均保留。 |
| 最终义务 | AI5 与 prompt 10 仅在筛选有依据支持继续后，完成新冻结双3.10/3.12全量、strict typing、构建、双干净安装源码外完整 smoke，及三路两侧各3次 fresh 串行交替完整比较。可复用限本轮同身份/条件样本；明确禁止以 A1 旧矩阵替代新产品矩阵。 |
| 归因/失败 | 小值计数、全部 freeze exclusive、嵌套 cumulative 不能冒作可省秒数；各次/失败/中位、build/decode/总耗时/峰值及退化分别披露，profile 与无插桩 wall 分开。新工具先自检，原证据/finding/失败不覆盖。 |
| 停止/owner | 收益不清或退化抵消时保留候选/真实结果，明确未完成最终矩阵、未获产品验收，交 PM 停止；不能扩包或冒验收。PM 维护要求/阶段/入口；独立 reviewer 不参与实现或测量工具设计；执行交 PM，不合 main 或启动下一节点。 |
| 可恢复性/阶段 | prompt 从所列分支最新 PM 准备 head 恢复并核远端完整 SHA、工作区及实际 producer/consumer；只在 PM 标记“可执行”后修改产品。初审“待准备”与本轮准备工作一致，旧 AP1–AP5 不再充当本轮执行指令。 |

轻量检查实际通过：`git diff --check`；上述 hash 复算；AGENTS/协作规则及 plan/review/delivery 五文件逐字节等于 base；task 的 W012 本地附件链接存在。相对 base 的 runtime/正式测试、pyproject、README、架构及原示例受保护路径 diff 为空。只用 Git/文件读取及 Python 标准库，不导入产品。

未跑产品、原型、263项全清单、工程矩阵或完整性能实验；未重读大 wire 或旧安装树。对旧方案的采信限已存在、未改变的受审方案及其独立结论，不重新证明 A1 工程数字，也不证明未来实现正确/有收益。

## 交接边界

PM 可据本报告完成接收、阶段和导航元数据后发布准备提交；实际实施仍须按 AI1–AI6 交新产品证据或有依据的停止结论。远端最终提交身份由发布交接绑定，本报告未声称检查了尚未产生的远端 head。

## PM 元数据局部复核

PM 补入方案接收后，task SHA-256 为 `5363b9228962bb41b69eeff655827c4e30f8c3e35bf4e656046197d0f21fab72`；prompt 与六行 AI 要求 hash 均与初审相同。实读新增 PM6 和 current-work/docs 导航/roadmap diff，确认“已验收”仅指 AP1–AP5 方案交付，尚未实施或单独合 main，下一步仍限两 encoder、先筛选再决定最终交付，收益不足交 PM，不把 A2 当 M1 功能硬依赖。

此轮元数据复核通过，新增及剩余必须项仍为0；阶段仍为“待准备”，待 PM 接收本报告后单独维护。未重审 PM 审计工具/输出或重跑其有限检查，PM6 的旧方案接收事实由其独立证据承担。

## 最终发布补记复核

PM 最终 task SHA-256 为 `ae985380eae0c37bae5c805dd3fea1fd4367f99d9c465ed6a147c57c33358471`。实读顶部阶段、AI标题和派发接收句：现为“两 encoder 最小实施可执行”，继续明确未实施/未获产品验收、筛选不足交 PM 停止及原最终验证义务。六行 AI 要求及 prompt hash 均与初审相同；**发布补记复核通过，新增及剩余必须项0，前述边界继续适用。**
