import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "data", "results")
HISTORY_DB = os.path.join(os.path.dirname(__file__), "data", "history.db")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
