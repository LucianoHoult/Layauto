# W014 工程工具

本目录从 W013 工程工具复制并适配，旧工具和历史证据不改写。准备阶段的
Python 3.10 语法、CLI、源身份枚举和 readiness 只表示工具就绪，不表示产品
通过；最终 runner 在创建矩阵输出前拒绝未集成的 API 断言。实际运行材料在
[verification](../verification/)：双全量、typing、build及双clean安装源码外三路
smoke均已通过，最终整体结果见[实际回执](../verification/receipt.json)。

环境为 `/workspace/work/w014-env/dev310/bin/python`（3.10.22）和
`/workspace/work/w014-env/dev312/bin/python`（3.12.14），分别安装 `.[dev,all]`。
两者 `pip check` 通过；实际解释器、包路径及依赖版本由最终
`verification/environment-310.stdout.txt`和`environment-312.stdout.txt`保存。
早期环境preflight的临时记录不代替最终环境证据，也不按旧session版本采信。

`source_identity.py` 使用当前所有 tracked/untracked 产品、测试、配置、fixture、
README 及 W006 所需固定记录样本的路径→字节 hash，涵盖未提交修改；不以 HEAD
或测试数量替代源身份。`run_check.py` 为开发命令保存源身份前后核对和原始输出。

产品冻结及 direct/readback/mismatch 早期资源检查后，保存引用原测量的资源回执：
`status: passed`、实际 `source_id`、三路 `cases`。该回执是资源证据身份门，
不是额外用户审批；显著资源放大按 W014 要求先交 PM。默认矩阵串行，只有实测资源
足够且回执含 `parallel_matrices_safe: true` 时才并行。

```sh
/workspace/work/w014-env/dev312/bin/python -B \
  docs/tasks/W014/verification-tools/source_identity.py --root /workspace/Layauto \
  --out <new-source-identity.json>

/workspace/work/w014-env/dev312/bin/python -B \
  docs/tasks/W014/verification-tools/prepare_final.py \
  --root /workspace/Layauto --out <new-evidence-dir> --work <new-work-dir> \
  --smoke docs/tasks/W014/verification-tools/installed_smoke.py \
  --python310 /workspace/work/w014-env/dev310/bin/python \
  --python312 /workspace/work/w014-env/dev312/bin/python \
  --baseline-collection docs/tasks/W013/verification-r2/collection-312.stdout.txt \
  --baseline-sha256 <baseline-sha256> --expected-tests <current-collected-count> \
  --expected-source-id <frozen-source-id> --resource-clearance <new-clearance.json> \
  --matrix-workers 1
```

Runner 保存唯一新源快照，完成双解释器 collection/全量/strict mypy/pip check、
wheel+sdist 构建、3.10 sdist 与 3.12 wheel 的全新环境安装、源码外 `-I -B`
三路组合 smoke，并核对包与安装后的完整 runtime 字节。包 smoke 在矩阵后串行执行。
输出目录必须新建，失败原始输出保留；变更源、测试、配置后重新冻结最终矩阵。
独立 review 和 PM 对相同源身份可复用这些证据，不复制大 wire 或安装树。

早期资源探针 `run_resource_checkpoint.py` 默认串行执行六个新进程：同环境 W013
三路 reference，再执行 W014 三路。固定 mismatch URI 对两者相同；检查共同捕获
来源和保留的完整 W010 wire hash 相同。probe 只观察公开路径已发生的调用，不添加
额外认证调用，不改认证语义；build/encode/decode 分别记录旧 W010 decode 次数和
neutral W011/W013/body 调用。进程 HWM 在解包统计前固定，报告新增 compact bytes、
总 wire、原输入 bytes、耗时和比例；不写大 wire。

```sh
/workspace/work/w014-env/dev312/bin/python -B \
  docs/tasks/W014/verification-tools/run_resource_checkpoint.py \
  --root /workspace/Layauto --python /workspace/work/w014-env/dev312/bin/python \
  --out <new-resource-evidence-dir>
```

准备期的CLI和stand-in核验不代替产品实跑；实际三路资源、失败修复和最终
源身份采信见[execution](../execution.md)与[resource-review](../resource-review.md)。
单样本测量不构成稳定性能收益承诺；suite不自动替PM作显著放大的判断，也不
将资源串行gate当作单次内存改善。
