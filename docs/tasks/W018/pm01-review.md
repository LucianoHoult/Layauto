# W018 PM-01 独立补修复核

**PM-01 已关闭。** 未参与此次产品及正式测试修正的 reviewer 分别从基线 `dc82d2348a748d50d7de3886e999b1d198d0c1d1` 和冻结修正 `61dc2087b8d242cc01142cf79b9407486061219d` 的 Git 归档运行同一探针。两者的产品差异限于公共闭合对象校验器的未知键分支。该分支先将字面 `~` 编为 `~0`，再将 `/` 编为 `~1`，作为一个字段路径段附加。正式合同测试新增三种字面键的文件入口回归。[PM 原反例](../W018-coordinate-occupancy-core.md#pm1-receipt)

探针重绑 W003/W004 副本的 coordinate owner，从实际 site 读取、认证 GDS 并请求投影。独立解码器逐段读取错误引用所指的**同一份捕获字节**。下表的路径相对于 `/coordinate_projection/layers/LI/`，相邻的合法嵌套字段 `x_edges.pitch_dbu` 在两次归档及所有反例中均读为 20。

| 插入位置与字面键 | 基线按返回路径读取 | 修正后返回的相对路径 | 修正后读取 |
| --- | --- | --- | ---: |
| LI 下的 `x_edges/pitch_dbu` | 误读合法值 20 | `x_edges~1pitch_dbu` | 987 |
| LI.x_edges 下的 `pitch~1dbu` | 无法解析到该字段 | `x_edges/pitch~01dbu` | 988 |
| LI.y_edges 下的 `~0/pitch~1_dbu` | 无法解析到该字段 | `y_edges/~00~1pitch~01_dbu` | 989 |

三次错误均为 `InvalidProjectionDeclaration`，URI 均为 `tech/layer-discretization.yaml`。逐项确认文件实读 bytes、捕获 bytes 及错误引用的 SHA-256 绑定。第一例的 owner 为 `4c7ec676c711dd754ccba9a2767b1206838cfe9028a83345a68abd945a52f829`。每次错误均保留传入的同一个 GeometryResult 实例，W008 几何值与加入声明前相等、40 条原记录完整。

## 复现与范围

Python 3.12.14、PyYAML 6.0.3、pytest 9.2.0。第一条命令在补修归档返回 987、988、989；传入基线归档目录则重现上述三项失败。第二条在补修归档复跑公共 schema 的相关旧配置诊断与 W018 合同，52 passed，76 deselected。[独立探针](pm01_review_probe.py)

```sh
python -B docs/tasks/W018/pm01_review_probe.py
python -B -m pytest -p no:cacheprovider -q tests/unit/test_w005_config.py tests/unit/test_w005_unicode.py tests/contracts/test_w018_projection.py -k 'unknown or missing or unicode'
```

现有双解释器矩阵仍绑定此前冻结的 `186c426ea550a6941ead417cd640a86c37017ba5`。本次对补修按 PM1 交接执行定向复核。正式 fixture 子树和审阅样例身份与原矩阵一致；若实际合并改动字段定位、捕获绑定或上述测试，应补跑对应探针和回归。
