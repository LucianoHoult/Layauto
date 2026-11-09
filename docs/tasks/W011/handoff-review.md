# W011 派发要求独立复核

Reviewer：`/root/w011_handoff_review`；日期：2026-11-09。
只读上游接口专项：`/root/w011_handoff_review/upstream_check`。

**结论：必须修正项 0，可以交 PM 将任务推进到可执行；产品方案、实现、测试与验收尚未发生。** 本次检查任务是否有充分依据、可交接且不扩大现行合同，不替代执行方案 review、代码 review 或用户另行要求的专门合并前 review。

## 被审身份与范围

- 仓库 `/workspace/Layauto`，分支 `codex/w011-channel-identity-fin-count`；HEAD/base 均为 `61775e8fde6e9ea247ec08a32067c44c3be48ff8`。
- 被审文件：[W011](../W011-channel-identity-fin-count.md)，初审时为唯一未跟踪的准备文件；SHA-256：`7a414a24a006be477430fdab75b16ae80abb0f7a4e393f8bda2df9e4d43e2870`。
- 读取根 AGENTS、README、协作规则；搜索 `docs/`、`tests/`、`layauto_v2/` 未发现局部 AGENTS。本 reviewer 只写本报告，未修改任务、实现、正式测试、fixture、PM/入口或 main。
- 直接对照架构 §1.4、§2.3、§4.5–4.6、§5.4/5.6、§6.2、§11.5/11.9；实际 `physical.json`、`derived.json`、`rules.json`、manual review 的逐根 crossing 与 MR-031/032.1；W007 normalization、GeometryInput、W009/W010 保留链和 extraction_mismatch overlay。没有运行产品测试、生成器、构建或 EDA。

## 核对结果

| 范围 | 判断及依据 |
| --- | --- |
| 最小可执行切片 | W007 已提供 canonical DeviceId、query key 与 seeds；W009 已有 active/channel/S/D；W010 提供局部 node/component。`GeometryInput.semantic_input` 保留 W007 输入，可在同一捕获调用 `normalize`。任务明确不把保留的输入误称已算出的语义结果。 |
| 几何 FIN 资格 | physical 的 FIN profile 明示完整 channel x 跨越、完整 active y 包含、partial unsupported；架构 §4.5 要求 X/Y 联合归属。任务保留完整原始 FIN，按 crossing 计量，不按声明值、Y 或面积替代。正常 5/7 与独立 oracle、manual 的具体矩形一致。 |
| 反例可达 | extraction_mismatch 提供 source.gds、header、device_info_Q17、normalized cache 与 body/context 的配套 replacement。ON 上边为 64nm，F05 下边为 64nm，应无正面积 crossing；source CDL 仍为 5。W007 未将 NFIN/L/W 锁死成 fixture 常量，4 对 5 和有限 L/W 差异可交给本任务计算。 |
| seed 定位/coverage | derived owner 只声明 exact rectangle、零 tolerance、channel trim、reject_ambiguous；没有所有 seed 必须 full channel 的通用准入规则。任务要求保留 exact 交集/coverage、检查整体一对一和缺失/歧义，且禁止把部分证据升级为全区 annotation，也没有提前新设全覆盖门槛。具体定位证明须在独立方案 review 中落实。 |
| 重复/重叠 FIN | 现行 owner 的 distinct rectangles 和旧 helper 均不能独自决定同几何重复记录应计 1 或 2。任务保留记录及重复关系，禁止默默双计数/去重；无法证明 profile 子集时 typed-unsupported 符合架构 §1.4。它没有声称所有重复记录必然不支持；若要扩充物理解释，仍要求带反例交 PM。 |
| source/target | 几何计量与 source/current 参数比较；target 差异保留为 intent。target-only 变化不反填几何，也不被误报为 source 提取错误。mismatch 的具体 DTO 形式可留给执行方案，但实测值、声明值与全部可判差异必须保留。 |
| 拓扑与范围 | 两 channel 可共享同一完整 POLY G，关联对象为 channel；G/S/D 回链只引用局部图。任务不按名字造边，不抹掉 T05 违规；不把有限 count/L/W 比较提升为完整 model/VT、D/G/S/B net、body、T03/T08、LVS 或 no_change 通过。 |
| U06 | 保留生产 leaf-cell 缺外部 tap/rail 的后续需求。当前 synthetic body_context 输入合同与本轮未处理的生产可选证据分开，没有把 toy 文件格式推广为生产条件。 |
| 公开合同/工程 | A1–A8 包含实际 direct/readback、来源错配、公开完整重建、alias/异常链、source差异和 scope；包括处理预期问题后二次构造的异常链。最终源码、双解释器/typing/包/安装与 review 绑定要求沿用上游合同，有限资源披露不冒充上界。 |

## 执行方案需继续明确的事项

以下为已有要求的落实提示，**不是新增必须修正项，也不要求在派发前请用户选择**：

1. 为 seed 恰等于 channel、仅覆盖部分 channel、同时命中两 channel、同身份多 seed 四类输入列具体候选/关联/coverage 结果。明确哪些事实由几何证明，哪些属于身份定位；不要把“不是 full coverage”自动改成新输入错误。
2. 为重复/重叠 FIN 给出保留记录、受影响 channel 和不能证明独立物理 FIN 的具体见证；unsupported 应绑定实际缺口，不用一句“重复不支持”替代 profile 分析。

上述工作已被任务“行为要求 2/3”和“先方案独立 review”覆盖。若后续方案必须改变输入解释或能力范围，按协作规则 §5 带具体材料交 PM；本次没有自行批准该类变化。

## 检查与限制

实际使用 `git status --short --branch`、`git rev-parse HEAD`、`rg`/`sed`/`cat` 读取原文和接口；`sha256sum` 与 Python hashlib 独立核对上述任务 hash。静态扫描任务的 10 个相对链接，目标路径全部存在；未执行锚点渲染或产品行为验证。上游专项也是静态可达性检查，没有把现有测试摘要当成本次实跑。

本报告仅支持 PM 接收 W011 派发要求。后续 PM 阶段/导航/交接补记不自动成为本 hash 的内容；若改动行为要求或验收项，需复核受影响部分。

### 准备稿空白清理复核

PM 仅清理任务第 31、34 行空白行末的三个空格，当前任务 SHA-256 为 `faf0a6a31d1d4acb0772ad0d328a6726e050fdb58c737c6c34c76daa8d6be3dc`。Reviewer 从当前 bytes 在这两行还原三个空格，重建 hash 恰为上述初审 `7a414a24…`，确认全文除此之外未变；结论继续适用。同期 PM 正在更新文档导航/当前入口/roadmap，这些文件不属于本次任务正文 hash 或产品验证范围。

### 最终派发身份复核

PM 更新任务阶段为可执行并追加接收记录后，最终任务 SHA-256 为 `05d6343f66845347afd098bc3805101f1b865c9da8ba5db46468c317fef4c6de`。Reviewer 仅复核该增量，并将阶段行和 PM 段恢复为前稿文本进行内存重建，SHA-256 精确等于 `faf0a6a3…`；确认行为要求、A1–A8 与执行 prompt 全部未变。新增记录正确区分准备接收和产品验收，**必须修正项仍为 0**；本次未扩大上游检查或运行产品测试。
