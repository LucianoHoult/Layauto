# W012 A1 PM 证据专项复核

受核交付：`db07a16fb7cbbac030adae84a9eb88cc0c8aa650`，`/workspace/Layauto` 原 A1 分支。结论：本专项必须修正项 **0**，A1-R01 关闭依据成立；有一类非阻断索引记录差异，见下文。本结论仅供 root PM 综合接收，不代替独立合同复核或集成决定。

按要求只读 AGENTS、README、协作/环境规则、W012 I1–I6、A1 执行/完整性能分析/独立 review 与原附件。未运行产品、codec、性能、矩阵、构建或安装，未修改仓库。性能/证据脚本 1305 项、独立工程/包脚本 1286 项轻量核验分别通过；这些是证据校验，不是产品测试数，也不去重相加充当覆盖率。第二次本地 checker 因 root 同时新增已告知的 `independent-premerge-prompt.md` 而触发“工作区全净”前置断言；失败输出保留于 `performance-attempt02-*`。随后明确允许该一项 PM 草稿，既有交付文件仍逐 hash 未变，最终通过。

## 本机实际核验

- 263 源/测试/配置、100 runtime：当前文件、产品冻结 `ca1f810c3c97376f71089d8b4054760ff198012f`、r2 manifest 与 tar 快照一致。性能 after 的 263 项同源，before 为 262 项，差异仅 codec 和新增测试；before 源 tar 的 100 runtime 与性能 before 和实际 before 包一致。
- 最终 r2：实读 21 条内部命令、原 stdout/stderr 并核 hash，均 exit 0。Python 3.10.22/3.12.14 原 stdout 各 `1656 passed`，原 1605 node IDs 全保留，仅新增 51 个 hex 用例；双 typing 各 54 文件成功。工程 78、before 包 18、交接 430、review 66 项附件 manifest 的实际文件及 hash 闭合。
- 四份实际 wheel/sdist：各 100 runtime 成员，同侧两格式 payload 相同，前后唯一 payload 差异为 `domain/codec.py`。before 是本轮从原受测源重建，不是 W011 原包 blob，也没有宣称本轮 before 安装/smoke。
- 18 个无插桩基准：实读每份单条 command、输出 hash、源/工具/实际导入路径、输入 URI、解释器/platform、GC 与结果记录；按 rep/case 的 before→after 次序，18 次时间区间串行不重叠，每次 fresh 由 runner 的独立 `Popen` 调用及实际 argv 支持。性能完整结束后才运行两份独立 profile，随后才开始工程矩阵。性能 preflight 保存依赖清单（PyYAML 6.0.3），工程准备记录明确既有性能 venv 未变；当前 venv 不存在，未声称本机重新盘点原环境。
- mismatch 的 35 项 origin 当前文件逐 hash/size 与 preflight 一致；三条路径实际 31 份 capture 的来源字节/hash 可从原始 fixture/origin 核对。before/after 固定 URI、RunRequest/cache、完整保留 roots 和 collect/GC 顺序由相同 probe 与原样本记录支持。正常 5/7、mismatch 4/7 对 source5/7、恰一项差异、完整 36 FIN evaluation/crossing、T05/body/局部图及 readback 状态边界均有原断言/原结果记录。

## 独立重算

直接使用每次 `wall_seconds` 的和，先求每次总值再取三次中位；未混入 runner 启动/轮询/保存 wire 耗时。结果与提交的 summary 完全一致。

| 路径 | 总秒中位 before→after | 峰值 KiB 中位 before→after | 耗时 / 峰值降幅 |
| --- | --- | --- | --- |
| normal direct | 94.418923302 → 75.799891287 | 2851076 → 325436 | 19.7196% / 88.5855% |
| normal readback | 186.625164656 → 144.066817015 | 7344896 → 708536 | 22.8042% / 90.3534% |
| extraction mismatch | 93.170487541 → 79.514097003 | 2860516 → 324668 | 14.6574% / 88.6500% |

