# W011 PM 工程证据专项

角色：`/root/w011_pm_evidence`，独立只读核验；交付 `3c464baade7b6ea8c712cfb84265490b8e3f754e`，冻结源 `e89bdaa6a091f56cfaf7862dced7232d34e22514`。

**本专项必须修正项 0，150 项字节、索引、实际 stdout 和资源重算检查通过。** 原始结果见 `audit-result.json`，本次命令为 `python /workspace/work/w011-pm-check/evidence/audit.py`，exit 0；`audit.stdout.json` 保存摘要，stderr 为空。没有运行产品导入、pytest、完整 codec、构建或安装；本结论只覆盖工程证据身份与表述，不替代产品 review 或 PM 验收。

- 262 项源码、正式测试、配置与当前文件、冻结 Git、交付 Git、snapshot tar 全部一致，归档内名称唯一；runtime 100 项与修正提交 `8917d38` 相同。执行未修改固定 fixture/current-work。
- 工程索引 83 项、资源索引及旧失败索引按全部实际文件重算匹配。21 条最终命令全部 exit 0，stdout/stderr 实际 bytes 与行回执及索引相符；源 manifest、snapshot、runner、smoke 的独立身份相符。
- 两解释器 collection 各唯一 1605 IDs，包含原 1465，新增 140 均属于 W011；实际 pytest stdout 为 1605 passed，3.10 为 12905.97s、3.12 为 7310.82s。实际 typing stdout 各为 54 files，无问题。3.10 命令耗时 12908.836s，包含 W011 gate 等待 2603.347384s。原始 WAIT/ACQUIRED/FINISH/RELEASED 事件与归档一致，两个 W011 重阶段串行；未删除或替换测试。
- wheel/sdist 两个真实归档哈希匹配，各 100 runtime 字节等于冻结源。两份已归档安装记录各含 100 项相同 runtime；分别绑定 sdist、wheel，fresh/isolated 与源码外 `-I -B` smoke 回执一致。实际 smoke stdout 的 direct/readback 为 5/7、equal，原 extraction_mismatch 为 4/7、mismatch、恰 1 项 source 差异，attempt 不变。
- **本机不存在原 clean-310 / clean-312 安装树。** 上述安装结论来自已归档安装清单、实际包和成功 smoke 输出的身份链；本次没有重新观察原安装文件或重新安装。独立原 reviewer 在原环境核对 live 安装的历史结论可按其范围采信，不能把它改写为本机实测。
- 原失败矩阵 `2 failed,1603 passed` 的 stdout 与 exit 1 完整保留，未混作最终通过；最终双矩阵是测试准备补修后的完整重跑。

## 资源数据核验

每例一个 fresh 进程的原始回执均 exit 0、完整 Result roundtrip 成立、31 capture 共 280,706 B、18 FIN 和 36 evaluations；源/配置与最终工程矩阵一致。表中 RSS 是整进程 `ru_maxrss`，含 imports、上游构造、原对象及 codec，**不是 W011 增量分配**；constructor 认证已包含在 build/decode，未单独计时。

| case | wire bytes | peak RSS KiB / GiB | W011 build / encode / decode 秒 |
| --- | --- | --- | --- |
| normal direct | 54,050,313 | 2,847,416 / 2.716 | 37.209 / 1.522 / 46.759 |
| normal readback | 136,461,405 | 7,322,828 / 6.984 | 74.948 / 3.064 / 101.861 |
| extraction mismatch | 54,049,506 | 2,854,456 / 2.722 | 35.419 / 1.397 / 45.179 |

`136.5 MB` 以十进制表示有依据；约 `7 GiB` 是 readback fresh-process 的整个进程高水位。readback 保留 W010 与独立 semantic result 的完整输入链和 W006 readback，不是只有 channel/FIN 草稿的占用。

1399 条约 10s 的原始资源采样已逐条重算，所有 PID 的采样最大值与 summary 一致，最大共享 cgroup 采样为 12,299,743,232 B。3.10 全矩阵采样 RSS 高点 9,257,804 KiB（约 8.83 GiB），3.12 为 6,248,624 KiB；两安装 smoke 的采样高点分别为 9,119,696 与 6,927,912 KiB。长进程采样与 fresh-process `ru_maxrss` 的范围不同，不能用约 7 GiB 覆盖所有 W011 执行方式，也不能把离散采样写成精确峰值。原 observer 晚于 launcher 约 28 秒，历史 cgroup `memory.peak` 不能归因本次。

这些数据充分支持“有限 toy 样本成本很高、需保留明确资源限制”的陈述，不能证明最大输入、多片、多器件、并发或生产可用上界。是否需要后续优化由 PM 规划；本次没有发现记录不实或既定工程门未完成的阻塞问题。
