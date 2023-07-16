"""Utilities used by project scripts."""

ERROR: str = "\033[31m"
CLEAR: str = "\033[0m"
BOLD: str = "\033[1m"
SUCCESS: str = "\033[32;1m"


def print_bold(text: str):
    print(BOLD + text + CLEAR)


def print_success(text: str):
    print(SUCCESS + text + CLEAR)


def print_error(error_text: str):
    print(ERROR + error_text + CLEAR)
