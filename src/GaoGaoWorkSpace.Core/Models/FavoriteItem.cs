namespace GaoGaoWorkSpace.Core.Models;

public sealed class FavoriteItem
{
    public string Id { get; init; } = Guid.NewGuid().ToString("N");
    public string TargetPath { get; set; } = string.Empty;
    public string DisplayName { get; set; } = string.Empty;
    public NodeType NodeType { get; set; } = NodeType.Folder;
    public string GroupName { get; set; } = "默认";
    public int SortOrder { get; set; }
    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.Now;
    public DateTimeOffset? LastOpenedAt { get; set; }
    public bool IsPinned { get; set; }
}
