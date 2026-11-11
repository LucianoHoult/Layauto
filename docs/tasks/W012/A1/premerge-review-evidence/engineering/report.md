# 独立合并前工程证据专项

本 session 的只读工程辅助 `/root/engineering_audit` 未参与此前 A1 设计、实现、正式测试或性能工具。审查 base `0a3326aa363477724465886cd05874d0997fba3e` 到待审 head `e4179dd42cc0de853df73bafd9140a363c8fa5be`，新增必须项 **0**。独立轻量检查器 [check.py](check.py) 的 **1413 项证据检查通过**，原始 [stdout](stdout.txt)、[stderr](stderr.txt) 与 [命令/身份](command.json) 保留；这些数量不是正式产品测试数。

- 实际逐一读取并校验 263 源/测试/配置和 100 runtime，与 `ca1f810c3c97376f71089d8b4054760ff198012f`、原独立 review `44a91c472fdeba5bb4b8a6071c0580313336c379`、本次 head 的对应 Git 对象一致。`source-manifest` 的记录起点确为 `212554cdc402f6b86e92b8b81cd43752a01ff858`；实际 tar 的 263 个成员及身份完全一致。
- 整个 main→head 为 595 个路径：593 文档/调查工具/证据路径、唯一 runtime `domain/codec.py` 及唯一新增正式测试 `test_w012_hex_validation.py`。前序 P1/P2 未合 main 的调查材料属于交付范围；原 review 后 107 路径均为文档/证据封包或 PM 接收，未改变产品/测试/配置或 P1/P2 附件。
- 实读 r2 的 21 条独立命令 JSON、42 份原 stdout/stderr，并重算其 hash，与最终 receipt 一致；78 项附件 manifest 全部闭合。双解释器的收集项实际都是 1656，原 1605 个 node ID 全保留，恰新增 51 个 A1 用例；两份 pytest 原输出分别为 1656 passed（7939.88s/5716.06s），typing 原输出均为 54 源文件通过。
- 实际打开 Git 中四份 before/after wheel/sdist，各有 100 runtime 成员；同侧格式 payload 相同，before 与 main 原 runtime 相同，after 与冻结 runtime 相同，跨侧仅 `domain/codec.py` 的成员 bytes 不同。before 是本轮重建包，不冒充 W011 历史 blob；没有声称 before 曾运行本轮安装 smoke。
- 双 after 安装原命令均创建全新环境，3.10 安装 sdist、3.12 安装 wheel；原安装身份均为 isolated=1、100 成员等于冻结 runtime。源码外 `-I -B` 完整 smoke 的原输出保留三路径 5/7、4/7、一项 mismatch、18 FIN、图 14/8/6、body 6 及 attempt/checkpoint 不变、无 terminal。安装 smoke 使用 snapshot 输入且 mismatch 使用临时路径，其 wire hash 不充当固定 URI 性能证据，也不要求跨解释器相同。
- 首轮 26 项原 partial 附件逐 hash 保留，约 39%/43% 输出没有通过尾部。r2 外层 wrapper 的原 JSON 仍只有 started，没有伪造退出码；实际完成由内部 21 条命令及最终 receipt 支持。重连原记录明确 detached 子进程存活且未重启。
- A1-R01 原 buggy runner、隔离覆写复现、原失败输出及独立关闭证据存在且版本对应。此次又对当前 runner 实跑四种非空 stage（仅 stdout、仅 stderr、仅 frozen identity、三者）隔离探针；均在 Popen 前拒绝，旧文件逐字节保持，没有启动产品/性能进程。新 probe 只替换身份/preflight 以到达 guard，范围不扩成完整 runner 执行保证。

本机原安装树不存在；双全量、typing、安装及完整 synthetic smoke 按未变源、原命令/输出身份和原独立 reviewer 实读安装结论采信，本轮未重跑小时级矩阵或重新安装。四个包和源码快照则是本轮实际读取。历史报告、正式测试和 fixture 均未修改。
