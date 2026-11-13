# W013 双解释器开发环境准备

2026-11-12，环境准备者 `/root/validation_inventory/dual_env_setup`。
这只是工程运行条件，不是 W013 产品、资源检查点或最终矩阵通过。

已就绪：

- `/workspace/work/w013-env/dev310/bin/python`：CPython 3.10.22，由 uv 官方托管发行下载；
- `/workspace/work/w013-env/dev312/bin/python`：CPython 3.12.14，复用本环境已有可信 runtime。

依赖按本目录两份 requirements 安装；核心库实际 import、双 `pip check` 通过。
完整依赖版本见 `evidence/freeze310.stdout.txt` / `freeze312.stdout.txt`，解释器实际路径、
binary SHA-256 和全部包元数据见 `evidence/identity310.stdout.txt` / `identity312.stdout.txt`。
两开发环境均未安装 layauto 产品，后续开发或冻结快照 cwd 提供实际源码。

`receipt.json` 汇总身份与每条原始命令回执，`manifest.json` 列本目录材料 hash。
`run_command.py` 保留每次 argv/cwd/环境覆盖、原 stdout/stderr/hash、时间/返回码，拒绝覆盖
已有 attempt。原始 proxy/CA 保持，TLS 验证开启；无需提权、未改 HOME 或旧开发环境。
初始只读 home UV cache inventory 失败保留于 `evidence/initial-cache-observation.txt`；
之后 UV install/cache/bin、pip cache 与 matplotlib config 全在 `/workspace/work/w013-env`。

本次实跑：解释器/依赖准备、实际 imports、pip check/freeze、requirement 和回执 hash 核验。
按身份引用：仅旧 A1 requirements 的版本选择，没有采信它的矩阵作为 W013 检查。
未覆盖：W013 产品组合、三路新增成本、最终双全量/typing/build/双干净安装 smoke。
触发补跑：解释器/依赖/环境位置改变或新产品冻结；环境准备不能代替最终矩阵。

最终矩阵只在 root 给出冻结身份并通过资源节点后运行，不能在此准备阶段启动。
