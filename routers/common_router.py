import os
import uuid
import shutil
import requests
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import get_db
from sqlalchemy.orm import Session
from models.home_model import HomeImage  # 你的图片表

common_router = APIRouter(prefix="/common", tags=["通用功能"])

BASE_UPLOAD_DIR = "static/uploads"

ALLOWED_MODULES = {
    "service": "service",
    "about": "about",
    "news": "news",
    "avatar": "avatars",
    "default": "",
    "industry": "industry",
    "solution": "solution",
}

@common_router.post("/upload_image", summary="通用图片上传接口")
async def upload_image(
        file: UploadFile = File(...),
        module: str = Form(default="default")
):
    if module not in ALLOWED_MODULES:
        sub_dir = ALLOWED_MODULES["default"]
    else:
        sub_dir = ALLOWED_MODULES[module]

    upload_dir = os.path.join(BASE_UPLOAD_DIR, sub_dir)
    os.makedirs(upload_dir, exist_ok=True)

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只能上传图片文件")

    original_filename = file.filename or "image.png"
    ext = original_filename.rsplit(".", 1)[1].lower() if "." in original_filename else "jpg"
    allowed_exts = ["jpg", "jpeg", "png", "gif", "webp"]
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"不支持的格式：{ext}")

    unique_filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(upload_dir, unique_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败：{str(e)}")

    image_url = f"/static/uploads/{sub_dir}/{unique_filename}"

    return {
        "code": 200,
        "msg": "上传成功",
        "data": {"url": image_url}
    }


# ===================== ✅ 【你要的】通用删除图片接口 =====================
@common_router.delete("/delete_image", summary="通用删除图片（通用所有模块）")
def delete_image(
    img_url: str,
    db: Session = Depends(get_db)
):
    """
    通用删除图片：
    1. 删除服务器物理文件
    2. 删除 home_images 表里的记录
    全项目统一使用！
    """
    try:
        # 1. 删除物理文件
        clean_path = img_url.lstrip('/')
        file_path = os.path.join(os.getcwd(), clean_path)

        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"已删除文件: {file_path}")

        # 2. 删除数据库记录（根据 url 删除，最稳定）
        img_obj = db.query(HomeImage).filter(HomeImage.img_url == img_url).first()
        if img_obj:
            db.delete(img_obj)
            db.commit()
            print(f"已删除数据库记录: {img_url}")

        return {
            "code": 200,
            "msg": "删除成功"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


class WechatImageDTO(BaseModel):
    img_url: str
    module: str = "default"

@common_router.post("/download_wechat_image", summary="下载微信公众号防盗链图片")
async def download_wechat_image(dto: WechatImageDTO):
    img_url = dto.img_url
    module = dto.module

    if "mmbiz.qpic.cn" not in img_url:
        raise HTTPException(status_code=400, detail="不是微信公众号图片")

    if module not in ALLOWED_MODULES:
        sub_dir = ALLOWED_MODULES["default"]
    else:
        sub_dir = ALLOWED_MODULES[module]

    upload_dir = os.path.join(BASE_UPLOAD_DIR, sub_dir)
    os.makedirs(upload_dir, exist_ok=True)

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://mp.weixin.qq.com"
        }

        resp = requests.get(img_url, headers=headers, timeout=15, stream=True)
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail="微信图片下载失败，可能已过期")

        content_type = resp.headers.get("Content-Type", "")
        if "png" in content_type:
            ext = "png"
        elif "gif" in content_type:
            ext = "gif"
        elif "webp" in content_type:
            ext = "webp"
        else:
            ext = "jpg"

        unique_filename = f"{uuid.uuid4()}.{ext}"
        save_path = os.path.join(upload_dir, unique_filename)

        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024):
                f.write(chunk)

        image_url = f"/static/uploads/{sub_dir}/{unique_filename}"

        return {
            "code": 200,
            "msg": "微信图片下载成功",
            "data": {"url": image_url}
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"微信图片处理失败：{str(e)}")


# ===================== 视频上传接口 =====================
@common_router.post("/upload_video", summary="通用视频上传接口")
async def upload_video(
        file: UploadFile = File(...),
        module: str = Form(default="default")
):
    if module not in ALLOWED_MODULES:
        sub_dir = ALLOWED_MODULES["default"]
    else:
        sub_dir = ALLOWED_MODULES[module]

    upload_dir = os.path.join(BASE_UPLOAD_DIR, "videos", sub_dir)
    os.makedirs(upload_dir, exist_ok=True)

    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="只能上传视频文件")

    original_filename = file.filename or "video.mp4"
    ext = original_filename.rsplit(".", 1)[1].lower() if "." in original_filename else "mp4"
    allowed_exts = ["mp4", "mov", "avi", "flv", "wmv", "webm", "mkv"]
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"不支持的视频格式：{ext}")

    unique_filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(upload_dir, unique_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"视频保存失败：{str(e)}")

    video_url = f"/static/uploads/videos/{sub_dir}/{unique_filename}"

    return {
        "code": 200,
        "msg": "视频上传成功",
        "data": {"url": video_url}
    }