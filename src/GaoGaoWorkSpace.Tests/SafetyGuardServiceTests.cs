using GaoGaoWorkSpace.Core.Services;

namespace GaoGaoWorkSpace.Tests;

public class SafetyGuardServiceTests
{
    private readonly SafetyGuardService _service = new();

    [Theory]
    [InlineData("\\\\server\\share")]
    [InlineData("C:\\")]
    [InlineData("C:\\Windows\\System32")]
    public void RiskyPath_Should_BeDetected(string path)
    {
        var risky = _service.IsRiskyPath(path, out _);
        Assert.True(risky);
    }
}
