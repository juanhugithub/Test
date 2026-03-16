namespace GaoGaoWorkSpace.Core.Models;

public sealed class MarkdownNode
{
    public string Name { get; init; } = string.Empty;
    public bool IsDirectory { get; init; }
    public int Level { get; init; }
}
