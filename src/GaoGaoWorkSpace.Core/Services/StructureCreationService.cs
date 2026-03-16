using GaoGaoWorkSpace.Core.Interfaces;
using GaoGaoWorkSpace.Core.Models;

namespace GaoGaoWorkSpace.Core.Services;

public sealed class StructureCreationService(ISafetyGuardService safetyGuardService) : IStructureCreationService
{
    public IReadOnlyList<BuildPreviewItem> Preview(IReadOnlyList<MarkdownNode> nodes, string targetRoot, bool createFiles = false)
    {
        var list = new List<BuildPreviewItem>();
        var stack = new List<string>();

        foreach (var node in nodes)
        {
            while (stack.Count > node.Level) stack.RemoveAt(stack.Count - 1);

            string destination;
            if (node.Level == 0)
            {
                destination = Path.Combine(targetRoot, node.Name);
                stack = [destination];
            }
            else
            {
                if (stack.Count == 0) throw new MarkdownFormatException("层级结构异常，缺少父节点。");
                destination = Path.Combine(stack[^1], node.Name);
                if (stack.Count == node.Level) stack.Add(destination);
                else
                {
                    stack[node.Level] = destination;
                    stack = stack.Take(node.Level + 1).ToList();
                }
            }

            var allowWrite = safetyGuardService.IsWriteAllowed(destination, out var reason);
            var exists = Directory.Exists(destination) || File.Exists(destination);
            var shouldCreate = allowWrite && (node.IsDirectory || createFiles) && !exists;

            list.Add(new BuildPreviewItem
            {
                TargetPath = destination,
                NodeType = node.IsDirectory ? NodeType.Folder : NodeType.File,
                ExistsAlready = exists,
                WillCreate = shouldCreate,
                Reason = allowWrite ? (exists ? "已存在，跳过" : "将创建") : reason
            });
        }

        return list;
    }

    public BuildSummary Apply(IReadOnlyList<MarkdownNode> nodes, string targetRoot, bool createFiles = false)
    {
        var summary = new BuildSummary();
        foreach (var item in Preview(nodes, targetRoot, createFiles))
        {
            if (item.NodeType == NodeType.Folder)
            {
                if (item.ExistsAlready) { summary.ExistingDirs++; continue; }
                if (!item.WillCreate) { summary.Skipped++; continue; }
                Directory.CreateDirectory(item.TargetPath);
                summary.CreatedDirs++;
            }
            else
            {
                if (!createFiles) { summary.Skipped++; continue; }
                if (item.ExistsAlready) { summary.ExistingFiles++; continue; }
                if (!item.WillCreate) { summary.Skipped++; continue; }
                Directory.CreateDirectory(Path.GetDirectoryName(item.TargetPath)!);
                using var _ = File.Create(item.TargetPath);
                summary.CreatedFiles++;
            }
        }

        return summary;
    }
}
