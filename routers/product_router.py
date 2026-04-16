import uuid
import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from datetime import datetime
from database import get_db
from models import RobotProduct, SportProduct  # 使用你的模型
from models.category_model import Category  # 分类模型

product_router = APIRouter(prefix="/product", tags=["产品管理"])


# =============================================================================
# ✅ 统一上传接口
# =============================================================================
@product_router.post("/upload", summary="统一图片上传接口")
async def upload_image(
        file: UploadFile = File(...),
        folder: str = Query("common", description="上传目录名")
):
    """统一上传接口，返回图片URL"""
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "只能上传图片文件")

    upload_dir = f"static/uploads/{folder}"
    os.makedirs(upload_dir, exist_ok=True)

    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else "jpg"
    filename = f"{uuid.uuid4()}.{ext}"
    save_path = os.path.join(upload_dir, filename)

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    url = f"/static/uploads/{folder}/{filename}"
    return {"code": 200, "data": {"url": url}}


# =============================================================================
# ✅ 请求体定义
# =============================================================================
class RobotSaveRequest(BaseModel):
    id: Optional[int] = None
    product_name: str
    model_number: str
    robot_type: str
    category_id: int
    if_main: Optional[int] = 0
    is_active: Optional[bool] = True
    main_image_url: Optional[str] = None
    max_arm_span: Optional[str] = None
    max_weight: Optional[str] = None
    switch_num: Optional[str] = None
    weight: Optional[str] = None
    custom_tables: Optional[List[Dict]] = None


class SportSaveRequest(BaseModel):
    id: Optional[int] = None
    product_name: str
    model_number: str
    robot_type: str
    category_id: int
    if_main: Optional[int] = 0
    is_active: Optional[bool] = True
    main_image_url: Optional[str] = None
    name: Optional[str] = None
    detail: Optional[str] = None
    img: Optional[str] = None
    line1: Optional[str] = None
    line2: Optional[str] = None
    line3: Optional[str] = None
    sport_pram: Optional[dict] = None
    sport_pram_two: Optional[dict] = None


