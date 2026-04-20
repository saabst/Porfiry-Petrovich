import os
import logging
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, '.env'), override=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PorfiryV5")

class Config:
    XIAOZHI_TOKEN = os.getenv("XIAOZHI_MCP_TOKEN")
    DIARY_DOC_ID = os.getenv("DIARY_DOC_ID")
    NOVEL_DOC_ID = os.getenv("NOVEL_DOC_ID")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    CREDS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    COMPILE_THRESHOLD = int(os.getenv("COMPILE_THRESHOLD", "12"))

    @classmethod
    def validate(cls):
        required = {
            "XIAOZHI_MCP_TOKEN": cls.XIAOZHI_TOKEN,
            "DIARY_DOC_ID": cls.DIARY_DOC_ID,
            "NOVEL_DOC_ID": cls.NOVEL_DOC_ID,
            "DEEPSEEK_API_KEY": cls.DEEPSEEK_API_KEY
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(f"❌ Отсутствуют в .env: {', '.join(missing)}")
        if not os.path.exists(cls.CREDS_FILE):
            raise FileNotFoundError(f"❌ {cls.CREDS_FILE} не найден в {BASE_DIR}")