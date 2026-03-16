using GaoGaoWorkSpace.Core.Models;

namespace GaoGaoWorkSpace.Core.Interfaces;

public interface IMarkdownImportService
{
    IReadOnlyList<MarkdownNode> Parse(string markdownText);
    TreeNodeModel BuildTree(IReadOnlyList<MarkdownNode> nodes, string? fakeRootPath = null);
}
