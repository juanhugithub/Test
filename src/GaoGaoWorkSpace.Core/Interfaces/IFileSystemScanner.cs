using GaoGaoWorkSpace.Core.Models;

namespace GaoGaoWorkSpace.Core.Interfaces;

public interface IFileSystemScanner
{
    Task<TreeNodeModel> ScanAsync(string rootPath, bool includeFiles, bool includeHidden, int? maxDepth, IReadOnlyCollection<string>? ignorePatterns = null, CancellationToken cancellationToken = default);
}
