using GaoGaoWorkSpace.Core.Models;
using GaoGaoWorkSpace.Infrastructure.Persistence;

namespace GaoGaoWorkSpace.Infrastructure.Services;

public sealed class AppConfigService(JsonFileStore store, string filePath)
{
    public Task<AppConfig> LoadAsync() => store.ReadOrDefaultAsync(filePath, new AppConfig());
    public Task SaveAsync(AppConfig config) => store.WriteAsync(filePath, config);
}
