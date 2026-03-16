using GaoGaoWorkSpace.Core.Services;

namespace GaoGaoWorkSpace.Tests;

public class NodeTypeRecognitionTests
{
    [Fact]
    public void TrailingSlash_Should_BeDirectory()
    {
        var svc = new MarkdownService();
        var nodes = svc.Parse("# 根/\n## 文件夹/\n- 文件.txt\n");

        Assert.True(nodes[1].IsDirectory);
        Assert.False(nodes[2].IsDirectory);
    }
}
