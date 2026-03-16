using GaoGaoWorkSpace.Core.Models;

namespace GaoGaoWorkSpace.Core.Interfaces;

public interface ISearchService
{
    IReadOnlyList<TreeNodeModel> SearchTree(TreeNodeModel root, string keyword, bool includePath = true);
    IReadOnlyList<FavoriteItem> SearchFavorites(IEnumerable<FavoriteItem> favorites, string keyword);
}
