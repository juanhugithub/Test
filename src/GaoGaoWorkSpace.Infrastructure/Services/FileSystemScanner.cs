using GaoGaoWorkSpace.Core.Interfaces;
using GaoGaoWorkSpace.Core.Models;

namespace GaoGaoWorkSpace.Infrastructure.Services;

public sealed class FileSystemScanner : IFileSystemScanner
{
    public Task<TreeNodeModel> ScanAsync(string rootPath, bool includeFiles, bool includeHidden, int? maxDepth, IReadOnlyCollection<string>? ignorePatterns = null, CancellationToken cancellationToken = default)
    {
        var root = new DirectoryInfo(rootPath);
        if (!root.Exists) throw new DirectoryNotFoundException($"目录不存在：{rootPath}");

        var node = Scan(root, includeFiles, includeHidden, maxDepth, 0, ignorePatterns ?? [], cancellationToken);
        return Task.FromResult(node);
    }

    private static TreeNodeModel Scan(DirectoryInfo dir, bool includeFiles, bool includeHidden, int? maxDepth, int depth, IReadOnlyCollection<string> ignorePatterns, CancellationToken ct)
    {
        ct.ThrowIfCancellationRequested();

        var model = new TreeNodeModel
        {
            Name = dir.Name,
            FullPath = dir.FullName,
            ParentPath = dir.Parent?.FullName ?? string.Empty,
            NodeType = NodeType.Folder,
            LastWriteTime = dir.LastWriteTimeUtc,
            IsLoaded = true
        };

        if (maxDepth.HasValue && depth >= maxDepth.Value) return model;

        IEnumerable<FileSystemInfo> children;
        try
        {
            children = dir.EnumerateFileSystemInfos();
        }
        catch
        {
            return model;
        }

        foreach (var child in children.OrderBy(c => c is FileInfo).ThenBy(c => c.Name, StringComparer.OrdinalIgnoreCase))
        {
            if (!includeHidden && child.Attributes.HasFlag(FileAttributes.Hidden)) continue;
            if (ShouldIgnore(child.Name, ignorePatterns)) continue;

            if (child is DirectoryInfo childDir)
            {
                model.Children.Add(Scan(childDir, includeFiles, includeHidden, maxDepth, depth + 1, ignorePatterns, ct));
            }
            else if (includeFiles && child is FileInfo file)
            {
                model.Children.Add(new TreeNodeModel
                {
                    Name = file.Name,
                    FullPath = file.FullName,
                    ParentPath = file.DirectoryName ?? string.Empty,
                    NodeType = NodeType.File,
                    Size = file.Length,
                    LastWriteTime = file.LastWriteTimeUtc,
                    IsLoaded = true
                });
            }
        }

        return model;
    }

    private static bool ShouldIgnore(string name, IReadOnlyCollection<string> patterns)
    {
        foreach (var pattern in patterns)
        {
            if (string.IsNullOrWhiteSpace(pattern)) continue;
            if (pattern == name) return true;
            if (pattern.StartsWith("*.") && name.EndsWith(pattern[1..], StringComparison.OrdinalIgnoreCase)) return true;
            if (pattern.EndsWith("*") && name.StartsWith(pattern[..^1], StringComparison.OrdinalIgnoreCase)) return true;
        }
        return false;
    }
}
