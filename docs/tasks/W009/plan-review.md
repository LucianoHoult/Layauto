# W009 独立方案 review

- 日期：2026-11-03；reviewer：`/root/plan_review`，未参与方案设计或产品实现。数学/范围只读专项：`/root/plan_review/math_scope_probe`。
- 仓库：`LucianoHoult/Layauto`；分支：`codex/w009-effective-geometry-terminals`；基线 HEAD：`4975e565a33d9594782645b6ad0f944b78ee6ae8`。
- 受审对象：`docs/tasks/W009/plan.md`；初审 SHA-256：`05de138af4287a391b0e1336eca049b27cf33307f6194f27c742734a2a64d56c`；修后复核 SHA-256：`b14226b6aa68dae2f9d305b57adf5f5bb27eaa6e61c4eb625847786133d37deb`。
- 结论：**IR-01 已按原范围修正并独立复核关闭；剩余必须修正项 0，可按修后方案实现。** 本结论不代表代码 review、A1–A8 实跑通过或 PM 验收。

## Finding 与复核

| ID | 严重性 / 原 finding | 执行处置与独立复核 |
| --- | --- | --- |
| IR-01 | 需修正的方案合同歧义：初稿第9行写 OD/POLY 的 `diffusion/poly` 角色，但实际 `drawn.json` 的 `/layers/4/role` 是 `gate`，照字面实现将拒绝正常样本。另外只按 `role=cut` 筛选后校验会遗漏被改成错误 role 的 CUT 声明，可能静默跳过应消费的差集 policy。依据：W009 行为2/A2，以及实际 OD/POLY/LI/CUT 声明。 | 执行者明确先定位选定 toy profile 的四个声明，再逐项校验 `OD=diffusion`、`POLY=gate`、`LI=interconnect`、`CUT=cut`，不先按 cut role 过滤。Reviewer 重新读取第9行并重算修后全文 SHA-256，确认与实际 owner 一致。**关闭**。实现及测试仍须覆盖错误 role/target/operator 反例。 |

## 独立判断

1. 输入路径与分层符合 W008 合同。`GeometryInput._verify` 已重新解析捕获的六个 owner，physical source 是 tech evidence 的对应独立 source role；W009 成功 aggregate 仍需核验新增 physical evidence 与该输入 payload/source 完全关联。state/domain 只做中立一致性校验，认证留在 normalization；不依赖 IO、repository 或 parser。完整嵌入 W008 receipt 能保留 run/readback/单位/原图形与占用身份。
2. 差集的 x slabs + y 区间合并/扣除 + 相同 span 横向合并是本范围内可行的精确规范化方案。其所有边界来自整数输入和精确交集；重复/重叠 CUT 按集合覆盖处理而来源记录仍完整。孔洞、多片、空结果、未命中及边角相接均有明确表达，不以 bbox 代替集合。分组只用于单原 record 的局部几何区域，不形成跨 record 电气图。
3. region 与 piece refs 绑定 owner、角色、全部贡献记录、单位、算子与 exact geometry，aggregate 重新计算完整期望集合，能针对漏片、多片、外来来源及填洞设计公开 constructor/decode 反例。真实 GDS 重排应改变 provenance refs，另以保留 multiset 数量的 geometry digest 比较语义；两者没有混淆。
4. 对矩形 OD、单一矩形 stripe，正面积交集覆盖 active 全 y 且 x 严格位于内部，恰好形成完整左 S/右 D；部分高度、全覆盖、贴边及横向切分均不能得到该 toy profile 的两端区，因此定位拒绝符合任务。完全相同 POLY 几何只形成一个集合 stripe 且保留全部记录来源，与 record 重数/集合覆盖的区分一致；不同几何同时命中时不合成为 gate，按多 gate/歧义拒绝。这里没有增加生产 gate grouping 或 S/D swap 规则。
5. 半开矩形只用于计数/索引，闭包边界留给后续接触谓词；内部 slabs 没有被提升为完整工艺坐标。方案保留 FIN/body/marker、W007 语义/query，以及 U06 后续义务；没有建立 net/DeviceId join、S↔D edge、全层 connectivity 或发布成功。
6. 验证计划包含独立手算、逐 arrangement cell 的点归属判据、包含/交叠/边角反例及真实 W005/W006 两条组合；没有仅依赖面积或另一次同算法调用作为 oracle。730项兼容、双解释器/typing/build/两套干净安装、最终身份与有限压力规模均明确；复杂度/片段增长有披露且无新增外部上限。

## 审阅方法与限制

核对根 AGENTS、README、协作规则、W009 完整任务及执行 prompt，架构 §2.2–2.3、§3.1/3.4–3.6、§4.5–4.8、§5.6–5.9、§11.2–11.3/11.14–11.15、§12.3/12.5，实际 `tech/drawn.json`、`physical.json`、`formats.json`，W008 `geometry_input.py`、`geometry.py`、`LayoutDraft`/geometry DTO 与 codec 边界及 W003 相关输入合同。数学专项独立核对差集分解、gate/terminal 条件和边角语义，与主 reviewer 结论一致。

实查 HEAD/branch/工作区并用 `sha256sum docs/tasks/W009/plan.md` 绑定初审和修后全文。开始时产品尚未实现。未运行测试、EDA、构建或性能检查；不把设计可行性当运行证据。唯一写入为本报告；没有修改受审方案、产品代码、fixture、历史证据或任务 PM 段，也没有提交/推送。代码完成后仍须由未参与设计/实现者独立代码 review。
