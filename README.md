# MockIncrementalData · 增量数据源模拟器

一个独立的桌面模拟器，用 GPS 位置、IP 会话和目标档案三张表，持续产生可复现的新增、修改和删除事务。界面内嵌，Windows 安装包包含显示窗口、Python 引擎和数据库驱动；使用电脑不需要另外安装 Python、Node 或数据平台。

## 快速使用

1. 下载对应系统的安装包或 ZIP。Windows ZIP 解压完整文件夹后，双击 `MockIncrementalData.exe`；或运行 `Setup` 安装程序。
2. 本机先准备好运行中的 MySQL。打开应用，点右上 **数据库连接**。
3. 类型选 MySQL；本机通常填 `127.0.0.1`、`3306`，数据库填 **`signal_sim_demo`**，账号密码填你自己的数据库账号。
4. 点 **测试连接 → 保存连接 → 初始化模拟表 → 确认初始化**。初始化会创建专用数据库和三张表；需要建库建表权限。已有完整三表只校验，不会重置。
5. 点 **完成**。先点 **新增一批**，表计数及“已提交操作”立即显示变化；切换 GPS、IP 会话、目标档案查看真实源表。
6. 设置发送间隔和本轮最多批数，点 **开始自动模拟**。点 **停止自动模拟**停止后保留已提交数据。应用关闭时会停止本应用的模拟引擎。

“修改最近记录”更新已有业务数据；“删除最近一批”会二次确认。不会扫描或修改专用三表之外的业务表。数据库名必须以 `signal_sim_` 开头，不能直接指定现有生产库。

可选择在本机加密记住密码；保存内容绑定当前系统账号，迁移主机后请重新填写。安装包和仓库不包含任何已连接账号。未选择记住密码时，密码只用于当前会话。

## 模拟的是什么

- GPS：6个虚构终端的运动轨迹，包含位置、方向、速度、卫星和波束字段。
- IP：与同一虚构终端关联的会话，使用文档测试网段地址。
- target：6个虚构终端的档案，按终端身份更新。
- `dumm_flag=1` 标识仿真记录。每个操作在一个源数据库事务中处理三张表。
- 自动循环每10批中的第10批删除；其余每3批中的第3批修改；其他批次新增。

模拟器提交普通数据库事务。MySQL 开启 Binlog 后会由数据库产生真实日志；消费系统再自行采集、加工和发布。本程序不伪造 Binlog，不直接写入下游 RAW、湖表或本体。

PostgreSQL 也可作源端模拟；这不代表任何消费平台已经支持 PostgreSQL WAL 增量采集。两种源结构的差异见 [字段结构](docs/SCHEMA.md)。

## 安装包与适用范围

- 本轮优先验证 **Windows x64**。
- Linux、macOS 有独立构建任务，产物须在对应系统生成和验收。一个 Windows EXE 不能直接跨系统使用。
- GitHub Actions 的 **Test and build desktop** 提供按系统区分的构建产物。源代码 ZIP 与可直接打开的安装包是不同交付物。
- MySQL/PostgreSQL 数据库服务器由使用者准备，不随应用安装。连接远程数据库时填写对应主机地址。

详细步骤见 [使用说明](docs/USER-GUIDE.md)，构建方式见 [开发说明](docs/DEVELOPMENT.md)，验收和未通过项见 [验收报告](docs/ACCEPTANCE.md)。

## 开发

需要 Node 24、Python 3.12。安装依赖后：

```text
python -m pip install -r build-requirements.txt
npm ci --ignore-scripts
node node_modules/electron/install.js
python -m unittest discover -s engine -p "test_*.py"
npm test
python scripts/build-engine.py
npm run dist:win
```

开发启动：`npm start`；Python 不在 PATH 时设置 `MOCK_PYTHON` 为开发环境解释器路径。安装后的应用使用内置引擎，不读取这个开发选项。

## 项目边界

本项目独立维护模拟器、字段结构和打包脚本，不包含具体平台部署配置或平台模块实现。后续增加数据模型、发送策略和数据库类型时，先保留当前结构兼容性，再补源端和消费端分别可验证的测试。

来源与第三方组件见 [来源记录](docs/SOURCE-NOTICE.md)。
