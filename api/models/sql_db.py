# api/database/sql_db.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 讀取環境變數，預設為本地 SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./medinotes.db")

# 設定 connect_args (僅針對 SQLite 需要 check_same_thread=False)
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

# 建立 Engine
engine = create_engine(
    DATABASE_URL, 
    connect_args=connect_args
)

# 建立 SessionLocal 類別
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 定義 Base (供 models 使用)
Base = declarative_base()

# Dependency: 讓 FastAPI 路由可以依賴這個 function 取得 DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()