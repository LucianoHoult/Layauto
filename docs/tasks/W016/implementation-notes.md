# W016 实施记录

起点/远端准备 HEAD：`efc881d461ce2c87370f6df402ac50ae43c094e8`。
启动 checkout `/workspace/Layauto` 的 `work` 分支，工作区干净；fetch 后创建原任务分支
`codex/w016-single-cell-analysis`，远端 HEAD 与指定起点相同。仅根 AGENTS 适用。

启动时拟实施顺序与文件表（不是已落地清单；资源门中断后的实际范围见下）：

| 范围 | 文件/责任 |
| --- | --- |
| 新合同 | domain/analysis.py 中立 evidence/view；tech/analysis_schema.py 独立封闭 schema |
| 获取/认证 | importers/analysis_reader.py；normalization/analysis_input.py 从实际捕获重parse，固定获取 alias，禁止磁盘续读 |
| source/local | semantic.py、identity.py 抽纯 operand；normalization/analysis.py 组合中立 geometry/channel |
| annotation | domain/analysis_annotation.py、state/analysis_annotation.py 与原 owner 下 pure kernel；旧 DTO guard 不变 |
| body/terminal | 原 derive owner 下 pure kernel；新 wrapper 绑定独立 scope |
| facade/report | analysis.py、reporting/analysis.py；只公开顶层，不公开 receipt 续算 |
| 验证/交付 | tests/support/analysis_inputs.py、tests/unit/test_analysis_*.py、tests/contracts/test_analysis_*.py、typing、README、W016 evidence |

异常：只在所属边界处理 InputError/SchemaError/现有 typed component problem；未知异常和
interrupt 传播。先连通 local 实际文件；新 schema 不复用旧 ParseResult success 或 target。
测试按 A1–A8/T01–T10；开发仅新增及受影响回归，冻结后双 3.10/3.12 全量/typing/build/
源码外双 clean-install smoke。同源旧 DTO/wire/hash parity 不用旧 golden 更新替代。

资源按三 case 串行，分别记录获取/认证/计算/report、HWM、去重 capture/report bytes 和构造次数；
最早可运行立即测，不将旧 build+encode+decode 当新 build+report 对照。
未参与实现的 `/root/w016_review` 独立审查，当前尚无实现通过结论。

## 本轮实际落地与尚缺

实际产品新增：domain/analysis.py、domain/analysis_annotation.py、tech/analysis_schema.py、
importers/analysis_reader.py、normalization/analysis_input.py、state/analysis_annotation.py、
reporting/__init__.py、reporting/analysis.py。
实际旧owner提取：normalization/semantic.py、identity.py、annotation/net_regions.py、
domain/net_annotation.py、derive/net_annotation.py、body_relations.py、state/annotation.py。
新增正式测试：tests/unit/test_analysis_foundation.py；临时文件迁移helper目前在该测试文件内。

尚未落地：normalization/analysis.py、顶层analysis.py、完整analysis result/facet/status、
manual schema、外部获取/认证wrapper、terminal operands与新DTO、最终README入口及typing清单。
body helper仅拆出，尚无新调用链。完整执行状态见resource-checkpoint.md；不把计划文件表当产物。
