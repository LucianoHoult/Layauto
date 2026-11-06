# W010 工程预检（非最终 A8）

执行者 `/root/engineering_preflight`，2026-11-05；只负责环境/验证脚本与证据，不参与产品设计或实现。

起始产品、测试与配置从 `9758a157115cc22d91ce095ac2002209b9f210d3` 的 Git 对象冻结，未读取随后变更的产品文件。`baseline-source.tar.gz` 和 `baseline-manifest.json` 保留原始子集快照；`baseline-corrected-source.tar.gz` / `baseline-corrected-manifest.json` 补入原 W006 测试所需的 `docs/tasks/W003/examples/records.json`。两份均可按相对路径重建。

初轮 3.10 baseline 在冻结起始快照执行；在缺少该文档时，`test_f1_request_independently_matches_accepted_sample` 已失败。该失败是本预检快照遗漏测试依赖，未修改产品或既有测试以解决。补齐来自同一起始 Git 对象的文档后，定向复测 `1 passed`；原失败另在原始未补文档快照中定向重现，见 `baseline-harness-before310.{json,txt}`，明确为 FileNotFoundError；原失败材料保留，不能把它写作“1149 项基线全通过”。该文档仅供测试的独立样张比较，安装 smoke 不将其作为 runtime 输入。

为给最终冻结版本的双解释器 1464 项矩阵释放资源，根执行者明确授权精确停止该重复预检。停止前核对 wrapper/pytest 的 PID 与完整 argv，只向本预检 wrapper 发 SIGTERM、pytest 子进程发 SIGINT。原输出保留于 `baseline-pytest-310.partial.txt`，实际汇总 **992 passed、1 failed、KeyboardInterrupt，950.02 秒**；不能声称原 1149 项全通过。其后原 wrapper 预定的 3.10 typing / 3.12 全量步骤未执行；源码输入仍由起始快照和补齐文档的 correction 身份分别保存。

3.10.22 / 3.12.14 的开发环境及 .[dev,gds] 已准备；环境/版本及实际 pip check 输出随附。3.12 strict mypy 在起始冻结快照通过，44 source files；完整双版本最终回归、typing、新包及干净安装仍需对最终产品另行执行。

并行 3.12 安装首次经历代理断开，Pillow 传输在 1.0/7.1MB 停止，pip 以 SHA 不符拒绝安装；原日志 `install-dev312.txt` 保留。正常 `--no-cache-dir` 重试成功，未关闭 hash/TLS 校验、改变代理或改依赖要求。临时环境/cache 不随证据提交；路径仅用于说明实际执行位置，不包含凭据。
