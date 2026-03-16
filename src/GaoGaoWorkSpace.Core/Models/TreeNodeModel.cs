using System.Collections.ObjectModel;

namespace GaoGaoWorkSpace.Core.Models;

public sealed class TreeNodeModel
{
    public string Id { get; init; } = Guid.NewGuid().ToString("N");
    public string Name { get; set; } = string.Empty;
    public string FullPath { get; set; } = string.Empty;
    public string ParentPath { get; set; } = string.Empty;
    public NodeType NodeType { get; set; } = NodeType.Folder;
    public ObservableCollection<TreeNodeModel> Children { get; init; } = [];
    public bool IsFavorite { get; set; }
    public bool IsExpanded { get; set; }
    public bool IsLoaded { get; set; }
    public DateTimeOffset? LastWriteTime { get; set; }
    public long? Size { get; set; }
    public string? Alias { get; set; }
    public List<string> Tags { get; init; } = [];
    public string? Notes { get; set; }

    public bool IsDirectory => NodeType == NodeType.Folder;
}
