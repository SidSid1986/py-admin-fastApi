import os
import shutil
import zipfile
from fastapi import APIRouter, UploadFile, File, Header, HTTPException

# 创建部署路由
deploy_router = APIRouter()

# 安全密钥
UPLOAD_SECRET = "YN8gpq9DLAEblpA"

# 宝塔网站根目录
VUE3_ADMIN_PATH = "/www/wwwroot/free-admin"
NUXT_WEB_PATH = "/www/wwwroot/free-nuxt"


# =================================================================

# 解压覆盖函数
def unzip_cover(zip_path: str, target_path: str):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # 先删除旧目录（完全覆盖）
        if os.path.exists(target_path):
            shutil.rmtree(target_path)
        os.makedirs(target_path, exist_ok=True)

        # 解压
        zip_ref.extractall(target_path)


# ====================== 部署接口 ======================

# 部署 Vue3 管理端
@deploy_router.post("/deploy/vue3-admin")
async def deploy_vue3(
        file: UploadFile = File(...),
        secret: str = Header(None)
):
    if secret != UPLOAD_SECRET:
        raise HTTPException(status_code=403, detail="密钥错误")

    zip_save_path = "/tmp/deploy_vue3.zip"
    with open(zip_save_path, "wb") as f:
        f.write(await file.read())

    unzip_cover(zip_save_path, VUE3_ADMIN_PATH)
    return {"status": "success", "msg": "Vue3管理端部署成功！"}


# 部署 Nuxt 官网
@deploy_router.post("/deploy/nuxt-web")
async def deploy_nuxt(
        file: UploadFile = File(...),
        secret: str = Header(None)
):
    if secret != UPLOAD_SECRET:
        raise HTTPException(status_code=403, detail="密钥错误")

    zip_save_path = "/tmp/deploy_nuxt.zip"
    with open(zip_save_path, "wb") as f:
        f.write(await file.read())

    unzip_cover(zip_save_path, NUXT_WEB_PATH)
    return {"status": "success", "msg": "Nuxt官网部署成功！"}