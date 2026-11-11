# I-R02 测量工具修正记录（执行者）

`/root/measurement` 编写工具并在原回归 exit0 后启动第一轮筛选。`performance/before-normal-direct-r1` 已完成公开 build/encode/decode 及完整 DTO equality，但随后新增测量断言 `ref.uri.endswith('/target.cdl')` 失败。原合法 SourceRef URI 保留 `target.cdl` 字面值；该断言误加了前导路径分隔符假设。这是测量工具缺陷，无产品异常结论；首个样本未写 result/wire，不能作为成功 before 复用。

原源码分别保存在 `probe-before-I-R02.py.txt`、`selfcheck-before-I-R02.py.txt`、`analyze-before-I-R02.py.txt`。原 `performance/` 全部 started/command/stdout/stderr/samples 和 outer `development/performance-r1.*` 原位未改，真实 exit1 和 traceback 保留。轻量定位第一次脚本末尾误取 `FrozenMap.sources` 的 AttributeError、第二次成功结果已导出为本目录 `attempt01/02*.txt`；它们明确标记来自原工具输出，没有冒记为新运行或虚构精确 UTC。

已授权修正只涉及测量附件：

- `probe.check_preservation` 核 source 的 exact `SemanticCircuitDraft` 和 target 的 exact `TargetCircuit`，两者独立；各自完整 preservation 必须等于 `parsed.completed` 中唯一对应 `source_cdl` / `target_cdl` 的原 EvidenceRecord。保持原 kind、来源字段与捕获 hash 解析，不改写 URI；原 `check_sources_target` 的捕获 bytes/来源/query/body 检查保留。
- `selfcheck` 对固定正常和原 mismatch 两条路径实际运行 `read_inputs → from_parse_result → normalize`，核合法相对 URI 和完整原 preservation；以保留 exact 类的浅复制伪造 swapped preservation，确认 helper 拒绝，再复核原对象未变。无完整 W008–W011 构造/大 wire 编码。
- `analyze` 新增可选 `--failure-samples` 目录参数，与当前 samples 目录合并，汇总保留的旧失败 command 并记录扫描目录，不让后续成功 attempt 掩盖本次 exit1。轻量自检包含失败目录+成功重试目录+重复目录，核旧失败保留一次。

两次实际修正自检均 exit0：`development/measurement-selfcheck-I-R02.*`（先核原保留证据）；`development/measurement-selfcheck-I-R02-final.*`（加失败目录汇总后的最终工具），结果为本目录 `selfcheck-result.json` / `selfcheck-final-result.json`。首份中间 selfcheck 源码依据精确差异重建并核其 SHA 与首结果记录相符，保存为 `selfcheck-I-R02-before-failure-aggregation.py.txt`；最终工具身份以 final result 为准。

本记录不是独立 finding 复核或关闭。待未参与工具设计者复核修正，再由 root 决定新工具冻结和 `performance-attempt02` / 新 wire 目录重跑；本执行者尚未重新冻结或自动启动第二轮。产品源码/正式测试/配置仍为原候选 c0a9a2e4c292255202a0ec82b6277cd8a8dd6b78；原输入路径、捕获 bytes 和 URI 字面值完全保持。
