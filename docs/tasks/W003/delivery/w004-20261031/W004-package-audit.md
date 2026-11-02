# W004 最终封包独立身份审计

Reviewer：`independent_review`，2026-10-31；专项archive核对由未参与实现的`raw_review`执行。结论：**封包身份、补丁重建及review原文保全均通过，无交付阻塞。** 本次只读原仓库/封包，在reviewer独立目录重建基线并应用patch；未修改repo、既有封包或重新运行实现审阅。

- 基准/当前HEAD均为`9f6735dcede8e8b2135f89ff10f079a752ed758b`，branch为`codex/w004-task-convergence`。工作区未提交，index无staged差异且审计前后bytes不变。实际tracked diff加完整untracked文件集恰好等于patch的149路径；未提交交回表述正确。
- 以`git archive <base>`在`reviewer/package-reconstruction/`独立还原，再执行`git apply --check`和实际`git apply`，均exit 0。最终68修改、67新增、14移除，共149路径与identity及snapshot一致；155个snapshot文件全部匹配重建bytes，移除文件实际不存在。
- r3受审145文件中144文件完全未变；唯一修改W004仅为交付身份/限制及review原文和导航。新增8份review附件与各reviewer原稿逐字节相等。封包snapshot另补`docs/README.md`、`pyproject.toml`两份未变基线上下文，非新增实现。受审fixture/helper/图/报告未变。
- 独立专项校验manifest的8,988条实际bytes全部相符；delivery共8,989文件，唯一未列为manifest自身。archive的`W004-delivery/`下8,989文件与delivery逐字节一致；遗漏、多余、错误hash、重复或不安全条目均0。
- 指定`/codex/.../output`展示目录不可创建的限制及实际封包路径已经写入最终W004，没有假链接或上传/Git发布声称。此审计不重新证明环境错误原因，只核对交付位置与所披露状态一致。

| 对象 | SHA-256 |
| --- | --- |
| delivery/identity.json | `f24e1aa544f9eac60de2cf24e526b2e4eddd2a3ae25854c1b6084d08f67f9116` |
| delivery/full.patch | `78cadcd685f0b794166c0bb02da1fc9d6fb535dc7ac54a1c8418d937b9d172d4` |
| delivery/SHA256SUMS.json | `1a92c560ec4433a8ef18579b742f87a3f00875a519add27723ec17be0d5c9e25` |
| artifacts/W004-delivery.tar.gz | `3cd7bc497391d76656e0327b415ec5c77ce26aa827423dc2b054654977173b39` |

Archive大小10,570,253 bytes。命令、返回值及详细结果保存于`/workspace/work/w004/reviewer/package_audit.py`、`package-audit-result.json`和`raw/package-audit.json`。本审计为封包完成后的旁证，不在被审archive内部，不产生自指hash要求。原r3结论及PM/真实工具边界不变。
