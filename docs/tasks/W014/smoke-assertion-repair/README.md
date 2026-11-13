# 安装烟测断言修正与静态复核

独立最终专项发现 `check_body` 对 mismatch 仍套用正常 MN0 四边 margin。
原脚本完整保存在 `installed_smoke.before.py`，字节身份见 `tool-change.json`，
修改差异见 `installed_smoke.patch`。本次只给 `check_body(body, rows, case)` 传入
case，normal 精确要求 `(20,20,20,20)`，mismatch 精确要求 `(20,20,20,26)`；
原四边、min、阈值和所有其它断言均保留。

`verify_geometry.py` 只使用 stdlib 读取真实 GDS/body/tech owner 和原 R2 capture
manifest，未导入 runtime、fixture helper、oracle/spec/expected。它逐 GDS record
读取原 XY，按真实 formats 唯一 nominal tick 和 REAL8 半 ULP 合同精确核单位；
不取整图形。最终原输出是 `geometry-math.final.stdout.json`。

实际核对：两份 source 均40个 BOUNDARY、相同 layer 数量；全部 local bindings
各自唯一匹配真 GDS。唯一 drawn bbox 变化为 MN0 active 的上边70→64nm，
因此 BN 包围四边由20/20/20/20变为20/20/20/26，最小仍20。MP0四边仍为
20/10/20/20，全部本地 body/rail、外部 body/tap/rail 与关联完全相同；tap两侧
最小包围仍8/2nm。独立原始矩形/交集计量复得目标总面积35090/34634nm²、
实际 FIN5/7与4/7；31个captured source的逻辑路径集相同，替换恰为烟测已声明
的5个capture文件。

其余烟测差异静审：source CDL 与预期D/G/S/B不变；shared gate及本地14/8/6
拓扑不变；全部body规则margin min/边长/阈值不变；capture数量31、图形数量40
不变。FIN与coverage总面积已按 case 分别断言；mismatch继续保留source5对
observed4及整体source comparison=mismatch。原W013已验收直接覆盖3170nm²
和本地unknown body的断言继续保留，不用端子一致升级整体匹配。

双3.10/3.12只运行CLI help和Python3.10语法检查，未运行产品链或安装烟测。
`W014_SMOKE_READY=True`仍只表示断言已集成。完整烟测须由最终clean安装矩阵实跑。

独立stdlib核对脚本的准备失败也保留：attempt01在解析格式的字符串分子/分母时
误用Fraction(str,str)，尚未读GDS；attempt02的最后manifest连接误假设GDS URI
带斜杠，数学断言已通过但脚本整体失败；extended第一次按原URI直接比较不同
输入目录的绝对normalized cache路径，最后集合检查失败。修正均只涉及独立证据
脚本的token/逻辑路径处理，未改产品、fixture、原资源证据或烟测数学标准。
