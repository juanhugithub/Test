using GaoGaoWorkSpace.Core.Models;

namespace GaoGaoWorkSpace.Core.Interfaces;

public interface IFavoritesService
{
    Task<IReadOnlyList<FavoriteItem>> LoadAsync();
    Task SaveAsync(IReadOnlyList<FavoriteItem> favorites);
}
