# W009 PM 分支接收

日期：2026-11-03。核验对象：`codex/w009-effective-geometry-terminals@5b1d9b5196a7c5181822c4dd0f1bd2f678475116`，准备起点 `4975e565a33d9594782645b6ad0f944b78ee6ae8`；远端 main 为 `4df07e68b05df4c57a8b8d44bc41e7e073938d3a`。

**分支技术接收通过，本次未发现新增必须修正项；阶段为待验收。** 当前已有交付方案/代码独立 review，但尚未进行另一个 session 的合并前复核及 main 集成组合验证，不宣称 W009 最终验收或 M1 完成。

## 要求与修正处置

PM 阅读 W009 要求、方案、执行记录与独立方案/代码 review，并核对四个新增产品模块、公开导出、typing 配置、旧 W007 依赖边界测试的精确例外及新增合同测试。原 IR-01 是算子角色解释，CR-01 是意外异常被翻译，CR-02 是相等但可变的外来对象进入公开结果；原 finding、修正阶段和独立关闭依据保留，未改写 reviewer 结论。

| 验收项 | 本次核验及依据 |
| --- | --- |
| A1–A2 | 成功结果保存完整认证 W008 输入，并从其同一捕获取得 physical owner；消费的 profile/operator/角色逐字段检查。正常直接读取与 W006 readback 组合由完整回归覆盖。未重新读取输入或把 query/CDL 名称当几何依据。 |
| A3–A5 | PM 几何专项独立穷举 512 个 CUT 覆盖掩码，41,472 点归属、独立 BFS 分组、等覆盖 CUT 分解、重复/重排及大整数变换均通过。实际正常组合得到手算一致的 2 个 channel 和 4 个端区；special cut-islands 及孔洞/全覆盖/不适用 gate 情形由完整回归覆盖。见[专项报告](pm-evidence/geometry/geometry-review.md)。 |
| A6 | 聚合构造按原 base/owner 重建完整区域；closed wire 和原对象图检查保留。PM 重跑原 CR-01 probe，draft/result 两入口各9类异常均保持同对象；重跑 CR-02 Fraction 原子别名 probe，当前边界明确拒绝。完整回归覆盖其余已关闭反例。 |
| A7 | raw drawn/base occupancy、语义/query/body 证据仍独立保留。几何分组和 toy 左右 S/D 未冒充电气 component、canonical device join、body 证明或运行成功。fixture、答案及 W003–W008 历史文件相对准备起点未改。 |
| A8 | 实际重算 240 项源清单和源码 tar、117 项验证证据、15 条命令的原始输出、wheel/sdist 各90项 runtime，全部对应本次交付；最终 probe/方案/性能身份匹配。见[证据专项报告](pm-evidence/evidence/report.md)。 |

## 实跑与采用的证据

本次 PM 实跑 Python 3.12 完整 v2 **914 passed / 599.29s**，strict mypy **44 source files** 通过；18项异常同对象检查、Fraction 可变原子拒绝及上述几何/证据专项均通过。pytest 有1条外部 anyio 插件使用旧 pytest API 的弃用提示，原文保存在 stdout；无失败。

本机采用既有 Linux Python 3.12.14 PM 环境，pytest 9.2.0、mypy 2.4.1、PyYAML 6.0.3；不是新建环境或干净安装。命令、HEAD、环境、耗时、退出码及 stdout/stderr hash 保存在 [PM 回执](pm-receipt.json) 和 `pm-evidence/`。

执行者 Python 3.10.22/3.12.14 各914项、各44模块 typing、新 wheel/sdist、两套全新安装和源码外 smoke，经最终清单与原独立审计核验后采信。原两套安装树不在当前机器，本次重算了包实物、安装来源和日志记录，未重新构建、安装、遍历原安装树或实跑3.10。证据内容一致不能单独证明所有历史命令的执行；历史运行事实仍归原回执/review。

最终源清单 SHA-256：`32e60e783a7a7e4172ee3916e3ceb4fade329585b87a7c7091a85c8a6418d1b6`。此次仅新增 PM 文档与证据，产品、测试、配置及上述清单对应源码不变；任务后续 PM 追加记录不改写旧验证清单或历史快照。

## 下一步与限制

沿用用户此前的会话分工，下一步由单独 session 做合并前复核，关注原 W009 A1–A8、W003/manual review 的相关几何语义、W008 输入与边界、CR-01/CR-02 关闭有效性及当前交付身份。本次 PM 专项不能冒称该独立 session 已完成。复核通过后再做 main 集成与组合验证，届时记录最终验收；本轮不启动 W010。

仍处于 M1 的物理事实构建部分。完整工艺坐标、有效区域投影、物理接触/连接图、器件/FIN/body 提取、query 空间标注、规则与发布、无变化整轮判定及 Stage 6 尚未完成。有限穷举不构成全整数输入或生产性能证明。U06 单独 leaf cell 缺外部 tapcell/全局电源上下文需求继续保留；当前 synthetic body_context 必填没有改变，未执行真实 EDA/PDK 验证。
