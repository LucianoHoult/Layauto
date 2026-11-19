# W017 独立复核

复核者单独读取架构 §2.2–2.3、3.4–3.6、4.1–4.2、4.8、11.3、12.3、12.5、MR-051/052、W008/W009/W016 合同、任务卡及实际 fixture。复算探针在收到执行版本前直接从 GDS 读数。环境为 Linux x86_64、CPython 3.12.14，命令从仓库根运行。

## 受审版本及结论

基线 `15bfc855f8ee97c331b8c9f7a842a155455d8211`，受审提交 `483d1965b115a45a07221e0f7af1214cac7bbe6f`。两者实际 diff 限于任务卡及其材料，共 10 个文件。核对时 staged/unstaged 没有对受审内容的修改，未跟踪文件只有 reviewer 探针与记录。逐项读取方案、实施 prompt、选择/声明、数学输入、计算器、生成入口和两份输出；文件引用可解析。独立核对 selection 的字节 SHA 及六份捕获来源。样张重新生成后与冻结的 samples.json 逐字节相同，其 SHA-256 为 `14001206e42379b65ca3f321cfddc95bbe1f2c0a85d7aa740ba342664c957347`。

A1 表的全部 15 项与 drawn owner 和实物数目一致；FIN 的尺寸出处、候选编号窗、LI 候选两轴、无实物及跳过投影的层可区分。A2 的部分模型有显式选择、来源绑定、有限域、精确片段及定位失败，旧例/无资料仍可访问几何。A3 四组样张与独立值一致。A4 的首包 prompt 指定 importer/normalization、纯换算、占用与下游责任，列出 W008 并存、W009 effective 同源、旧接口回归和资源上限。合规产品 wire、完整认证/预算策略及批准新接口仍属于下一包；三项 PM 决策见[执行方案](../proposal.md)。

修后的冻结版本上 R1、R2 均已独立重放并关闭，剩余必须修正项 **0**。允许 PM 接收调查方案并决定产品合同。

## 实跑与独立数值

| 复核对象 | 方法与结论 |
| --- | --- |
| S1 / A1 | Python 标准库遍历原始 GDS，将层号和 datatype 映射回 drawn owner。检查原始 UNITS 两个 56-bit mantissa 与 formats 中各自的有理 nominal、源 XY 五点闭合和四边。40 条主图形，15 个声明层。FIN 首条 BOUNDARY 的字节位置为 496，Y 为 [24,26]，末条位置为 1328，Y 为 [194,196]。18 个实测中心按物理 profile 独立反算得到索引 0…17，30 nm 与两侧差为 +5/−5 nm。POLY 仅一条，CUT/BTAP_N/BTAP_P 本地无图，BOUNDARY/MARKER 保留并关闭投影。 |
| S2 | 枚举源矩形的 32 个整数单位方格，以中心归属核对每片位置，再核对半开区间端点。四片面积依格号依次为 12、12、4、4。贴边矩形只落 (0,0)。边界 ±1/100 DBU、精确负下界和正上界分别验证。枚举与对照均保留每片覆盖，任何重叠或遗漏都会改变计数。 |
| S3 | 从专例 GDS 的 LI（字节 182）和 CUT（246）独立枚举单位方格并取差。80 个 drawn 方格，8 个位于交区；左右各 36，间隔 2 nm。用 spec 的 index_witness 计算，均在 (4,1)。实际输出保留共同源 LI、同一 CUT、不同 region/piece，与第三条远端 LI 分开。 |
| S4及资源 | 对主 GDS 的三条 LI 按单位方格及显式候选格边分组，与每个源 record 的输出逐片核对。原候选、Y 相位加 1、交换 X/Y pitch 得到 20、23、16 片。1 DBU pitch 的占用格及片段均为 1110；大空范围的潜在格数为 10¹⁸，仍只输出 20 片；同尺寸满覆盖在枚举前返回 resource_limit。独立复跑三行耗时约 0.470、9.746、0.639 ms，峰值 4,648、324,464、4,648 bytes。时间受机器负载影响，tracemalloc 仅计投影片段及去重集合的 Python 分配。 |
| 旧入口 | W005/W008 随 PM 探针与原型从 site 实跑。W016 独立以 tests/support/analysis_inputs.py 的 materialize 在临时目录生成无 body 输入，调用 analyze_cell(AnalysisRequest(tmp/analysis.json))，得到 completed，FIN 5/7，六个 D/G/S equal，两 B indeterminate，parent_global unknown。 |

```sh
python -B docs/tasks/W017/pm_preflight.py
python -B docs/tasks/W017/run.py | cmp - docs/tasks/W017/samples.json
python -B docs/tasks/W017/review/recompute.py
python -B docs/tasks/W017/review/counterexamples.py
python -B docs/tasks/W017/run.py --resources
```

## 必须修正项

| 编号 | 原反例与影响 | 处置和复核 |
| --- | --- | --- |
| R1 | 未冻结初稿调用 Tracks.locate(30.1) 实际给出 5.100000000000001、−4.899999999999999 nm；bool 也可通过 Fraction 转换。精确结果含二进制浮点误差。 | 原反例保存在 counterexamples.py。修后严格检查 int/Fraction，30.1 与 True 均定位 invalid_query；301/10 精确返回 51/10、−49/10。反向索引 True 也拒绝。 |
| R2 | 从原候选独立复制 JSON，分别设置 axes=[]、axes={"broken":null}、layers=[] 并重选新内容 SHA，初稿绑定器均抛裸 AttributeError，缺失声明错误位置。 | 修后在 /axes、/axes/broken、/layers 各返回 invalid_declaration。复核另覆盖错维度、错引用、对关闭投影的层强选、旧哈希、部分越界、合法上界接触及预算差一片。 |

## 采信与补测

W016 实际集成 `ef40ac4882c3207a1753723a367c21c331c53388` 与 W017 基线 `15bfc855f8ee97c331b8c9f7a842a155455d8211` 的产品、测试、fixture 与 pyproject 逐路径 diff 为空。三项 Git 身份依次为 `40b37d7a908b5da877a3a618206ab417ef5a9021`、`66792512857f4b0e877756552e99453538d9ff99`（tests 含 fixture）、`4b0a96516b34f047a4fc2fc2c04c127b60891281`。按原环境、依赖与冻结身份采信旧合同验证。[W016 PM3 与原证据](../../W016-single-cell-analysis.md#pm3-integration)

本轮仅覆盖 synthetic flat rectangle、已绑定的 nominal 单位和样本有限域。产品实现、生产 PDK、布线、修改、签核和发布尚待各自能力与证据。产品或输入生产者、路径/hash、投影约定、范围/预算与集成组合变化时，重跑受影响边界；进入产品交付时在新冻结版本执行双解释器全量、typing、构建、干净安装。仅文档补记核对链接与身份。[验证复用规则](../../../collaboration/rules.md#verification-reuse)
