# W012 A2：编码端私有 typed pack 收敛方案

执行日期：2026-11-11（Asia/Shanghai）。执行者 `/root`；只读设计调查协作者 `/root/call_chain`，A1 身份/数据调查协作者 `/root/a1_evidence`。他们均不承担本方案独立 review。

## 交 PM 的建议与范围

**推荐一个最小候选：只在 W010/W011 现有 closed encoder 内，用操作私有 dict/tuple 标签树代替编码阶段的临时 FrozenMap 包装，再交给未变的 canonical 全树 freeze。** 两处 owner 是 `normalization/local_connectivity_codec.py` 与 `channel_identity_codec.py`。不是 token writer、reader、memo 三包，不改 domain codec，也不扩至下层四个 codec。现有公开入口、`/1`、完整来源及认证不变。有限小值见证已证明该机制能减少临时构造且产生相同字节；尚未实施产品或测得完整收益。

建议 PM 可据本方案另派一次有限最小实施。依据是实际 build/decode 多次进入这两个 encoder、现有 wrapper 对已打包子树重复 freeze 的静态事实及有界构造次数对照；**不是**把全部 freeze 成本认作收益。若未来同条件完整结果不能支持这两个落点的开发维护成本，保留测量并交 PM 回 M1 网络标注，不自动扩下层 encoder、writer、reader、memo、B 或删认证。本轮在独立 review、必须项复核后交 PM 停止，不代 PM 验收或改变阶段。

## 起点、合同与所采信证据

- 仓库 `/workspace/Layauto`；初始 branch `work`、HEAD/main 内容 `2489b4609ae97d8211bf450d55cac9392492ac71`，staged/unstaged/untracked 均空。实际 `git ls-remote origin refs/heads/main refs/heads/codex/w012-a2-serialization-plan` 分别返回 main 上述完整 SHA 与 A2 `842c5c1ea8f1d01bb3f04e4703f105e11f94158c`。显式 fetch 后从后者恢复原 A2 分支；首次 fetch 因 narrow refspec 未创建 remote-tracking ref，第二次显式 refspec 后成功，无历史改写。
- 已读根 AGENTS、README、docs 导航、协作规则、local-setup/remote-development；`rg --files -g AGENTS.md` 仅有根规则。读 W012 当前 PM4/PM5、AP1–AP5、A2 派发 review、原 P1 `implementation-proposal.md`、A1 performance-analysis/原 profile/manifest/integration。架构依据为 §2.2–2.3 的 exact 原始输入/来源与事实边界，§2.6 的递归防御冻结和发布唯一 owner，§3.7–3.8 的派生读取面与无可写别名，§11.2/11.9/11.15 的 codec/派生/依赖与内容身份要求。方案不修改这些合同。
- Cloud 环境 id 为 `ccarenv_b64_Y2NhcmVudl8xMzdiZTRiZDRjMTg4MTkxYjg0YWFkNjEwNTkwYTdhNQ`；启动后状态 running、observations_current=true、网络策略 enforced；读 `/etc/codex/network-policy.json`，VPN=false。实际执行 Python3.12.14，无安装依赖。使用的 runtime 位置、系统信息、脚本身份和命令见 [check.command.json](check.command.json)、[check-result.json](check-result.json)。
- [A1 263 项 manifest](../A1/verification-r2/source-manifest.json) 对磁盘、A1 冻结 `ca1f810c3c97376f71089d8b4054760ff198012f`、实际 merge `08dd232139918dc97b0a6d255aad237eb844686a` 和 PM 准备提交逐文件 SHA-256 相同，其中 runtime100。9 份 after 样本及 readback after-profile 的 source map 也相同。manifest 自带历史 git_head 不被当作受测冻结证明。
- 因本轮 runtime/正式测试/配置不变，按 [A1 集成回执](../A1/integration-receipt.json)、[最终工程回执](../A1/verification-r2/receipt.json)及既有独立 review 采信双3.10/3.12各1656、strict typing54、构建/双干净安装及全长 wire 对照。不重跑小时级矩阵或18条基准；没有声称本机重读原约1.47GB wire 或旧安装树。

## AP1：真实热点及可归因范围

下表直接复算 A1 `performance/after-{case}-r{1,2,3}.json`，单位秒。总中位先对每个样本所有阶段求和，再对三次取中位；不能把不同样本的阶段中位相加当总数。

