# W005 独立接口 review

Reviewer：`interface_review` 子 agent，未参与方案编写或产品实现。日期：2026-11-02。

## 受审身份与范围

基线 `5b7205009b3ed7f8fe15e135e674654f2f544557`，分支 `codex/w005-input-reading-binding`。启动时工作区干净；本次审阅执行者提供的 `work/w005-api-draft.txt` v1，SHA-256 为 `293b6934179252909e7eb253ede5464d18e82268335cbcb6611036967ace354a`。该草案正文由执行者归入 [W005 方案段](../W005-input-reading-binding.md)，本记录只保留历史 review 身份，不另定义产品合同。

已读取根 AGENTS、README、协作规则、W005、架构 §2.1–2.3、§3.1–3.2、§4.8、§5、§11.2/11.10/11.13–11.15、§12.1–12.8、W003 contracts，以及实际 site/tech formats/physical/query header/requests/raw/normalized/body context 和反例清单。核查的是 API/DTO、错误归属、数据来源和 Stage 1/2 边界；尚无产品实现或测试可据此宣称通过。

## 结论

**接口方案可进入实现；当前方案无必须修正项。** `read_inputs` 作为只读组件入口，底层 parser 只消费同次读取的 bytes 与已校验 profile；中立 tagged results、递归不可变值、exact codec 和逐文件 provenance 与架构一致。公共入口不承担 pipeline/run lifecycle，也不提前构建 layout state。

方案已吸收本 reviewer 在形成草案前提出的接口风险提示：

| 检查点 | 方案落实及最终代码 review 的可观察依据 |
| --- | --- |
| 同源 bytes | 每次调用的 byte store 统一提供 hash 与 parser 输入；失败保留已读来源和完成的组件 evidence。文件未实际读取时不得伪造 bytes hash。 |
| 错误 variant | success/error 字段组合经过 runtime validation；预期读取/格式错误转为 EvidenceIssue，意外异常保留根因，KeyboardInterrupt/SystemExit 传播。 |
| 不可变与 exact | 防御性复制并递归冻结，原 XY/REAL8/lexeme 保留；跨进程 digest 稳定，解码拒绝非法或非规范 exact 表示。Frozen dataclass 本身不能代替 alias-mutation 测试。 |
| Schema 与边界 | bootstrap ceiling 明确归属 `layauto-input/1`，文本按全部 bytes、root container 深度 1 测量；tech profile 只可收紧。未知 key/type/version 递归拒绝，owner/registry/单位/模型引用须验证。 |
| Query 来源 | 全部 raw 必须先解析，normalized 仅可选比较缓存；parser contract 与 product parser version 分开；synthetic 状态组合即使重绑 hash 也不能变成 executed/matched。 |
| Stage 1/2 | nXref/NET NAMES/requests 的格式关联在 reader；CDL↔query 语义/cardinality 与空间 join、single-finger admission、物理 body 类型匹配及几何连接留 Stage 2。Body 仅做内部引用、类型声明合法性与 source/top/unit/profile 绑定；不把 FRAME/BN 等当作 GDS object ID。 |

## 实现后的复核入口

最终代码 review 必须另行绑定实现版本并实测：A1–A7、第二合法输入、重绑后的语法反例、缓存缺失/漂移、synthetic 伪真、递归 schema/DTO 非法组合、隔离 imports、构建安装及解释器证据。C08/C09/C10、C13–C16、C19/C20 与 body 物理失败见证应明确交给后续接收方；读取成功不表示这些后续准入或物理检查通过。

本记录不代表 W005 验收、生产工具验证或 M1 完成；PM 接收与最终验收仍由 PM 负责。
