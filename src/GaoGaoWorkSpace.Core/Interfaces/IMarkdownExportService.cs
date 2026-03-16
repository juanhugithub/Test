using GaoGaoWorkSpace.Core.Models;

namespace GaoGaoWorkSpace.Core.Interfaces;

public interface IMarkdownExportService
{
    string Export(TreeNodeModel root, bool includeFiles = true);
}
