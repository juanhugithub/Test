namespace GaoGaoWorkSpace.Core.Models;

public sealed class AppConfig
{
    public string Theme { get; set; } = "Light";
    public List<string> RecentPaths { get; set; } = [];
    public List<FavoriteItem> FavoriteItems { get; set; } = [];
    public string LastOpenedWorkspace { get; set; } = string.Empty;
    public bool ExportIncludeFiles { get; set; } = true;
    public int? ExportMaxDepth { get; set; }
    public bool BuildCreateFiles { get; set; } = false;
    public List<string> IgnorePatterns { get; set; } = ["*.tmp", "~$*", ".DS_Store"];
    public string WindowState { get; set; } = "Normal";
    public List<string> SharedPathWarningRules { get; set; } = ["\\\\", "共享", "share"];
}
