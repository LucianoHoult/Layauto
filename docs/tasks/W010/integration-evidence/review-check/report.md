# W010 集成前复核交付事实检查

日期：2026-11-06。执行者：PM委派的只读专项 `/root/w010_integration_review_check`。本项核查版本、证据身份和E-N01摘要精度，不重新进行完整代码review、产品验证或PM验收。

**结论：只读事实核验通过，未发现阻止集成的问题，必须修正项0。** 独立合并前review的0项结论及P3非阻塞性质有相应版本和原输出支持。

## 对象与实际核查

- 新review交付：`f99b59abc88305133661dd2a510fbcaf36a9c6c6`。
- 实际受审head：`c4909ab679d0c0806200fcb132db8a5de1ad3e75`。
- 产品/正式测试：`0f5029df935bc0acd106aad1bc2be81304d4f442`。

实际读取根AGENTS、协作/环境规则、W010独立premerge报告和机器证据，运行标准库只读 `audit.py`。脚本以指定Git版本取证，同时核当前受管源字节，避免把后续PM文档改变误判为原交付变化。

1. f99相对c490共73个变更路径，均限新独立review报告/目录和任务文件；任务文件仅在reviewer区增加R2，原PM段与其他段未改。
2. 最终252项source/tests/config逐字节匹配产品Git、已审c490、review交付f99及当前文件；94项runtime清单完整。源清单SHA-256为`cef29336dba1bf572fd30227f354365d4a4d780e721d089b70095589d0f55889`。完整tar恰含252个唯一普通成员，路径/字节与清单一致。
3. 独立premerge的完整pytest和typing回执均记录head/finished_head为c490、exit0；各原始stdout/stderr hash吻合。真实原输出分别为**1465 passed**与**48 source files**，命令范围为完整unit/contracts与strict mypy。
4. 新来源、几何、异常及45项工程专项的原脚本/输出hash、指定源码hash与本交付一致；补充readback wire大小来自通过的source probe。以上是原执行证据的内容/身份核查，不冒称本机重跑这些动态检查。

## E-N01准确澄清

四个去除optional normalized cache的direct路径样例：

| case | result wire bytes |
| --- | ---: |
| normal | 15,470,850 |
| special_cut_islands | 12,579,736 |
| extra_20_isolated_M1 | 17,086,974 |
| extra_8_duplicate_CONTACT | 16,096,466 |

建议PM澄清为：**四例无optional cache的direct回执wire为12,579,736–17,086,974 bytes（十进制约12.58–17.09 MB），原摘要15.47–17.09 MB遗漏cut-islands下界。原正常含cache的direct wire约22.79 MB；本次独立review补充readback完整回执为59,422,834 bytes（约59.42 MB），因保留链不同不作同一身份比较。累积进程RSS高水位约988 MiB，不是逐例增量；这些均非生产资源上界。**

E-N01仅校正文字下界，原最大wire、累积RSS及全部性能样例max-pieces=1的限制未被低估。无需产品改动或新增合并门槛，可在PM集成说明中澄清并保留原报告/证据。

## 命令、产物与限制

```sh
cd /workspace/Layauto
PYTHONDONTWRITEBYTECODE=1 python3 -B /workspace/work/w010-integration/review-check/audit.py > /workspace/work/w010-integration/review-check/audit-result.json 2> /workspace/work/w010-integration/review-check/audit.stderr.txt
```

最终exit0，stderr空；完整结果为 `audit-result.json`。脚本初版按字符diff检查插入位置时，公共`##`前缀使harness把位置算到PM标题的两个字符之后，断言失败；已改为按行diff以对应Git实际新增行。原harness错误保留在 `audit-initial.stderr.txt`，不记产品finding或通过结果。

没有运行pytest、typing、构建、安装或性能探针，没有重新观察历史命令执行，也未修改仓库、产品、正式测试、fixture、报告或Git状态；所有本项材料只写工作区外。实际合并和合并后组合验证由主PM继续完成。
