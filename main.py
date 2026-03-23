from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# --- 数据库相关导入 (新增) ---
from database import engine, Base
# 必须导入所有模型类，这样 create_all 才能识别到它们并建表
from models.home_model import HomeImage       # 假设你之前的图片模型叫这个，如果文件名不同请调整
from models.service_model import ServiceContent # <--- 刚刚新建的服务内容模型

# home
from routers.home_router import home_router

# service
from routers.service_router import service_router

# about 关于我们
from routers.about_router import about_router

# 文件
from routers.file_router import file_router

# 新闻news
from routers.news_router import news_router

# 行业
from routers.industry_router import industry_router

# 解决方案
from routers.solution_router import solution_router

# 产品分类
from routers.category_router import category_router

# 产品
from routers.product_router import product_router

#上传图片
from routers.common_router import common_router




app = FastAPI(title="首页图片与服务接口", version="1.0")

# 挂载静态文件目录 (用于访问上传的图片)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- 自动创建数据库表 (新增) ---
# 这行代码会检查数据库，如果表不存在则自动创建，如果已存在则忽略
Base.metadata.create_all(bind=engine)

# 3. 注册路由
app.include_router(home_router)
app.include_router(service_router)

app.include_router(about_router)

app.include_router(file_router)

app.include_router(news_router)

app.include_router(industry_router)

app.include_router(solution_router)

app.include_router(category_router)

app.include_router(product_router)


app.include_router(common_router)


@app.get("/", summary="健康检查")
def root():
    return {
        "msg": "服务运行正常",
        "docs": "/docs",
        "available_endpoints": [
            "/home/images (首页图片管理)",
            "/service/content (服务内容管理)"
        ]
    }