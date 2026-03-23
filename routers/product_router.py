from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from database import get_db
from models.product_model import RobotProduct, SportProduct
from models.category_model import Category
from datetime import datetime
from pydantic import BaseModel, Field

# 如果是 Pydantic V2，需要 ConfigDict；如果是 V1，使用 class Config
try:
    from pydantic import ConfigDict

    PYDANTIC_V2 = True
except ImportError:
    PYDANTIC_V2 = False

product_router = APIRouter(prefix="/product", tags=["产品管理"])


# =============================================================================
# 1. 请求模型 (用于接收前端提交的数据)
# =============================================================================

class RobotSaveRequest(BaseModel):
    id: Optional[int] = Field(None, description="ID (有则更新，无则新增)")
    product_name: str = Field(..., min_length=1)
    model_number: str = Field(..., min_length=1)
    main_image_url: Optional[str] = None
    category_id: int = Field(..., gt=0)
    is_active: bool = True
    # 机器人特有
    robot_name: str = Field(..., min_length=1)
    max_arm_span: Optional[str] = None
    max_weight: Optional[str] = None
    switch_num: Optional[str] = None
    weight: Optional[str] = None
    perprecision: Optional[str] = None
    ip_level: Optional[str] = None
    ins_type: Optional[str] = None
    drive_type: Optional[str] = None
    auth_support: Optional[str] = None
    ins_require: Optional[str] = None
    remark: Optional[str] = None
    detail_img: Optional[str] = None

    if PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class SportSaveRequest(BaseModel):
    id: Optional[int] = Field(None, description="ID (有则更新，无则新增)")
    product_name: str = Field(..., min_length=1)
    model_number: str = Field(..., min_length=1)
    main_image_url: Optional[str] = None
    category_id: int = Field(..., gt=0)
    is_active: bool = True
    # 控制器特有
    name: str = Field(..., min_length=1)
    detail: Optional[str] = None
    img: Optional[str] = None
    line1: Optional[str] = None
    line2: Optional[str] = None
    line3: Optional[str] = None
    sport_pram: Optional[dict] = None
    sport_pram_two: Optional[dict] = None

    if PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


# =============================================================================
# 2. 响应模型 (直接映射数据库模型，实现“查什么返什么”)
# =============================================================================

# 我们直接复用 SQLAlchemy 模型作为响应结构，或者定义一个包含所有字段的简单模型
# 这里为了清晰，定义两个直接对应数据库字段的响应模型

class RobotDetailResponse(BaseModel):
    """直接映射 RobotProduct 表的所有字段"""
    id: int
    product_name: str
    model_number: str
    main_image_url: Optional[str]
    category_id: int
    category_path: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    # 特有字段
    robot_name: str
    max_arm_span: Optional[str]
    max_weight: Optional[str]
    switch_num: Optional[str]
    weight: Optional[str]
    perprecision: Optional[str]
    ip_level: Optional[str]
    ins_type: Optional[str]
    drive_type: Optional[str]
    auth_support: Optional[str]
    ins_require: Optional[str]
    remark: Optional[str]
    detail_img: Optional[str]

    # 额外标记类型，方便前端判断
    product_type: str = "ROBOT"

    if PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class SportDetailResponse(BaseModel):
    """直接映射 SportProduct 表的所有字段"""
    id: int
    product_name: str
    model_number: str
    main_image_url: Optional[str]
    category_id: int
    category_path: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    # 特有字段
    name: str
    detail: Optional[str]
    img: Optional[str]
    line1: Optional[str]
    line2: Optional[str]
    line3: Optional[str]
    sport_pram: Optional[dict]
    sport_pram_two: Optional[dict]

    # 额外标记类型
    product_type: str = "SPORT_CONTROLLER"

    if PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


# =============================================================================
# 3. 辅助函数
# =============================================================================

def get_category_path(db: Session, category_id: int) -> str:
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        return "未知分类"
    path_parts = [cat.name]
    current = cat
    while current.parent_id:
        parent = db.query(Category).filter(Category.id == current.parent_id).first()
        if parent:
            path_parts.insert(0, parent.name)
            current = parent
        else:
            break
    return " / ".join(path_parts)


