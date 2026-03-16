using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using GaoGaoWorkSpace.Core.Interfaces;
using GaoGaoWorkSpace.Core.Models;
using GaoGaoWorkSpace.Core.Services;
using GaoGaoWorkSpace.Infrastructure.Persistence;
using GaoGaoWorkSpace.Infrastructure.Services;

namespace GaoGaoWorkSpace.UI.ViewModels;

public partial class MainViewModel : ObservableObject
{
    private readonly IFileSystemScanner _scanner;
    private readonly IMarkdownExportService _markdownExportService;
    private readonly IMarkdownImportService _markdownImportService;
    private readonly IStructureCreationService _structureCreationService;
    private readonly ISearchService _searchService;
    private readonly ISafetyGuardService _safetyGuardService;
    private readonly IFavoritesService _favoritesService;
    private readonly IShellOpenService _shellOpenService;
    private readonly ILoggingService _loggingService;
    private readonly AppConfigService _configService;

    private readonly string _dataDir;
    private TreeNodeModel? _currentTreeRoot;
    private IReadOnlyList<MarkdownNode> _importedNodes = [];

    public ObservableCollection<TreeNodeModel> RootNodes { get; } = [];
    public ObservableCollection<TreeNodeModel> SearchResults { get; } = [];
    public ObservableCollection<FavoriteItem> Favorites { get; } = [];
    public ObservableCollection<string> RecentPaths { get; } = [];
    public ObservableCollection<BuildPreviewItem> BuildPreviewItems { get; } = [];

    [ObservableProperty] private string _workspacePath = string.Empty;
    [ObservableProperty] private string _statusText = "就绪";
    [ObservableProperty] private string _searchKeyword = string.Empty;
    [ObservableProperty] private string _selectedNodePath = string.Empty;
    [ObservableProperty] private string _selectedNodeInfo = "请选择节点";
    [ObservableProperty] private string _exportMarkdownPath = string.Empty;
    [ObservableProperty] private string _importMarkdownPath = string.Empty;
    [ObservableProperty] private string _targetRootPath = string.Empty;
    [ObservableProperty] private string _buildSummaryText = "尚未执行";
    [ObservableProperty] private bool _includeFiles = true;
    [ObservableProperty] private bool _includeHidden;
    [ObservableProperty] private bool _createFiles;
    [ObservableProperty] private string _favoriteFilter = string.Empty;
    [ObservableProperty] private FavoriteItem? _selectedFavorite;
    [ObservableProperty] private TreeNodeModel? _selectedNode;

    public MainViewModel()
    {
        _dataDir = Path.Combine(AppContext.BaseDirectory, "data");
        var configDir = Path.Combine(AppContext.BaseDirectory, "config");
        var logDir = Path.Combine(AppContext.BaseDirectory, "logs");

        Directory.CreateDirectory(_dataDir);
        Directory.CreateDirectory(configDir);
        Directory.CreateDirectory(logDir);

        var store = new JsonFileStore();
        _scanner = new FileSystemScanner();
        var markdownService = new MarkdownService();
        _markdownExportService = markdownService;
        _markdownImportService = markdownService;
        _searchService = new SearchService();
        _safetyGuardService = new SafetyGuardService();
        _structureCreationService = new StructureCreationService(_safetyGuardService);
        _favoritesService = new FavoritesService(store, Path.Combine(_dataDir, "favorites.json"));
        _loggingService = new LoggingService(Path.Combine(logDir, "operations.log"));
        _shellOpenService = new ShellOpenService();
        _configService = new AppConfigService(store, Path.Combine(configDir, "appsettings.json"));
    }

    public async Task InitializeAsync()
    {
        var config = await _configService.LoadAsync();
        WorkspacePath = config.LastOpenedWorkspace;
        IncludeFiles = config.ExportIncludeFiles;
        CreateFiles = config.BuildCreateFiles;

        var favorites = await _favoritesService.LoadAsync();
        Favorites.Clear();
        foreach (var item in favorites.OrderByDescending(x => x.IsPinned).ThenBy(x => x.SortOrder))
            Favorites.Add(item);

        RecentPaths.Clear();
        foreach (var p in config.RecentPaths)
            RecentPaths.Add(p);

        StatusText = "配置与收藏已加载";
    }

    [RelayCommand]
    private async Task LoadWorkspaceAsync()
    {
        if (string.IsNullOrWhiteSpace(WorkspacePath) || !Directory.Exists(WorkspacePath))
        {
            StatusText = "请选择有效目录";
            return;
        }

        var root = await _scanner.ScanAsync(WorkspacePath, IncludeFiles, IncludeHidden, null, cancellationToken: default);
        _currentTreeRoot = root;

        RootNodes.Clear();
        RootNodes.Add(root);
        StatusText = $"已载入：{WorkspacePath}";
        await AddRecentPathAsync(WorkspacePath);
        await _loggingService.WriteAsync(new OperationLogEntry { Action = "LoadWorkspace", Message = WorkspacePath });
    }

    [RelayCommand]
    private void SearchTree()
    {
        SearchResults.Clear();
        if (_currentTreeRoot is null || string.IsNullOrWhiteSpace(SearchKeyword)) return;
        foreach (var item in _searchService.SearchTree(_currentTreeRoot, SearchKeyword))
            SearchResults.Add(item);
        StatusText = $"搜索完成，命中 {SearchResults.Count} 项";
    }

