using System.Diagnostics;
using GaoGaoWorkSpace.Core.Interfaces;

namespace GaoGaoWorkSpace.Infrastructure.Services;

public sealed class ShellOpenService : IShellOpenService
{
    public void Open(string path)
    {
        Process.Start(new ProcessStartInfo
        {
            FileName = path,
            UseShellExecute = true
        });
    }

    public void OpenFolder(string path)
    {
        if (File.Exists(path)) path = Path.GetDirectoryName(path)!;
        Open(path);
    }

    public void RevealInExplorer(string path)
    {
        if (Directory.Exists(path))
        {
            Process.Start("explorer.exe", path);
            return;
        }
        Process.Start("explorer.exe", $"/select,\"{path}\"");
    }
}
