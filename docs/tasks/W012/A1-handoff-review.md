# W012 A1 派发要求独立复核

**派发准备复核通过，新增必须修正项 0。** 本结论仅说明最小 A1 的要求和执行交接可落实，供 PM 接收后推进阶段；不是算法方案 review、产品正确性或性能 review，不代表 A1 已实施、产品收益已达成或 W012 整体完成。

Reviewer：`/root/w012_a1_handoff_review`，未参与 P1/P2 调查、方案设计或执行，也未起草本轮派发要求。只读辅助专项 `source_contract_check` 独立核对既有源码与测试合同，未设计实现、未改文件或运行产品检查。本轮 reviewer 仅写本报告，不改任务阶段、执行 prompt、入口、产品或原证据。

## 受审身份与范围

工作目录 `/workspace/Layauto`，分支 `codex/w012-compatible-hex-validation`，HEAD / 调查接收起点 `9b573c99d5f4021636f498292f42b53540bff1a1`。启动时已有改动仅为任务文档及未跟踪的 A1 prompt；产品优化未实施。

| 受审工作区材料 | SHA-256 |
| --- | --- |
| [W012 任务](../W012-capture-wire-performance.md)，含 A1 I1–I6 | `c9ab53287f654dcd26e4e5d4f5eea7abc1a29ee19695681e331076ec4774e105` |
| [A1 执行 prompt](A1-execution-prompt.md)，最终复核版本 | `70ab51c2e5395d1d62c69ad88664decd7253a88c442997f624f6ec200ddd1c3a` |

prompt 初读 SHA-256 为 `424a20c1e981aef87c089e298b87bb1fd16c2e33fb0c8099283ef1806437ad98`；PM 在复核期间补入调查接收及已验收 main 的完整起点 SHA。已重读最终版本，改动限恢复元数据，以下结论绑定上表版本。

实际读取根 AGENTS、README、协作及本地/远端环境规则、任务 A1 与新旧 prompt；回查架构 §2.2–2.3、§2.6、§3.7–3.8、§11.2/11.9/11.15、公共及嵌套 codec 和相关现有测试。对照 [cost-analysis](cost-analysis.md)、[implementation-proposal](implementation-proposal.md)、[independent-review](independent-review.md)、[PM 接收说明](pm-receipt.md)/[回执](pm-receipt.json)及[PM 方案专项](pm-evidence/plan/report.md)，核对调查依据与此次授权的区别；未重新全量审计 P1/P2 原证据。

## 逐项结论及依据

