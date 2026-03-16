namespace GaoGaoWorkSpace.Core.Interfaces;

public interface ISafetyGuardService
{
    bool IsRiskyPath(string path, out string reason);
    bool IsWriteAllowed(string path, out string reason);
}
