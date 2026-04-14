from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# --- 数据库相关导入 ---
from database import engine, Base

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
#上传图片(通用)
from routers.common_router import common_router

#工艺
from routers.process_router import process_router

# 部署
from routers.deploy_router import deploy_router

# 聊天
from routers.chat_router import chat_router


GLOBAL_PREFIX = "/api"

app = FastAPI(title="首页图片与服务接口", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://www.ytfreeie.com/",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://www.your-domain.com",
        "https://your-domain.com",
        "https://api.your-domain.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 自动创建数据库表
Base.metadata.create_all(bind=engine)

# 注册路由
app.include_router(home_router, prefix=GLOBAL_PREFIX)
app.include_router(service_router , prefix=GLOBAL_PREFIX)
app.include_router(about_router , prefix=GLOBAL_PREFIX)
app.include_router(file_router, prefix=GLOBAL_PREFIX)
app.include_router(news_router, prefix=GLOBAL_PREFIX)
app.include_router(industry_router, prefix=GLOBAL_PREFIX)
app.include_router(solution_router, prefix=GLOBAL_PREFIX)
app.include_router(category_router, prefix=GLOBAL_PREFIX)
app.include_router(product_router, prefix=GLOBAL_PREFIX)
app.include_router(common_router, prefix=GLOBAL_PREFIX)

app.include_router(process_router, prefix=GLOBAL_PREFIX)

# 部署
app.include_router(deploy_router, prefix=GLOBAL_PREFIX)

# 聊天（公众号）
app.include_router(chat_router, prefix=GLOBAL_PREFIX)


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


# ======================  启动代码 ======================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )