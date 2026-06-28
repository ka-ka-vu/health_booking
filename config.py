import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")

EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

SECRET_KEY = os.getenv("SECRET_KEY")

if not MONGO_URI:
    raise ValueError("Thiếu MONGO_URI trong file .env")

if not EMAIL_ADDRESS:
    raise ValueError("Thiếu EMAIL_ADDRESS trong file .env")

if not EMAIL_PASSWORD:
    raise ValueError("Thiếu EMAIL_PASSWORD trong file .env")

if not SECRET_KEY:
    raise ValueError("Thiếu SECRET_KEY trong file .env")