| 无插桩 after | direct | readback | extraction mismatch |
| --- | ---: | ---: | ---: |
| W011 build 中位 | 27.860428 | 51.426606 | 28.757855 |
| W011 decode 中位 | 35.128253 | 66.114896 | 37.506055 |
| 最终 W011 encode 中位 | 1.422533 | 2.616473 | 1.458006 |
| 各次阶段和的中位 | 75.799891 | 144.066817 | 79.514097 |
| 完整 wire B | 54,050,313 | 136,471,701 | 54,045,042 |

完整 hash、原 RSS 各次和 A1 前后差异见 [A1 性能报告](../A1/performance-analysis.md)；本方案不产生新降幅。readback after RSS 为706668/708860/708536 KiB。旧20%耗时/50%峰值只是历史宽包建议，均不是 A2 硬门；兼容方案 **wire 降幅必须为0**。

[真实 after-profile](../A1/profile/after-normal-readback-r1.profile.json) SHA-256 为 `51e1b4dbc732dcb453b0d40687ba2203e5d2273a32bddb0d8130690263f6a7f3`。这是有 cProfile/观测器开销的另一运行，不把插桩秒数换算成无插桩可省秒数。

| readback profile | W011 build | W011 decode | 最终 encode |
| --- | ---: | ---: | ---: |
| 插桩 wall s | 177.304140 | 222.849795 | 7.756393 |
| domain.codec 全函数 exclusive s | 98.236572 | 124.771350 | 3.683182 |
| freeze/map 家族 exclusive s | 89.925018 | 114.519416 | 3.362036 |
| `_wire` exclusive s | 6.903948 | 8.247991 | 0.289736 |
| freeze calls（含递归） | 30,479,491 | 36,315,537 | 1,052,453 |
| FrozenMap init calls（含递归） | 7,463,302 | 9,031,067 | 297,814 |
| canonical_bytes calls | 19,731 | 25,921 | 1,025 |

freeze/map 家族指 `domain/codec.py` 的 line20/21/23/25/31/32/38/52/56，含必须保留的防御快照/解码和公开构造，**不能整体删除或当候选预算**。freeze cumulative124.858326/157.577538与FrozenMap init cumulative126.896077/160.144440互相嵌套，不能相加。calls也区分 recursive/primitive，原行保存在新 check-result 中。collections ABC `__iter__` exclusive另有18.524976/23.153833s，但没有 caller 边归因，不能都算本候选。

选择 pack 而非新 writer 的理由：`_wire` 已小于 freeze/map 家族，重写 token/UTF-8/大整数错误顺序会增加等价成本；本候选保留这些成熟算法。只处理 W010/W011 是因为它们已经先对原图执行 `validate_closed_graph`，拒绝外来 subclass、equal-object、可变集合；semantic/publication 等旧 encoder 的 admissibility 分支不同，不在本次统一。

## AP2：owner、入口、数据流与精确算法

未来产品 diff 的预期落点只有这两个 codec 的编码辅助函数及其正式定向测试，**本轮未写产品 diff**。不新增公开 codec，不给用户暴露 trusted/cache/skip-validation 参数。内部新函数命名可用 `_pack_for_encode(value: object) -> object`，不导出；旧 `_pack(value) -> Value` 原样留给 decoder。

| owner / 现入口 | 保留 | 仅拟替换的表达式 |
| --- | --- | --- |
| W010 `local_connectivity_codec.encode_record`（当前line117） | 根 exact type/`_SPEC`检查、`validate_closed_graph(record, _ALL_TYPES)`、原 envelope | envelope 的 `record: _pack(record)` → `record: _pack_for_encode(record)` |
| W011 `channel_identity_codec.encode_record`（当前line138） | 同上、所有 delegated encoder 与完整 nested bytes | 同上 |

数据流：**原记录 → 原根类型检查 → 原 closed graph 原图检查 → 操作内 owned 标签树 → 原 canonical_bytes → 原全树 freeze → 原 _wire → 原 json.dumps → 原整体 UTF-8 bytes**。不更改领域 to_value/ref算法，不把owned树交给业务或repository，不保留跨操作状态。

每个 owner 使用自己原 `_SPEC` 作为唯一字段清单，逐字段按原 tuple 次序 `getattr` 后递归；不 `asdict`、不自动发现新 dataclass、不按 `__eq__`/类名准入。算法如下，完整有限参考见 [reference_pack.py](reference_pack.py)。

