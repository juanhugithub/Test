using GaoGaoWorkSpace.Core.Interfaces;

namespace GaoGaoWorkSpace.Core.Services;

public sealed class SafetyGuardService : ISafetyGuardService
{
    public bool IsRiskyPath(string path, out string reason)
    {
        reason = string.Empty;
        if (string.IsNullOrWhiteSpace(path))
        {
            reason = "路径为空";
            return true;
        }

        var normalized = path.Trim();
        if (normalized.StartsWith("\\\\"))
        {
            reason = "检测到 UNC 网络路径（共享盘），请谨慎操作";
            return true;
        }

        var root = Path.GetPathRoot(normalized);
        if (!string.IsNullOrEmpty(root) && string.Equals(root.TrimEnd('\\'), normalized.TrimEnd('\\'), StringComparison.OrdinalIgnoreCase))
        {
            reason = "检测到盘符根目录，属于高风险路径";
            return true;
        }

        var lower = normalized.ToLowerInvariant();
        if (lower.Contains("windows") || lower.Contains("program files"))
        {
            reason = "检测到系统目录，禁止结构写入";
            return true;
        }

        return false;
    }

    public bool IsWriteAllowed(string path, out string reason)
    {
        if (IsRiskyPath(path, out reason)) return false;
        return true;
    }
}
