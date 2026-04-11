from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models.solution_model import Solution
from models.industry_model import Industry
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy import asc, desc
solution_router = APIRouter(prefix="/solution", tags=["解决方案管理"])



class SolutionSaveRequest(BaseModel):
    id: Optional[int] = Field(None, description="方案ID (有则更新，无则新增)")
    fid: int = Field(..., description="所属行业ID")
    title: str = Field(..., min_length=1, max_length=200, description="方案标题")
    cover1: Optional[str] = Field(None, description="封面图1 URL")
    cover2: Optional[str] = Field(None, description="封面图2 URL")
    content: str = Field(..., description="富文本详情内容")
    sort: int = Field(0, description="排序权重")
    is_active: Optional[bool] = Field(True, description="是否启用")


# --- 统一保存接口  ---
@solution_router.post("/save", summary="保存解决方案 (新增或更新)")
def save_solution(req: SolutionSaveRequest, db: Session = Depends(get_db)):
    """
    智能保存：根据 ID 是否存在自动判断是新增还是更新
    """

    # === 校验关联的行业是否存在 ===
    industry = db.query(Industry).filter(Industry.id == req.fid).first()
    if not industry:
        raise HTTPException(status_code=400, detail=f"所属的行业 (ID={req.fid}) 不存在")

    solution_record = None

    if req.id is None:
        # === 执行新增 ===
        new_solution = Solution(
            fid=req.fid,
            title=req.title,
            cover1=req.cover1,
            cover2=req.cover2,
            content=req.content,
            sort=req.sort,
            is_active=req.is_active if req.is_active is not None else True,
            create_time=datetime.now(),
            update_time=datetime.now()
        )
        db.add(new_solution)
        solution_record = new_solution
    else:
        # === 执行更新 ===
        solution = db.query(Solution).filter(Solution.id == req.id).first()
        if not solution:
            raise HTTPException(status_code=404, detail="解决方案记录不存在")

        # 如果更新了行业ID，再次校验新行业是否存在
        if solution.fid != req.fid:
            new_industry = db.query(Industry).filter(Industry.id == req.fid).first()
            if not new_industry:
                raise HTTPException(status_code=400, detail="新的所属行业不存在")
            solution.fid = req.fid

        # 动态赋值其他字段
        solution.title = req.title
        solution.cover1 = req.cover1
        solution.cover2 = req.cover2
        solution.content = req.content
        solution.sort = req.sort
        if req.is_active is not None:
            solution.is_active = req.is_active
        solution.update_time = datetime.now()

        solution_record = solution

    try:
        db.commit()
        db.refresh(solution_record)

        #  手动构建返回字典，只返回必要信息 (id)
        return {
            "code": 200,
            "msg": "保存成功",
            "data": {"id": solution_record.id}
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


@solution_router.get("/list", summary="获取解决方案列表")
def get_solution_list(
        fid: Optional[int] = Query(None, description="按行业ID筛选"),
        keyword: Optional[str] = Query(None, description="模糊搜索标题关键词"),
        only_active: bool = Query(False, description="是否只获取启用的方案"),

        page: int = Query(1, ge=1, description="页码，从1开始"),
        page_size: int = Query(10, ge=1, le=100, description="每页数量，范围1-100"),
        db: Session = Depends(get_db)
):
    query = db.query(Solution)

    #  应用筛选条件
    if fid is not None:
        query = query.filter(Solution.fid == fid)

    if keyword:
        query = query.filter(Solution.title.like(f"%{keyword}%"))

    if only_active:
        query = query.filter(Solution.is_active == True)

    # ---  计算总数  ---
    total = query.count()

    # --- 应用分页和排序 ---
    offset = (page - 1) * page_size
    solutions = query.order_by(
        asc(Solution.sort),
        desc(Solution.id)
    ).offset(offset).limit(page_size).all()

    # 转换数据
    data_list = []
    for item in solutions:
        industry_name = item.industry.name if item.industry else "未知行业"
        data_list.append({
            "id": item.id,
            "fid": item.fid,
            "industry_name": industry_name,
            "title": item.title,
            "cover1": item.cover1,
            "cover2": item.cover2,
            "sort": item.sort,
            "is_active": item.is_active,
            "create_time": item.create_time.strftime("%Y-%m-%d %H:%M:%S") if item.create_time else None,
            "update_time": item.update_time.strftime("%Y-%m-%d %H:%M:%S") if item.update_time else None,
        })


    return {
        "code": 200,
        "msg": "获取成功",
        "data": data_list,  # 直接返回数据列表
        "total": total,  # 数据总条数 (与 data 平级)
        "page": page,  # 当前页码
        "page_size": page_size,  # 每页数量
        "pages": (total + page_size - 1) // page_size  # 总页数
    }

# --- 4. 获取详情 (用于编辑回显) ---
@solution_router.get("/detail/{solution_id}", summary="获取解决方案详情")
def get_solution_detail(solution_id: int, db: Session = Depends(get_db)):
    solution = db.query(Solution).filter(Solution.id == solution_id).first()
    if not solution:
        raise HTTPException(status_code=404, detail="解决方案记录不存在")

    industry_name = solution.industry.name if solution.industry else "未知行业"

    # 返回完整数据，包括富文本 content
    data = {
        "id": solution.id,
        "fid": solution.fid,
        "industry_name": industry_name,
        "title": solution.title,
        "cover1": solution.cover1,
        "cover2": solution.cover2,
        "content": solution.content,
        "sort": solution.sort,
        "is_active": solution.is_active,
        "create_time": solution.create_time.strftime("%Y-%m-%d %H:%M:%S") if solution.create_time else None,
        "update_time": solution.update_time.strftime("%Y-%m-%d %H:%M:%S") if solution.update_time else None,
    }

    return {
        "code": 200,
        "msg": "获取成功",
        "data": data
    }


# --- 5. 删除 ---
@solution_router.delete("/delete/{solution_id}", summary="删除解决方案")
def delete_solution(solution_id: int, db: Session = Depends(get_db)):
    solution = db.query(Solution).filter(Solution.id == solution_id).first()
    if not solution:
        raise HTTPException(status_code=404, detail="解决方案记录不存在")

    #  由于模型中定义了 cascade="all, delete-orphan" 和 ondelete="CASCADE"
    # delete数据库处理关联逻辑
    db.delete(solution)
    db.commit()

    return {"code": 200, "msg": "删除成功"}