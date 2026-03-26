"""
Telegram bot + web admin in one process (polling in a background thread).

Run: python -m bot.run_all

On a server, two systemd units or Docker services are often cleaner.
"""

from __future__ import annotations

import threading

import uvicorn

from bot.config import ADMIN_WEB_HOST, ADMIN_WEB_PORT


def _run_bot() -> None:
    from bot.main import main

    main()


if __name__ == "__main__":
    t = threading.Thread(target=_run_bot, daemon=True, name="telegram-bot")
    t.start()
    uvicorn.run(
        "bot.admin_app:app",
        host=ADMIN_WEB_HOST,
        port=ADMIN_WEB_PORT,
        reload=False,
    )
