"""The bot's settings menus."""

BACK_BUTTON = "←"
ENABLED_INDICATOR = "✓"
DISABLED_INDICATOR = "✗"
MENU_BUTTON = "⊜ "


def create_title(title, is_enabled, is_toggle=False) -> str:
    if not is_toggle:
        return (f"{ENABLED_INDICATOR} " if is_enabled else "") + title
    return f"{ENABLED_INDICATOR if is_enabled else DISABLED_INDICATOR} {title}"


from . import (
    bot_settings,
    config_menu,
    data_receivers,
    model_menu,
    model_settings,
    tools_menu,
)
