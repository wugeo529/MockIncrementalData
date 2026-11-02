# 来源与第三方组件

作者：wugeo529。用户明确授权从既有data-access三表模拟器中提取独立项目；原工程基线d1c2a76575908efaaa98ab73e7243d955472f15e，提取来源包含当时未提交的模拟器工作，因此下列文件hash用于定位实际源字节，不声称它们已经存在于该Git提交。未复制平台实现、部署fixture、私人凭据或其他贡献者文档。

```json
{
  "signal_source.py": "1667d07270eb575e8ca3095838969df5d436a5f8d261d003dd8099a095a52846",
  "dashboard.py": "80315116b585b333861a8a9efac306634b2776945631cca9f6680598dbb394da",
  "dashboard.html": "59595b38d7d473ae0f40c69368323ccf6ec4ddb4836dbee41ee1786fce8336c2",
  "dashboard.js": "32f29bff459a4b423914c7d6c8d8a70440f7fa384e5421a138746b9c27519b54",
  "dashboard.css": "5d309ce54d2abf11c70895ba78c6b4ab3f4ca572077c6d8b48e210d800eae844",
  "schema.json": "9e6c2a12efd7ee367ab6815a1bfd096f80c1b631e00fa95f3a3bc578fb460bed",
  "mysql-schema.sql": "e1c4eed6b64d40c2fc1e7771f37d76063af1cf4383793fcd6b2d9b74bdbf9083",
  "postgresql-schema.sql": "761d5622eecc7c4532de5d83f526445d09f57aaa52cbdec2a17abfec33b98bdd"
}
```

显示与进程运行时：Electron（随发行包保留其LICENSE与LICENSES.chromium.html）。模拟引擎：Python、PyInstaller、PyMySQL、psycopg2-binary、cryptography及其依赖，各自保留对应授权声明。构建仅使用公开发布依赖，不将私人数据库或测试快照纳入分发。

本仓库当前未授予单独的开源许可证（package.json: UNLICENSED）；依赖组件继续遵循其各自许可证。后续如需指定项目开源许可证，由仓库所有者决定。
