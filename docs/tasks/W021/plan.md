# W021 实施方案

依赖方向为 normalization 生产、中立 state/mutation.py 定义只读字段、未来 initialization transaction 消费。中立合同只引用 state/domain 类型。唯一构造入口接收一个成功的 Stage2Facts，不开放组件拼接或替换构造。保留占用、layout、effective、local graph、annotation、端子和外部 body、来源和 readback 的既有冻结对象；source 为 current，单独上下文保存 target 和 typed differences。按层关联 drawn policy 与 coordinate 声明及投影结果，区分几何生命周期、空输入和占用缺项。策略从已认证输入和现有合同读取。

LI 样张：层策略 + 3 条 drawn records、2D 网格、20 drawn fragments。格 (1,3) 由既有索引解引用，沿 record/piece、节点/分量及实交标注回查 60 DBU²、R04/VSS。缩短 query 仅改变直接覆盖。POLY 样张：保留 1 条栅形及其 drawn 生命周期；coordinate owner 缺该层声明。对于栅轨初始化，列出轴、节距、首中心依据和编号范围，不推算数值。缺项限定到所请求的投影能力。

合同测试走正常完整捕获，分别检查同次读回绑定、等价重建、拒绝错配、只读、预算失败和 repository 边界。用同一份组装对象计时增量首次构建和内存，量化仅新增的数据并注明口径。发布另由后续任务处理。
