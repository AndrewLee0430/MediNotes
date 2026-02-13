"""
SQLite Database Configuration
提供 SQLAlchemy 連接和 Session 管理
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 資料庫檔案路徑
# 在開發環境使用本地路徑，在生產環境使用 EFS 掛載路徑
DB_DIR = os.getenv("DB_DIR", "data")
DB_PATH = os.path.join(DB_DIR, "medinotes.db")

# 確保目錄存在
Path(DB_DIR).mkdir(parents=True, exist_ok=True)

# SQLite 連接字串
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# 建立 Engine
# check_same_thread=False 允許多線程使用同一連接（SQLite 預設不允許）
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    echo=False  # 設為 True 可以看到 SQL 查詢 log
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    FastAPI dependency for getting database session
    
    使用方式:
    @app.get("/")
    def endpoint(db: Session = Depends(get_db)):
        ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化資料庫（建立所有 tables）
    通常在 app 啟動時呼叫
    """
    # Import all models here to ensure they are registered
    from api.models.sql_models import AuditLog, ChatHistory, UserFeedback
    
    Base.metadata.create_all(bind=engine)
    print(f"✅ Database initialized at {DB_PATH}")


# 測試用
if __name__ == "__main__":
    print(f"Database URL: {SQLALCHEMY_DATABASE_URL}")
    print(f"Database Path: {DB_PATH}")
    
    # 初始化資料庫
    init_db()
    
    # 測試連接
    db = SessionLocal()
    try:
        # 執行簡單查詢測試
        result = db.execute("SELECT 1")
        print("✅ Database connection successful!")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
    finally:
        db.close()