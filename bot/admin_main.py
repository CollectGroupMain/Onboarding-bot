"""Web admin only: python -m bot.admin_main"""

import uvicorn

from bot.config import ADMIN_WEB_HOST, ADMIN_WEB_PORT

if __name__ == "__main__":
    uvicorn.run(
        "bot.admin_app:app",
        host=ADMIN_WEB_HOST,
        port=ADMIN_WEB_PORT,
        reload=False,
    )
