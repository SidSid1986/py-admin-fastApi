from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from datetime import datetime
from pydantic import BaseModel
from database import get_db
from models.product_model import RobotProduct, SportProduct
from models.category_model import Category

# 初始化路由
product_router = APIRouter(prefix="/product", tags=["产品管理"])


# =============================================================================
# ✅ 机器人：保存请求体（已重构）
# =============================================================================
class RobotSaveRequest(BaseModel):
    id: Optional[int] = None
    product_name: str
    model_number: str
    main_image_url: Optional[str] = None
    robot_type: str = ""
    category_id: int
    if_main: Optional[bool] = None
    is_active: bool = True

    # 必须保留的4个核心机械参数
    max_arm_span: Optional[str] = None
    max_weight: Optional[str] = None
    switch_num: Optional[str] = None
    weight: Optional[str] = None

    # ✅ 新增：自定义多表格数据（JSON数组）
    custom_tables: Optional[List[Dict]] = None

    model_config = {"from_attributes": True}


# =============================================================================
# 控制器（暂时不动，后面再改）
# =============================================================================
class SportSaveRequest(BaseModel):
    id: Optional[int] = None
    product_name: str
    model_number: str
    main_image_url: Optional[str] = None
    category_id: int
    if_main: Optional[bool] = None
    is_active: bool = True
    robot_type: str = ""
    name: Optional[str] = None
    detail: Optional[str] = None
    img: Optional[str] = None
    line1: Optional[str] = None
    line2: Optional[str] = None
    line3: Optional[str] = None
    sport_pram: Optional[dict] = None
    sport_pram_two: Optional[dict] = None

    model_config = {"from_attributes": True}


# =============================================================================
# ✅ 机器人：详情响应体（已重构）
# =============================================================================
class RobotDetailResponse(BaseModel):
    id: int
    product_name: str
    model_number: str
    robot_type: str
    main_image_url: Optional[str]
    category_id: int
    category_path: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    if_main: Optional[bool]

    # 核心机械参数
    max_arm_span: Optional[str]
    max_weight: Optional[str]
    switch_num: Optional[str]
    weight: Optional[str]

    # ✅ 自定义表格
    custom_tables: Optional[List[Dict]]

    product_type: str = "robot"
    model_config = {"from_attributes": True}


class SportDetailResponse(BaseModel):
    id: int
    product_name: str
    model_number: str
    main_image_url: Optional[str]
    category_id: int
    category_path: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    if_main: Optional[bool]
    name: Optional[str] = None
    detail: Optional[str]
    img: Optional[str]
    line1: Optional[str]
    line2: Optional[str]
    line3: Optional[str]
    sport_pram: Optional[dict]
    sport_pram_two: Optional[dict]
    product_type: str = "sport"
    model_config = {"from_attributes": True}


class MainProductResponse(BaseModel):
    id: int
    product_name: str
    model_number: str
    main_image_url: Optional[str]
    category_id: int
    category_path: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    if_main: Optional[bool]
    product_type: str
    model_config = {"from_attributes": True}


# 产品类型映射
PRODUCT_TYPE_MAPPING: Dict[str, Dict] = {
    "robot": {"model": RobotProduct, "response_schema": RobotDetailResponse},
    "sport": {"model": SportProduct, "response_schema": SportDetailResponse},
}


# 工具函数：获取分类完整路径
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
# 产品详情
# =============================================================================
@product_router.get("/detail/{product_type}/{product_id}")
def get_product_detail(product_type: str, product_id: int, db: Session = Depends(get_db)):
    product_info = PRODUCT_TYPE_MAPPING.get(product_type.lower())
    if not product_info:
        raise HTTPException(404, "类型不存在")
    item = db.query(product_info["model"]).get(product_id)
    if not item:
        raise HTTPException(404, "产品不存在")

    return {"code": 200, "data": product_info["response_schema"].model_validate(item)}