```python
spec = _SPEC.get(type(value).__name__)
if spec is not None and type(value) is spec[0]:
    return {'record': type(value).__name__,
            'fields': {field: _pack_for_encode(getattr(value, field))
                       for field in spec[1]}}
# 逐条照原 classes/tag/encoder 顺序分派，exact type 命中后：
# return {tag: encoder(value)}   # 完整原 bytes；不解包/省略/缓存
if type(value) is FrozenMap:
    return {'map': freeze(value)}  # 此处立即快照，不能等待最终 canonical
if type(value) is tuple:
    return {'tuple': tuple(_pack_for_encode(item) for item in value)}
return {'scalar': freeze(value)}
```

W010 分派依次为 `_EFFECTIVE/effective_record`、`_GEOMETRY/geometry_record`、`_CAPTURED/captured_record`。W011 依次为 `_LOCAL/local_record`、`_GEOMETRY/geometry_record`、`_EFFECTIVE/effective_record`、`_SEMANTIC/semantic_record`、`_CAPTURED/captured_record`。全部沿用原 classes tuple、原函数和 `_captured_bytes`，调用顺序/次数不变；外部 codec 仍完整认证。

自建的wrapper dict和fields dict只含本操作创建的包装、立即冻结的叶或原nested encoder已返回的完整bytes。tuple仍当场按原序物化；禁止将 caller map/list 原指针暂存到最终 freeze。原公开 `FrozenMap`、`freeze`、`freeze_map` 和 `canonical_bytes` 实现不变；普通可变输入仍在原公开入口完成完整防御快照。单次集合快照 helper不变，不能先遍历验证原集合再第二次取保存值。

建议逐步落地：先加两个私有helper和新增/受影响定向对照，仍使用原 `_SPEC`；然后仅替换两处encoder表达式；冻结前检查旧 `_pack`所有decoder调用未动、lower codec/公开constructor及认证counts不变。无需先抽跨六codec通用框架；若将来出现字段表漂移，用同一registry覆盖性对照发现，不另建平行schema。

## AP3：字节等价、对象账本与异常防线

对任一通过原closed检查的有限记录/子值，以结构归纳证明 `freeze(new_pack(v)) == freeze(old_pack(v))`：record同exact type、同全字段；delegate同输入同原encoder；map在原分支位置完整freeze；tuple按序归纳；scalar原freeze。旧wrapper的FrozenMap只是对已经组装的子树再freeze；新wrapper的dict最终交给原canonical全树freeze，规范化后相同。这里的等式不是以hash相同代替认证，而是编码中间表示的完整结构关系。

| 项 | 必须保持的规则与原因 |
| --- | --- |
| closed / exact scalar | encoder原图 `validate_closed_graph` 在任何copy/fold前；bool/int/Fraction不凭等值互换，Fraction/DTO/str子类与可变别名仍拒绝；不能把当前fallback擅改成另一准入语言 |
| field/tag | 原_SPEC包含schema/status/value/issues/completed/input/semantic、run/owner/source等全部字段；opaque payload即使含record/fields/$map字样也仍是payload；nested wire完整按bytes保留 |
| 排序/escape/UTF-8 | 原json.dumps sort_keys=True、separators=(',',':')、ensure_ascii=False、allow_nan=False及最后完整str.encode('utf-8')不动；键以Python字符串排序，不新设Unicode归一化 |
| rational/bytes/integer | Fraction仍精确约分，原$rational decimal strings与denominator/numerator排序；$bytes仍lowercase hex含空串；不经float。大整数限制、非法数和surrogate由原canonical路径处理，不改为逐token编码 |
| decoder语言 | 原duplicate keys、未知/缺失fields、wrong tag、错误nested type、非规范排序/空白/hex/rational/float仍由原decoder拒绝；不扩大decoder接受格式 |
| 来源/身份 | 原bytes、URI拼写、SourceRef定位、six-owner/capture/run/checkpoint/attempt关系及全部hash/ref保留；content_ref/record_digest仍绑定完整原编码，不跨run或按相同sha合并 |

尤其不采用直接token UTF-8 writer：例如 `['\ud800', 10**5000]` 旧路径会先完成JSON数值转换，后统一UTF-8；逐token写可能改变首个异常及UnicodeEncodeError.object/start/end。当前方案不触碰该算法；小surrogate见证比较了完整错误属性。普通非法值优先在原freeze拒绝，也不因边序列化边快照改变错误次序。

