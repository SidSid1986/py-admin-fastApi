# fix_db.py
from database import engine
from models.category_model import Category
from sqlalchemy import inspect


def add_missing_columns():
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('categories')]

    if 'category_type' not in columns:
        print("⚠️ 检测到数据库缺少 category_type 列，正在添加...")
        from sqlalchemy import text
        with engine.connect() as conn:
            # 添加列
            conn.execute(text("ALTER TABLE categories ADD COLUMN category_type VARCHAR(50) NULL"))
            # 添加索引
            conn.execute(text("CREATE INDEX idx_category_type ON categories (category_type)"))
            conn.commit()
        print("✅ 数据库结构已更新！请重启后端服务。")
    else:
        print("✅ 数据库结构已是最新。")


if __name__ == "__main__":
    add_missing_columns()