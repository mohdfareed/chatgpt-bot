"""Formatter of messages sent by the bot."""

import html as _html
import re as _re

from bs4 import BeautifulSoup as _BeautifulSoup

# unsupported telegram tags:
# spoiler: using simpler syntax `<tg-spoiler>`
# code blocks: using `<code>` as it is copyable in telegram
# emoji: can't guarantee id validity


def _inline(symbol):
    return rf"(?<![@#\\\w]){symbol}(.+?){symbol}(?!\w)"


_MARKDOWN_PATTERNS = dict(
    underlined=_inline(r"__"),
    italic=_inline(r"_"),  # only after underlined
    code=_inline(r"```"),
    mono=_inline(r"`"),  # only after code blocks
    bold=_inline(r"\*"),
    strikethrough=_inline(r"~"),
    spoiler=_inline(r"\|\|"),
    link=r"(?<![@#\w])\[(.+?)\]\((.+?)\)(?!\w)",
)
"""Regex pattern of each markdown tag."""

_HTML_SYNTAX = dict(
    bold=r"<b>\1</b>",
    italic=r"<i>\1</i>",
    underlined=r"<u>\1</u>",
    strikethrough=r"<s>\1</s>",
    spoiler=r"<tg-spoiler>\1</tg-spoiler>",
    link=r'<a href="\2">\1</a>',
    mono=r"<code>\1</code>",
    code=r"<code>\1</code>",
)
"""HTML tag equivalent for each markdown tag."""

_VALID_HTML_TAGS = [
    # bold
    "b",
    "strong",
    # italic
    "i",
    "em",
    # underline
    "u",
    "ins",
    # strikethrough
    "s",
    "strike",
    "del",
    # spoiler
    "tg-spoiler",  # spoiler
    # link
    "a",
    # code
    "code",
    "pre",  # not preferred
]
"""Valid HTML tags, which are supported by Telegram."""

_VALID_TAG_ATTRS = {
    "a": ["href"],
    "code": ["class"],
}  # can't verify emoji-id validity, therefore not supported
"""Valid attributes for each HTML tag."""


def markdown_to_html(text: str) -> str:
    """Convert markdown text to HTML."""
    return _parse_html(_parse_markdown(text))


def _parse_html(text):
    for tag in (html_soup := _BeautifulSoup(text, "html.parser")).find_all():
        # escape invalid tags
        if tag.name not in _VALID_HTML_TAGS:
            tag.replace_with(_html.unescape(str(tag)))
            continue

        # escape tag if it has invalid attributes
        for attr in tag.attrs:
            if attr not in _VALID_TAG_ATTRS.get(tag.name, []):
                tag.replace_with(_html.unescape(str(tag)))

    return str(html_soup)


def _parse_markdown(text):
    for tag, pattern in _MARKDOWN_PATTERNS.items():
        # replace markdown with html syntax
        text = _re.sub(pattern, _HTML_SYNTAX[tag], text)

    return text