| 对象/路径 | 本候选拟减少 | 必须保留 |
| --- | --- | --- |
| encode私有包装 | record/fields、delegate、map、tuple、scalar各层临时FrozenMap，以及父wrapper对已pack整子树重复freeze生成的map/tuple/Fraction副本 | 新owned dict/tuple也占空间；map/scalar叶快照、最终canonical完整快照仍保留 |
| `_wire`/JSON/hex | 无 | 完整_wire DOM、完整hex字符串、JSON文本、UTF-8结果bytes；未声称减少这些复制 |
| decode与公开DTO | 无 | domain.decode的FrozenMap构造和canonical重编码；每层_unpack、所有公开constructor、旧_pack(result)全值检查、最终encode_record(result)==原data |
| 来源完整重建 | 无 | W010/W009/W008/W007/publication完整嵌套构造/核源，所有原capture与中立draft；不以中立DTO替代捕获receipt |
| W011二次认证 | 无 | builder第一次_require_input，Result constructor再次_require_input、replace(self.value)、第二次_evaluate，完整draft/semantic/issues/completed字节比较 |

公开 `FrozenMap` constructor本身不改；减少的是这两个encoder为内部包装而调用它的次数，不是公共DTO的验证。原正式测试未发现对这类私有包装的第N次分配注入合同；不能保证故障“注入到已经删除的第N个内部allocation”仍发生，但不据此豁免任何既有公开验证或异常用例。MemoryError/RecursionError仍不捕获；本方案不宣称精确复现机器资源耗尽阈值或给新深度/大小上界。

所有剩余nested encoder/constructor、scalar/map freeze和认证抛出的意外异常直接传播，不新增catch/rethrow/translation；原预期错误处理位置不动。`test_w011_exceptions.py` 的第二次认证故障须继续发生，并保持同一exception对象/cause/context/suppress；nested Parameter及W007–W010故障同理。若未来发现公开异常依赖拟删临时构造，恢复该路径或带反例交PM，不能删测试/放宽合同。W009 ChangingList单次集合快照、W011原图拒绝mutable text/equal-object及全部来源负例保持。

## AP4：逐路径收益依据、残余和验证成本

现有profile只含函数聚合，没有完整caller边，不能把 `_pack` cumulative或freeze家族按两个owner准确切分。以下calls是实际after运行事实；不是建议删除的次数。

| 实际路径 | 经本候选的入口与依据 | 保留的重成本/不确定性 |
| --- | --- | --- |
| W011 build | channel builder先_require_input→local完整encode/decode，Result constructor再次走同链；原profile local encode30次、channel encode2次 | 两次_require_input/_evaluate；effective decode36、geometry decode428、publication decode754；lower pack与decoder旧_pack不动 |
| W011 decode | domain.decode先canonical检查→_unpack各公开constructor→W011再次核源→每层尾部encode；local encode95次、channel encode3次 | local decode15、effective decode112、geometry decode608、publication decode1059；旧_pack全树比对及来源重建保留 |
| 最终W011 encode | 本候选在channel及委托的local编码中生效；local encode14次、channel encode1次 | 本段无constructor认证，未变的effective encode93、geometry encode346、publication encode530；无插桩整段只约2.6s，不能外推前两段收益 |

同一组公共build/decode调用链也用于direct/mismatch，只是readback增加run/checkpoint捕获；本轮只对readback有这份after-profile，不能将其calls照搬成另外两路实测counts。三路均有无插桩A1 wall起点，未来必须分别比较。跨codec调用有包含关系，不相加cumulative；例如local pack build cumulative21.310800与channel pack1.451856可能包含lower encode，均非可减秒数。

有界实例确实减少临时构造：SeedLocation原freeze263/FrozenMap init151 → 参考91/43；ContactComponent原290/169 → 91/41，实际小wire逐字节相同并交原公开decoder重建。这些是标准cProfile **调用次数**，不是微基准，也没有候选产品计时。不能乘以大profile总calls换算总收益。

主要退化风险：新dict树与原canonical snapshot阶段同时存活；叶map额外即时快照及最终freeze仍有成本；lower codec和decoder重建占比可能主导，旧_pack原样保留限制decode收益；小对象额外分支/代码维护可能抵消节省。owned dict/tuple的生命周期不能跨操作，否则会增加保留峰值。A1 after-profile720336KiB残余峰值在最后matcher窗口之后，未逐allocator归因；本方案不承诺消除它。完整54/136MB wire与嵌套hex膨胀完全保留，生产上界未知。

