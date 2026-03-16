using GaoGaoWorkSpace.Core.Interfaces;
using GaoGaoWorkSpace.Core.Models;
using GaoGaoWorkSpace.Infrastructure.Persistence;

namespace GaoGaoWorkSpace.Infrastructure.Services;

public sealed class FavoritesService(JsonFileStore store, string filePath) : IFavoritesService
{
    public async Task<IReadOnlyList<FavoriteItem>> LoadAsync()
        => await store.ReadOrDefaultAsync(filePath, new List<FavoriteItem>());

    public Task SaveAsync(IReadOnlyList<FavoriteItem> favorites)
        => store.WriteAsync(filePath, favorites.ToList());
}
