from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from database import get_db
from models.industry_model import Industry
from datetime import datetime
from pydantic import BaseModel, Field

industry_router = APIRouter(prefix="/industries", tags=["行业管理"])


# --- 1. 统一定义接收数据的模型 (仅用于校验输入) ---
class IndustrySaveRequest(BaseModel):
    id: Optional[int] = Field(None, description="行业ID (有则更新，无则新增)")
    name: str = Field(..., description="行业名称")
    sort: int = Field(0, description="排序权重")
    icon1: Optional[str] = Field(None, description="默认图标URL")
    icon2: Optional[str] = Field(None, description="选中图标URL")
    is_active: Optional[bool] = Field(True, description="是否启用")


# --- 2. 统一保存接口 (新增/更新 二合一) ---
# 注意：这里不写 response_model，直接返回 dict
@industry_router.post("/save", summary="保存行业 (新增或更新)")
def save_industry(req: IndustrySaveRequest, db: Session = Depends(get_db)):
    """
    智能保存：根据 ID 是否存在自动判断是新增还是更新
    """

    # === 校验名称唯一性 ===
    query = db.query(Industry).filter(Industry.name == req.name)
    if req.id is not None:
        query = query.filter(Industry.id != req.id)  # 更新时排除自己

    if query.first():
        raise HTTPException(status_code=400, detail=f"行业名称 '{req.name}' 已存在")

    industry_record = None

    if req.id is None:
        # === 执行新增 ===
        new_industry = Industry(
            name=req.name,
            sort=req.sort,
            icon1=req.icon1,
            icon2=req.icon2,
            is_active=req.is_active if req.is_active is not None else True,
            create_time=datetime.now(),
            update_time=datetime.now()
        )
        db.add(new_industry)
        industry_record = new_industry
    else:
        # === 执行更新 ===
        industry = db.query(Industry).filter(Industry.id == req.id).first()
        if not industry:
            raise HTTPException(status_code=404, detail="行业记录不存在")

        # 动态赋值
        industry.name = req.name
        industry.sort = req.sort
        industry.icon1 = req.icon1
        industry.icon2 = req.icon2
        if req.is_active is not None:
            industry.is_active = req.is_active
        industry.update_time = datetime.now()

        industry_record = industry

    try:
        db.commit()
        db.refresh(industry_record)

        # 【关键】手动构建返回字典，只返回必要信息 (id)，避免直接返回 ORM 对象导致序列化问题
        return {
            "code": 200,
            "msg": "保存成功",
            "data": {"id": industry_record.id}
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


# --- 3. 获取列表 ---
# 注意：这里也不写 response_model
# --- 3. 获取列表 ---
@industry_router.get("/list", summary="获取行业列表")
def get_industry_list(
        only_active: bool = Query(True, description="是否只获取启用的行业"),
        db: Session = Depends(get_db)
):
    query = db.query(Industry)
    if only_active:
        query = query.filter(Industry.is_active == True)

    # 【修改点】调整排序逻辑
    # 1. asc(Industry.sort): 排序值越小，越靠前 (0, 1, 2...)
    # 2. asc(Industry.id): 如果排序值相同，ID 越小（越早创建的）越靠前。
    #    这样新增的数据（ID 大）自然会排在同 sort 值的后面。
    industries = query.order_by(
        asc(Industry.sort),
        asc(Industry.id)  # 这里从 desc 改为 asc
    ).all()

    # 手动转换为字典列表
    data_list = [
        {
            "id": item.id,
            "name": item.name,
            "icon1": item.icon1,
            "icon2": item.icon2,
            "sort": item.sort,
            "is_active": item.is_active,
            "create_time": item.create_time.strftime("%Y-%m-%d %H:%M:%S") if item.create_time else None,
            "update_time": item.update_time.strftime("%Y-%m-%d %H:%M:%S") if item.update_time else None,
        }
        for item in industries
    ]

    return {
        "code": 200,
        "msg": "获取成功",
        "data": data_list
    }


# --- 4. 删除 ---
@industry_router.delete("/delete/{industry_id}", summary="删除行业")
def delete_industry(industry_id: int, db: Session = Depends(get_db)):
    industry = db.query(Industry).filter(Industry.id == industry_id).first()
    if not industry:
        raise HTTPException(status_code=404, detail="行业记录不存在")

    db.delete(industry)
    db.commit()

    return {"code": 200, "msg": "删除成功"}