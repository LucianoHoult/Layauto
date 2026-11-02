# W004 REQ-01 局部精度修复独立复核

Reviewer：`/root/req01_review`，2026-11-02；未参与本次实现。**REQ-01 已修正并经独立定向复核，剩余必须修正项为 0，可交 PM 接收。** 原 [REQ-01](w004-requirements-review.md#3-finding) 和历史审查结论保留；本结论限于 body helper 精确匹配及对应回归，不代作 PM 验收或 W005 开工决定。

## 受审身份与改动范围

基线为 `06821ef64ac710963dcc947861a374cd0fe9dd6d`。执行者停止写入后，reviewer 核对并在验证前后确认以下工作区文件身份不变：

| 文件 | SHA-256 |
| --- | --- |
| `tests/support/w004_body.py` | `df0fa16c427b5c104f6f4c73b2c62f4b13a41fa37ed91b99e253599efb824e7b` |
| `tests/fixture_support/test_w004_body.py` | `7108d32a4bd0c20345feea48cc6d06f64c94983212da8cec82f734439ae1e504` |

已阅读根规则、原需求复核 finding、W004 对应决定、body/query/support 实际调用、fixture physical/derived 合同及架构 §2.2、§3.3/3.6、§12.5 的精确值与 annotation 边界。实施改动只将 bbox 解码从整数除法改为 `Fraction` 精确值比较，新增一份 fixture helper 回归；原 `BodyTargetRailMismatch` 不变，不引入容差、几何移动、新输入或产品能力。

W004 E5 是执行者提供的事实记录，本次检查其陈述与实际改动一致。正常 fixture、原 29 例清单/答案、合同、原需求复核报告、架构及 `layauto_v2/` 与基线无差异。测试使用 spec/oracle 识别未变对象以隔离 helper 行为，不声称提供另一套独立几何答案。

## 本轮实际验证

环境为 Python `3.12.14`，仅标准库，无依赖安装。Reviewer 实际执行：

```sh
python -B -m unittest discover -s tests/fixture_support -v
```

3 个测试方法全部通过；其中原失败案例方法包含 C22 及 7 个 body 子例。Reviewer 另外以 `git show 06821ef:tests/support/w004_body.py` 取出旧函数，用独立脚本在仓库外复制的相同输入上比较旧函数与冻结的新函数，不导入执行者的测试来产生该对照结果。

| 检查 | 独立观察 |
| --- | --- |
| 正常两关联 | 旧/新结果逐字段相等：MN0→MN/VSS、MP0→MP/VDD；body 接续 90/100nm、rail 接续 10/10nm、tap 包围 8/2nm，`local_graph_union=false` 保持 |
| 精度变体的构造与前置 | 实际 raw 的 VSS rail 右侧两点 x=900→901；重绑实际 header/hash、从 raw 重建 normalized。bindings、缓存一致性及 432 处 net-region 来源回链通过；GDS、source/target CDL、body context、tech 入口与 physical/derived owner 的 bytes 未变 |
| REQ-01 旧/新对照 | raw bbox 精确为 `[0,48,901/20,58]`，本地 MN 为 `[0,48,45,58]`。旧 helper 返回两条正常关联；新 helper 抛出 `BodyTargetRailMismatch`，没有以 hash、缓存或其它前置错误代替目标拒绝 |
| C22 / 缺 body 算子 | 真实 replacement 后 bindings 通过，原 consumer 路径拒绝 `RequiredBodyOperatorUnavailable` |
| 缺 context / 错 source binding | 实际 remove/replacement 后分别命中 `RequiredBodyContextUnavailable` / `BodySourceBindingMismatch` |
| 类型 / 断开 / 歧义 / 包围 / 错 rail | 逐个应用原 overlay，bindings 通过后分别命中 `BodyTypeMismatch`、`BodyContinuationMismatch`、`BodyUniqueMatchFailure`、`BodyTapEnclosureFailure`、`BodyTargetRailMismatch` |

测试和独立探针均直接经过所修 helper/其原 tech consumer，未用 mock 的 normalized 坐标跳过 raw 读取。新增测试在旧实现上的失败日志属于执行者 E5 证据；本 reviewer 自己重现的是上表旧/新函数对照及修后测试，不把执行者日志称作本人重跑。

本机复核材料位于 `/workspace/work/w004-req01-review-rko7ninr/`，含两份受审文件 snapshot、unittest stdout/stderr、实际副本及 `result.json`；结果 SHA-256 为 `a18de30f2b6413df71654ca8e0e03ee6d1f4c0d057beb29ba59cb048492f83ba`。跨环境重跑关键检查可使用仓库路径下的持久测试和原报告完整复现附录；临时目录不作为唯一交接材料。

## 结论与限制

精确比较保持正常整数坐标的既有含义，拒绝了原先被截断吞掉的 0.05nm 差异。REQ-01 闭合，无需改变 W005 输入定义、既有正常答案或原 29 例目的；本轮未扩张 Stage 1/Stage 2 的责任。

未执行 KLayout/完整 `witness()`、全量生成、全部 29 例重跑、产品 parser/runtime、真实 EDA/LVS 或生产验证。未重验旧完整封包；其原证据身份和限制不因本局部修复被改写。本 reviewer 只新增本报告并追加 W004 R4，未修改实现、原 finding 或 PM 状态，未提交/推送/合并。
