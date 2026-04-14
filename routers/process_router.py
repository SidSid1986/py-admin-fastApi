from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models.process_model import Process
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy import asc, desc

process_router = APIRouter(prefix="/process", tags=["流程方案管理"])


class ProcessSaveRequest(BaseModel):
    id: Optional[int] = Field(None, description="方案ID (有则更新，无则新增)")
    title: str = Field(..., min_length=1, max_length=200, description="方案标题")
    cover1: Optional[str] = Field(None, description="封面图1 URL")
    cover2: Optional[str] = Field(None, description="封面图2 URL")
    content: str = Field(..., description="富文本详情内容")
    sort: int = Field(0, description="排序权重")
    is_active: Optional[bool] = Field(True, description="是否启用")



# 2. 保存接口
@process_router.post("/save", summary="保存流程方案 (新增或更新)")
def save_process(req: ProcessSaveRequest, db: Session = Depends(get_db)):
    process_record = None

    if req.id is None:
        # 新增
        new_process = Process(
            title=req.title,
            cover1=req.cover1,
            cover2=req.cover2,
            content=req.content,
            sort=req.sort,
            is_active=req.is_active if req.is_active is not None else True,
            create_time=datetime.now(),
            update_time=datetime.now()
        )
        db.add(new_process)
        process_record = new_process
    else:
        # 更新
        process = db.query(Process).filter(Process.id == req.id).first()
        if not process:
            raise HTTPException(status_code=404, detail="流程方案记录不存在")

        process.title = req.title
        process.cover1 = req.cover1
        process.cover2 = req.cover2
        process.content = req.content
        process.sort = req.sort
        if req.is_active is not None:
            process.is_active = req.is_active
        process.update_time = datetime.now()
        process_record = process

    try:
        db.commit()
        db.refresh(process_record)
        return {
            "code": 200,
            "msg": "保存成功",
            "data": {"id": process_record.id}
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")



# 列表（分页 筛选 关键词）
@process_router.get("/list", summary="获取流程方案列表")
def get_process_list(
    keyword: Optional[str] = Query(None, description="模糊搜索标题关键词"),
    only_active: bool = Query(False, description="是否只获取启用的方案"),
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量，范围1-100"),
    db: Session = Depends(get_db)
):
    query = db.query(Process)

    # 筛选条件
    if keyword:
        query = query.filter(Process.title.like(f"%{keyword}%"))
    if only_active:
        query = query.filter(Process.is_active == True)

    # 总数
    total = query.count()

    # 分页 + 排序
    offset = (page - 1) * page_size
    processes = query.order_by(
        asc(Process.sort),
        desc(Process.id)
    ).offset(offset).limit(page_size).all()

    # 数据格式化
    data_list = []
    for item in processes:
        data_list.append({
            "id": item.id,
            "title": item.title,
            "cover1": item.cover1,
            "cover2": item.cover2,
            "sort": item.sort,
            "is_active": item.is_active,
            "create_time": item.create_time.strftime("%Y-%m-%d %H:%M:%S") if item.create_time else None,
            "update_time": item.update_time.strftime("%Y-%m-%d %H:%M:%S") if item.update_time else None,
        })

    # 返回格式
    return {
        "code": 200,
        "msg": "获取成功",
        "data": data_list,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size
    }


#  详情（编辑回显）
@process_router.get("/detail/{process_id}", summary="获取流程方案详情")
def get_process_detail(process_id: int, db: Session = Depends(get_db)):
    process = db.query(Process).filter(Process.id == process_id).first()
    if not process:
        raise HTTPException(status_code=404, detail="流程方案记录不存在")

    data = {
        "id": process.id,
        "title": process.title,
        "cover1": process.cover1,
        "cover2": process.cover2,
        "content": process.content,
        "sort": process.sort,
        "is_active": process.is_active,
        "create_time": process.create_time.strftime("%Y-%m-%d %H:%M:%S") if process.create_time else None,
        "update_time": process.update_time.strftime("%Y-%m-%d %H:%M:%S") if process.update_time else None,
    }

    return {
        "code": 200,
        "msg": "获取成功",
        "data": data
    }



# 删除
@process_router.delete("/delete/{process_id}", summary="删除流程方案")
def delete_process(process_id: int, db: Session = Depends(get_db)):
    process = db.query(Process).filter(Process.id == process_id).first()
    if not process:
        raise HTTPException(status_code=404, detail="流程方案记录不存在")

    db.delete(process)
    db.commit()
    return {"code": 200, "msg": "删除成功"}