# test_db.py
from database import SessionLocal, engine
from models.home_model import HomeImage
from sqlalchemy import text

print("1. 测试数据库引擎连接...")
try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ 数据库连接成功！")
except Exception as e:
    print(f"❌ 数据库连接失败: {e}")
    exit()

print("\n2. 测试查询表数据...")
db = SessionLocal()
try:
    # 尝试查询一条数据，这会强制检查表是否存在
    count = db.query(HomeImage).count()
    print(f"✅ 表存在且可查询，当前数据量: {count}")

    # 尝试查询具体字段
    sample = db.query(HomeImage).first()
    if sample:
        print(f"   示例数据: ID={sample.id}, Type={sample.type}")
    else:
        print("   表是空的，但这没关系。")

except Exception as e:
    print(f"❌ 查询失败: {e}")
    print("💡 提示：如果是 'Table ... doesn't exist'，请运行下面的建表脚本。")
finally:
    db.close()