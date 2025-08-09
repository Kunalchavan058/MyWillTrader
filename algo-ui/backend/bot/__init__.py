# Re-export the public surface so existing imports keep working:
#   from . import bot as trading_bot
# will still expose API_AUTH_TOKEN, run_bot, start_bot_background, stop_bot, etc.
from .core import (
    API_AUTH_TOKEN,
    run_bot,
    start_bot_background,
    stop_bot,
)
