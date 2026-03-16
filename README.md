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


## 发布到 GitHub Release（自动化）

仓库已提供工作流：`.github/workflows/release.yml`。

### 触发方式

1. 确保本地提交已推送到 GitHub 远程仓库
2. 创建并推送语义化标签（如 `v1.0.0`）

```bash
git tag v1.0.0
git push origin v1.0.0
```

推送标签后，GitHub Actions 会自动：

- 还原/构建/测试
- 生成两个发布包：
  - `GaoGaoWorkSpace-win-x64-framework.zip`
  - `GaoGaoWorkSpace-win-x64-self-contained.zip`
- 自动创建 GitHub Release 并上传附件

你也可以用脚本：

```powershell
./scripts/publish_release.ps1 -Version v1.0.0
```

## 常见报错排查（你这次遇到的错误）

### 1）“当前上下文中不存在名称 Path / File / Directory”

这通常是代码文件缺少 `System.IO` 命名空间引用导致。当前仓库已修复该问题（在 `MainViewModel.cs` 增加了显式 `using System.IO;` 等）。

如果你本地仍看到旧错误：

1. `git pull` 拉最新代码
2. Visual Studio 菜单：`生成` -> `清理解决方案`
3. 再执行：`生成` -> `重新生成解决方案`

### 2）“XML 命名空间中不存在标记 MainViewModel”

这个错误多数是**上一步 C# 编译失败引起的连带 XAML 错误**。

按下面顺序处理：

1. 先解决 C# 编译错误（尤其是 `Path/File/Directory`）
2. 关闭 `MainWindow.xaml` 设计器标签，再重新打开
3. 执行 `重新生成解决方案`

### 3）“不再需要使用 Microsoft.NET.Sdk.WindowsDesktop SDK”

这是 SDK 提示，不是致命错误。当前仓库已改为推荐写法：

- `GaoGaoWorkSpace.App.csproj` 使用 `Microsoft.NET.Sdk`
- 并保留 `<UseWPF>true</UseWPF>`

### 4）“Your Windows doesn't fully support CET”

这是系统环境提示（和 Windows 更新/安全特性相关），一般不影响你调试本项目。

建议：

- 在 Windows 更新里安装所有可用更新
- 更新后重启电脑

