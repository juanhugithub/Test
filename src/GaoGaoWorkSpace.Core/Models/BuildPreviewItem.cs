namespace GaoGaoWorkSpace.Core.Models;

public sealed class BuildPreviewItem
{
    public string TargetPath { get; init; } = string.Empty;
    public NodeType NodeType { get; init; } = NodeType.Folder;
    public bool ExistsAlready { get; init; }
    public bool WillCreate { get; init; }
    public string Reason { get; init; } = string.Empty;
}