# =============================================================================
# 首页产品（if_main = True）
# =============================================================================
@product_router.get("/main/products")
def get_main_products(
        page: int = 1,
        page_size: int = 6,
        product_type: Optional[str] = None,
        db: Session = Depends(get_db)
):
    models = []
    if product_type == "robot":
        models.append(RobotProduct)
    elif product_type == "sport":
        models.append(SportProduct)
    else:
        models = [RobotProduct, SportProduct]

    all_items = []
    total = 0
    for m in models:
        q = db.query(m).filter(m.if_main == True)
        total += q.count()
        all_items.extend(q.order_by(desc(m.created_at)).all())

    all_items.sort(key=lambda x: x.created_at, reverse=True)
    start = (page - 1) * page_size
    end = start + page_size
    items = all_items[start:end]

    data = []
    for item in items:
        data.append({
            "id": item.id,
            "productName": item.product_name,
            "modelNumber": item.model_number,
            "mainImageUrl": item.main_image_url,
            "categoryId": item.category_id,
            "categoryPath": item.category_path,
            "robotType": item.robot_type,
            "productType": "robot" if isinstance(item, RobotProduct) else "sport",
            "isActive": item.is_active,
            "ifMain": item.if_main,
            "createTime": item.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return {"code": 200, "total": total, "data": data}


# =============================================================================
# ✅ 保存机器人（已完全重构）
# =============================================================================
@product_router.post("/robot/save")
def save_robot(request: RobotSaveRequest, db: Session = Depends(get_db)):
    category_path = get_category_path(db, request.category_id)

    if not request.id:
        # 新增
        item = RobotProduct(
            product_name=request.product_name,
            model_number=request.model_number,
            robot_type=request.robot_type,
            main_image_url=request.main_image_url,
            category_id=request.category_id,
            category_path=category_path,
            is_active=request.is_active,
            if_main=request.if_main,

            # 核心参数
            max_arm_span=request.max_arm_span,
            max_weight=request.max_weight,
            switch_num=request.switch_num,
            weight=request.weight,

            # ✅ 自定义表格
            custom_tables=request.custom_tables,

            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(item)
    else:
        # 更新
        item = db.query(RobotProduct).get(request.id)
        if not item:
            raise HTTPException(404, "产品不存在")

        item.product_name = request.product_name
        item.model_number = request.model_number
        item.robot_type = request.robot_type
        item.main_image_url = request.main_image_url
        item.category_id = request.category_id
        item.category_path = category_path
        item.is_active = request.is_active
        item.if_main = request.if_main

        # 核心参数
        item.max_arm_span = request.max_arm_span
        item.max_weight = request.max_weight
        item.switch_num = request.switch_num
        item.weight = request.weight

        # ✅ 自定义表格
        item.custom_tables = request.custom_tables

        item.updated_at = datetime.now()

    db.commit()
    db.refresh(item)
    return {"code": 200, "data": {"id": item.id}}


# =============================================================================
# 保存控制器（不动，后面再改）
# =============================================================================
@product_router.post("/sport/save")
def save_sport(request: SportSaveRequest, db: Session = Depends(get_db)):
    path = get_category_path(db, request.category_id)
    if not request.id:
        item = SportProduct(
            product_name=request.product_name,
            model_number=request.model_number,
            robot_type=request.robot_type,
            main_image_url=request.main_image_url,
            category_id=request.category_id,
            category_path=path,
            is_active=request.is_active,
            if_main=request.if_main,
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
        db.add(item)
    else:
        item = db.query(SportProduct).get(request.id)
        if not item: raise HTTPException(404)
        item.product_name = request.product_name
        item.model_number = request.model_number
        item.robot_type = request.robot_type
        item.main_image_url = request.main_image_url
        item.category_id = request.category_id
        item.category_path = path
        item.is_active = request.is_active
        item.if_main = request.if_main
        item.name = request.name
        item.detail = request.detail
        item.img = request.img
        item.line1 = request.line1
        item.line2 = request.line2
        item.line3 = request.line3
        item.sport_pram = request.sport_pram
        item.sport_pram_two = request.sport_pram_two
        item.updated_at = datetime.now()

    db.commit()
    db.refresh(item)
    return {"code": 200, "data": {"id": item.id}}


# =============================================================================
# 产品列表
# =============================================================================
@product_router.get("/list")
def get_product_list(
    page: int = 1, page_size: int = 10, keyword: Optional[str] = None, model_number: Optional[str] = None,
    category_id: Optional[int] = None, product_type: Optional[str] = None, db: Session = Depends(get_db)
):
    models = []
    if product_type == "robot":
        models.append(RobotProduct)
    elif product_type == "sport":
        models.append(SportProduct)
    else:
        models = [RobotProduct, SportProduct]

    all_items = []
    total = 0
    for m in models:
        q = db.query(m)
        cond = []
        if keyword:
            cond.append(m.product_name.contains(keyword))
        if model_number:
            cond.append(m.model_number.contains(model_number))
        if cond:
            q = q.filter(or_(*cond))
        if category_id:
            q = q.filter(m.category_id == category_id)
        total += q.count()
        all_items.extend(q.order_by(desc(m.created_at)).all())

    all_items.sort(key=lambda x: x.created_at, reverse=True)
    items = all_items[(page-1)*page_size : page*page_size]

    data = []
    for item in items:
        data.append({
            "id": item.id,
            "productName": item.product_name,
            "modelNumber": item.model_number,
            "mainImageUrl": item.main_image_url,
            "categoryId": item.category_id,
            "categoryPath": item.category_path,
            "robotType": item.robot_type,
            "productType": "robot" if isinstance(item, RobotProduct) else "sport",
            "isActive": item.is_active,
            "ifMain": item.if_main,
            "createTime": item.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    return {"code": 200, "total": total, "data": data}


# =============================================================================
# 删除产品
# =============================================================================
@product_router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    item = db.query(RobotProduct).get(product_id) or db.query(SportProduct).get(product_id)
    if not item:
        raise HTTPException(404, "产品不存在")
    db.delete(item)
    db.commit()
    return {"code": 200, "msg": "删除成功"}