"""Tools that give agents access to external resources."""

import wikipedia
from langchain import LLMMathChain, OpenAI
from langchain.agents import Tool
from langchain.utilities import GoogleSerperAPIWrapper, WikipediaAPIWrapper

from chatgpt import OPENAI_API_KEY, SERPER_API_KEY

_search_disc = "Search the internet. Useful for finding information \
about current events. Input is a targeted search query."
_wiki_disc = "Search Wikipedia. Useful for finding information \
about new or unknown subjects and topics. Input is a targeted search query."
_calc_desc = "Answer math questions. Useful for solving math problems. Input \
is a valid numerical expression."


class InternetSearch(Tool):
    """A tool for searching the internet."""

    def __init__(self, serper_api_key: str = SERPER_API_KEY):
        tool = GoogleSerperAPIWrapper(serper_api_key=serper_api_key)
        super().__init__(
            func=tool.run,
            coroutine=tool.arun,
            name="Internet Search",
            description=_search_disc,
        )


class WikiSearch(Tool):
    """A tool for searching Wikipedia."""

    def __init__(self):
        self._wiki_client = WikipediaAPIWrapper(wiki_client=wikipedia)
        super().__init__(
            func=self._wiki_client.run,
            coroutine=self.async_wiki,
            name="Wikipedia",
            description=_wiki_disc,
        )

    async def async_wiki(self, *args, **kwargs):
        return self._wiki_client.run(*args, **kwargs)


class Calculator(Tool):
    """A tool for solving math problems."""

    def __init__(self, openai_api_key: str = OPENAI_API_KEY):
        model = OpenAI(openai_api_key=openai_api_key)  # type: ignore
        chain = LLMMathChain.from_llm(model)
        super().__init__(
            func=chain.run,
            coroutine=chain.arun,
            name="Calculator",
            description=_calc_desc,
        )