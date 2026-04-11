import os
import uuid
import shutil
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
from models.about_model import AboutUs, Banner, AboutStep
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



# ================= 轮播图相关接口 =================

@about_router.post("/banner/upload", summary="上传轮播图 (自动入库)")
async def upload_banner_image(
        file: UploadFile = File(...),
        sort_order: int = Form(default=0),
        db: Session = Depends(get_db)
):
    """
    专门用于轮播图：
    1. 接收文件
    2. 保存到硬盘 (复用 about 目录)
    3. 自动在数据库 banner 表中创建一条记录
    """
    # 校验文件
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只能上传图片文件")

    # 处理文件名
    original_filename = file.filename or "banner.jpg"
    ext = original_filename.rsplit(".", 1)[1].lower() if "." in original_filename else "jpg"
    allowed_exts = ["jpg", "jpeg", "png", "gif", "webp"]
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"不支持的格式：{ext}")

    # 生成唯一名
    unique_filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(ABOUT_UPLOAD_DIR, unique_filename)

    # 保存文件
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败：{str(e)}")

    # 生成 URL
    img_url = f"/static/uploads/about/{unique_filename}"

    # 写入数据库
    new_banner = Banner(
        img_url=img_url,
        sort_order=sort_order,
        create_time=datetime.now(),
        update_time=datetime.now()
    )
    db.add(new_banner)
    try:
        db.commit()
        db.refresh(new_banner)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="数据库写入失败")

    return {
        "code": 200,
        "msg": "轮播图添加成功",
        "data": {
            "id": new_banner.id,
            "img_url": new_banner.img_url,
            "sort_order": new_banner.sort_order
        }
    }


@about_router.get("/banners", summary="获取轮播图列表")
def get_banner_list(db: Session = Depends(get_db)):
    """
    获取所有轮播图，按排序权重升序排列
    """
    banners = db.query(Banner).order_by(Banner.sort_order.asc()).all()

    banner_data = [
        {"id": b.id, "img_url": b.img_url, "sort_order": b.sort_order}
        for b in banners
    ]

    return {
        "code": 200,
        "msg": "获取成功",
        "data": banner_data,
        "total": len(banner_data)
    }


# ================= 发展历程 (AboutStep) 接口 =================

class StepCreateRequest(BaseModel):
    id: Optional[int] = Field(None, description="步骤ID，用于更新时传入，新增时忽略")
    title: str = Field(..., description="步骤标题 (如年份)")
    img_url: str = Field(..., description="图片URL")
    sort_order: int = Field(default=0, description="排序权重")


# 上传step图片
@about_router.post("/step/img/upload", summary="上传历程步骤图片 (仅保存文件，不入库)")
async def upload_step_image(file: UploadFile = File(...)):
    """
    专门用于历程步骤的图片上传：
    1. 接收文件
    2. 保存到硬盘 (复用 about 目录)
    3. 返回图片访问 URL (不操作数据库)
    """
    # 校验文件
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只能上传图片文件")

    # 处理文件名
    original_filename = file.filename or "step_image.jpg"
    ext = original_filename.rsplit(".", 1)[1].lower() if "." in original_filename else "jpg"
    allowed_exts = ["jpg", "jpeg", "png", "gif", "webp"]
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"不支持的格式：{ext}")

    # 生成唯一名
    unique_filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(ABOUT_UPLOAD_DIR, unique_filename)

    # 保存文件
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败：{str(e)}")

    # 生成并返回 URL
    img_url = f"/static/uploads/about/{unique_filename}"

    return {
        "code": 200,
        "msg": "上传成功",
        "data": {
            "img_url": img_url
        }
    }

@about_router.get("/steps", summary="获取发展历程列表")
def get_steps(db: Session = Depends(get_db)):
    """
    获取所有历程步骤，按排序权重升序排列
    """
    steps = db.query(AboutStep).order_by(AboutStep.sort_order.asc()).all()

    step_data = [
        {
            "id": s.id,
            "title": s.title,
            "img": s.img_url,
            "sort_order": s.sort_order
        }
        for s in steps
    ]

    return {
        "code": 200,
        "msg": "获取成功",
        "data": step_data,
        "total": len(step_data)
    }


@about_router.post("/step/save", summary="保存历程步骤 (新增或更新)")
def save_step(
        request: StepCreateRequest, # 只接收请求体对象
        db: Session = Depends(get_db)
):
    """
    统一的保存接口：
    - 如果 request 对象中包含有效的 id，则更新现有步骤
    - 如果 request 对象中没有 id 或 id 无效，则创建新步骤
    """
    # 1. 从请求体 (request) 中获取 ID
    step_id_from_request = request.id

    # 2. 尝试根据 ID 查找现有记录
    step = None
    if step_id_from_request:
        step = db.query(AboutStep).filter(AboutStep.id == step_id_from_request).first()

    # 3. 判断逻辑
    if step:
        # --- 更新 ---
        step.title = request.title
        step.img_url = request.img_url
        step.sort_order = request.sort_order
        step.update_time = datetime.now()

        # 提交后返回更新后的对象
        db.commit()
        db.refresh(step)
        msg = "更新成功"
    else:
        # --- 新增 ---
        # 检查请求中是否包含 id，如果包含但数据库中找不到对应记录，可能是客户端错误
        if step_id_from_request is not None:
             raise HTTPException(status_code=404, detail=f"ID 为 {step_id_from_request} 的步骤不存在，无法更新。")

        new_step = AboutStep(
            title=request.title,
            img_url=request.img_url,
            sort_order=request.sort_order,
            create_time=datetime.now(),
            update_time=datetime.now()
        )
        db.add(new_step)
        db.commit()
        db.refresh(new_step)
        step = new_step
        msg = "添加成功"

    # 4. 统一返回
    return {
        "code": 200,
        "msg": msg,
        "data": {
            "id": step.id,
            "title": step.title,
            "img": step.img_url,
            "sort_order": step.sort_order
        }
    }

@about_router.delete("/step/delete/{step_id}", summary="删除历程步骤")
def delete_step(step_id: int, db: Session = Depends(get_db)):
    """
    删除指定ID的历程节点
    """
    step = db.query(AboutStep).filter(AboutStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="步骤未找到")

    db.delete(step)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="删除失败")

    return {"code": 200, "msg": "删除成功"}


#删除banner的接口
@about_router.delete("/banner/delete/{banner_id}", summary="删除轮播图")
def delete_banner(banner_id: int, db: Session = Depends(get_db)):
    """
    删除指定ID的轮播图
    1. 从数据库删除记录
    2. 同时删除对应的图片文件
    """
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="轮播图未找到")

    # 获取图片路径
    img_path = banner.img_url.lstrip('/')  # 去掉开头的斜杠

    # 从数据库删除记录
    db.delete(banner)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="删除失败")

    # 删除物理文件
    try:
        full_img_path = os.path.join(os.getcwd(), img_path)
        if os.path.exists(full_img_path):
            os.remove(full_img_path)
    except Exception as e:
        # 文件删除失败不影响数据库操作，但可以记录日志
        print(f"警告：删除图片文件失败 {full_img_path}: {str(e)}")

    return {"code": 200, "msg": "删除成功"}



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