# 合并前性能证据独立核查

审查者为本次新 session 的只读辅助 `/root/performance_audit`，未参与此前 A1 设计、实现、正式测试或性能工具。受审 main `0a3326aa363477724465886cd05874d0997fba3e` → head `e4179dd42cc0de853df73bafd9140a363c8fa5be`。**新增必须项 0。** 本专项没有运行产品、完整 codec/readback 或前后 benchmark。

本机实际运行 [check.py](check.py)，5,973 项轻量身份/原输出/统计/调用记录核查通过，见 [command.json](command.json)、[原 stdout](stdout.txt)、[原 stderr](stderr.txt) 和 [result.json](result.json)。这些不是产品正式测试数。

18 条无插桩记录与 2 条 profile 的逐条 `.command.json`、最终 receipt、原 stdout/stderr hash 均闭合；源分别对照指定 main 与受审 head 的实际 Git blob，262/263 源、各 100 runtime、工具、实际导入根、解释器/platform、GC、固定输入 URI、captures、完整结果事实均核对。命令时序为每 rep/case before 后 after，18 条串行完成后才进入 profile；baseline 在工具代码中不启用 hook/cProfile，每个样本独立 Popen。RunRequest、cache 语义、获取前一次 GC 和完整 roots 保留顺序直接核原 probe/计划；依赖以原 preflight/frozen tool 身份采信，不冒称本机复原历史进程环境。

直接从原 `wall_seconds` 先求每次阶段总和，再取各侧三次中位；RSS 用各次整进程峰值中位，重新得到：

| 路径 | before → after 秒 | 耗时下降 | 峰值下降 |
| --- | --- | --- | --- |
| normal-direct | 94.418923 → 75.799891 | 19.72% | 88.59% |
| normal-readback | 186.625165 → 144.066817 | 22.80% | 90.35% |
| extraction-mismatch | 93.170488 → 79.514097 | 14.66% | 88.65% |

六处小阶段中位增幅与原分析完全一致，未用总值掩盖。旧 20%/50% 为完整兼容包建议，并非 A1 硬门。两侧 profile 的 65 个窗口 phase/长度/顺序相同、最大 118,841,892 字符；HWM 刷新 5 → 0。按 codec 两行位移归一后，各阶段所有可定位 runtime 函数 primitive/calls 相同，包含 constructor、认证、公开 codec；没有少认证的计数迹象。profile decode 221.043995 → 222.849795 秒的单次约 +0.82% 与无插桩样本分开。新 profile 总峰值 720,336 KiB，高于最后观测窗口 HWM 上限 648,896 KiB；该余量未作 allocator/逐函数归因，HWM 不当净分配。

`performance/commands.json` 最后 `after-extraction-mismatch-r3`、`profile/commands.json` 最后 `after-normal-readback-r1` 缺 bytecmp 字段；对应单条命令与最终 receipt 的完整比较记录相同，故不存在末样本缺失。原索引没有修改。原 runner 代码在阶段后按 1MiB 读取完整 wire 实比，bytecmp 不计入阶段时间；18 次 wire 长度/hash 与三路径原记录一致，profile wire/captures 也一致。

本机原约 1.47GB wire、before 树、固定 mismatch 目标目录缺失；没有本机重新读取全部大 wire。原独立 reviewer 在 `44a91c472fdeba5bb4b8a6071c0580313336c379` 实际逐块比较的结论按未变版本/命令/receipt 采信。当前检查能实核原记录和关联，不能替代一次新的大 wire 比较，也不外推生产/最大输入保证。

另以 [investigation_check_r3.py](investigation_check_r3.py) 对 main 尚未接收的 P1/P2 范围作补查：188 项通过，92 成员旧 delivery manifest 闭合，原六路命令输出/工具、原 baseline/profile wire/captures 身份一致，原 R01 的 222/222/217 统计与 65 次原窗口/5 次 HWM 刷新成立，35 项 mismatch origin bytes 在本机逐项重读 hash/长度核对。A1 前后所有 P1/P2 目录附件未变；旧任务文本以旧 manifest 的 review commit 核原 blob，因为该任务随后按角色合法追加了 A1/PM 记录。

补查初次误将旧任务 hash 直接要求等于新任务，第二次误用 A1 `hwm_kib` 字段读取旧 P1 `ru_maxrss_kib`，均为本检查器错误，原检查器、失败命令及 stderr 保留；第三次只修正这两项证据层级/字段读取后通过。没有修改历史证据，也不将这些检查器失败归为产品 finding。见 [最终补查命令](investigation-r3-command.json)、[结果](investigation-result.json)；前两次的 `investigation-command.json` / `investigation-r2-command.json` 与对应脚本、输出均在本目录。
