import os
import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional

common_router = APIRouter(prefix="/common", tags=["通用功能"])

# 根目录
BASE_UPLOAD_DIR = "static/uploads"

# 定义允许的模块类型及其对应的子文件夹
# 这样既规范了路径，又防止用户随意传奇怪的路径
ALLOWED_MODULES = {
    "service": "service",  # 服务支持 -> static/uploads/service
    "about": "about",  # 关于我们 -> static/uploads/about
    "news": "news",  # 新闻资讯 -> static/uploads/news
    "avatar": "avatars",  # 用户头像 -> static/uploads/avatars
    "default": ""  # 默认未分类 -> static/uploads/
}


@common_router.post("/upload_image", summary="通用图片上传接口")
async def upload_image(
        file: UploadFile = File(...),
        module: str = Form(default="default")  # 前端传递模块名，如 'about', 'service'
):
    """
    通用上传接口：
    1. 接收 file 和 module 参数
    2. 根据 module 决定保存路径
    3. 返回 URL
    """

    # 1. 校验模块名，防止路径遍历攻击 (如 ../../etc)
    if module not in ALLOWED_MODULES:
        # 如果传了不认识的模块，就扔到 default 文件夹，或者报错
        # 这里选择扔到 default，保证健壮性
        sub_dir = ALLOWED_MODULES["default"]
    else:
        sub_dir = ALLOWED_MODULES[module]

    # 2. 构建完整路径
    upload_dir = os.path.join(BASE_UPLOAD_DIR, sub_dir)
    os.makedirs(upload_dir, exist_ok=True)  # 确保目录存在

    # 3. 文件校验
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只能上传图片文件")

    original_filename = file.filename or "image.png"
    ext = original_filename.rsplit(".", 1)[1].lower() if "." in original_filename else "jpg"

    allowed_exts = ["jpg", "jpeg", "png", "gif", "webp"]
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"不支持的格式：{ext}")

    # 4. 生成唯一文件名
    unique_filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(upload_dir, unique_filename)

    # 5. 保存文件
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败：{str(e)}")

    # 6. 构建 URL
    # 结果示例：/static/uploads/about/uuid-xxx.jpg
    image_url = f"/static/uploads/{sub_dir}/{unique_filename}"

    return {
        "code": 200,
        "msg": "上传成功",
        "data": {
            "url": image_url,
            "module": sub_dir  # 可选：返回实际保存的模块名供调试
        }
    }