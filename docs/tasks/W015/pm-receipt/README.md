# W015 PM接收与集成检查

交付`a73713bc8ff7e1e2d4cc61ab93fbd3ace178753d`，核心方案冻结`a2d55dbf20c1b07b9f5ca3faddad9c6a8721637b`。
PM核11个核心文档/候选输入hash不变，284个runtime/tests/config文件与已验收产品相同，
阅读全部合同/样张/实施方案及独立review，F01–F04关闭依据成立。

`delivery-check`、`identity`、`candidate`在交付head运行；`merge-candidate`在PR72实际merge
`d0bb5628384f3a9fec1fe87b6311b854996f574b`运行。merge tree与交付head相同。
每项command记录argv/cwd/完整HEAD/耗时/exit及stdout/stderr哈希，实跑均exit0。
候选探针仅验证现parser能消费原raw及候选引用，得到2/4/2/8条记录，**不是新分析API运行**。
源码检查脚本约束原PM段不变，复现须回记录中的交付版本；后续PM验收补记后不可用该检查
声称当前导航仍未修改。原输出不覆盖，完整hash见[receipt.json](receipt.json)。

原W014工程矩阵按未变产品身份采信；本轮未重跑全量/typing/构建/安装/性能/EDA。
本轮方案通过，实施由[W016](../../W016-single-cell-analysis.md)负责；不表示生产适用。
