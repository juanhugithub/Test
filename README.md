# GaoGaoWorkSpace（糕糕工作台）

本仓库包含两部分：

- 旧版 Python 原型：`folder_tree_workbench/`
- 新版 WPF 重构工程：`src/`（C# + .NET 8 + MVVM）

## 新版架构（WPF）

```text
src/
  GaoGaoWorkSpace.App/            # WPF 启动项目（Window、App）
  GaoGaoWorkSpace.Core/           # 领域模型、接口、业务服务
  GaoGaoWorkSpace.Infrastructure/ # 文件系统、JSON持久化、Shell、日志
  GaoGaoWorkSpace.UI/             # ViewModel（MVVM）
  GaoGaoWorkSpace.Tests/          # 单元测试
```

## 已实现能力（V1）

- 读取目录并展示树结构（含文件/文件夹、基础过滤）
- 节点搜索（名称+路径）
- 收藏系统（分组字段、别名字段、持久化）
- 导出 XMind 兼容 Markdown
- 导入 Markdown、结构预览、创建目录（默认仅目录，跳过覆盖）
- 风险路径识别（UNC、盘根、系统目录）
- 本地 JSON 配置与本地日志

## 运行（本地 Windows）

```bash
dotnet restore
dotnet build GaoGaoWorkSpace.sln
```

启动：

```bash
dotnet run --project src/GaoGaoWorkSpace.App
```

## 测试

```bash
dotnet test src/GaoGaoWorkSpace.Tests
```

## 发布建议

- Framework-dependent:

```bash
dotnet publish src/GaoGaoWorkSpace.App -c Release -r win-x64 --self-contained false
```

- Self-contained:

```bash
dotnet publish src/GaoGaoWorkSpace.App -c Release -r win-x64 --self-contained true
```
