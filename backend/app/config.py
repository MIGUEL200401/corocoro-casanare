import os
from dotenv import load_dotenv
load_dotenv()

class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY","")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY","")
    GROQ_MODEL = os.getenv("GROQ_MODEL","openai/gpt-oss-20b")
    REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY","")
    PIAPI_API_KEY = os.getenv("PIAPI_API_KEY","")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY","")
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","")
    ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID","")  # Telegram ID del admin Yeferson
    ADMIN_PHONE = os.getenv("ADMIN_PHONE","+573145979898")  # +57 3145979898 corregido
    DATABASE_URL = os.getenv("DATABASE_URL","sqlite:///./corocoro.db")
    CASANARE_API = os.getenv("CASANARE_API","http://localhost:4000")
    ELEVENLABS_KEY = os.getenv("ELEVENLABS_API_KEY","")
    PORT = int(os.getenv("PORT","8000"))
settings = Settings()
