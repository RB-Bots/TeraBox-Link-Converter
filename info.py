import os

# ==============================
# 🔧 Telegram Bot Configuration
# ==============================

API_ID = int(os.environ.get("API_ID", 123456))  # Replace default with your API ID
API_HASH = os.environ.get("API_HASH", "abcd1234efgh5678")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "123456:ABC-xyz")

# ==============================
# 💾 Database (MongoDB)
# ==============================

MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://username:password@cluster.mongodb.net")

# ==============================
# 👑 Admin Settings
# ==============================

# You can add multiple admin IDs separated by commas in Render env:
# e.g. ADMINS=123456789,987654321
ADMINS = [int(x) for x in os.environ.get("ADMINS", "123456789").split(",")]

# ==============================
# 🌐 Other Optional Settings
# ==============================

BOT_USERNAME = os.environ.get("BOT_USERNAME", "TeraBoxLinkBot")
DATABASE_NAME = os.environ.get("DATABASE_NAME", "terabox")

# ==============================
# ✅ Status Message (Optional)
# ==============================
START_MSG = """
👋 **Welcome to TeraBox Link Converter Bot!**

Send me any TeraBox link, and I’ll convert it into a fast download link 🚀
"""

HELP_MSG = """
**🧩 Available Commands:**
/start - Show welcome message
/help - Show this help menu
/login - Login with BDUSS + STOKEN
/logout - Remove your account
"""

# ==============================
# ⚠️ Debug Mode (Optional)
# ==============================
DEBUG = bool(os.environ.get("DEBUG", False))
