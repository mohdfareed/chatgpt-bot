"""Formatter of messages sent by the bot."""

import html
import re

from bs4 import BeautifulSoup

# unsupported telegram tags:
# spoiler: using simpler syntax `<tg-spoiler>`
# code blocks: using `<code>` as it is copyable in telegram
# emoji: can't guarantee id validity


def _inline(symbol):
    return fr'(?<![@#\\\w]){symbol}(.+?){symbol}(?!\w)'


_MARKDOWN_PATTERNS = dict(
    underlined=_inline(r'__'),
    italic=_inline(r'_'),  # only after underlined
    code=_inline(r'```'),
    mono=_inline(r'`'),  # only after code blocks
    bold=_inline(r'\*'),
    strikethrough=_inline(r'~'),
    spoiler=_inline(r'\|\|'),
    link=r'(?<![@#\w])\[(.+?)\]\((.+?)\)(?!\w)'
)

_HTML_SYNTAX = dict(
    bold=r'<b>\1</b>',
    italic=r'<i>\1</i>',
    underlined=r'<u>\1</u>',
    strikethrough=r'<s>\1</s>',
    spoiler=r'<tg-spoiler>\1</tg-spoiler>',
    link=r'<a href="\2">\1</a>',
    mono=r'<code>\1</code>',
    code=r'<code>\1</code>'
)

_VALID_HTML_TAGS = [
    'b', 'strong',         # bold
    'i', 'em',             # italic
    'u', 'ins',            # underline
    's', 'strike', 'del',  # strikethrough
    'tg-spoiler',          # spoiler
    'a',                   # link
    'code', 'pre'          # code, preferring <code> over <pre>
]

_VALID_TAG_ATTRS = {
    'a':        ['href'],
    'code':     ['class']
}  # can't verify emoji-id validity, therefore not supported


def markdown_to_html(text: str) -> str:
    return _parse_html(_parse_markdown(text))


def _parse_html(text):
    for tag in (html_soup := BeautifulSoup(text, 'html.parser')).find_all():
        if tag.name not in _VALID_HTML_TAGS:  # escape invalid tags
            tag.replace_with(html.unescape(str(tag)))
            continue
        for attr in tag.attrs:  # escape tag if it has invalid attributes
            if attr not in _VALID_TAG_ATTRS.get(tag.name, []):
                tag.replace_with(html.unescape(str(tag)))
    return str(html_soup)


def _parse_markdown(text):
    for tag, pattern in _MARKDOWN_PATTERNS.items():
        text = re.sub(pattern, _HTML_SYNTAX[tag], text)
    return text
