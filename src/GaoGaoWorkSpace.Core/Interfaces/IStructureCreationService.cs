using GaoGaoWorkSpace.Core.Models;

namespace GaoGaoWorkSpace.Core.Interfaces;

public interface IStructureCreationService
{
    IReadOnlyList<BuildPreviewItem> Preview(IReadOnlyList<MarkdownNode> nodes, string targetRoot, bool createFiles = false);
    BuildSummary Apply(IReadOnlyList<MarkdownNode> nodes, string targetRoot, bool createFiles = false);
}