全部六个阶段中位增幅与报告一致：direct W005 +3.6129%、W008 +2.4581%；readback prepare +4.7386%、W009 +0.6471%；mismatch W008 +0.8443%、encode +0.8179%。有限三次样本不足以归因为噪声或稳定算法退化；原报告没有声称所有阶段改善。20%/50%不是 A1 硬门。

从原 profile 函数记录独立重算，每阶段明确 constructor、认证、normalize、公开 encode/decode 调用数相同；归一 codec 的已知两行位移后，所有可定位 runtime 函数 calls/primitive calls 相同。65 个大 matcher 窗口长度/顺序相同，HWM 刷新 5→0；最大窗口 118841892 字符，旧 HWM 3604172→7326636 KiB、新 501568→501568 KiB。新版 profile 整体峰值 720336 KiB，高于全部窗口上限 648896 KiB；原始 profile decode 增幅约 0.8169% 仍存在，不能用插桩计时替代三次基准，残余成本没有逐 allocator 归因。

## 原证据采信及访问限制

本机 `/workspace/w012-a1-performance/wires/baseline`、`wires/profile`、`/workspace/w012-a1-before`、固定 mismatch 目录、原性能 venv、`/workspace/w012-a1-final-r2` 均不存在。两个原干净安装树及解释器亦不存在。

因此，**PM 本机未重新读取或逐字节比较原巨大 wire，也未重 hash 原安装树/重跑安装 smoke**。原单条 command 和最终 receipt 对 18 次基准与两次 profile 都保存了实际完整 wire 按 1MiB 块比较为真的结果，原独立 reviewer 另记录了实际重读/比较；此项按已核身份的原执行和独立复核证据采信。各路径原记录的完整 wire 长度为 54050313 / 136471701 / 54045042 B，各侧各次 hash 相同，wire 减幅为 0。

安装侧采信已 hash 的原 100 成员安装身份、3.10 sdist/3.12 wheel 安装命令与原输出，以及源码/snapshot 外 cwd 下 `-I -B` 完整组合 smoke。smoke 使用其冻结 snapshot 的输入 URI，未与固定 URI 性能 hash 混为一谈。四个包、源 tar、工具和原结果都在 Git 内可实读重建；原巨大 wire/安装树缺失作为当前复核限制保留，不补造“本机实比/重装”结论。

## 中断与 A1-R01

首轮 26 项 archive 逐 hash 保留，双 pytest 约 39%/43% partial 无 completed receipt，未被计入通过；OOM=0 不证明中断原因。第二次重连后的外层 wrapper 仍只有 started，无 exit_code；最终依据是内部 21 命令和闭合 r2 receipt，不补造外层 exit0。恢复仅变工程调度，性能早已结束，未算作产品收益。

A1-R01 的原 faulty runner、复现结果、原输出、首次 reviewer checker 类型捕获错误及修正后关闭证据均保留。当前 guard 在任何 stage mkdir/frozen-identity 写入前拒绝非空 stage，selfcheck 先返回，另拒绝已有 wire。正式所有样本中的 runner SHA 均为修正后的 `aca026ad…`，原独立 guard 结果证实已有 stdout/stderr/frozen-identity 字节保留、无进程启动。该关闭成立。

非阻断观察：`performance/commands.json` 最后第 18 条及 `profile/commands.json` 最后第 2 条缺 `actual_complete_wire_byte_comparison` 字段，原因是 runner 在追加该字段前写聚合索引、最后未回写。对应单条 `.command.json` 与最终 `receipt.json` 均完整，末项比较证据和结论不受影响。后续宜使用单条回执或最终 receipt，不把聚合索引当唯一比较依据。本轮不改原输出/工具来补写历史。

机器结果：`performance-result.json`、`verification-payload/result.json`；脚本和命令记录：`performance-check.py`、`performance-command.json`、`verification-payload/check.py`、`verification-payload/command.json`。
