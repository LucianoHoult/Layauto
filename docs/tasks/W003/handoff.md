# W003 接收与后续实施入口

本附件交 PM 核对本地 synthetic 样本；阶段和验收结论仍由 PM 在 [W003](../W003-m1-fixture-contracts.md) 维护。当前产品 runtime 未实现，本包不授权进入下一实现任务。

PM 在执行期间新增了完成后的人工核验安排。用户确认尚未执行：应以同一冻结版本覆盖正常例与 `failures/cases.json` 全部22例，逐项记录正确性/使用预期的已确认、需修改、未决；独立技术 review 不能替代用户这一步。实际 parser 上传/目标机验证另待后续明确实现包，不上传本包辅助当产品 parser。

## 要求到产物

| W003 要求 | 具体入口 | 接收方法 |
| --- | --- | --- |
| source geometry/semantic/target | [fixture](../../../tests/fixtures/w003_m1/README.md) 的 source.gds/source.cdl/target.cdl、spec.json | 对每个 drawn shape/tick、cell、pin order、terminal/model/全参数核对；target 只在语义上等同 |
| 四种 query capability 与同源 | query/raw、query/header.json、query/normalized | raw lexeme/单位/坐标顺序/count/terminator、hash/closure 到 normalized 逐项比；synthetic 不标 matched/live |
| tech/site/policy/limitation | tech.json、site_config.yaml、export_policy.json、validation_policy.json、limitations.json | registry 唯一解析；toy 完整物理定义与全部适用规则；site 不含设计事实、不放宽 mandatory |
| 独立正确性 | 手写 spec/oracle、README 图和逐 crossing/terminal/rule 表、独立核对辅助 | source GDS 独立 readback，手算 5/7、body/连通/FIN及frame不变；generator 的 regen-clean 单列，不作唯一 oracle |
| 共享记录/输出 | [contracts](contracts.md)、[schema](examples/schema.json)、[records](examples/records.json)、fixture expected/ | owner、typed refs、exact encoding、empty chain、Manifest 实际样张 byte hash 与语义比较分开 |
| 报告/失败 | [人读报告](examples/report.expected.md)、[机器报告](examples/report.expected.json)、[失败样张](examples/failures.json)、fixture failures/ | required fail/error/report failure reject；pre-context、sealed、freeze、Stage6/terminal 分开，所有产品状态为预期 |

## 定向 legacy 取用

本轮源材料从当前基线只读，不修改 archive、运行旧 generator 或引入 legacy import。来源是 [W002 E1](../W002-first-input-admission.md#e1-已有输入来源与可取用材料) 已审范围，以下只记录本包实际采取的方式。

| 旧材料 | 保留的启发 | 替换/拒绝的部分 |
| --- | --- | --- |
| gen_buffer_layout.py 的 generate_calibre_ixref/nxref/net_names/device_info/net_shapes | instance/net 四种 capability 分文件、显式 record count/terminator、numeric lexeme 的组织 | 另选显式 `w003` synthetic dialect/version；不用旧名字假装 Calibre 标准，不复制默认单位/模型/swap/未trim bbox，重建 source/closure/hash |
| generate_cdl、矩形序列化思路 | 小 inverter、D G S B 和文本保真测试组织 | 显式 TOY_N/TOY_P 全参数/轴；保持 top 身份，单位 exact；不用旧 float/round、FIN参数命名top或未知层忽略逻辑 |
| generate_all_fixtures、旧 target GDS/JSON | 只作反面依据 | 不调用、不整体迁移；其按目标参数重建 FIN/frame/rails 不适合作 fixed-frame ECO golden |
| test_calibre_query.py | 正常 raw、缺输出、count/terminator/格式漂移和 mocked failure 的分层 | 本包只是样本辅助；真实 runner/正式 parser 首交另测；mock 不证明 live acquisition |
| test_dummy_roundtrip.py | 输入→解析→输出→核对的组合验证组织 | 不保留 convenience JSON truth、FIN remove、edit-stream replay 与旧状态流断言 |

这里没有逐行迁移 legacy runtime 代码，因此不声称旧实现 parity 已验证；复用的是已审格式观察与测试场景，新的输入正确性以手写 oracle/独立 reader 为依据。

## 下一实现任务必须同批验收

以下来自 W002 E7/R4 与架构，不是本轮已完成的测试：

1. 真实 Stage 1 文件链、strict safe-load/codec/runtime validation、raw-normalized binding；至少缺 header/closure/terminator/单位、非矩形/未知 stream key/property、CDL表达式/include/未知参数、多 target 冲突、非单指/非一对一/需要归并的拒绝。
2. Stage 2 完整 baseline 与 immutable context/components。Initialize race、nested alias mutation、lifecycle/operator failure、create/seal/close/finalize 的 phase/revision/mode guards、same key same/different digest、响应丢失重放、no_change state-head CAS。
3. Semantic/extraction-aware equality 与全单元 mandatory rules：count正确但spacing/enclosure/body/连通错误必须失败；缺 predicate/context、indeterminate/error 不得通过。Annotation 不增删物理边，多 fragment、via qualification、cut 与 gate S/D separation 同批验证。
4. Stage 6 GDS/CDL/JSON independent readback、Manifest 实际 bytes、输出不可表示/越界/缺core、snapshot digest 不变、freeze/check/report/terminal/unexpected failure/interrupt 等错误路径；人机报告不能仅统计 edit ops。
5. 项目 Python ≥3.10；先在现有指定 venv 检查，未来包选择并执行 strict typing、wheel build、干净安装与支持解释器检查。W002 建议 mypy strict、Python 3.10/3.11 初始矩阵，尚未变成已实现 CI 或提高最低版本。本包无需安装 type/build 工具来测试不存在的 runtime。

上述实现不由本包 generator 或示例校验脚本代替。独立 reviewer 与 PM 接收具体 toy spec/profile/oracle 后，才按新授权推进。

## 真实缺项与 PM 决策边界

| 缺项 | 当前事实与影响 |
| --- | --- |
| 生产反馈权限 | 只知可向内上传代码、向外描述数值脱敏格式；raw/日志/hash/结果/通过失败摘要都未获准外传，不据格式重建声称 matched |
| 平台和离线依赖 | OS/CPU/Calibre build、Python版本、wheel可用性、是否能携带测试样本均未知；未部署 runner/VM/EDA |
| 真实 profile 与 evidence | 真实同源 design/model/query/物理operator/规则/closure 仍缺 W002 G1–G4，阻塞真实 M2；本系统 live acquisition G5 最迟 M3 |
| 真实验收回执 | 由谁在内网 review、PM 可据哪种回执验收未确认；不能用 synthetic review 降低真实门 |
| 样张格式状态 | 本包选定的 toy 与审查 wire schema 是本地 fixture 合同；实际生产 CDL/query syntax、关键对外wire/验收变化需带具体样例交 PM |

现有信息足以制作本地 synthetic dialect，不存在必须现在向用户索取生产材料的语法阻塞。未来发现具体 ambiguity，再以不含生产数值/标识的最小语法样例澄清；不得扩大回传权限。
