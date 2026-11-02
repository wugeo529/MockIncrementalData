# 0.1.0 本地验收报告

日期：2026-11-02。结论：Windows x64 ZIP与安装版在本机真实桌面操作通过；MySQL、PostgreSQL源端原生回归通过。本报告不代替其他主机/操作系统实机验收或消费平台的生产资格。

## 已执行

|项目|结果及证据|
|---|---|
|Python单元回归|19/19通过；字段、主键、仿真标记、运行互斥、连接校验/失败保留/密码复用、PG目标库权限及schema范围|
|Node回归|4/4通过；慢连接串行轮询、加密设置、禁止明文回退、同源IPC|
|真实MySQL 8.4|独占随机signal_sim_accept_*库：初始化6/6/6、再次初始化保留、插入7/7/6、修改不改行数、删除6/6/5、自动3批、运行中停止、API鉴权、拒绝夹有其他表的初始化；通过后清理自己的测试库|
|真实PostgreSQL 14.22|同等源端用例通过；另外人为设置数据库search_path为fixture_shadow,public，验证引擎固定public再建表/写入|
|Windows包内PG驱动|同一最终ZIP的真实窗口连接PG，初始化、I/U/D、自动/停止、加密保存/重开和退出清理通过；没有借用宿主Python驱动|
|桌面ZIP|完整解压到新目录，通过真实窗口逐按钮测试；执行时PATH仅保留Windows系统目录，客户端无需宿主Python/Node|
|桌面安装版|NSIS静默安装到用户指定目录返回0；安装后的EXE通过同一组真实窗口测试|
|窗口操作|测试连接、保存、初始化取消/确认、未保存目标拒绝初始化、手动I/U/D、删除取消/确认、三表切换、自动3批结束、运行中停止、刷新均通过|
|重启与退出|两种包均关闭后本机服务不可访问；重开可解密恢复连接；测试结束恢复原本机设置|
|窗口隔离|真实进程验证nodeIntegration=false、contextIsolation=true、sandbox=true，页面无require|
|凭据|本机设置中没有明文测试密码，使用系统加密；源码、分发包不携带用户连接配置|

可复核证据位于[MySQL原生结果](evidence/native-mysql.json)、[PG原生结果](evidence/native-postgres.json)、[ZIP窗口结果](evidence/windows-portable.json)、[安装窗口结果](evidence/windows-installed.json)、[ZIP-PG窗口结果](evidence/windows-postgres.json)。界面截图见[Windows窗口](evidence/windows-desktop.png)。回归脚本在scripts目录，私有账号文件不属于证据或交付。PG补测初次在重开后等待默认MySQL项连通而超时，改为显式选择已保存PG连接后全流程通过，属于测试选择错误；没有修改应用行为或重新打包。

独立复核的三个P2问题均已修复：慢响应被新轮询持续丢弃、PG目标库用户被维护库权限误阻断、PG search_path可能使写入与校验不在同一schema。相应回归已执行，最终包重新构建并重新完成ZIP/安装验收。

## 构建与尚未通过项

- Windows运行时Electron45.2.1、Python3.12.14；Windows11 x64本机验收。工具下载遇到TLS中断时使用镜像获取字节，并按发布方校验值验证；未关闭证书或校验。最终构建在全新输出目录完成。构建中间失败没有作为正式产物。
- Windows包未代码签名；[首轮CI](https://github.com/wugeo529/MockIncrementalData/actions/runs/41402659925)已通过三系统构建及MySQL/PG原生测试，共5个job。CI源码为a1f74db260516a1cbb696b1c151350bc8ef473bd，结果见[CI收据](evidence/ci-first-build.json)。Linux/macOS目标系统的真实窗口安装/运行尚未验收；Windows包不能在其他操作系统直接执行。
- 本次npm审计有15个中等级构建依赖告警、0高危、0严重，根链涉及minimatch/glob等；它们属于开发打包依赖，应用没有业务npm运行依赖。未用强制降级规避告警；后续工具升级需重新验证。不能据此宣称整包不存在安全问题。
- 没有随包安装MySQL/PG数据库，没有迁移用户数据、消费位点或自动建立下游Mapping。需要运行中的目标数据库和使用者自己的账号。
- PostgreSQL本轮是源端模拟；消费平台WAL采集、跨主机网络、容量/HA/72小时长稳及完整本体消费不在本独立客户端验收结论内。
- 发布源码、安装包、ZIP的提交/标签与下载校验值以仓库Releases及校验文件为准。源码ZIP仅供开发，不等同于桌面ZIP。

## 发布收据

[v0.1.0 Release](https://github.com/wugeo529/MockIncrementalData/releases/tag/v0.1.0)源码标签指向a1f74db260516a1cbb696b1c151350bc8ef473bd。两个Windows文件已实际上传，GitHub返回的大小、SHA256与[本地制品清单](evidence/artifacts.json)一致。公开交付不含平台数据库盘点、私人连接设置或平台运行配置；平台分支没有随本次独立项目发布推送。
