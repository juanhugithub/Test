using GaoGaoWorkSpace.Core.Models;

namespace GaoGaoWorkSpace.Core.Interfaces;

public interface ILoggingService
{
    Task WriteAsync(OperationLogEntry entry, CancellationToken cancellationToken = default);
}
