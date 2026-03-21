import os
import shutil
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
from models.home_model import HomeImage
from datetime import datetime

# 配置上传文件夹路径 (相对于项目根目录)
UPLOAD_DIR = "static/uploads"

# 确保目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)

home_router = APIRouter(prefix="/home", tags=["首页接口"])


@home_router.get("/index_images", summary="获取首页所有图片")
def get_index_images(db: Session = Depends(get_db)):
    """
    获取首页图片，现在会额外返回 original_name 供前端展示
    """
    # 查询 Banner
    banners = db.query(HomeImage).filter(
        HomeImage.type == "banner",
        HomeImage.is_active == True
    ).order_by(HomeImage.sort.asc()).all()

    # 查询 Core
    cores = db.query(HomeImage).filter(
        HomeImage.type == "core",
        HomeImage.is_active == True
    ).order_by(HomeImage.sort.asc()).all()

    # 查询 Footer (通常只有一个)
    footer = db.query(HomeImage).filter(
        HomeImage.type == "footer",
        HomeImage.is_active == True
    ).first()

    # 构建返回数据
    # 使用 getattr(img, 'original_name', None) 是为了防止旧数据没有该字段时报错
    data = {
        "banners": [
            {
                "id": img.id,
                "img_url": img.img_url,
                "sort": img.sort,
                "original_name": getattr(img, 'original_name', None)  # 新增
            } for img in banners
        ],
        "cores": [
            {
                "id": img.id,
                "img_url": img.img_url,
                "sort": img.sort,
                "original_name": getattr(img, 'original_name', None)  # 新增
            } for img in cores
        ],
        "footer": {
            "id": footer.id,
            "img_url": footer.img_url,
            "original_name": getattr(footer, 'original_name', None)  # 新增
        } if footer else None
    }

    return {"code": 200, "msg": "获取成功", "data": data}


@home_router.post("/upload_image", summary="上传图片并记录到数据库")
async def upload_image(
        file: UploadFile = File(...),
        img_type: str = Form(...),
        sort: int = Form(default=0),
        db: Session = Depends(get_db)
):
    # 1. 验证文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只能上传图片文件")

    # 2. 验证类型参数
    allowed_types = ["banner", "core", "footer"]
    if img_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"类型错误，必须是 {allowed_types}")

    # 3. 提取原始文件名和后缀
    original_filename = file.filename or "unknown.png"
    # 安全提取后缀，防止文件名中没有点
    if "." in original_filename:
        file_extension = original_filename.rsplit(".", 1)[1].lower()
    else:
        file_extension = "jpg"

    # 限制后缀白名单 (可选，增强安全)
    allowed_extensions = ["jpg", "jpeg", "png", "gif", "webp"]
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式：{file_extension}")

    # 4. 生成唯一的物理文件名 (UUID)
    unique_filename = f"{uuid.uuid4()}.{file_extension}"

    # 5. 构建保存路径
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # 6. 保存文件到磁盘
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        # 如果保存失败，尝试删除可能产生的空文件
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"文件保存失败：{str(e)}")

    # 7. 生成访问 URL
    image_url = f"/static/uploads/{unique_filename}"

    # 8. 写入数据库
    new_image = HomeImage(
        img_url=image_url,
        type=img_type,
        sort=sort,
        is_active=True,
        create_time=datetime.now(),
        # 【关键】保存原始文件名到数据库
        original_name=original_filename
    )

    db.add(new_image)
    db.commit()
    db.refresh(new_image)

    # 🔍【新增调试代码】在返回前打印到终端
    print("=" * 50)
    print(f"🔍 DEBUG: new_image.id = {new_image.id}")
    print(f"🔍 DEBUG: new_image.original_name 类型 = {type(new_image.original_name)}")
    print(f"🔍 DEBUG: new_image.original_name 值 = '{new_image.original_name}'")

    # 检查字典构建过程
    response_data = {
        "id": new_image.id,
        "img_url": image_url,
        "type": img_type,
        "original_name": new_image.original_name
    }
    print(f"🔍 DEBUG: 准备返回的字典内容 = {response_data}")
    print("=" * 50)
    return {
        "code": 200,
        "msg": "✅ 测试成功：代码已更新！原始文件名是：" + str(original_filename),  # 修改这里
        "data": {
            "id": new_image.id,
            "img_url": image_url,
            "type": img_type,
            "original_name": new_image.original_name
        }
    }


@home_router.delete("/delete_image/{image_id}", summary="删除图片")
def delete_image(image_id: int, db: Session = Depends(get_db)):
    img_obj = db.query(HomeImage).filter(HomeImage.id == image_id).first()
    if not img_obj:
        raise HTTPException(status_code=404, detail="图片未找到")

    # ===  物理文件删除逻辑 ===
    try:
        # 1. 获取数据库中的相对路径 (例如："/static/uploads/xxx.png")
        relative_path = img_obj.img_url

        # 2. 去掉开头的斜杠，变成 "static/uploads/xxx.png"
        clean_path = relative_path.lstrip('/')

        # 3. 直接拼接当前工作目录 (main.py 所在目录)
        # 结果：/your/project/path/static/uploads/xxx.png
        file_path = os.path.join(os.getcwd(), clean_path)

        print(f"尝试删除文件: {file_path}")  # 调试打印，方便看实际路径

        # 4. 检查并删除
        if os.path.exists(file_path):
            os.remove(file_path)
            print("✅ 物理文件删除成功")
        else:
            print(f"⚠️ 文件不存在: {file_path}")

    except Exception as e:
        print(f"❌ 删除物理文件时出错: {e}")
        # 这里可以选择是否抛出异常，通常记录日志即可，继续执行数据库删除

    # === 删除数据库记录 ===
    db.delete(img_obj)
    db.commit()

    return {"code": 200, "msg": "删除成功"}