import unittest

import bot.formatter

_complex_md = """
*bold _italic bold ~italic bold strikethrough ||italic bold strikethrough spoiler||~ __underline italic bold___ bold*
[inline URL](http://www.example.com/)
`inline fixed-width code`
```
pre-formatted fixed-width code block
```
"""

_complex_html = """
<b>bold <i>italic bold <s>italic bold strikethrough <tg-spoiler>italic bold strikethrough spoiler</tg-spoiler></s> <u>underline italic bold</u></i> bold</b>
<a href="http://www.example.com/">inline URL</a>
<code>inline fixed-width code</code>
<pre>
pre-formatted fixed-width code block
</pre>
"""


class TestMarkdownToHtml(unittest.TestCase):
    def test_bold(self):
        self.assertEqual(
            bot.bot.formatter.md_html("This is *bold* text."),
            "This is <b>bold</b> text.",
        )

    def test_italic(self):
        self.assertEqual(
            bot.formatter.md_html("This is _italic_ text."),
            "This is <i>italic</i> text.",
        )

    def test_underlined(self):
        self.assertEqual(
            bot.formatter.md_html("This is __underlined__ text."),
            "This is <u>underlined</u> text.",
        )

    def test_strikethrough(self):
        self.assertEqual(
            bot.formatter.md_html("This is ~strikethrough~ text."),
            "This is <s>strikethrough</s> text.",
        )

    def test_spoiler(self):
        self.assertEqual(
            bot.formatter.md_html("This is ||spoiler|| text."),
            "This is <tg-spoiler>spoiler</tg-spoiler> text.",
        )

    def test_link(self):
        self.assertEqual(
            bot.formatter.md_html(
                "This is a [link](https://www.example.com)."
            ),
            'This is a <a href="https://www.example.com">link</a>.',
        )

    def test_code(self):
        self.assertEqual(
            bot.formatter.md_html("This is `code`."),
            "This is <code>code</code>.",
        )

    def test_mono(self):
        self.assertEqual(
            bot.formatter.md_html("This is `mono` text."),
            "This is <code>mono</code> text.",
        )

    def test_nested(self):
        self.assertEqual(
            bot.formatter.md_html("This is *bold and _italic_* text."),
            "This is <b>bold and <i>italic</i></b> text.",
        )

    def test_mention(self):
        self.assertEqual(
            bot.formatter.md_html("This is a @mention_of_user."),
            "This is a @mention_of_user.",
        )
        self.assertEqual(
            bot.formatter.md_html("This is a formatted _@mention_of_user_."),
            "This is a formatted <i>@mention_of_user</i>.",
        )
        self.assertEqual(
            bot.formatter.md_html("This is a _@username_mention._"),
            "This is a <i>@username_mention.</i>",
        )
        self.assertEqual(
            bot.formatter.md_html("This is a _@username_mention."),
            "This is a _@username_mention.",
        )

    def test_complex(self):
        self.assertEqual(
            bot.formatter.md_html(_complex_md),
            _complex_html,
        )
