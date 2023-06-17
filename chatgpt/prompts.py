"""Collection of prompts used by the different models."""

SUMMARIZATION = """\
Progressively summarize the lines of the conversation provided, adding onto \
the previous summary and returning a new summary.

EXAMPLE

Current summary:
Person asks what you think of artificial intelligence. You think artificial \
intelligence is a force for good.

New lines of conversation:
Person: Why do you think artificial intelligence is a force for good?
You: Because it will help humans reach their full potential.

New summary:
Person asks what the you think of artificial intelligence. You think \
artificial intelligence is a force for good because it will help humans reach \
their full potential.

END OF EXAMPLE

Current summary:
{0}

New lines of conversation:
{1}

New summary:
"""
"""The prompt for summarizing a conversation."""

CHAT_INSTRUCTIONS = """\
You are chatting through Telegram. Use ONLY the following markdown syntax in \
your reply: *bold* _italic_ ~strikethrough~ __underline__ ||spoiler|| \
[inline URL](http://www.example.com/) `monospaced` @mentions #hashtags
```language
code blocks
```

You are provided the chat history and the new message to which you are \
replying. The new message you received is formatted as follows:
```
[user | metadata] The message's text.
[you | your reply's metadata]
```
ONLY PROVIDE YOUR REPLY'S TEXT. DO NOT INCLUDE `[you | metadata]`.
"""
