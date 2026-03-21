import os
import uuid
import shutil
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from models.about_model import AboutUs
from datetime import datetime
from pydantic import BaseModel, Field

about_router = APIRouter(prefix="/about", tags=["关于我们管理"])

# 配置上传目录
ABOUT_UPLOAD_DIR = "static/uploads/about"
os.makedirs(ABOUT_UPLOAD_DIR, exist_ok=True)

# --- 定义接收数据的模型 ---
class AboutUpdateRequest(BaseModel):
    cover_image: str = Field(..., description="封面图片URL")
    content: str = Field(..., description="富文本HTML内容")

@about_router.get("/info", summary="获取关于我们信息")
def get_about_info(db: Session = Depends(get_db)):
    """获取当前存储的信息"""
    record = db.query(AboutUs).filter(AboutUs.id == 1).first()

    if not record:
        return {
            "code": 200,
            "msg": "暂无数据",
            "data": {
                "cover_image": "",
                "content": ""
            }
        }

    return {
        "code": 200,
        "msg": "获取成功",
        "data": {
            "cover_image": record.cover_image or "",
            "content": record.content or ""
        }
    }

@about_router.post("/save", summary="保存关于我们信息 (封面 + 内容)")
def save_about_info(
        request: AboutUpdateRequest,
        db: Session = Depends(get_db)
):
    """
    接收 JSON 数据，保存或更新关于我们的信息。
    预期 JSON: { "cover_image": "/static/...", "content": "<p>...</p>" }
    """
    # 查找记录 (假设只存一条，ID 固定为 1)
    record = db.query(AboutUs).filter(AboutUs.id == 1).first()

    if not record:
        # 不存在则创建
        record = AboutUs(
            id=1,
            cover_image=request.cover_image,
            content=request.content,
            update_time=datetime.now()
        )
        db.add(record)
    else:
        # 存在则更新
        record.cover_image = request.cover_image
        record.content = request.content
        record.update_time = datetime.now()

    try:
        db.commit()
        db.refresh(record)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"数据库保存失败: {str(e)}")

    return {
        "code": 200,
        "msg": "保存成功",
        "data": {
            "id": record.id,
            "cover_image": record.cover_image,
            "content": record.content
        }
    }

@about_router.post("/upload_image", summary="上传图片 (封面或富文本)")
async def upload_about_image(file: UploadFile = File(...)):
    """
    上传图片并返回访问 URL
    """
    # 1. 校验
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只能上传图片文件")

    # 2. 处理文件名
    original_filename = file.filename or "image.png"
    ext = original_filename.rsplit(".", 1)[1].lower() if "." in original_filename else "jpg"
    allowed_exts = ["jpg", "jpeg", "png", "gif", "webp"]
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"不支持的格式：{ext}")

    # 3. 生成唯一名
    unique_filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(ABOUT_UPLOAD_DIR, unique_filename)

    # 4. 保存
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败：{str(e)}")

    # 5. 返回 URL (确保与 static 挂载路径一致)
    image_url = f"/static/uploads/about/{unique_filename}"

    return {
        "code": 200,
        "msg": "上传成功",
        "data": {
            "url": image_url
        }
    }