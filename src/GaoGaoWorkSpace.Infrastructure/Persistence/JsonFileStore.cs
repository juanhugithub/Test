using System.Text.Json;

namespace GaoGaoWorkSpace.Infrastructure.Persistence;

public sealed class JsonFileStore
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = true
    };

    public async Task<T> ReadOrDefaultAsync<T>(string filePath, T defaultValue)
    {
        if (!File.Exists(filePath)) return defaultValue;

        try
        {
            await using var fs = File.OpenRead(filePath);
            return (await JsonSerializer.DeserializeAsync<T>(fs, JsonOptions)) ?? defaultValue;
        }
        catch
        {
            return defaultValue;
        }
    }

    public async Task WriteAsync<T>(string filePath, T data)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(filePath)!);
        await using var fs = File.Create(filePath);
        await JsonSerializer.SerializeAsync(fs, data, JsonOptions);
    }
}
