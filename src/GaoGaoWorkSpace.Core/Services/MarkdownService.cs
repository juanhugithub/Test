using System.Text;
using System.Text.RegularExpressions;
using GaoGaoWorkSpace.Core.Interfaces;
using GaoGaoWorkSpace.Core.Models;

namespace GaoGaoWorkSpace.Core.Services;

public sealed partial class MarkdownService : IMarkdownExportService, IMarkdownImportService
{
    [GeneratedRegex("^(#{1,6})\\s+(.+?)\\s*$")]
    private static partial Regex HeadingRegex();

    [GeneratedRegex("^([ \\t]*)([-*+])\\s+(.+?)\\s*$")]
    private static partial Regex BulletRegex();

    public string Export(TreeNodeModel root, bool includeFiles = true)
    {
        var lines = new List<string> { $"# {DisplayName(root)}" };
        foreach (var child in root.Children)
        {
            if (!includeFiles && child.NodeType == NodeType.File) continue;
            lines.Add($"## {DisplayName(child)}");
            if (child.NodeType == NodeType.Folder)
            {
                WriteBullets(lines, child.Children, includeFiles, 0);
            }
        }
        return string.Join(Environment.NewLine, lines) + Environment.NewLine;
    }

    public IReadOnlyList<MarkdownNode> Parse(string markdownText)
    {
        var lines = markdownText.Split('\n', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        if (lines.Length == 0)
            throw new MarkdownFormatException("Markdown 内容为空。");

        var nodes = new List<MarkdownNode>();
        var currentHeadingLevel = 0;
        int? indentUnit = null;

        for (var index = 0; index < lines.Length; index++)
        {
            var raw = lines[index].TrimEnd('\r');
            var heading = HeadingRegex().Match(raw);
            if (heading.Success)
            {
                var headingLevel = heading.Groups[1].Value.Length - 1;
                var (name, isDirectory) = NormalizeName(heading.Groups[2].Value, index + 1);
                nodes.Add(new MarkdownNode { Name = name, IsDirectory = isDirectory, Level = headingLevel });
                currentHeadingLevel = headingLevel;
                continue;
            }

            var bullet = BulletRegex().Match(raw);
            if (bullet.Success)
            {
                var indent = bullet.Groups[1].Value;
                var spaces = indent.Sum(c => c == '\t' ? 2 : 1);
                var depth = 0;
                if (spaces > 0)
                {
                    indentUnit ??= spaces;
                    if (indentUnit <= 0 || spaces % indentUnit != 0)
                        throw new MarkdownFormatException($"第 {index + 1} 行缩进不一致：{raw}");
                    depth = spaces / indentUnit.Value;
                }

                var (name, isDirectory) = NormalizeName(bullet.Groups[3].Value, index + 1);
                nodes.Add(new MarkdownNode { Name = name, IsDirectory = isDirectory, Level = currentHeadingLevel + 1 + depth });
                continue;
            }

            throw new MarkdownFormatException($"第 {index + 1} 行不是受支持的 XMind Markdown 结构：{raw}");
        }

        if (nodes[0].Level != 0)
            throw new MarkdownFormatException("Markdown 必须从 # 根节点开始。");

        var prev = 0;
        for (var i = 1; i < nodes.Count; i++)
        {
            if (nodes[i].Level > prev + 1)
                throw new MarkdownFormatException($"第 {i + 1} 行层级跳跃过大：{nodes[i].Name}");
            prev = nodes[i].Level;
        }

        return nodes;
    }

    public TreeNodeModel BuildTree(IReadOnlyList<MarkdownNode> nodes, string? fakeRootPath = null)
    {
        if (nodes.Count == 0)
            throw new MarkdownFormatException("节点为空。");

        var rootPath = fakeRootPath ?? nodes[0].Name;
        var root = new TreeNodeModel
        {
            Name = nodes[0].Name,
            FullPath = rootPath,
            NodeType = nodes[0].IsDirectory ? NodeType.Folder : NodeType.File
        };

        var stack = new List<TreeNodeModel> { root };
        foreach (var node in nodes.Skip(1))
        {
            while (stack.Count > node.Level)
                stack.RemoveAt(stack.Count - 1);

            var parent = stack[^1];
            var fullPath = Path.Combine(parent.FullPath, node.Name);
            var child = new TreeNodeModel
            {
                Name = node.Name,
                ParentPath = parent.FullPath,
                FullPath = fullPath,
                NodeType = node.IsDirectory ? NodeType.Folder : NodeType.File
            };
            parent.Children.Add(child);
            if (node.IsDirectory) stack.Add(child);
        }

        return root;
    }

    private static void WriteBullets(List<string> lines, IEnumerable<TreeNodeModel> nodes, bool includeFiles, int indent)
    {
        var prefix = new string(' ', indent * 2) + "- ";
        foreach (var node in nodes)
        {
            if (!includeFiles && node.NodeType == NodeType.File) continue;
            lines.Add(prefix + DisplayName(node));
            if (node.NodeType == NodeType.Folder)
                WriteBullets(lines, node.Children, includeFiles, indent + 1);
        }
    }

    private static (string name, bool isDirectory) NormalizeName(string raw, int lineNo)
    {
        var name = raw.Trim();
        var isDirectory = name.EndsWith('/');
        if (isDirectory) name = name[..^1];
        if (string.IsNullOrWhiteSpace(name))
            throw new MarkdownFormatException($"第 {lineNo} 行名称为空。");
        if (name.IndexOfAny(['/', '\\']) >= 0)
            throw new MarkdownFormatException($"第 {lineNo} 行名称非法，不能包含路径分隔符：{name}");
        return (name, isDirectory);
    }

    private static string DisplayName(TreeNodeModel node)
        => node.Name + (node.NodeType == NodeType.Folder ? "/" : string.Empty);
}
