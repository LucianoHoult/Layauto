# W010 来源、公开完整性与作用域专项

Reviewer `/root/source_review`，2026-11-06，未参与 W010 产品、正式测试或原 review。受审 `/workspace/Layauto-w010@c4909ab679d0c0806200fcb132db8a5de1ad3e75`，产品冻结 `0f5029df935bc0acd106aad1bc2be81304d4f442`。只写本目录 `source-*`，没有修改产品、正式测试或历史记录。

**本专项未发现必须修正项。** 独立 probe 最终 **31 个具名检查：6 个正常/中立对照通过，25 个反例按预期明确拒绝；exit 0，176.807 秒**。这不是完整回归、几何独立答案或全部异常矩阵的替代。

依据为根 AGENTS/README、协作/环境规则、W010 要求/方案及 review，架构 §2.2–2.3、§3.6、§5.9、§11.2–11.3、W003/W004 当前 body scope，以及 W008/W009 的输入/来源/公开合同和 W009 IPMR-01、FXR-01 修后边界。回查实际 `geometry_input.py`、semantic/readback/captured codec 与四个 W010 runtime 模块，已有通过记录仅作线索。

## 实跑与判断

| 范围 | 独立观察 |
| --- | --- |
| 实际 direct/readback | 从真实 W005 reader 与 W006 repository 已读记录分别经过 W008→W009→W010。W010 调用期间禁 `Path.open/read_bytes/read_text/resolve`、`builtins.open`、`io.open`；readback 另禁 repository 的 read/load_attempt/load_checkpoint/read_terminal。两条路径完整物理节点、边及分量多重集合相同，14/8/6、16 audit；本专项未把数量当唯一判据。 |
| 原事实与运行身份 | `input`、`value.effective`、`body_evidence` 保持原对象，completed 全量保持，原 W009 digest 不变；readback binding 保留，attempt 仍 unsealed，checkpoint 不变，terminal 仍为 None。错 run 的已篡改 prior handoff 在 adapter 明确报 `readback checkpoint/value differs from ready attempt`。 |
| 实际 rules source role | rules payload 等于完整捕获的 `tech.rules`，source 等于 tech evidence 第6索引（第7项、rules角色）。`geometry_input._OWNERS` 为 drawn/derived/physical/formats/coordinate/rules，且逐 owner 验捕获 bytes、首选 URI、角色数量及同源声明。W010 的固定索引与该合同一致。 |
| 中立和 captured 分层 | 将 rules 来源改为未获取 URI，或改为已捕获 drawn source role，公开 neutral builder 均可形成自洽草稿；放入原 captured `LocalConnectivityResult` 均报 `local graph/audit differs from this captured input or rules owner`。中立自洽没有冒充捕获认证。 |
| 成组伪造 | 保留原 captures，同时一致修改 parse.value、tech completed payload、nested semantic/input/geometry/effective receipts：rules enclosure=2、physical cross-layer 解释、VIA0 连接对、formats canonical tick。每组分别经过 W010 builder 和公有 result constructor，8次均为 **GeometryInputError / GeometryCaptureBindingMismatch / tech.json /tech**，非任意异常；证实会重新解析真实 bytes。 |
| 公有拓扑完整性 | 新增重复节点、伪造 BODY_N↔BODY_P 同层边、所有节点假 union、假 audit、外来 node ref，分别由公有 draft constructor 和嵌套 result wire 拒绝，10次均明确 `local graph omitted/added nodes, edges, components or independent enclosure facts`。外来 unit ref、丢 completed、false success constructor/wire 也明确拒绝。 |
| 标签与物理图 | 只在临时 fixture 副本改变实际 query 名称、路径、排序和 query identity，重绑 actual-byte hashes，重新 reader/构建。完整物理图多重集合和 semantic_digest 不变；neutral geometry draft ref 也不变，完整 captured result digest 改变。query/CDL/body 标签没有进入 state 的候选/union。 |
| Wire | 实际 readback 完整 result 往返相等，canonical bytes 和 record_digest 稳定。本次该回执 wire 为 **59,422,834 bytes**，是包含 readback 捕获链的身份，不拿它和 direct receipt 的约22.8MB当同一捕获比较。 |

`normalization/local_connectivity.py:31–41` 在编码复制前检查完整原对象图，再 decode 完整 W009 receipt；`:44–49`取同源 rules；`:66`及`:90–92`分别验证输入与实际捕获图。`state/local_connectivity.py:157–203`只枚举本地 layout records 和有效区域；外部 body 形状、CDL B端、net/query标签不参与 edge。BODY 节点仍作为本地图形保留，同层关系以几何为依据。逐侧 audit 与图边分开，coverage 明示后续义务。本专项没有发现来源认证或 scope 扩大的路径。

## 可复验材料与限制

在仓库根运行：

```sh
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/layauto/bin/python -B \
  docs/tasks/W010/independent-premerge-review/source-run.py
```

[独立脚本](source-probe.py)、[runner](source-run.py)、[最终输出](source-probe.stdout.json)、[stderr](source-probe.stderr.txt)、[命令/版本/退出码/输出身份](source-receipt.json)。实际 Python 3.12.14；既有开发环境，临时捕获在 `/tmp/w010-source-*`，无字节码，缓存路径独立；没有安装或运行3.10，也没有重建包。fixture helper 仅用于临时复制、query原始输入改名和hash重绑，不提供产品预期答案；完整物理签名比较由本脚本定义。

先前两个 **harness失败**按原脚本/输出保留，不能当通过：第一次在 rejection wrapper 外构造错run InputsReady，被公有constructor提前正确拒绝；第二次错误要求 query-only变化必须改变 neutral geometry ref。最终修正为把错run prior交给adapter，并比较完整 captured result digest，未放宽产品要求。详见[历史说明和文件映射](source-harness-history.json)。第一次进程加载脚本后曾改进磁盘脚本，故其 traceback 显示的行文本属于后来的版本，实际已加载源码另存 `source-initial-probe.py`；该事实在初次回执中明确披露。第二次原 receipt 中的输出路径已映射到 `source-second.*`，原 bytes 未变。

本专项没有采信历史工程矩阵来冒称实跑；完整正常几何独立答案、有限数学枚举、畸形与原异常链/单次集合快照由其他专项及主 reviewer 汇总。未验证生产 PDK/EDA、完整工艺坐标、有效region occupancy、外部body/U06、FIN/器件提取、query空间标注、其余mandatory/lifecycle、baseline/no_change/Stage6；这些是明确后置范围。未新增性能准入门槛。最终是否集成由主 reviewer 全部证据汇总后交 PM 决定。
