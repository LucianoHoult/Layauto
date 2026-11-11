# A1 最小方案独立 review

**所审最小方案可进入 A1 实施，新增/剩余必须修正项 0。** 这不是实现正确性、性能收益或 PM 验收；实施后的 I1–I6 和最终独立 review 仍须实际完成。

Reviewer：`/root/a1_plan_review`，未参与算法、测试、测量工具或方案设计。受审提交 `3b341b7420221599f5ff0eac7d945f57b98a19e3`，base为PM准备 `7f7c1304bdafd941791421cef64864fb1616303c`；独立 worktree `/workspace/w012-a1-review` 初始干净。只新增本报告及独立轻量证据，未修改产品、正式测试、执行方案、PM记录或current-work。

已读AGENTS、README、协作/本地与远端环境规则，W012最新PM1/PM2和I1–I6、P1/P2成本/实施建议/独立review、PM接收说明/回执及方案专项；回查架构的canonical bytes/不可变/领域与依赖边界，现有公共/嵌套codec和readback/异常合同。只读辅助专项 `/root/a1_plan_review/a1_exception_check` 独立核对异常边界，未设计方案、写文件或运行重型组合。

## 核对结果

| 范围 | 独立结论 |
| --- | --- |
| 最小实现范围 | 候选只改 `domain/codec.py::_decode` 的原hex条件；原 `isinstance(..., str)`、`bytes.fromhex(raw)`、错误raise、最终canonical复验及其它runtime均不动。没有writer/reader重构、memo/cache、`/2`、证据省略或认证绕过。与此次I1–I6派发一致。 |
| 接受语言 | H为小写ASCII hex字符集合，原语言(HH)*等于H*且长度为偶数，含空串。`fullmatch('[0-9a-f]*',raw)`不会扩大到Unicode digit/大小写近似或空白，长度条件拒绝原本无匹配的奇数串。原fromhex仍仅在相同完整语言准入后调用。 |
| 调用与异常 | matcher仍先调用一次，包含奇数和非法串，不通过新长度短路遮蔽原matcher故障。未添加except或重包。原matcher/fromhex的异常object/cause/context/suppression可保持；W011两次 `_require_input`（builder与constructor）和 `test_w011_exceptions.py:105–126` 的第二次故障路径不在改动范围。嵌套geometry/effective/channel codec的既有错误与canonical重编码继续保留，必须按计划实测。 |
| 格式与身份 | 不改encoder、schema、公开签名或认证/构造次数，预期 `/1` canonical bytes、wire大小、所有digest/content refs均不变；不能以本方案逻辑替代实施后的完整三路径逐字节对照。publication与channel的digest均绑定实际encode输出，任何差异仍须定位，不能顺手迁移。 |
| 验证与测量 | 计划先新增/受影响，再最终冻结双解释器全量、strict typing、包及双干净安装源码外组合smoke，不能采信旧同源矩阵作为新源码结果。before/after导入位置分开、输入URI和RunRequest/cache/GC/roots固定，先重建35项mismatch清单，最终两侧每路径各3个fresh串行样本、保留失败和各次/中位数、父进程逐块比较wire，符合I4–I6。新旧profile/窗口诊断与baseline分离，重型样本串行；未来工具须核实际runtime导入位置和完整源/工具身份。 |
| 收益与停止边界 | 单字符重复消除原外层分组repeat结构是合理内存候选，但语言证明和regex opcode不构成完整路径内存证明。20%/50%仍是整包建议，不是A1硬门；必须报告实际改善、退化和残余成本，不扩成writer/memo或新格式。PM接收/用户新wire决定门保持。 |

实际运行[独立轻量检查](plan-review-evidence/check.py)，原[命令](plan-review-evidence/command.json)/[stdout](plan-review-evidence/stdout.txt)/[stderr](plan-review-evidence/stderr.txt)及[结果/身份/regex debug](plan-review-evidence/result.json)已保存：**307,773项断言通过，153,658个有限语言候选**。覆盖全部ASCII字符对、代表字母表0–6长度完整枚举、全部256字节及其序列转换、空/奇数/大小写/空白/换行/Unicode/有限长边界、matcher先调用/fromhex准入、5类异常的原对象及cause/context/suppression。另核当前公开JSON/native string与malformed/canonical拒绝；本轮未安装依赖、未运行正式产品矩阵或重型性能组合。

当前CPython3.12.14的 `re.DEBUG` 显示新pattern使用 `REPEAT_ONE` 且无原外层分组 `REPEAT`，原pattern的分组repeat结构按原输出保留。3.10、新实现双矩阵和完整内存/时间收益尚未在本方案review执行，须由后续冻结验收完成。独立校验当前262源/100runtime仍与W011冻结manifest一致，受审计划及原codec SHA256见结果JSON。

## 非阻断边界说明

新 `len(raw)` 若用于**直接私调** `_decode` 并传入恶意 `str` 子类，会调用其覆盖的 `__len__`；原正则/`bytes.fromhex`可直接处理底层字符串。公共 `decode` 经过现行 `json.loads` 得到原生str字段，未见公共入口暴露该子类路径。当前方案仅承诺公共JSON语言/错误合同，未宣称私有函数对任意子类副作用也完全等价；不将此扩大为新的必须项或要求顺手收紧类型。最终实现仍应保持原公开输入类型和canonical错误测试。

原P1/P2的R01与原证据保持原位；本轮无新增finding，不覆盖历史finding。执行者可按所审最小候选实施，之后交独立代码/正确性/性能review；本报告不批准验收、main集成、下一子项或新wire格式。
