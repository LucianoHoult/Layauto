# W011 双解释器资源 gate 独立静态 review

Reviewer：`/root/code_review`，补充静态检查：`/root/code_review/boundary_review`。2026-11-09。只审执行 harness，不修改产品/正式测试，不运行重型或小型 probe；工程自己的小样证据另作审计。

**结论：当前简单 gate 可用于本次已冻结测试的双解释器矩阵，剩余 harness 必须项 0。** 这不代表矩阵/A8 已通过，不是任意未来输入的内存上界证明。被审源码为 `/workspace/work/w011-engineering/prepare_final_gate.py`（SHA-256 `66456ce9659d2ad2481ab0f8b4309054caf19a41057f1a86b01531f3dd914794`）和 `w011_resource_gate.py`（SHA-256 `1c78c2066736f0f56d80f3353da133a1d23407b0675a0a8f5e471b1337469d70`）。计划归档到 W011 的 `prepare_final.py`、`w011_resource_gate.py`；实际归档字节/最终执行事件仍须在 A8 核对。

## 原发现与修正（保留）

**HG-01：首次等待失败后可能无锁放行后续 W011（必须修正，已关闭）。** 最初候选先把 `os.open` 返回值赋给全局 `_LOCK_FD`，然后写 WAIT、调用 `flock`；后续 setup 用 `_LOCK_FD is None` 判断是否需要锁。若 WAIT/flock 抛出异常且 pytest 继续下一个测试，非空 FD 并不代表已获锁，会直接 yield 进入后续 fixture。该项由静态控制流发现，没有把未执行的故障注入称为实跑。

修后先使用 local descriptor，WAIT/flock 出错时关闭该 descriptor 并原样抛出，只有 flock 成功后才发布 `_LOCK_FD`。因此非空全局 FD 才代表已获锁。ACQUIRED 日志若失败会使测试/工程失败，但锁已实际持有，不会放行未加锁的重对象计算。sessionfinish 也仅对确实持锁状态记事件。主 reviewer 与补充 reviewer 均逐分支确认原缺口关闭。

## fixture 与完整测试覆盖

当前三个 `test_w011_*` 模块的重对象构建位于 module fixtures 或测试 body，没有在 collection/import 时执行。实际安装 pytest 的 `_pytest.runner.py::pytest_runtest_setup` 是普通 hook，调用 `_setupstate.setup(item)` 才建立 fixtures；gate 的 `hookwrapper=True, tryfirst=True` 在 yield 前获得锁。因此首个 W011 的 session/module/function fixture setup、body、teardown 都处于锁内，不能只保护 test body 而漏掉 captures fixture 的完整 wire。

raw descriptor 不在 sessionfinish 解锁/关闭，持有到 pytest 进程退出，由 OS 释放，避免 sessionfinish 后仍保留的大对象与另一个 W011 进程重叠。FD 使用 Python `os.open` 的 non-inheritable 默认；当前 W011 没有 fork-only 子进程。正常退出、中断或 kill 都不会留跨进程永久锁；中断等待的进程未取得锁时，原发现修正保证不伪报持锁。

插件只等待并记录事件，不实现 collection 修改、skip、reorder、fixture 替换或结果覆盖。runner 的完整命令仍为两解释器各自运行 `tests/unit tests/contracts`，保留全部 1605 node IDs/原 1465 包含校验和完整 passed 数量门槛，不把门控拆分成少跑用例。两个 worker 必须显式提供 gate；通过 `-p w011_resource_gate` 加载保存字节的插件副本，shared lock 是同一 fresh work 目录下的绝对路径，日志按解释器分开，PYTHONPATH/完整命令与环境进入 receipt。runtime 的冻结目录解析和文件哈希校验不变。

## 日志、调度边界与限制

WAIT/ACQUIRED/SESSION_FINISH_LOCK_RETAINED 记录 PID、首个 W011 node、插件 hash、锁路径/device/inode 和观察 UTC。parent 仅在 `subprocess.run` 完成、命令 receipt 已写后追加 RELEASED；它准确标为 parent 观察退出时间，可能晚于另一进程 ACQUIRED，不冒称内核精确解锁时刻。runner 在双矩阵结束后核对事件全集、首 node、插件来源/复制 hash 与同一 inode，才继续 build、两个顺序 clean install/smoke；资源测量另按执行调度后置。

工程的小样 `gate-demo01` 原 receipt 已审：两解释器各跑一个专用测试，session/module fixture setup、body、teardown 中另开 FD 尝试非阻塞独占锁均不能成功；相同 inode，第二次 ACQUIRED 在第一进程 session finish 后，FD non-inheritable。该小样使用上述最终插件 hash。它只证明执行插件样例，不替代任一正式 1605 回归；本 reviewer 没有重复运行该小样。计划完整归档位置为 `preflight/gate-demo01/`。

使用条件明确：旧的未接 gate 完整矩阵必须先结束；完整包 smoke、资源 probe 和其它未参与锁协议的重进程不得与新矩阵重叠。gate 只约束参与的两个 pytest 进程，不能给外部进程加锁。16 GiB cgroup 下采用“一个 W011 重阶段 + 另一解释器约 1–1.7 GiB 的旧阶段”的依据是有限实际观察，约 7 GiB W011 峰值也不是最坏上限；真实最终运行仍须保留失败、资源事件与退出状态，不能仅因 gate 存在就宣称容量保证或 A8 通过。

实际预归档已核对：被审 [runner](../preflight/prepare_final_gate.py)、[plugin](../preflight/w011_resource_gate.py) 与上述 SHA-256 一致；工程小样的[receipt](../preflight/gate-demo01/receipt.json)、源码与原 JSONL/stdout/stderr 已完整保存。新旧脚本身份及调度原因见 [gate-harness-preparation.json](../preflight/gate-harness-preparation.json)。这些预归档不改变仍在运行的旧矩阵源码；正式新运行的根路径映射与结果在 A8 再核。
