from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, UploadFile,File
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
import os
import uuid
import shutil
from datetime import datetime

from models.service_model import ServiceContent
from database import get_db


UPLOAD_DIR = "static/uploads/service"
os.makedirs(UPLOAD_DIR, exist_ok=True)

service_router = APIRouter(prefix="/service", tags=["服务管理"])

class ServiceContentUpdate(BaseModel):
    content: Optional[str] = Field(None, description="服务内容")

 # 获取wangEditor数据
@service_router.get("/content", summary="获取服务内容")
def get_service_content(db: Session = Depends(get_db)):
    content_obj = db.query(ServiceContent).filter(ServiceContent.id == 1).first()

    if not content_obj:
        content_obj = ServiceContent(id=1, content="暂无服务内容")
        db.add(content_obj)
        db.commit()
        db.refresh(content_obj)

    # 直接返回统一格式的字典
    return {
        "code": 200,
        "msg": "获取成功",
        "data": {
            "id": content_obj.id,
            "content": content_obj.content
        }
    }

# 修改wangEditor
@service_router.put("/content", summary="更新服务内容")
def update_service_content(
        update_data: ServiceContentUpdate,
        db: Session = Depends(get_db)
):
    content_obj = db.query(ServiceContent).filter(ServiceContent.id == 1).first()

    if not content_obj:
        content_obj = ServiceContent(id=1, content=update_data.content or "")
        db.add(content_obj)
    else:
        if update_data.content is not None:
            content_obj.content = update_data.content

    db.commit()
    db.refresh(content_obj)

    return {
        "code": 200,
        "msg": "更新成功",
        "data": {
            "id": content_obj.id,
            "content": content_obj.content
        }
    }


@service_router.post("/upload_image", summary="富文本编辑器图片上传")
async def upload_rich_text_image(file: UploadFile = File(...)):
    """
    专门供 WangEditor 使用的图片上传接口
    不需要存入数据库，只需保存文件并返回 URL
    """
    # 1. 校验文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只能上传图片文件")

    # 2. 提取后缀
    original_filename = file.filename or "image.png"
    if "." in original_filename:
        ext = original_filename.rsplit(".", 1)[1].lower()
    else:
        ext = "jpg"

    # 安全白名单
    allowed_exts = ["jpg", "jpeg", "png", "gif", "webp"]
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"不支持的格式：{ext}")

    # 3. 生成唯一文件名 (防止覆盖)
    # 格式：uuid + .ext
    unique_filename = f"{uuid.uuid4()}.{ext}"

    # 4. 构建物理路径
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # 5. 保存文件
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败：{str(e)}")

    # 6. 构建访问 URL
    # 关键点：这里必须是前端能访问到的 HTTP 地址
    # 假设你的 FastAPI 启动了 static 目录映射，且前缀是 /static
    image_url = f"/static/uploads/service/{unique_filename}"

    # 7. 返回 WangEditor 需要的格式
    # 你的前端代码期待：{ code: 200, data: { url: "..." } }
    return {
        "code": 200,
        "msg": "上传成功",
        "data": {
            "url": image_url  # 这里的 key 必须是 url
        }
    }