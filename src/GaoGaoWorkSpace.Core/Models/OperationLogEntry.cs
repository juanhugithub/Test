namespace GaoGaoWorkSpace.Core.Models;

public sealed class OperationLogEntry
{
    public DateTimeOffset Time { get; init; } = DateTimeOffset.Now;
    public string Level { get; init; } = "Info";
    public string Action { get; init; } = string.Empty;
    public string Message { get; init; } = string.Empty;
}