# =============================================================================
# 4. 接口定义
# =============================================================================

# --- 🆕 获取详情 (核心：直接查库，直接返回，不做复杂转换) ---
@product_router.get("/detail/{product_id}", summary="获取产品详情 (直接回显)")
def get_product_detail(product_id: int, db: Session = Depends(get_db)):
    # 1. 先查机器人表
    item = db.query(RobotProduct).filter(RobotProduct.id == product_id).first()
    if item:
        response_data = RobotDetailResponse.from_orm(item) if not PYDANTIC_V2 else RobotDetailResponse.model_validate(item)

        return {"code": 200, "msg": "success", "data": response_data}

    # 2. 再查控制器表
    item = db.query(SportProduct).filter(SportProduct.id == product_id).first()
    if item:
        response_data = SportDetailResponse.from_orm(item) if not PYDANTIC_V2 else SportDetailResponse.model_validate(item)

        return {"code": 200, "msg": "success", "data": response_data}

    raise HTTPException(status_code=404, detail="产品不存在")


# --- 🤖 机器人保存 ---
@product_router.post("/robot/save", summary="保存机器人 (新增/更新)")
def save_robot(request: RobotSaveRequest, db: Session = Depends(get_db)):
    category_path = get_category_path(db, request.category_id)

    if request.id is None:
        # 新增
        new_item = RobotProduct(
            product_name=request.product_name,
            model_number=request.model_number,
            main_image_url=request.main_image_url,
            category_id=request.category_id,
            category_path=category_path,
            is_active=request.is_active,
            robot_name=request.robot_name,
            max_arm_span=request.max_arm_span,
            max_weight=request.max_weight,
            switch_num=request.switch_num,
            weight=request.weight,
            perprecision=request.perprecision,
            ip_level=request.ip_level,
            ins_type=request.ins_type,
            drive_type=request.drive_type,
            auth_support=request.auth_support,
            ins_require=request.ins_require,
            remark=request.remark,
            detail_img=request.detail_img,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return {"code": 200, "msg": "创建成功", "data": {"id": new_item.id}}
    else:
        # 更新
        item = db.query(RobotProduct).filter(RobotProduct.id == request.id).first()
        if not item:
            raise HTTPException(status_code=404, detail="产品不存在")

        # 逐个字段更新 (前端传什么就更新什么)
        item.product_name = request.product_name
        item.model_number = request.model_number
        if request.main_image_url is not None: item.main_image_url = request.main_image_url
        if request.category_id != item.category_id:
            item.category_id = request.category_id
            item.category_path = category_path
        item.is_active = request.is_active

        item.robot_name = request.robot_name
        if request.max_arm_span is not None: item.max_arm_span = request.max_arm_span
        if request.max_weight is not None: item.max_weight = request.max_weight
        if request.switch_num is not None: item.switch_num = request.switch_num
        if request.weight is not None: item.weight = request.weight
        if request.perprecision is not None: item.perprecision = request.perprecision
        if request.ip_level is not None: item.ip_level = request.ip_level
        if request.ins_type is not None: item.ins_type = request.ins_type
        if request.drive_type is not None: item.drive_type = request.drive_type
        if request.auth_support is not None: item.auth_support = request.auth_support
        if request.ins_require is not None: item.ins_require = request.ins_require
        if request.remark is not None: item.remark = request.remark
        if request.detail_img is not None: item.detail_img = request.detail_img

        item.updated_at = datetime.now()
        db.commit()
        db.refresh(item)
        return {"code": 200, "msg": "更新成功", "data": {"id": item.id}}


# --- 🎮 控制器保存 ---
@product_router.post("/sport/save", summary="保存控制器 (新增/更新)")
def save_sport(request: SportSaveRequest, db: Session = Depends(get_db)):
    category_path = get_category_path(db, request.category_id)

    if request.id is None:
        # 新增
        new_item = SportProduct(
            product_name=request.product_name,
            model_number=request.model_number,
            main_image_url=request.main_image_url,
            category_id=request.category_id,
            category_path=category_path,
            is_active=request.is_active,
            name=request.name,
            detail=request.detail,
            img=request.img,
            line1=request.line1,
            line2=request.line2,
            line3=request.line3,
            sport_pram=request.sport_pram,
            sport_pram_two=request.sport_pram_two,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return {"code": 200, "msg": "创建成功", "data": {"id": new_item.id}}
    else:
        # 更新
        item = db.query(SportProduct).filter(SportProduct.id == request.id).first()
        if not item:
            raise HTTPException(status_code=404, detail="产品不存在")

        item.product_name = request.product_name
        item.model_number = request.model_number
        if request.main_image_url is not None: item.main_image_url = request.main_image_url
        if request.category_id != item.category_id:
            item.category_id = request.category_id
            item.category_path = category_path
        item.is_active = request.is_active

        item.name = request.name
        if request.detail is not None: item.detail = request.detail
        if request.img is not None: item.img = request.img
        if request.line1 is not None: item.line1 = request.line1
        if request.line2 is not None: item.line2 = request.line2
        if request.line3 is not None: item.line3 = request.line3
        if request.sport_pram is not None: item.sport_pram = request.sport_pram
        if request.sport_pram_two is not None: item.sport_pram_two = request.sport_pram_two

        item.updated_at = datetime.now()
        db.commit()
        db.refresh(item)
        return {"code": 200, "msg": "更新成功", "data": {"id": item.id}}


# --- 📋 列表接口 ---
@product_router.get("/list", summary="获取产品列表")
def get_product_list(
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=100),
        keyword: Optional[str] = Query(None),
        category_id: Optional[int] = Query(None),
        product_type: Optional[str] = Query(None),
        db: Session = Depends(get_db)
):
    models_to_query = []
    if product_type == "ROBOT":
        models_to_query.append(RobotProduct)
    elif product_type == "SPORT_CONTROLLER":
        models_to_query.append(SportProduct)
    else:
        models_to_query = [RobotProduct, SportProduct]

    all_results = []
    total = 0

    for model in models_to_query:
        q = db.query(model)
        if keyword:
            q = q.filter(or_(model.product_name.contains(keyword), model.model_number.contains(keyword)))
        if category_id:
            q = q.filter(model.category_id == category_id)

        total += q.count()

        if len(models_to_query) > 1:
            items = q.order_by(desc(model.created_at)).all()
        else:
            items = q.order_by(desc(model.created_at)).offset((page - 1) * page_size).limit(page_size).all()

        p_type = "ROBOT" if model == RobotProduct else "SPORT_CONTROLLER"
        all_results.extend([(item, p_type) for item in items])

    if len(models_to_query) > 1:
        all_results.sort(key=lambda x: x[0].created_at, reverse=True)
        start = (page - 1) * page_size
        all_results = all_results[start:start + page_size]

    data_list = []
    for item, p_type in all_results:
        data_list.append({
            "id": item.id,
            "productName": item.product_name,
            "modelNumber": item.model_number,
            "mainImageUrl": item.main_image_url,
            "categoryId": item.category_id,
            "categoryPath": item.category_path,
            "productType": p_type,
            "isActive": item.is_active,
            "createTime": item.created_at.strftime("%Y-%m-%d %H:%M:%S") if item.created_at else None
        })

    return {"code": 200, "msg": "success", "total": total, "data": data_list}


# --- 🗑️ 删除接口 ---
@product_router.delete("/{product_id}", summary="删除产品")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    item = db.query(RobotProduct).filter(RobotProduct.id == product_id).first()
    if item:
        db.delete(item)
        db.commit()
        return {"code": 200, "msg": "删除成功"}

    item = db.query(SportProduct).filter(SportProduct.id == product_id).first()
    if item:
        db.delete(item)
        db.commit()
        return {"code": 200, "msg": "删除成功"}

    raise HTTPException(status_code=404, detail="产品不存在")