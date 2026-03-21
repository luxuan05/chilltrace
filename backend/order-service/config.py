import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SSL_CA = os.getenv("SSL_CA")
    PORT = int(os.getenv("PORT", 5000))

    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("DATABASE_URL is not set in .env")

    if SSL_CA:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "connect_args": {
                "ssl": {
                    "ca": SSL_CA
                }
            },
            "pool_pre_ping": True
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True
        }