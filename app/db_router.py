# app/db_router.py
import socket
from sqlalchemy import create_engine, text
from config import Config

SQLSERVER_HOST = "190.255.33.10"
SQLSERVER_PORT = 2500

def is_online(timeout=1.5):
    try:
        with socket.create_connection((SQLSERVER_HOST, SQLSERVER_PORT), timeout=timeout):
            return True
    except OSError:
        return False

def get_remote_engine():
    # pool_pre_ping evita conexiones muertas
    return create_engine(Config.SQLALCHEMY_DATABASE_URI_SQLSERVER, pool_pre_ping=True)
