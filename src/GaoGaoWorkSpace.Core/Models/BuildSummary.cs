namespace GaoGaoWorkSpace.Core.Models;

public sealed class BuildSummary
{
    public int CreatedDirs { get; set; }
    public int ExistingDirs { get; set; }
    public int CreatedFiles { get; set; }
    public int ExistingFiles { get; set; }
    public int Skipped { get; set; }
}
