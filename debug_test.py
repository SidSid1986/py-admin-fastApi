# debug_test.py
# 这是一个完全独立的脚本，不依赖 FastAPI 路由系统，直接测试核心逻辑
import sys
import os

# 确保能导入项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("💣 [START] 脚本开始执行...")

try:
    print("💣 [STEP 1] 导入数据库配置...")
    from database import SessionLocal

    print("✅ SessionLocal 导入成功")

    print("💣 [STEP 2] 导入模型...")
    from models.home_model import HomeImage

    print("✅ HomeImage 导入成功")

    print("💣 [STEP 3] 尝试创建数据库会话...")
    db = SessionLocal()
    print("✅ 数据库会话创建成功！")

    print("💣 [STEP 4] 尝试查询数据...")
    results = db.query(HomeImage).filter(HomeImage.type == "banner").all()
    print(f"✅ 查询成功！找到 {len(results)} 条数据")

    # 尝试序列化数据（模拟 FastAPI 的行为）
    import json

    data = [{"id": r.id, "url": r.img_url} for r in results]
    json_str = json.dumps(data)
    print(f"✅ 数据序列化成功: {json_str}")

    print("🎉 [SUCCESS] 所有步骤通过！代码逻辑没有问题。")
    print("👉 结论：问题出在 FastAPI 的路由注册、Depends 注入或 Uvicorn 的配置上。")

except Exception as e:
    print(f"❌ [FATAL ERROR] 发生致命错误: {e}")
    import traceback

    traceback.print_exc()

finally:
    if 'db' in locals():
        db.close()
        print("🔒 数据库连接已关闭")