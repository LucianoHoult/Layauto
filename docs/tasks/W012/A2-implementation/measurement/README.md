# A2 同条件完整筛选工具

本轮测量工具由 `/root/measurement` 在独立 worktree 编写，未参与独立 review。不导入 runtime 或正式产品测试，不改 P1/A1/A2 原工具和输出。首次轻量自检已重建原固定路径 mismatch 35 项/五 overlay，原 35 项 hashes、完整 bytes 均核实；原正常 fixture 不变。首次自检的 raw stdout/stderr/result 保留，见 `selfcheck-attempt01/`。该次由执行工具直接运行，未另存精确 UTC command receipt；后续命令使用下述统一 wrapper 记录真实起止及退出。

- `common.py` 从 A1 原 preflight 的 35 项明确清单重建固定 mismatch，不重新生成内容；额外拒绝已有不同 bytes 或额外文件。正常输入固定 `/workspace/Layauto/tests/fixtures/w003_m1/site_config.yaml`，mismatch 固定 `/workspace/w012-inputs/extraction-mismatch/site_config.yaml`。
- `prepare.py` 从精确 A1 验收 `2489b4609ae97d8211bf450d55cac9392492ac71` 在本机创建 detached baseline，263 项同时对 A1 manifest 和 Git tree 核验。固定两侧实际源码/正式测试/配置，新增测试动态加入，完整 snapshot 与 hashes 保存。只允许两 runtime owner 和直接必要正式测试差异，原文件不删除。
- `probe.py` 沿用原 A1 `check_result`（自检 AST 相同）及公开完整路径/阶段、RunRequest、roots、GC、原 cache 设置。运行时导入树与固定输入路径分离，先确认实际包路径。无 hook/profile/额外 encode，保留全部上游对象、原 Result、wire 及 restored；原字段全值相等覆盖全部来源/局部图/T05/body/语义。记录固定峰值后，再核 31 捕获原 bytes、所有 completed source refs、source/target 分开、query seed 来源和 stored typed refs；完整 wire IO、hash/bytecmp 均在计时与峰值记录之后。
- `run.py` 每条 fresh process，按 rep→case→before/after 串行交替。`--reps 1` 为六条有限筛选；支持继续时同一已冻结版本用 `--reps 2 3` 补十二条，可复用本轮 r1。每次启动记录、原 stdout/stderr/exit/2秒 RSS 采样独立保存，完整 wire 与 before-r1 逐块实比，after 同次功能/来源/refs/GC/URI 逐项匹配 before。已有目标样本、wire 或 receipt 一律拒绝覆写/静默恢复。
- `analyze.py` 保留各次真实阶段、all-build/W011-build/encode/decode/总耗时及整进程峰值，对每次先求阶段总和再取中位，披露各阶段增减，wire 减幅为 0；不自行设硬门或判验收。失败 command 独立列出。若发生失败，原目录完整保留，在新 attempt 目录明确重跑，不移动原证据冒充同次。

冻结必须在 root 集成实际候选及正式测试后执行。示例从 root checkout 调用（路径均可显式设置；不以本说明宣称已跑）：

```sh
/workspace/.venvs/layauto/bin/python -B docs/tasks/W012/A2-implementation/measurement/selfcheck.py --before-root /workspace/work/w012-a2/before --output docs/tasks/W012/A2-implementation/measurement/selfcheck-final/result.json
/workspace/.venvs/layauto/bin/python -B docs/tasks/W012/A2-implementation/measurement/prepare.py --before-root /workspace/work/w012-a2/before --after-root /workspace/Layauto --out docs/tasks/W012/A2-implementation/freeze
/workspace/.venvs/layauto/bin/python -B docs/tasks/W012/A2-implementation/measurement/run.py --freeze docs/tasks/W012/A2-implementation/freeze/freeze.json --out docs/tasks/W012/A2-implementation/performance --wires /workspace/work/w012-a2/wires --reps 1
/workspace/.venvs/layauto/bin/python -B docs/tasks/W012/A2-implementation/measurement/analyze.py --samples docs/tasks/W012/A2-implementation/performance --reps 1 --output docs/tasks/W012/A2-implementation/screen-summary.json
```

完整重型筛选尚未由工具设计者启动。解释器固定现有 `/workspace/.venvs/layauto/bin/python` 3.12.14；没有安装依赖。`environment()` 比较 Python、包版本、platform 和静态 cgroup 限制，不把波动的当前占用作为固定条件。最终是否继续工程矩阵/补 r2-r3 由完整筛选证据决定，不能从有限静态计数外推收益。
