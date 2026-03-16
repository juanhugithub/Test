using GaoGaoWorkSpace.Core.Services;

namespace GaoGaoWorkSpace.Tests;

public class MarkdownServiceTests
{
    private readonly MarkdownService _service = new();

    [Fact]
    public void Parse_Should_Parse_XMindMarkdown()
    {
        const string md = "# 工作台/\n## 项目/\n- 子目录/\n";

        var nodes = _service.Parse(md);

        Assert.Equal(3, nodes.Count);
        Assert.True(nodes[0].IsDirectory);
        Assert.Equal(0, nodes[0].Level);
        Assert.Equal("子目录", nodes[2].Name);
    }

    [Fact]
    public void Parse_Should_Throw_When_JumpLevelTooLarge()
    {
        const string md = "# 根/\n    - 错误/\n";
        Assert.Throws<MarkdownFormatException>(() => _service.Parse(md));
    }
}
