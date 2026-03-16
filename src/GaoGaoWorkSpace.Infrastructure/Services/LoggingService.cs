using GaoGaoWorkSpace.Core.Interfaces;
using GaoGaoWorkSpace.Core.Models;

namespace GaoGaoWorkSpace.Infrastructure.Services;

public sealed class LoggingService(string logFilePath) : ILoggingService
{
    public async Task WriteAsync(OperationLogEntry entry, CancellationToken cancellationToken = default)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(logFilePath)!);
        var line = $"[{entry.Time:yyyy-MM-dd HH:mm:ss}] [{entry.Level}] {entry.Action}: {entry.Message}{Environment.NewLine}";
        await File.AppendAllTextAsync(logFilePath, line, cancellationToken);
    }
}
