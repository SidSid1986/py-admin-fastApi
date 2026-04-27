import uuid
import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from datetime import datetime
from database import get_db
from models import RobotProduct, SportProduct
from models.category_model import Category

product_router = APIRouter(prefix="/product", tags=["产品管理"])


# 统一图片上传接口
@product_router.post("/upload", summary="统一图片上传接口")
async def upload_image(
        file: UploadFile = File(...),
        folder: str = Query("common", description="上传目录名")
):
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


# 请求体
class RobotSaveRequest(BaseModel):
    id: Optional[int] = None
    product_name: str
    model_number: str
    robot_type: str
    category_id: int
    if_main: Optional[int] = 0
    is_active: Optional[bool] = True
    main_image_url: Optional[str] = None
    img: Optional[str] = None
    images: Optional[List[str]] = None
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
    name: Optional[str] = ""
    detail: Optional[str] = None
    img: Optional[str] = None
    images: Optional[List[str]] = None
    selling_points: Optional[List[Dict[str, Union[str, int]]]] = None
    custom_tables: Optional[List[Dict]] = None


# 产品列表
@product_router.get("/list")
def get_product_list(
        page: int = 1,
        page_size: int = 10,
        keyword: Optional[str] = None,
        category_id: Optional[int] = None,
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
            "img": item.img or "",
            "images": item.images or [],
            "categoryPath": get_category_path(db, item.category_id),
            "robotType": item.robot_type,
            "productType": "robot" if isinstance(item, RobotProduct) else "sport",
            "isActive": item.is_active,
            "ifMain": item.if_main,
            "createTime": item.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return {"code": 200, "total": total, "data": data}


# 机器人保存
@product_router.post("/robot/save")
def save_robot(request: RobotSaveRequest, db: Session = Depends(get_db)):
    if not request.id:
        item = RobotProduct(
            product_name=request.product_name,
            model_number=request.model_number,
            robot_type=request.robot_type,
            category_id=request.category_id,
            is_active=request.is_active,
            if_main=request.if_main == 1,
            main_image_url=request.main_image_url,
            img=request.img,
            images=request.images,
            max_arm_span=request.max_arm_span,
            max_weight=request.max_weight,
            switch_num=request.switch_num,
            weight=request.weight,
            custom_tables=request.custom_tables
        )
        db.add(item)
    else:
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
        item.img = request.img
        item.images = request.images
        item.max_arm_span = request.max_arm_span
        item.max_weight = request.max_weight
        item.switch_num = request.switch_num
        item.weight = request.weight
        item.custom_tables = request.custom_tables

    db.commit()
    return {"code": 200, "data": {"id": item.id}}


@product_router.get("/robot/{robot_id}")
def get_robot_detail(robot_id: int, db: Session = Depends(get_db)):
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
            "img": item.img or "",
            "images": item.images or [],
            "max_arm_span": item.max_arm_span,
            "max_weight": item.max_weight,
            "switch_num": item.switch_num,
            "weight": item.weight,
            "custom_tables": item.custom_tables or [],
            "is_active": item.is_active,
            "if_main": item.if_main
        }
    }


# 运动产品保存
@product_router.post("/sport/save")
def save_sport(request: SportSaveRequest, db: Session = Depends(get_db)):
    if not request.id:
        item = SportProduct(
            product_name=request.product_name,
            model_number=request.model_number,
            robot_type=request.robot_type,
            category_id=request.category_id,
            is_active=request.is_active,
            if_main=request.if_main == 1,
            main_image_url=request.main_image_url,
            name=request.name or "",
            detail=request.detail,
            img=request.img,
            images=request.images,
            selling_points=request.selling_points,
            custom_tables=request.custom_tables
        )
        db.add(item)
    else:
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
        item.name = request.name or ""
        item.detail = request.detail
        item.img = request.img
        item.images = request.images
        item.selling_points = request.selling_points
        item.custom_tables = request.custom_tables
        item.updated_at = datetime.now()

    db.commit()
    return {"code": 200, "data": {"id": item.id}}


@product_router.get("/sport/{sport_id}")
def get_sport_detail(sport_id: int, db: Session = Depends(get_db)):
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
            "img": item.img or "",
            "images": item.images or [],
            "selling_points": item.selling_points,
            "custom_tables": item.custom_tables or [],
            "is_active": item.is_active,
            "if_main": item.if_main
        }
    }


# 通用详情
@product_router.get("/detail/{product_type}/{product_id}")
def get_product_detail(product_type: str, product_id: int, db: Session = Depends(get_db)):
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
        "robot_type": item.robot_type,
        "img": item.img or "",
        "images": item.images or []
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
            "selling_points": item.selling_points,
            "custom_tables": item.custom_tables or []
        })

    return {"code": 200, "data": base_data}


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
            "img": item.img or "",
            "images": item.images or [],
            "categoryPath": get_category_path(db, item.category_id),
            "robotType": item.robot_type,
            "productType": "robot" if isinstance(item, RobotProduct) else "sport",
            "isActive": item.is_active,
            "ifMain": item.if_main,
            "createTime": item.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return {"code": 200, "total": total, "data": data}


# 删除产品
@product_router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    robot_item = db.query(RobotProduct).filter(RobotProduct.id == product_id).first()
    if robot_item:
        if robot_item.main_image_url:
            delete_image_file(robot_item.main_image_url)
        if robot_item.img:
            delete_image_file(robot_item.img)
        if robot_item.images:
            for url in robot_item.images:
                delete_image_file(url)
        if robot_item.custom_tables:
            for table in robot_item.custom_tables:
                if "images" in table and table["images"]:
                    for image_obj in table["images"]:
                        if "url" in image_obj and image_obj["url"]:
                            delete_image_file(image_obj["url"])
        db.delete(robot_item)
        db.commit()
        return {"code": 200, "msg": "删除成功"}

    sport_item = db.query(SportProduct).filter(SportProduct.id == product_id).first()
    if sport_item:
        if sport_item.main_image_url:
            delete_image_file(sport_item.main_image_url)
        if sport_item.img:
            delete_image_file(sport_item.img)
        if sport_item.images:
            for url in sport_item.images:
                delete_image_file(url)
        if sport_item.custom_tables:
            for table in sport_item.custom_tables:
                if "images" in table and table["images"]:
                    for image_obj in table["images"]:
                        if "url" in image_obj and image_obj["url"]:
                            delete_image_file(image_obj["url"])
        db.delete(sport_item)
        db.commit()
        return {"code": 200, "msg": "删除成功"}

    raise HTTPException(404, "产品不存在")


# 辅助
def get_category_path(db: Session, category_id: int) -> str:
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
    try:
        p = url.lstrip("/")
        if os.path.exists(p):
            os.remove(p)
    except:
        pass