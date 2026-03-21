import os
import uuid
import shutil
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database import get_db
from models.file_model import FileRecord
from datetime import datetime
from pydantic import BaseModel

file_router = APIRouter(prefix="/files", tags=["文件管理"])

# 配置上传目录
FILE_UPLOAD_DIR = "static/uploads/files"
os.makedirs(FILE_UPLOAD_DIR, exist_ok=True)


# --- 响应模型 ---
class FileInfo(BaseModel):
    id: int
    original_name: str
    file_path: str
    file_size: int
    content_type: Optional[str]
    upload_time: datetime

    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    code: int
    msg: str
    data: list[FileInfo]
    total: int


class DeleteResponse(BaseModel):
    code: int
    msg: str


# --- 1. 上传文件接口 ---
@file_router.post("/upload", summary="上传文件")
async def upload_file(
        file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """
    上传通用文件，返回文件信息
    """
    # 1. 基础校验
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    # 可选：限制文件大小 (例如 50MB)
    # 注意：需要在 FastAPI 启动时配置 max_upload_size，这里做二次检查
    # 简单检查：如果读取完发现太大再抛错，或者依赖中间件
    # 这里假设由服务器配置限制，只做逻辑处理

    # 2. 生成唯一文件名
    original_filename = file.filename
    if "." in original_filename:
        ext = original_filename.rsplit(".", 1)[1].lower()
    else:
        ext = ""

    unique_filename = f"{uuid.uuid4()}.{ext}" if ext else uuid.uuid4().hex
    file_path_rel = f"/static/uploads/files/{unique_filename}"
    file_path_abs = os.path.join(FILE_UPLOAD_DIR, unique_filename)

    # 3. 保存文件
    try:
        with open(file_path_abs, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 获取文件大小 (需要重新定位或统计，shutil.copyfileobj后文件指针在末尾)
        # 简单做法：直接读 os.path.getsize
        file_size = os.path.getsize(file_path_abs)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败：{str(e)}")

    # 4. 存入数据库
    new_record = FileRecord(
        original_name=original_filename,
        stored_name=unique_filename,
        file_path=file_path_rel,
        file_size=file_size,
        content_type=file.content_type,
        upload_time=datetime.now()
    )

    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    return {
        "code": 200,
        "msg": "上传成功",
        "data": {
            "id": new_record.id,
            "original_name": new_record.original_name,
            "file_path": new_record.file_path,
            "file_size": new_record.file_size,
            "upload_time": new_record.upload_time
        }
    }


# --- 2. 获取文件列表接口 ---
@file_router.get("/list", summary="获取文件列表", response_model=FileListResponse)
def get_file_list(
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, description="每页数量"),
        db: Session = Depends(get_db)
):
    """
    分页获取文件列表，按上传时间倒序
    """
    # 计算偏移量
    offset = (page - 1) * page_size

    # 查询总数
    total = db.query(FileRecord).count()

    # 查询当前页数据 (按时间倒序)
    records = db.query(FileRecord) \
        .order_by(desc(FileRecord.upload_time)) \
        .offset(offset) \
        .limit(page_size) \
        .all()

    return {
        "code": 200,
        "msg": "获取成功",
        "data": records,
        "total": total
    }


# --- 3. 删除文件接口 ---
@file_router.delete("/delete/{file_id}", summary="删除文件", response_model=DeleteResponse)
def delete_file(
        file_id: int,
        db: Session = Depends(get_db)
):
    """
    删除文件：同时删除数据库记录和本地物理文件
    """
    # 1. 查找记录
    record = db.query(FileRecord).filter(FileRecord.id == file_id).first()

    if not record:
        raise HTTPException(status_code=404, detail="文件记录不存在")

    # 2. 构建物理路径
    # 注意：record.file_path 是 /static/...，需要去掉 /static 映射到本地磁盘
    # 假设 project_root/static/uploads/files
    # 更稳妥的方式是利用 stored_name 重新构建，或者解析 path
    # 这里我们直接用 stored_name 构建，因为目录结构是固定的
    file_name = record.stored_name
    file_path_abs = os.path.join(FILE_UPLOAD_DIR, file_name)

    # 3. 删除物理文件
    if os.path.exists(file_path_abs):
        try:
            os.remove(file_path_abs)
        except Exception as e:
            # 如果文件删除失败，可以选择回滚或不删除数据库，这里选择记录警告但继续删库
            print(f"Warning: 物理文件删除失败 {file_path_abs}: {e}")

    # 4. 删除数据库记录
    db.delete(record)
    db.commit()

    return {
        "code": 200,
        "msg": "删除成功"
    }