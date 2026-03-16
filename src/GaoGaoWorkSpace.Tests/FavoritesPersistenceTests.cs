using GaoGaoWorkSpace.Core.Models;
using GaoGaoWorkSpace.Infrastructure.Persistence;
using GaoGaoWorkSpace.Infrastructure.Services;

namespace GaoGaoWorkSpace.Tests;

public class FavoritesPersistenceTests
{
    [Fact]
    public async Task Favorites_Should_Roundtrip_ByJsonStore()
    {
        var temp = Path.Combine(Path.GetTempPath(), $"favorites_{Guid.NewGuid():N}.json");
        var service = new FavoritesService(new JsonFileStore(), temp);

        var expected = new List<FavoriteItem>
        {
            new() { DisplayName = "项目A", TargetPath = "D:\\Data\\项目A", GroupName = "项目", SortOrder = 1 }
        };

        await service.SaveAsync(expected);
        var actual = await service.LoadAsync();

        Assert.Single(actual);
        Assert.Equal("项目A", actual[0].DisplayName);

        File.Delete(temp);
    }
}
