# W013 最终工程工具准备

这些是 W013 新副本，未修改旧 A1 工具或报告。环境路径和原安装证据见
[environment/README-handoff.md](../environment/README-handoff.md)。本阶段仅准备工程条件，
**尚未运行 W013 产品矩阵或安装 smoke**。

`prepare_final.py` 保留完整源快照、双解释器 collection/full pytest/strict mypy/pip check、
wheel+sdist 构建、两次全新安装、源码外 `-I -B` 组合 smoke 与包/安装源字节核验。
它不硬编码 runtime 文件数、旧测试数或“无 net 字段”假设；显式检查解释器为3.10和3.12。
tracked、staged、unstaged、untracked 的实际源字节均由完整文件映射覆盖，不以 HEAD 代替。

`installed_smoke.py` 当前是 **未就绪骨架**：W005/W006→W010、14/8/6本地范围、完整来源、
外置 body 和 attempt/checkpoint/unsealed/无 terminal 检查已准备，但实际 W013
`AnnotationDraft/Result` 公开 API 及独立 coverage/component 断言须由 root 集成后完成。
`W013_SMOKE_READY=False` 和未实现 hook 会拒绝成功，不能以本文件冒充已通过的 smoke。
它不实例化 W011，也不解析 oracle/spec/expected。临时 mismatch URI 仅作安装正确性测试，
不是固定 URI 性能对照。

执行顺序（由 root 在产品和工具冻结后完成）：

1. 完成 smoke 的 W013 public build/codec/独立预期断言，并删除其准备阶段限制；核新工具身份。
2. 用 `source_identity.py --root /workspace/Layauto --out <new-source-identity.json>` 保存实际
   源/测试/config/全部fixture与必要样本的路径和字节映射。`source_id` 是排序相对路径→文件
   SHA-256 映射的 canonical JSON SHA-256；绝对路径和 Git 元数据不参与此值。
3. 资源节点通过后提供新小回执：`status: "passed"`、同一 `source_id`、
   `cases: ["normal-direct", "normal-readback", "extraction-mismatch"]`。原测量及 review
   证据保留原 owner 并在此回执中引用；该回执只作证据身份门，不是用户审批或性能数据。
   若同机实测支持两矩阵并行，可明确附 `parallel_matrices_safe: true`。
4. 指定已验收 A1 baseline collection 的实际文件与 SHA-256、当前新 collection 的期望数量，
   调用最终 runner。默认串行；`--matrix-workers 2` 需上述并行调度字段。两个全量结束后才运行
   build 和串行双安装 smoke，避免包装烟测与全量叠加峰值。

```sh
/workspace/work/w013-env/dev312/bin/python -B \
  docs/tasks/W013/verification-tools/prepare_final.py \
  --root /workspace/Layauto --out <new-evidence-dir> --work <new-work-dir> \
  --smoke docs/tasks/W013/verification-tools/installed_smoke.py \
  --python310 /workspace/work/w013-env/dev310/bin/python \
  --python312 /workspace/work/w013-env/dev312/bin/python \
  --baseline-collection docs/tasks/W012/A1/verification-r2/collection-312.stdout.txt \
  --baseline-sha256 <baseline-file-sha256> --expected-tests <new-collected-count> \
  --expected-source-id <frozen-source-id> --resource-clearance <new-clearance.json> \
  --matrix-workers 1
```

输出/工作目录必须新建，原失败不能覆盖。每条命令保留原输出、argv/cwd/解释器与依赖、
环境覆盖和 hash；proxy/CA 原样继承。运行结束重核源路径、完整字节、工具、baseline、
clearance 身份。源码/测试/config 再变时，重新冻结并执行要求的最终矩阵。

准备阶段轻量验证见 [engineering-preparation](../engineering-preparation/)：双解释器检查所有
脚本3.10语法、CLI帮助、完整source-id、当前1656条baseline、smoke未就绪拒绝及资源门拒绝。
这些检查没有运行产品组合、typing、构建安装或最终矩阵。
