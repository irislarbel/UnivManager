import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# Blackboard 설정
BLACKBOARD_URL = os.getenv("BLACKBOARD_URL", "https://blackboard.yourschool.edu")
BLACKBOARD_USER = os.getenv("BLACKBOARD_USER", "")
BLACKBOARD_PASS = os.getenv("BLACKBOARD_PASS", "")

# Telegram 설정
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# AI 및 분석 설정 (Gemini 3 Pro)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# 데이터베이스 저장 경로 (ChromaDB)
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")

# 데이터 및 파일 저장 경로
DOWNLOAD_PATH = os.path.join(os.getcwd(), "downloads")
DATA_FILE = "processed_items.json"

# 필요한 폴더 생성
if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)
if not os.path.exists(CHROMA_DB_PATH):
    os.makedirs(CHROMA_DB_PATH)

