# GaoGaoWorkSpace（糕糕工作台）

这是 **C# + WPF + MVVM** 的桌面版本工程（.NET 8）。

## 项目结构

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

## 在本地用 Visual Studio 测试

### 1) 下载到本地

```bash
git clone <你的仓库地址>
cd Test
```

或者如果你已经有仓库，只需拉最新：

```bash
git pull
```

### 2) 用 Visual Studio 打开

- 使用 **Visual Studio 2022**（建议 17.8+）
- 勾选工作负载：
  - **.NET 桌面开发**
- 打开根目录下：
  - `GaoGaoWorkSpace.sln`

### 3) 还原并运行

在 VS 中：

1. 右键解决方案 → `还原 NuGet 包`
2. 将 `GaoGaoWorkSpace.App` 设为启动项目
3. 选择 `Debug | Any CPU`（或 `x64`）
4. 按 `F5` 运行

### 4) 运行测试

- 打开 `测试` -> `测试资源管理器`
- 点击 `运行所有测试`
- 或在终端执行：

```bash
dotnet test src/GaoGaoWorkSpace.Tests
```

## 命令行构建/运行

```bash
dotnet restore
dotnet build GaoGaoWorkSpace.sln
dotnet run --project src/GaoGaoWorkSpace.App
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
