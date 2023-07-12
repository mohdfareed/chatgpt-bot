"""Formatter of messages sent by the bot."""

import html
import re

import bs4

# unsupported telegram tags:
# spoiler: using simpler syntax `<tg-spoiler>`
# code blocks: using `<code>` as it is copyable in telegram
# emoji: can't guarantee id validity

_inline = r"(?<![@#\\\w]){0}(.+?){0}(?!\w)"

_markdown_patterns = dict(
    bold=_inline.format(r"\*"),
    italic=_inline.format(r"_(?!_)"),
    underlined=_inline.format(r"__"),
    strikethrough=_inline.format(r"~"),
    spoiler=_inline.format(r"\|\|"),
    mono=_inline.format(r"`(?!`)"),
    code=r"(?<![@#\\\w])```(.*)\n([\s\S]+?)\n\s*```(?!\w)",
    link=r"(?<![@#\w])\[(.+?)\]\((.+?)\)(?!\w)",
)

_html_syntax = dict(
    bold=r"<b>\1</b>",
    italic=r"<i>\1</i>",
    underlined=r"<u>\1</u>",
    strikethrough=r"<s>\1</s>",
    spoiler=r"<tg-spoiler>\1</tg-spoiler>",
    link=r'<a href="\2">\1</a>',
    mono=r"<code>\1</code>",
    code=r"<code>\2</code>",  # use <code> instead of <pre>
)

_valid_tags = [
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

_valid_attrs = {
    "a": ["href"],
    "code": ["class"],
}  # can't verify emoji-id validity, therefore not supported


def md_html(text: str) -> str:
    """Format text by convert markdown to Telegram-supported HTML."""
    return _parse_html(_parse_markdown(text))


def _parse_html(text):
    html_soup = bs4.BeautifulSoup(text, "html.parser")
    for tag in html_soup.find_all():
        # escape invalid tags
        if tag.name not in _valid_tags:
            tag.replace_with(html.unescape(str(tag)))
            continue

        # escape tag if it has invalid attributes
        for attr in tag.attrs:
            if attr not in _valid_attrs.get(tag.name, []):
                tag.replace_with(html.unescape(str(tag)))

    return str(html_soup)


def _parse_markdown(text):
    for tag, pattern in _markdown_patterns.items():
        # replace markdown with html syntax
        text = re.sub(pattern, _html_syntax[tag], text)

    return text
