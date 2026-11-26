# W023 独立方案复核

审阅基线为 `74b05f5dcfa5aa1513993460385510ebab22163f`。审阅对象是任务文件“方案与决定”中的三项设计，审阅时工作树只有该文件的方案修改。对照 §2.3、§2.6、§3.8、§9.2、§11.8 和 W006、W020–W022 的实际入口后，方案可实施。此处结论限于设计。[任务和方案](../W023-atomic-baseline-publication.md) · [架构](../../architecture.md)

| 情形 | 仓库读者应能独立确认的结果 |
| --- | --- |
| A 首次建立第 0 版 | 空 head、revision 1 上的一次发布同时登记第 0 版快照、事件、head、上下文和回执，attempt 为 sealed_open/revision 2。切换前故障仍能解析原 checkpoint 和输入审计。切换后丢失响应，使用原键和同一请求可取得原引用。 |
| B 请求 A 的既有 head | B 的证据与 A 有相同的来源 URI 和内容、能力及模式。B 有独立的运行与捕获身份。B 的 attempt 封存后指向同一版，并能查自己的输入审计。真实改变原始证据或工艺并重绑，保留原版及 B 的 unsealed/revision 1。 |

实施复核时检查以下边界。

- `create_attempt` 与发布均在锁内核对 lineage 的预期 head。两个 run 同时见过空 head，落败方只保留自己此前的 attempt 和审计。响应丢失时重放须先于 phase/head/revision 检查。给调用者保留可重新提交的中立请求，或让公开入口能用原参数找回回执。
- W021 的 `capture_binding.readback` 带有本 run 的 request、attempt、checkpoint、parse 与 tool 引用。W022 的判定从同一候选生成。仓库提交边界须拒绝将其它捕获的内容配上本次的正确引用，以及旧 head/其它 lineage 或无法解析的引用。仅比较调用者填入的摘要无法证明同源。
- 相容性使用所选绑定的实际内容。本样本的原始 query header 绑定 target 和工艺闭包。绝对临时目录、create 键、run ID、工具执行记录及审计内容引用可随 B 的新捕获变化。B 指向的起始事实仍由 A 的已发布快照提供。
- 物理见证以读回的格号、精确矩形及 GDS 偏移核对。通过已有 region、物理 node/component 和 annotation 引用追到 R04/VSS，未知区域保留显式状态。gate 二维占用与一维轨号分别读取。[W022 层检查](../../../layauto_v2/state/layer_checks.py) · [W021 候选](../../../layauto_v2/normalization/initial_state.py)

后续独立代码复核将覆盖至少一个故障或竞争探针及一个物理来源见证。此轮检查未运行测试；阶段双解释器全量由 PM 在实际合并版执行。
