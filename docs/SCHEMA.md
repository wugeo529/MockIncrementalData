# 三表结构

字段真源：`engine/signal_source.py` 的COLUMNS；机器可读结构：`engine/schema.json`；两种数据库DDL与其一致。

|表|字段数|主键与兼容差异|
|---|---:|---|
|s_signal_2_1_gps|17|两种版本均id主键；保留原字段拼写alititude|
|s_signal_2_1_ipsession|11|PG原结构未加主键；MySQL演示版id主键|
|s_signal_2_1_target|PG9/MySQL10|PG原结构无新增主键；MySQL演示版增加_sim_id技术主键|

PG的int4/int2对应MySQL INT/SMALLINT；timestamp(6)/(0)对应DATETIME(6)/(0)；PG float8在MySQL演示版使用DECIMAL(20,8)，这是消费兼容转换，不是声称二进制浮点与十进制语义完全等价。varchar长度255、可空性、注释和字段顺序保留。

所有生成行dumm_flag=1，IMSI以00101开头，终端名称/坐标/目标信息均为合成；IP使用文档测试网段。不会复制原截图里的具体业务记录。日期按UTC无时区保存。