| 要求 | 独立核对及结论 |
| --- | --- |
| 最小范围 / 可执行性 | 任务允许写入及 A1 正文只授权 `layauto_v2/domain/codec.py::_decode` 的 bytes hex 校验和直接必要的测试/新 A1 工具记录；prompt 同步排除通用 writer/reader、memo/cache、删捕获及跳过认证。`implementation-proposal.md` 推荐项 1 与 `cost-analysis.md` 第 4 节把优先点定位到原 matcher 窗口：118,841,892 字符调用期间 HWM 到 7,319,108 KiB。材料保留“窗口定位、不等于净分配、未测清 native 内部分配”的限制，足以支持先派最小改动；未把后续建议一并批准。具体候选和验证计划仍须执行者提出、由未参与设计者先 review。 |
| I1 接受语言 / 拒绝边界 | `domain/codec.py:109–113` 当前以 `re.fullmatch(r'(?:[0-9a-f]{2})*', raw)` 准入后才 `bytes.fromhex`，原语言确实含空串且仅为小写 ASCII hex 的偶数长度串。`:116–130` 另有 duplicate-key、非精确 JSON 数字拒绝与最终 canonical 原字节复验。I1 和 prompt 要求的空/奇数/大小写/空白/换行/Unicode/tag/JSON 见证及保持原类型合同准确；不限定唯一新算法，也未授权只靠宽松 `fromhex` 准入。原 `test_w005_contracts.py:23–40、60–69` 是既有依据，新算法完整语言等价证据仍须新增，不能把现有少量例子当已证明。 |
| I2 `/1` bytes / ref / 认证 | I2 与 prompt 明确保持 schema、公开签名、完整 Result、原 bytes、wire 大小、全部 hash/ref、source/run/owner 和 constructor/认证次数，保留最终重编码检查。`normalization/channel_identity_codec.py:132–158` 由完整 constructor 重建、闭合图和 `/1` 重编码控制最终编码，`record_digest` hash 实际 encode 输出；`domain/publication_codec.py:116–143` 也由实际 `/1` 编码派生 digest/content ref。因此逐字节三路对照及 wire 减幅为 0 是必要且可落实的要求，不能仅以 hash 相同替代完整字节/来源/认证验证。 |
| I3 异常与嵌套边界 | 原 `domain/codec.py:109–130` 未捕获 matcher/fromhex 意外异常；`test_w008_geometry_wire.py:24–36`、`test_w009_nested_base_decode.py:26–49` 及 `test_w011_exceptions.py:47–126` 保留原异常 object/cause/context/suppression、嵌套公开 codec 和二次认证故障。特别是 W011 `:105–126` 要求第二次 `_require_input` 仍发生且保留原历史。I3/prompt 要求验证这些路径、不宽捕获或重包、不改原 finding/删断言，与现有合同一致；算法选择不能以新短路无意遮蔽原故障路径。 |
| I4 完整前后性能 | I4/prompt 明确同机、解释器、依赖、固定输入 URI、RunRequest/cache、保留 roots/GC，三条完整公开构造/encode/decode，最终每条路径 before/after 两侧各 3 个 fresh 串行无插桩样本，报告原次/失败、各次及中位数和峰值/退化；允许复用本轮身份/条件相同的样本。`measurement-plan.md` 与 `probe.py:215–298` 提供原输入、RunRequest、GC、保留对象和计时边界。运行时导入位置可以分离，原工具须保留、必要适配写新 A1 工具。历史 W011/P1 一次、不同条件样本和 profile/窗口诊断不能混作当前 before；要求已明确。 |
| I5 原产品行为 / 固定输入 | I5/prompt 保持正常 5/7、原 mismatch 实际 4 对 source 5 且恰一项差异、完整 FIN/crossing/来源/局部图/T05/body、target 独立及 readback unsealed/checkpoint/无 terminal。`measurement-plan.md`、`probe.py:143–181、255–287` 与 `preflight.json` 的 origin/target/hash/bytes 清单提供可复用见证。PM 原接收已明示本机固定 mismatch 目录缺失；任务和 prompt 把按原清单重建/核对放在比较之前，未冒称目录现存或已重测。更广受影响来源/错型等值/别名/异常负例仍须按影响选择，三条固定输入不代表覆盖全部攻击面。 |
| I6 工程 / review / 停止边界 | I6/prompt 延续协作规则 §5 的“开发新增/受影响优先，最终新冻结源双解释器全量、strict typing、构建和双干净安装源码外组合 smoke”，不以旧同源 W011 矩阵替代改变公共 codec 后的新最终验证。要求源码/测试/配置、工具/输入、包与原输出/失败身份可访问，独立方案/代码/正确性/性能 review 的必须项关闭后交 PM；不自行验收、合 main、改入口或启动下一子项。证据与交接责任完整。 |
| 目标建议 / B 未批准 | PM1、I4 后说明及 prompt 一致将 20% 时间/50% RSS 留作完整兼容包的建议，未升格为最小 A1 硬门、收益承诺或生产上界。`cost-analysis.md:92–98` 的估算有 profile 扰动和窗口范围限制；此次要求实报 matcher/整进程峰值及逐路耗时退化，不为追百分比扩范围。新 `/2`、公开默认/兼容期、hash/ref 和历史迁移另需具体用户决定材料，B 不随 A1 获批也不阻塞此最小内部优化。 |

## Findings 与交接

新增必须修正项 **0**，剩余必须项 **0**；没有要求本次派发准备新增产品测试或重型样本。原 P1/P2 的 R01 finding、修正和独立关闭仍保留于其原报告，不被本轮零 finding 覆盖。

本轮只做文档/源码/既有证据的静态核对和 Git/文件身份检查，未运行新算法、产品回归、重型 baseline/profile、双全量、typing 或构建安装；没有新的产品性能测值。PM 可据此接收派发准备并维护阶段/恢复元数据，之后由独立执行 session 按最新发布身份完成 A1；本报告不代替其最小方案 review、最终实现/正确性/性能 review 或 PM 验收。

## PM 接收后最终身份复核

已将初审任务全文与 PM 接收后的任务全文直接对照：仅“当前阶段 / 阻塞”行及原“派发要求独立复核尚待”段替换为可执行阶段、PM2 接收和恢复交接元数据；其余全文、I1–I6 六行及 A1 prompt 均逐字不变。`git diff --check` 通过；初审结论继续成立，新增/剩余必须项仍为 0，无新增产品 review 或性能结论。

- 最终任务 SHA-256：`6a92ae938e0b12bf542f3409a22f35befb78cde0d5da92d41af6d533b2a5bda3`。
- 最终 prompt SHA-256：`70ab51c2e5395d1d62c69ad88664decd7253a88c442997f624f6ec200ddd1c3a`，与上表受审最终版本相同。
