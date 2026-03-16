using GaoGaoWorkSpace.Core.Interfaces;
using GaoGaoWorkSpace.Core.Models;

namespace GaoGaoWorkSpace.Core.Services;

public sealed class SearchService : ISearchService
{
    public IReadOnlyList<TreeNodeModel> SearchTree(TreeNodeModel root, string keyword, bool includePath = true)
    {
        var key = keyword.Trim().ToLowerInvariant();
        if (string.IsNullOrWhiteSpace(key)) return [];

        var results = new List<TreeNodeModel>();
        var stack = new Stack<TreeNodeModel>();
        stack.Push(root);

        while (stack.Count > 0)
        {
            var node = stack.Pop();
            var hit = node.Name.Contains(key, StringComparison.OrdinalIgnoreCase) ||
                      (includePath && node.FullPath.Contains(key, StringComparison.OrdinalIgnoreCase));
            if (hit) results.Add(node);

            foreach (var child in node.Children.Reverse()) stack.Push(child);
        }

        return results;
    }

    public IReadOnlyList<FavoriteItem> SearchFavorites(IEnumerable<FavoriteItem> favorites, string keyword)
    {
        var key = keyword.Trim();
        if (string.IsNullOrWhiteSpace(key)) return favorites.ToList();

        return favorites
            .Where(f => f.DisplayName.Contains(key, StringComparison.OrdinalIgnoreCase)
                        || f.TargetPath.Contains(key, StringComparison.OrdinalIgnoreCase)
                        || f.GroupName.Contains(key, StringComparison.OrdinalIgnoreCase))
            .OrderByDescending(f => f.IsPinned)
            .ThenBy(f => f.SortOrder)
            .ToList();
    }
}