    [RelayCommand]
    private async Task ExportMarkdownAsync()
    {
        if (_currentTreeRoot is null || string.IsNullOrWhiteSpace(ExportMarkdownPath))
        {
            StatusText = "请先加载目录并设置导出文件";
            return;
        }

        var markdown = _markdownExportService.Export(_currentTreeRoot, IncludeFiles);
        Directory.CreateDirectory(Path.GetDirectoryName(ExportMarkdownPath)!);
        await File.WriteAllTextAsync(ExportMarkdownPath, markdown, Encoding.UTF8);
        StatusText = $"导出完成：{ExportMarkdownPath}";
        await _loggingService.WriteAsync(new OperationLogEntry { Action = "ExportMarkdown", Message = ExportMarkdownPath });
    }

    [RelayCommand]
    private async Task ImportMarkdownPreviewAsync()
    {
        if (string.IsNullOrWhiteSpace(ImportMarkdownPath) || !File.Exists(ImportMarkdownPath))
        {
            StatusText = "请选择有效的 Markdown 文件";
            return;
        }

        var text = await File.ReadAllTextAsync(ImportMarkdownPath, Encoding.UTF8);
        _importedNodes = _markdownImportService.Parse(text);
        var previewRoot = _markdownImportService.BuildTree(_importedNodes, "MarkdownPreview");

        RootNodes.Clear();
        RootNodes.Add(previewRoot);
        StatusText = $"解析成功，共 {_importedNodes.Count} 个节点";
    }

    [RelayCommand]
    private void PreviewBuild()
    {
        BuildPreviewItems.Clear();
        if (_importedNodes.Count == 0 || string.IsNullOrWhiteSpace(TargetRootPath))
        {
            StatusText = "请先导入 Markdown 并填写目标目录";
            return;
        }

        foreach (var item in _structureCreationService.Preview(_importedNodes, TargetRootPath, CreateFiles))
            BuildPreviewItems.Add(item);
        StatusText = $"预览完成，条目 {BuildPreviewItems.Count}";
    }

    [RelayCommand]
    private async Task ApplyBuildAsync()
    {
        if (_importedNodes.Count == 0 || string.IsNullOrWhiteSpace(TargetRootPath))
        {
            StatusText = "无可执行结构创建任务";
            return;
        }

        if (!_safetyGuardService.IsWriteAllowed(TargetRootPath, out var reason))
        {
            StatusText = $"风险路径：{reason}";
            return;
        }

        var summary = _structureCreationService.Apply(_importedNodes, TargetRootPath, CreateFiles);
        BuildSummaryText = $"新建文件夹：{summary.CreatedDirs}，已存在文件夹：{summary.ExistingDirs}，新建文件：{summary.CreatedFiles}，跳过：{summary.Skipped}";
        StatusText = "结构创建完成";

        await _loggingService.WriteAsync(new OperationLogEntry
        {
            Action = "ApplyBuild",
            Message = BuildSummaryText
        });
    }

    [RelayCommand]
    private async Task AddFavoriteAsync()
    {
        if (SelectedNode is null || string.IsNullOrWhiteSpace(SelectedNode.FullPath)) return;
        if (Favorites.Any(f => string.Equals(f.TargetPath, SelectedNode.FullPath, StringComparison.OrdinalIgnoreCase)))
        {
            StatusText = "该节点已收藏";
            return;
        }

        var item = new FavoriteItem
        {
            DisplayName = SelectedNode.Name,
            TargetPath = SelectedNode.FullPath,
            NodeType = SelectedNode.NodeType,
            GroupName = "默认",
            SortOrder = Favorites.Count
        };

        Favorites.Add(item);
        await PersistFavoritesAsync();
        StatusText = $"已收藏：{item.DisplayName}";
    }

    [RelayCommand]
    private async Task RemoveFavoriteAsync()
    {
        if (SelectedFavorite is null) return;
        Favorites.Remove(SelectedFavorite);
        await PersistFavoritesAsync();
        StatusText = "收藏已移除";
    }

    [RelayCommand]
    private async Task OpenFavoriteAsync(FavoriteItem? favorite)
    {
        if (favorite is null) return;

        _shellOpenService.Open(favorite.TargetPath);
        favorite.LastOpenedAt = DateTimeOffset.Now;
        await PersistFavoritesAsync();

        if (favorite.NodeType == NodeType.Folder)
        {
            WorkspacePath = favorite.TargetPath;
            await LoadWorkspaceAsync();
        }

        await AddRecentPathAsync(favorite.TargetPath);
    }

    partial void OnSelectedNodeChanged(TreeNodeModel? value)
    {
        if (value is null) return;
        SelectedNodePath = value.FullPath;
        SelectedNodeInfo = $"名称：{value.Name}\n路径：{value.FullPath}\n类型：{value.NodeType}";
    }

    partial void OnFavoriteFilterChanged(string value)
    {
        if (string.IsNullOrWhiteSpace(value)) return;

        var filtered = _searchService.SearchFavorites(Favorites, value);
        Favorites.Clear();
        foreach (var item in filtered) Favorites.Add(item);
    }

    private async Task PersistFavoritesAsync()
    {
        var ordered = Favorites.OrderByDescending(x => x.IsPinned).ThenBy(x => x.SortOrder).ToList();
        await _favoritesService.SaveAsync(ordered);
    }

    private async Task AddRecentPathAsync(string path)
    {
        if (string.IsNullOrWhiteSpace(path)) return;

        var exists = RecentPaths.FirstOrDefault(x => string.Equals(x, path, StringComparison.OrdinalIgnoreCase));
        if (exists is not null) RecentPaths.Remove(exists);
        RecentPaths.Insert(0, path);

        while (RecentPaths.Count > 30) RecentPaths.RemoveAt(RecentPaths.Count - 1);

        var config = await _configService.LoadAsync();
        config.RecentPaths = [.. RecentPaths];
        config.LastOpenedWorkspace = WorkspacePath;
        config.ExportIncludeFiles = IncludeFiles;
        config.BuildCreateFiles = CreateFiles;
        await _configService.SaveAsync(config);
    }
}
