# 开发与发布

独立仓库：https://github.com/wugeo529/MockIncrementalData 。模拟器逻辑与平台分支分开维护；本仓库不需要平台工程即可运行。

- Python 3.12 / Node 24；Electron与打包工具精确版本由package-lock.json固定。
- `engine/signal_source.py` 修改字段或生成规则时，同步更新DDL/schema.json、字段说明及测试。
- `python -m unittest discover -s engine -p "test_*.py"`，`npm test`。
- 真实数据库回归：`python scripts/native_acceptance.py --config <本机私有JSON路径>`。脚本仅创建自己随机命名的signal_sim_accept_*临时库并在完成后删除，不能以此测试现有业务库。
- 桌面回归：安装Playwright到独立测试工具环境后，设置PLAYWRIGHT_MODULE为其模块绝对路径、PYTHON_EXE为测试用Python，运行`node scripts/desktop_acceptance.cjs <打包exe路径> <私有MySQL或PG配置JSON> <证据目录>`。测试用Python只建立/清理临时数据库，启动的客户端使用自己的引擎；测试会暂存并恢复原本机连接设置。请关闭已有模拟器客户端再测试。
- `python scripts/build-engine.py` 在当前操作系统构建原生引擎。
- `npm run dist:win` / `dist:linux` / `dist:mac`。各系统分别构建，不承诺跨系统执行相同二进制。
- Windows本地依赖可缓存安装，所有构建工具只用于开发电脑；最终安装包包含所需运行时。
- 版本写入package.json及CHANGELOG.md，执行测试和原生包验收后推送。GitHub Actions构建各系统并保存Artifacts；不将二进制或私人配置提交进Git历史。

Git和打包均按白名单：不含平台fixture/部署配置/补丁、个人凭据、数据库数据目录、应用用户配置。`*.private.json`、node_modules、build、release均忽略。

发布前要区分：本地Windows已验证、CI构建成功、目标系统真实安装通过，是三个不同证据。macOS代码签名/公证、Linux桌面依赖和Windows签名须按实际供应条件报告，不把未签名产物描述成已签名。

本次已执行依赖审计，发现构建工具链的中等级依赖告警（具体清单见验收记录）；没有运行时业务npm依赖。不得使用`audit fix --force`把当前打包工具自动降级为旧大版本；升级和overrides必须有兼容测试。
