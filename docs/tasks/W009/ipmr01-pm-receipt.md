# W009 IPMR-01 补修 PM 接收

日期：2026-11-04。交付分支 `codex/w009-effective-geometry-terminals`，受核验 HEAD `6cb4ecc2ecaa8bd6e5236b28b70149d9a4917534`，产品/正式测试提交 `73e38df8f932bbb5bd9caf074b442ad2f5c286e9`，补修起点 `cdf3d2d5d2aeb0c441221c8bb0b41d0b302d8afa`。main 仍为 `4df07e68b05df4c57a8b8d44bc41e7e073938d3a`。

**补修分支接收通过，IPMR-01、FXR-01关闭依据成立，剩余必须修正项0；可进入main集成与组合验证。** 当前阶段为待验收，尚未记录main集成及最终验收。

## 变更与 findings 核验

PM 对照[补修要求](ipmr01-fix-task.md)、[原独立合并前报告](independent-premerge-review.md)、[执行交接](ipmr01-fix.md)及[独立修后复核](ipmr01-fix-review.md)，核对完整8个 runtime/3份正式测试的产品 diff。修复围绕 W009 实际可达的 W008 base、semantic/readback 和捕获 DTO 重建路径；没有机械取消全部历史异常边界。预期畸形字段由消费位置显式校验，事实重建中的意外异常按原对象传播。

| Finding | 关闭依据 |
| --- | --- |
| IPMR-01 | 独立 reviewer 检查完整 diff，并在最终源上重跑99项矩阵、畸形对照、真实两路径和既有cause/context见证。PM再次实际运行未修改的原99项脚本，并检查JSON而非只看退出码，结果99/99、identity_failures=[]。新正式回归同时覆盖W008/W009重建、semantic/readback和捕获hash，以及畸形输入明确拒绝。 |
| FXR-01 | 独立 reviewer 保留双遍历反例并复核修后单次tuple快照；校验和保存使用同一快照，原list子类支持保持。PM正式回归包含四类集合入口×valid-first/invalid-first共8项，另委派公有边界专项。见[PM代码专项](ipmr01-pm-evidence/code/report.md)。 |

既有 source/owner 认证、closed graph、几何数学及 canonical wire schema 保持；同捕获兼容对照证明旧版和修后 W008 result、W009 draft/result 的 wire/digest 相同。fixture/答案、原独立失败脚本及历史证据未被改写；原PM1/PM2各保留当时版本事实，不把旧结论冒充修后身份。

## 本次实际验证

- Python3.12补修正式回归：**235 passed / 316.54s**，覆盖本轮全部三份新增正式测试；外部anyio插件有1条pytest弃用提示，原文保留。
- 原独立异常脚本：**99/99同对象，identity_failures=[] / 89.110s**。
- Strict mypy：**44模块通过 / 1.746s**。
- PM代码专项：**41例通过**，覆盖list/tuple子类双向快照、真实完整result roundtrip、捕获内部故障及畸形SourceFile wire；未发现新增必须修正。
- PM证据专项：245项源码/归档、两包各90项runtime、24条命令与恢复/历史材料身份核验通过。

本机为既有 Linux Python3.12.14 PM环境，pytest9.2.0、mypy2.4.1、PyYAML6.0.3，不属于新包干净安装。各命令的实际HEAD、环境、耗时、退出码、stdout/stderr及hash见[PM机器回执](ipmr01-pm-receipt.json)与 `ipmr01-pm-evidence/`。仅对补修受影响范围补跑，不重复已核验的1149项全量。

## 交付身份及采用的原证据

最终245项源/测试/配置清单 SHA-256 为 `40a60ada56e2b560d1af88fec9c16e4d60a6b1384fb042f39202edfcaefefc2c`。PM证据专项实际核对当前源、完整源码tar、两包各90项runtime、命令输出和恢复记录，详见[专项报告](ipmr01-pm-evidence/evidence/report.md)。原两套实际安装树不在当前主机，本次未遍历这些目录、重新构建或安装；安装结论按原独立字节/来源审计采信，未把历史记录改称本机执行。

原最终执行的Python3.12完整1149项、Python3.10受影响988项、双typing及两包/两次干净安装smoke，按最终身份与原独立审计采用。3.10范围为全部contracts及W006 publication unit，未跑其余unit；旧3.10完整914项仍仅属于原版本。

11月3日已完成的构建/安装/smoke和独立probe按同一源码、命令及输出身份沿用；11月4日重跑缺失的pytest/typing等。中断partial和修前材料保留但不计为完整通过，复验hash不能单独等同重新观察历史命令执行。

## 下一步

原独立合并前复核及本次独立修后复核已有完整交接，本轮接收后可进入main集成与组合验证。W009仍须记录集成版本与组合结果，之后才作最终验收；本轮未合main或启动W010。

仍处于M1的物理事实构建部分，完整工艺坐标/区域投影、物理接触及连接图、器件/FIN/body提取、标注、规则/发布、完整无变化运行与Stage6继续后置。U06生产叶cell缺外部tapcell/全局电源上下文需求保持；本次未执行真实EDA/PDK或建立生产性能结论。
