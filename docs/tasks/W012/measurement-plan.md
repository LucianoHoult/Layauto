# PP1 冻结与测量计划

本计划在重型组合前冻结。授权仅调查，不改产品、正式测试、fixture、架构或 current-work。

- 恢复远端 W012 `f3698b7ffda3b0737a2eb61ca85dbf3b40bc89fe`，含已验收 main `0a3326aa363477724465886cd05874d0997fba3e`。262 源和 100 runtime 与 W011 冻结 `e89bdaa6a091f56cfaf7862dced7232d34e22514` 相同；原 W011 双1605、typing54、构建/双安装按此身份采信，本次不重新运行。
- 解释器固定 `/workspace/.venvs/layauto/bin/python`（3.12.14）；无安装。Linux/cgroup 16GiB/4CPU。启动前原工作区干净，无其他重型进程；环境、源及输入逐项哈希另存 `preflight.json`，工具单独 `tool-identity.json`，轻量自检 `selfcheck.json`。
- 正常输入固定 `/workspace/Layauto/tests/fixtures/w003_m1/site_config.yaml`，直接读取与 caller-read readback 都采用原站点声明的 normalized cache（仍从 raw 验证）。不修改文件/URI、不去cache。mismatch 固定 `/workspace/w012-inputs/extraction-mismatch/site_config.yaml`；从原输入复制（不复制 expected/oracle/spec/failures/输出），再逐字节覆盖原 extraction_mismatch 的 source.gds、query/header.json、query/raw/device_info_Q17.txt、query/normalized/device_regions.yaml、body/context.json 五项。复制清单/来源哈希持久保存，可在未来同路径重建；不使用临时随机 URI。
- readback 的 RunRequest 固定 proposed_run_id=`w012-investigation-run`、lineage_id=`w012-investigation-lineage`、idempotency_key=`create-w012`、site_path=上述正常绝对路径；各 selections 为原默认空 tuple。每个进程新建 repository，无热缓存。正常 direct/mismatch 无 RunRequest。
- fresh process 串行 baseline direct→readback→mismatch，然后相同顺序 profile。获取前显式 gc.collect 一次，其后默认自动GC（不手工收集）。始终保留 parsed/geometry/effective/local/result；readback 额外保留 repository/ready/checkpoint/parse/tool/audits/attempt。完整 encode 保留原对象，完整 decode 同时保留 wire 和原对象；无流式释放或只测中立draft。计时只包实际阶段调用，最终 hash/断言/诊断不计入阶段时间。
- baseline 不装 hook/cProfile/tracemalloc；整进程 ru_maxrss 包含 import、上游全部构造、wire及恢复对象，不作函数差值。外部每2秒取 /proc VmRSS/HWM/cgroup，仅为离散样本，不能代替进程峰值。阶段包含 W005或W006获取/caller reads、W008 adapter/build、W009、W010、W011、完整encode/decode。
- profile 使用每阶段 cProfile，记录函数原始 exclusive/cumulative/calls。encode/decode wrapper 只读现有参数类型、返回长度；domain._wire wrapper 只累计已出现bytes的长度，绝不额外encode/digest/repr/asdict/deepcopy。hook改变profile开销，不能用其时间作为baseline。跨层时间有包含关系，不把cumulative相加。
- profile 后才遍历对象图：按id去重及按bytes内容分组，另计算按所有引用路径展开的bytes总量。区分共享引用、同内容独立对象、wire按值展开。shallow size不是RSS（不含实例字典、allocator/native）；id只作进程内诊断。wire长度由已有返回值取得，hex占比由真实 _wire 事件取得，不重新编码大对象。
- 三路径断言均包含：完整36项FIN evaluation/全部crossing与手写矩形见证、正常5/7，mismatch4/7且恰一项 measured4/source5，touch FIN保留；原40图形/18FIN、8edge/6component、T05 pass、body/completed来源完整、same-capture source语义、完整公开DTO roundtrip相等。原对象local/body identity保持；readback attempt/checkpoint保持unsealed且无terminal。完整roundtrip比较同时覆盖恢复后来源/局部图/T05/body。partial/未知等广泛负例沿用同源W011，不宣称三条固定输入覆盖这些攻击路径。
- 所有命令保留 argv/cwd/UTC/exit/stdout/stderr/hash，失败不删。不提交巨大wire本体，仅记录实际bytes/hash。每case一次有限样本，无资源上界/生产保证；W011原URI、RunRequest、环境与本轮不完全相同，其数字仅为历史参照。未来前后对照必须原样复用本计划，目标待实测收敛。
