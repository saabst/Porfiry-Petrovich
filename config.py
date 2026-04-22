import os
import logging
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, '.env'), override=True)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Porfiry")

class Config:
    # Обязательные
    XIAOZHI_TOKEN = os.getenv("XIAOZHI_MCP_TOKEN")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    COMPILE_THRESHOLD = int(os.getenv("COMPILE_THRESHOLD", "12"))

    # Опциональные Google Docs
    DIARY_DOC_ID = os.getenv("DIARY_DOC_ID")
    NOVEL_DOC_ID = os.getenv("NOVEL_DOC_ID")
    GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

    # Настройки стилей и расширений
    AUTHOR_STYLE = os.getenv("AUTHOR_STYLE", "pelevin")
    USE_GRAPH = os.getenv("USE_GRAPH", "true").lower() == "true"
    USE_IMAGES = os.getenv("USE_IMAGES", "true").lower() == "true"
    USE_PANDOC = os.getenv("USE_PANDOC", "false").lower() == "true"
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
    PANDOC_TEMPLATE = os.getenv("PANDOC_TEMPLATE", "")

    @classmethod
    def validate(cls):
        required = ["XIAOZHI_TOKEN", "DEEPSEEK_API_KEY"]
        missing = [r for r in required if not getattr(cls, r)]
        if missing:
            raise ValueError(f"Missing env: {', '.join(missing)}")