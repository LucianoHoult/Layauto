# W011 owner 拒绝层级测试增量 review

Reviewer：`/root/code_review`，2026-11-09；只做合同/补丁审查及轻量实际读取，不修改产品、正式测试或 fixture，不运行重型 W011 probe。

旧矩阵第二个失败为 `test_consumed_operator_changes_fail_at_located_component_boundary[physical-effective_fin_operator-foreign]`。原 3.10 定向输出 `1 failed in 0.42s` 表明：`build→build_local→build_effective→w007_cases.read` 的 success-only helper 在 `InvalidSchema: expected 'identity'` 上断言失败，尚未得到可交 W011 的成功 W010 receipt。

该行为符合既有入口合同。`tech/schema.py` 将 `physical.fin_count_profile.effective_fin_operator` 定义为 literal `identity`；W005 `validate_document` 将 SchemaError 转成带来源位置的 `InputError('config', ...)`，公共 `read_inputs` 返回 error 并保留已经完成的 evidence 和已读取来源。W011 只接受成功 W010 receipt，不应为了让非法 schema 抵达 W011 而放宽 reader 或绕过认证。

独立 [operator-admission-probe.py](operator-admission-probe.py) 对复制并重绑的四个原 case 实际读取（Python 3.12.14，1.00s，退出 0）：

- `effective_fin_operator='foreign'`：唯一 issue 为 `config/InvalidSchema`、message `expected 'identity'`，来源 `tech/physical.json#/fin_count_profile/effective_fin_operator`；value=None。实际捕获 site、tech 根、drawn、derived、physical 五文件，坏 owner 原 bytes/SHA 与 issue SHA 一致；completed 恰为 config，且其 payload 与实际 site JSON、来源 hash 均一致。
- qualification、derived trim、annotation tolerance 三个 schema 合法变体：读取成功、无 issue，保留九类 completed，可以继续通过完整 W008/W009/W010 到达 W011 的有限 owner 检查。这次轻量 probe 没有将它们的 read success 冒称 W011 已拒绝。

原输出见 [stdout](operator-admission-probe.stdout.txt)/[stderr](operator-admission-probe.stderr.txt)。受测 runtime 与 `8917d38` 完全相同，输入只改临时副本。

已审拟补修保留四个原参数 ID：literal-invalid case 显式检查实际 reader 的 typed error、精确 owner field/SHA、五文件捕获 bytes 和 config completed，然后结束该 case；其余三项仍执行完整 W011，保留 status/value/issues/completed 断言并加强 `UnsupportedChannelOperator`、owner URI、field 与 source SHA。没有删除测试、skip、泛化异常捕获或降低 schema 要求，没有修改 runtime、helper、fixture/答案。此修正纠正测试的入口层级假设，不引入新的产品语义。

正式四项定向结果、tests-only 提交及主分支映射待追加；旧矩阵失败必须保留，新冻结后仍需双完整矩阵。当前拟补丁审查无新的产品必须项，A8 仍 pending。

## 已提交补修的独立复核

最终 tests-only 提交为 `1cb7e1bc654c61690427ac22481b985156d9c9e6`，父提交 `05009b8c57b88d4dc051df2711db79cb8fae5346`。实际 Git diff 仅为 `tests/contracts/test_w011_geometry.py` 的 24 行增加，与上文所审拟补丁一致；相对已审 runtime `8917d38d916c914bfa785cb116982f3f299b38de` 的 `layauto_v2` 和 `tests/fixtures` 无差异。四个参数 ID 未改，既有入口约束及其余三项完整 W011 断言均保留。

独立核对定向实跑清单及原输出：Python 3.10.22，原四项一起运行 `4 passed in 182.45s`、exit 0；外层实测 182.6978s，child max RSS 1,181,168 KiB，UTC `2026-11-09T11:51:16.913464+00:00` 至 `11:54:19.611657+00:00`。运行时为父提交 `05009b8` 加唯一测试文件脏改，不能冒记运行时 Git HEAD 已是新提交；该文件实际 SHA-256 `869e833a0e5fbcd77e6fe49a06cf088e0bb84af4e2063690d9b6a6dbda781133` 与最终提交内字节完全相同，输出 SHA-256 `5ddd2fd0cb32c743ec6e418732d9731c8cd1cb243fa34b0eb35312c4044d825a`。

本次增量审查必须项 **0**。未重新运行重型组合，结论依据独立轻量实际 reader 探针、提交差异和原正式四项输出/身份交叉核对。原失败继续保留；主执行分支 cherry-pick 映射、最终冻结和双完整矩阵尚待后续 A8 审查，定向成功不替代最终矩阵。
