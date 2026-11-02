# 更新记录

## 0.1.0 — 2026-11-02

- 提取独立GPS/IP/target三表模拟器，保留MySQL及PostgreSQL源端逻辑。
- 增加内嵌页面的Windows桌面客户端、自带Python引擎、连接设置、显式初始化与本机加密密码保存。
- 保留手动增删改、有限批数自动模拟、停止、最新数据、提交日志。
- 独立构建、测试和按系统打包；Windows优先验收，Linux/macOS构建任务分别提供产物。
- 不包含消费平台的Binlog/WAL采集、Pipeline或Mapping实现。
