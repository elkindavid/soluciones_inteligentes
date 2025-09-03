import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "")
    SQLALCHEMY_DATABASE_URI_SQLITE = os.getenv("SQLALCHEMY_DATABASE_URI_SQLITE", "")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PREFERRED_URL_SCHEME = "https"

    # Bind para SQLite offline
    SQLALCHEMY_BINDS = {
    "local": f"sqlite:///{os.path.join(BASE_DIR, 'local.db')}"
}