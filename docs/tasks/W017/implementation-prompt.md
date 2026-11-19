# 首个产品实施 prompt（PM 接收并确认新合同后派发）

> 以 Layauto v2 执行角色实施首包 Stage 2 只读坐标与片段查询。先核对 PM 指定的集成基线、决策项和冻结的 W017 样张。读取 AGENTS、协作规则、架构 §2.2–2.3、3.4–3.6、4.1–4.2、4.8、11.3、12.3/12.5，以及 W005/W008/W009/W016 的输入与状态所有权。以下以 W017 的推荐合同为输入，差异按 PM 记录执行。
>
> 从真实主 site 的认证 W008 geometry 和显式 selection 开始，提供一个版本化 `project_coordinates(geometry_result, selection, requests, *, effective_result=None)` 入口。selection 在捕获阶段选文件、冻结 URI/声明与实得 SHA；在 `layauto_v2/importers/` 做一次获取与安全解析，在 `tech/schema.py` 或相邻独立 schema 校验层/轴/版本，在 `normalization/` 新组件逐项核实原始字节、owner、unit、GDS 与可选 W009 base/region 身份。旧 W005 owner/schema 保持原语义。首包支持固定 toy FIN Y 中心、有限等距 X/Y 格边和正面积轴对齐矩形；S2 的显式三条格边也可走既有 LayerPartition 数学接口。
>
> 在 `state/coordinate.py` 或同层新文件提供纯正/反查、point→cell、cell→bounds、rect→精确交片。用整数/Fraction，区分中心与边界，负值和半开边正确，对非 exact 类型作定位拒绝。FIN off-track 保留两侧偏差，越界不 snap。B 层独立解析双轴。缺轴、无投影、无效声明、超界、离轨、超预算各有可验证结果。把带模型/域身份、record/region/piece/unit 引用的多片存到 `state/occupancy.py` 或相邻新版只读类型；保留 W008 原 BasePartition/BaseOccupancy 与 refs。W009 的有效片段来自已认证的 region，保留 CUT contributors。调用在产出前先核对有界计数，错误时保留原几何与定位。新组件不创建拓扑边或推进发布。
>
> 回归从 S1–S4 及 W017 reviewer 的独立反例开始。覆盖 18 根 FIN 反算、半轨/极大整数/有理点/浮点与布尔输入、贴内外边/跨出/负格/非零偏移、换相位和方向、层表 15 项含空层与 none、显式及漏/错轴/非法 pitch、重复键或坏容器、GDS/owner/模型错绑、异源 region/重复图形、同格多片和 CUT 间隙。用独立区间覆盖证明拼回每条输入；测细 pitch、大空域、满窗超限与无部分结果。给读者一条从正常入口查询 FIN 与 LI 的命令和实际返回，并给出一条定位失败样张。
>
> 以同一旧输入核 W005 读取/错误边界，W008 原 wire/hash/fragment 身份，W009 effective refs 与 W016 无 tapcell 的本地 D/G/S、B/parent unknown；保留 W006 readback 的旧认证。先跑新增/受影响测试；记录本次与 W017 同条件的格/片段/耗时/内存，分开测新增投影与端到端成本。最后在冻结产品源/fixture/测试/配置上完成项目双解释器全量、strict typing、构建及两套干净安装/源码外 smoke。按 verification-reuse 交未参与实现者复核，给 PM 受测身份、剩余限制、必须项处置和实际集成需补测范围。产品提交、分支、集成按 PM 为该实施任务指定的授权执行。
