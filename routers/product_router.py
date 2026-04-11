from typing import Optional, List, Dict, Type
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy.orm import DeclarativeMeta

from database import get_db
from models.product_model import RobotProduct, SportProduct
from models.category_model import Category

# 初始化路由
product_router = APIRouter(prefix="/product", tags=["产品管理"])


class RobotSaveRequest(BaseModel):
    id: Optional[int] = None
    product_name: str
    model_number: str
    main_image_url: Optional[str] = None
    robot_type: str = ""
    category_id: int
    if_main: Optional[bool] = None
    is_active: bool = True
    robot_name: str = ""
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

    model_config = {"from_attributes": True}

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


# 响应模型
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


# 工具函数
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



# 产品详情
@product_router.get("/detail/{product_type}/{product_id}")
def get_product_detail(product_type: str, product_id: int, db: Session = Depends(get_db)):
    product_info = PRODUCT_TYPE_MAPPING.get(product_type.lower())
    if not product_info:
        raise HTTPException(404, "类型不存在")
    item = db.query(product_info["model"]).get(product_id)
    if not item:
        raise HTTPException(404, "产品不存在")


    return {"code":200,"data":product_info["response_schema"].model_validate(item)}

# 首页产品（if_main = True）
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

    # 按时间倒序
    all_items.sort(key=lambda x: x.created_at, reverse=True)

    # 分页
    start = (page - 1) * page_size
    end = start + page_size
    items = all_items[start:end]

    # ======================  list 接口返回 ======================
    data = []
    for item in items:
        data.append({
            "id": item.id,
            "productName": item.product_name,
            "modelNumber": item.model_number,
            "mainImageUrl": item.main_image_url,
            "categoryId": item.category_id,
            "categoryPath": item.category_path,
            "robotType": item.robot_type,  # ✅ 已加
            "productType": "robot" if isinstance(item, RobotProduct) else "sport",  # ✅ 已加
            "isActive": item.is_active,
            "ifMain": item.if_main,
            "createTime": item.created_at.strftime("%Y-%m-%d %H:%M:%S")  # ✅ 时间格式化
        })

    return {
        "code": 200,
        "total": total,
        "data": data
    }
# 保存机器人
@product_router.post("/robot/save")
def save_robot(request: RobotSaveRequest, db: Session = Depends(get_db)):
    path = get_category_path(db, request.category_id)
    if not request.id:
        item = RobotProduct(
            product_name=request.product_name,
            model_number=request.model_number,
            robot_type=request.robot_type,
            main_image_url=request.main_image_url,
            category_id=request.category_id,
            category_path=path,
            is_active=request.is_active,
            if_main=request.if_main,
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
        db.add(item)
    else:
        item = db.query(RobotProduct).get(request.id)
        if not item: raise HTTPException(404)
        item.product_name = request.product_name
        item.model_number = request.model_number
        item.robot_type = request.robot_type
        item.main_image_url = request.main_image_url
        item.category_id = request.category_id
        item.category_path = path
        item.is_active = request.is_active
        item.if_main = request.if_main
        item.robot_name = request.robot_name
        item.max_arm_span = request.max_arm_span
        item.max_weight = request.max_weight
        item.switch_num = request.switch_num
        item.weight = request.weight
        item.perprecision = request.perprecision
        item.ip_level = request.ip_level
        item.ins_type = request.ins_type
        item.drive_type = request.drive_type
        item.auth_support = request.auth_support
        item.ins_require = request.ins_require
        item.remark = request.remark
        item.detail_img = request.detail_img
        item.updated_at = datetime.now()

    db.commit()
    db.refresh(item)
    return {"code":200,"data":{"id":item.id}}

# 保存控制器
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
    return {"code":200,"data":{"id":item.id}}

# 产品列表
@product_router.get("/list")
def get_product_list(
    page:int=1, page_size:int=10, keyword:Optional[str]=None, model_number:Optional[str]=None,
    category_id:Optional[int]=None, product_type:Optional[str]=None, db:Session=Depends(get_db)
):
    models = []
    if product_type == "robot": models.append(RobotProduct)
    elif product_type == "sport": models.append(SportProduct)
    else: models = [RobotProduct, SportProduct]

    all_items = []
    total = 0
    for m in models:
        q = db.query(m)
        cond = []
        if keyword: cond.append(m.product_name.contains(keyword))
        if model_number: cond.append(m.model_number.contains(model_number))
        if cond: q = q.filter(or_(*cond))
        if category_id: q = q.filter(m.category_id == category_id)
        total += q.count()
        all_items.extend(q.order_by(desc(m.created_at)).all())

    all_items.sort(key=lambda x:x.created_at, reverse=True)
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
    return {"code":200,"total":total,"data":data}

# 删除
@product_router.delete("/{product_id}")
def delete_product(product_id:int, db:Session=Depends(get_db)):
    item = db.query(RobotProduct).get(product_id) or db.query(SportProduct).get(product_id)
    if not item: raise HTTPException(404)
    db.delete(item)
    db.commit()
    return {"code":200,"msg":"删除成功"}