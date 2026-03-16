namespace GaoGaoWorkSpace.Core.Interfaces;

public interface IShellOpenService
{
    void Open(string path);
    void OpenFolder(string path);
    void RevealInExplorer(string path);
}
