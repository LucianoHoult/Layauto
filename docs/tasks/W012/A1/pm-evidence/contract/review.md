# W012 A1 PM 合同专项核验

结论：新增必须项 0，剩余必须项 0；未发现超出兼容 A1 授权的产品改动。

本专项只读 `/workspace/Layauto`，base `7f7c1304bdafd941791421cef64864fb1616303c`，交付 HEAD `db07a16fb7cbbac030adae84a9eb88cc0c8aa650`。已读根 AGENTS、README、协作及本地/远端环境规则、W012 I1–I6、A1 prompt、方案/独立 review，以及架构 §2.6 的 canonical/不可变合同和 §11 的领域边界。未改仓库文件。

1. `git diff base..HEAD -- layauto_v2 tests pyproject.toml` 只有 `domain/codec.py` 修改和 `test_w012_hex_validation.py` 新增。真实 before 源取自 `git show base:layauto_v2/domain/codec.py`；其 SHA-256 与性能 frozen before 身份相同，当前源码与 frozen after 相同。将唯一条件换回旧式后，两份全模块 AST 完全相同。不存在其他执行语义/签名/encoder/schema/digest/canonical 检查变化。
2. 直接数学依据适用于原生字符串：令 H 为十六个小写 ASCII hex 字符，旧式语言 `(HH)*` 等于 `H* ∩ 偶数长度`，含空串；新的字符类没有 Unicode、大小写或空白扩张。有限候选只作为见证，不冒称证明所有输入。本次实际加载真实原版和交付源码，核 19,201 个有限候选，匹配独立逐字符/长度判据，且原版与交付转换结果相同。
3. 公共 `decode` 通过现行 `json.loads` 生成原生 str；畸形类型/tag、duplicate key、多余空白、Unicode 转义及尾随 JSON 的原拒绝/canonical 边界保持。没有收紧公共入参。私调 `_decode` 传入覆盖 `__len__` 的 str 子类时，新增 len 可有不同副作用，本专项实际复现；方案 review 已预先明确此私有非阻断边界。本交付没有声称任意恶意子类私调都副作用等价，故不新增必须项。
4. matcher 保持先执行一次；奇数串、空串及非法串均未先按长度跳过 matcher。`fromhex` 仍仅在完整合法语言内调用。对真实 before/after 共 120 个注入异常场景，ValueError/TypeError/KeyError/KeyboardInterrupt/SystemExit 的原对象、cause、context 和两种 suppression 保持。没有新增 except/rethrow。
5. 最终 canonical 重编码检查和原始 bytes 保留；小值 byte roundtrip、实际 canonical bytes 和 SHA-256 均一致。其余 runtime 未改，未引入 trusted/cache、writer/reader 重构、新 `/2` 或认证绕过。重新读取两侧原 profile，在 8 阶段的 322 个明确 runtime constructor/认证/分析/公开 encode/decode 函数条目中，calls 与 primitive_calls 均逐项相同；不是只转述 summary。W011 builder 和 constructor 的两个 `_require_input` 源码调用及既有二次故障合同测试未改。
6. 20%/50% 仍为整包建议，不是 A1 硬门；wire 减幅要求为 0。方案与最终 review 保留原 finding 和关闭记录，未以减少断言或放宽 I1–I6 收尾。本专项未重跑完整性能、双解释器矩阵或完整嵌套 codec，不替代其它 PM 证据核验。

独立探针 [check.py](check.py)、真实 before/after 源副本、[command.json](command.json)、原 [stdout.txt](stdout.txt)/[stderr.txt](stderr.txt) 和 [result.json](result.json) 保存于本目录。结果：39,187 条核验通过（含 19,201 个候选、120 个异常场景，以及源身份、公共入口、canonical/hash 与原 profile 计数核验）。

建议主 PM 在已核解释器中轻量运行 `python -B -m pytest -p no:cacheprovider tests/contracts/test_w012_hex_validation.py tests/contracts/test_w005_contracts.py -q`，预期原正式集合 89 项。W011 完整 capture fixture 与双全量可按冻结源码身份采信已有实际证据；本专项不建议重复重型矩阵。
