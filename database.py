# database.py 修正后代码
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

# 读取环境变量，增加默认值
DB_USER = os.getenv("DB_USER", "root")  # 默认root
DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")  # 默认空密码
DB_HOST = os.getenv("DB_HOST", "localhost")  # 默认localhost
DB_PORT = os.getenv("DB_PORT", "3306")  # 默认3306
DB_NAME = os.getenv("DB_NAME", "fastapi_admin")  # 默认数据库名


DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()