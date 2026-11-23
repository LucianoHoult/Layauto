# W019 独立方案复核

基线为 `codex/w019-single-cell-occupancy-query@d0b8540e0e06326f51f7fd4c56d3e43c7ca667c1`。复核时工作树干净。独立 reviewer 已核对任务卡 A1–A5、架构 §3.4–3.5、W016 读取和报告、W018 坐标绑定及占用消费接口。结论为可依以下方案实施。

- 公开调用采用 `analyze_cell(request, occupancy=OccupancyRequest(fragment_budget=48))`。调用方取得成功的 `result.occupancy.value` 后用 `in_cell("M1", 2, 2, view="drawn")` 找到片段，用 `fragment.source.record.source` 读 GDS 位置，再用 `for_record(record.id, view="drawn")` 取该原线全部片段。默认投影 drawn；显式选 `include_effective=True` 时预算覆盖 drawn 和已有 effective 区域的所有可投影片段。调用者可从同一成功结果重复查询。
- W016 的 `LocalAnalysisReceipt` 重放已捕获的字节并比对完整证据；tech 记录含 bundle、六个 owner 和各自来源。W018 模型身份依赖 tech 来源、layout 单位与已解析的轴。共同绑定算法只需当前 layout 与这些已认证的工艺操作数。W016 和 W018 各自在入口验证各自的来源，随后共享绑定与状态层投影；`DiscreteOccupancy` 继续拥有三种查询索引。外部上下文、请求清单和 query header 不参与本地模型身份。
- `local.facets.drawn`、所选的 `effective` 是构建前提。外部资料错误或其它独立 facet 失败仍可能有完整本地几何。若 local 认证早退或必需 facet 失败，请求过的占用返回欠依赖并保留原始定位；若未申请则为 `None`。旧 owner 可成功列出逐层缺声明；检查 `layers`、记录数和 diagnostics 后，可查询域内的空格才解释为空。声明错误用已选 coordinate 的捕获 URI、SHA-256 及转义后 JSON Pointer。W018 聚合预算先计数，超限时交回总需片数和首个越限来源。
- 原 W016 顶层结果按原规则汇总。未请求时跳过新绑定和建索引，保持原报告。请求时单列有界摘要，因为原报告器遍历 dataclass 字段，而模型包含映射代理并引用完整 layout/effective。摘要应能表示 Python 允许的整数预算，例如大于十进制转换限制的预算，且预算为零仍应按照内核的真实计数处理。

独立几何依据来自对两个固定流的字节检查。用 Python 标准库从各 BOUNDARY 偏移起按大端 16 位记录长度前进，遇 XY 记录按有符号 32 位解码。主 `source.gds`（SHA-256 `97cf8d88771ff97f2cf189f6ae6a2fdcce585fc14f93c93d0ecf32326b415429`）偏移 2352 的 XY 为 (0,48)、(45,48)、(45,58)、(0,58)、(0,48)。W018 样例 M1 的格边间距是 16 × 20 DBU，故 (2,2) 的交宽为 45−32=13，交高为 58−48=10。CUT 专例（SHA-256 `1f57cb548544c934827f49d3ffb181048efc55e02976ab7ebe66b43621a37ef2`）的偏移 182、246 分别覆盖 [130,150) × [20,24) 与 [139,141) × [18,26)。差集的两块各为 9 × 4，缝宽为 2。专例沿用 W018 的 32 × 16 LI 格设置验证同格见证。

本次实跑上述原始字节探针，审查对象为方案。实施后由代码 review 核验同一 layout/effective 对象、有效和错误的 body 选择、早退、owner 错误位置以及预算两侧边界。还需比较读取/构建次数和报告体积，验证已安装 wheel 的公开入口；模块依赖变化触发相应的架构边界检查。全量双解释器检查按任务卡归集成后的 PM 阶段。