不建议新设任意百分比或资源预算。兼容性是硬条件；性能建议是三路分别披露每次及中位、同条件可重复的build/decode改善、整路径和峰值退化。若有限重复测量无法分辨改善与运行波动，或某路退化抵消收益，交PM选择不实施/不集成并回M1，不为追旧20%/50%扩包。开发成本限两处helper/调用点及其合同对照；正式冻结矩阵和完整成对测量仍有小时级成本，因此先用开发定向验证和一组成对完整筛选判断是否值得最终冻结。这是未来派发建议，不是本轮启动许可。

未来验证必须固定：

1. baseline为同一主机/解释器/依赖上的A1原runtime，after为未来冻结实现；runtime导入树与输入目录分开，不能因checkout不同更换URI。正常URI `/workspace/Layauto/tests/fixtures/w003_m1/site_config.yaml`；mismatch `/workspace/w012-inputs/extraction-mismatch/site_config.yaml`，先按原35项清单/五项overlay逐字节重建核对。保留normalized cache并仍核raw，不删cache或使用随机临时路径。
2. readback RunRequest=`w012-investigation-run` / `w012-investigation-lineage` / `create-w012`，site_path为原正常绝对URI，selections等其余默认字段照原 [measurement-plan](../measurement-plan.md) / [A1 probe](../A1/probe.py)；fresh repository，无跨调用cache。URI或输入身份无法复原时，先同条件重建两侧新baseline，不和旧数字硬比。
3. 获取前显式gc.collect一次，其后默认自动GC；保留parsed/geometry/effective/local/result，readback加repository/ready/checkpoint/parse/tool/audits/attempt；encode保留原对象，decode同时保留wire和原对象及恢复对象。roots/GC/阶段包围范围按原计划，hash/bytecmp放计时外。
4. direct/readback/原mismatch完整公开构造/encode/decode，三路全部字段、所有hash/ref及完整wire逐块实比；正常5/7、mismatch实际4对source5恰一差异、36 FIN evaluations、来源/局部图/T05/body/独立target和readback unsealed/无terminal均核。先有限一组筛选；进入最终性能结论时两侧各3次fresh串行交替，原次/失败不覆盖。无插桩wall/RSS与额外profile分开，profile不得额外encode巨大对象。
5. 开发先新增/受影响检查，重点两codec所有_SPEC字段分支、delegates、bytes/Unicode/rational/大整数、closed错型等值、可变别名/单次快照、来源/run/owner、完整重建及第二次认证异常历史。原公开decoder接受/拒绝边界及旧_pack调用必须保留，不能删旧断言使新方案过关。
6. 真正产品实施最终冻结新源码/正式测试/配置，完成双3.10/3.12全量、strict typing、构建及双干净安装源码外完整组合smoke；源再变就定向修正后重冻要求矩阵。本次runtime未变，以上只列未来义务，采信同源A1工程证据，不重复运行。

## 本轮有限见证及限制

[check.py](check.py) 是新附件，不注册pytest、不导入附件到runtime、不修改或monkeypatch现有入口。参考原型仅允许2048节点/depth24/叶4096/整数256bit的自检值；这些是附件边界，不是产品限制。实际新增检查只为本方案的两个关键缺口：A1证据同源与“少wrapper仍同完整字节/边界”。6个真实小DTO root逐字节对照、原公开decoder重建，22个私有subvalue分支对照及snapshot/closed/异常/UTF-8/附件界限检查通过。没有创建完整Result或调用完整build/readback，不是产品性能实验。

原命令/解释器/UTC/exit见 [check.command.json](check.command.json)，原stdout/stderr和完整结果见 [check.stdout.txt](check.stdout.txt)、[check.stderr.txt](check.stderr.txt)、[check-result.json](check-result.json)。证据check和reference自身SHA记录于result；本轮不以六个小样本替代未来完整wire/错误回归或生产能力验证。正式测试/fixture、原P1/A1工具/报告/finding/输出、架构、PM阶段、current-work均保持。

独立review结果由未参与本方案/工具设计的reviewer写入本目录，其受审身份、finding原文和修正复核独立保留；执行者只处理方案修改，不代写review结论。最终Git提交/远端完整SHA由交接提供，PM接收决定是否实施，本轮不合main、不启动下一任务。