# =============================================================================
# ✅ 产品列表
# =============================================================================
@product_router.get("/list")
def get_product_list(
        page: int = 1,
        page_size: int = 10,
        keyword: Optional[str] = None,
        category_id: Optional[int] = None,
        product_type: Optional[str] = None,
        db: Session = Depends(get_db)
):
    """获取产品列表"""
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
        if keyword:
            q = q.filter(or_(m.product_name.contains(keyword), m.model_number.contains(keyword)))
        if category_id:
            q = q.filter(m.category_id == category_id)
        total += q.count()
        all_items += q.order_by(desc(m.created_at)).all()

    all_items.sort(key=lambda x: x.created_at, reverse=True)
    items = all_items[(page - 1) * page_size: page * page_size]

    data = []
    for item in items:
        data.append({
            "id": item.id,
            "productName": item.product_name,
            "modelNumber": item.model_number,
            "mainImageUrl": item.main_image_url or "",
            "categoryId": item.category_id,
            "categoryPath": get_category_path(db, item.category_id),
            "robotType": item.robot_type,
            "productType": "robot" if isinstance(item, RobotProduct) else "sport",
            "isActive": item.is_active,
            "ifMain": item.if_main,
            "createTime": item.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return {"code": 200, "total": total, "data": data}


# =============================================================================
# ✅ 机器人产品操作
# =============================================================================
@product_router.post("/robot/save")
def save_robot(request: RobotSaveRequest, db: Session = Depends(get_db)):
    """保存机器人产品"""
    if not request.id:
        # 新增产品
        item = RobotProduct(
            product_name=request.product_name,
            model_number=request.model_number,
            robot_type=request.robot_type,
            category_id=request.category_id,
            is_active=request.is_active,
            if_main=request.if_main == 1,
            main_image_url=request.main_image_url,
            max_arm_span=request.max_arm_span,
            max_weight=request.max_weight,
            switch_num=request.switch_num,
            weight=request.weight,
            custom_tables=request.custom_tables
        )
        db.add(item)
    else:
        # 更新产品
        item = db.query(RobotProduct).filter(RobotProduct.id == request.id).first()
        if not item:
            raise HTTPException(404, "产品不存在")

        item.product_name = request.product_name
        item.model_number = request.model_number
        item.robot_type = request.robot_type
        item.category_id = request.category_id
        item.is_active = request.is_active
        item.if_main = request.if_main == 1
        item.main_image_url = request.main_image_url
        item.max_arm_span = request.max_arm_span
        item.max_weight = request.max_weight
        item.switch_num = request.switch_num
        item.weight = request.weight
        item.custom_tables = request.custom_tables

    db.commit()
    return {"code": 200, "data": {"id": item.id}}


@product_router.get("/robot/{robot_id}")
def get_robot_detail(robot_id: int, db: Session = Depends(get_db)):
    """获取机器人详情"""
    item = db.query(RobotProduct).filter(RobotProduct.id == robot_id).first()
    if not item:
        raise HTTPException(404, "产品不存在")

    return {
        "code": 200,
        "data": {
            "id": item.id,
            "product_name": item.product_name,
            "model_number": item.model_number,
            "main_image_url": item.main_image_url,
            "max_arm_span": item.max_arm_span,
            "max_weight": item.max_weight,
            "switch_num": item.switch_num,
            "weight": item.weight,
            "custom_tables": item.custom_tables or [],
            "is_active": item.is_active,
            "if_main": item.if_main
        }
    }


# =============================================================================
# ✅ 运动控制器产品操作
# =============================================================================
@product_router.post("/sport/save")
def save_sport(request: SportSaveRequest, db: Session = Depends(get_db)):
    """保存运动控制器产品"""
    if not request.id:
        # 新增产品
        item = SportProduct(
            product_name=request.product_name,
            model_number=request.model_number,
            robot_type=request.robot_type,
            category_id=request.category_id,
            is_active=request.is_active,
            if_main=request.if_main == 1,
            main_image_url=request.main_image_url,
            name=request.name,
            detail=request.detail,
            img=request.img,
            line1=request.line1,
            line2=request.line2,
            line3=request.line3,
            sport_pram=request.sport_pram,
            sport_pram_two=request.sport_pram_two
        )
        db.add(item)
    else:
        # 更新产品
        item = db.query(SportProduct).filter(SportProduct.id == request.id).first()
        if not item:
            raise HTTPException(404, "产品不存在")

        item.product_name = request.product_name
        item.model_number = request.model_number
        item.robot_type = request.robot_type
        item.category_id = request.category_id
        item.is_active = request.is_active
        item.if_main = request.if_main == 1
        item.main_image_url = request.main_image_url
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
    return {"code": 200, "data": {"id": item.id}}


@product_router.get("/sport/{sport_id}")
def get_sport_detail(sport_id: int, db: Session = Depends(get_db)):
    """获取运动控制器详情"""
    item = db.query(SportProduct).filter(SportProduct.id == sport_id).first()
    if not item:
        raise HTTPException(404, "产品不存在")

    return {
        "code": 200,
        "data": {
            "id": item.id,
            "product_name": item.product_name,
            "model_number": item.model_number,
            "main_image_url": item.main_image_url,
            "name": item.name,
            "detail": item.detail,
            "img": item.img,
            "line1": item.line1,
            "line2": item.line2,
            "line3": item.line3,
            "sport_pram": item.sport_pram,
            "sport_pram_two": item.sport_pram_two,
            "is_active": item.is_active,
            "if_main": item.if_main
        }
    }


# =============================================================================
# ✅ 通用产品详情
# =============================================================================
# =============================================================================
# ✅ 通用产品详情
# =============================================================================
@product_router.get("/detail/{product_type}/{product_id}")
def get_product_detail(product_type: str, product_id: int, db: Session = Depends(get_db)):
    """获取产品详情"""
    model = RobotProduct if product_type == "robot" else SportProduct
    item = db.query(model).filter(model.id == product_id).first()
    if not item:
        raise HTTPException(404, "产品不存在")

    base_data = {
        "id": item.id,
        "product_name": item.product_name,
        "model_number": item.model_number,
        "main_image_url": item.main_image_url,
        "category_id": item.category_id,
        "category_path": get_category_path(db, item.category_id),
        "is_active": item.is_active,
        "if_main": item.if_main,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "product_type": product_type,
        "robot_type": item.robot_type  # <--- 添加这一行
    }

    if product_type == "robot":
        base_data.update({
            "max_arm_span": item.max_arm_span,
            "max_weight": item.max_weight,
            "switch_num": item.switch_num,
            "weight": item.weight,
            "custom_tables": item.custom_tables or []
        })
    else:
        base_data.update({
            "name": item.name,
            "detail": item.detail,
            "img": item.img,
            "line1": item.line1,
            "line2": item.line2,
            "line3": item.line3,
            "sport_pram": item.sport_pram,
            "sport_pram_two": item.sport_pram_two
        })

    return {"code": 200, "data": base_data}


# =============================================================================
# ✅ 首页产品
# =============================================================================
@product_router.get("/main/products")
def get_main_products(
        page: int = 1,
        page_size: int = 6,
        product_type: Optional[str] = None,
        db: Session = Depends(get_db)
):
    """获取首页展示产品"""
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
        q = db.query(m).filter(m.if_main == 1)
        total += q.count()
        all_items.extend(q.order_by(desc(m.created_at)).all())

    all_items.sort(key=lambda x: x.created_at, reverse=True)
    items = all_items[(page - 1) * page_size: page * page_size]

    data = []
    for item in items:
        data.append({
            "id": item.id,
            "productName": item.product_name,
            "modelNumber": item.model_number,
            "mainImageUrl": item.main_image_url or "",
            "categoryId": item.category_id,
            "categoryPath": get_category_path(db, item.category_id),
            "robotType": item.robot_type,
            "productType": "robot" if isinstance(item, RobotProduct) else "sport",
            "isActive": item.is_active,
            "ifMain": item.if_main,
            "createTime": item.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return {"code": 200, "total": total, "data": data}


# =============================================================================
# ✅ 删除产品
# =============================================================================
@product_router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """删除产品"""
    # 尝试删除机器人产品
    robot_item = db.query(RobotProduct).filter(RobotProduct.id == product_id).first()
    if robot_item:
        # 删除图片文件
        if robot_item.main_image_url:
            delete_image_file(robot_item.main_image_url)
        if robot_item.custom_tables:
            for table in robot_item.custom_tables:
                if "image_url" in table and table["image_url"]:
                    delete_image_file(table["image_url"])

        db.delete(robot_item)
        db.commit()
        return {"code": 200, "msg": "删除成功"}

    # 尝试删除运动控制器产品
    sport_item = db.query(SportProduct).filter(SportProduct.id == product_id).first()
    if sport_item:
        # 删除图片文件
        if sport_item.main_image_url:
            delete_image_file(sport_item.main_image_url)
        if sport_item.img:
            delete_image_file(sport_item.img)

        db.delete(sport_item)
        db.commit()
        return {"code": 200, "msg": "删除成功"}

    raise HTTPException(404, "产品不存在")


# =============================================================================
# ✅ 辅助函数
# =============================================================================
def get_category_path(db: Session, category_id: int) -> str:
    """获取分类路径"""
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        return "未知分类"
    path = [cat.name]
    cur = cat
    while cur.parent_id:
        p = db.query(Category).filter(Category.id == cur.parent_id).first()
        if not p:
            break
        path.insert(0, p.name)
        cur = p
    return " / ".join(path)


def delete_image_file(url: str):
    """删除图片文件"""
    try:
        p = url.lstrip("/")
        if os.path.exists(p):
            os.remove(p)
    except:
        pass