from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from database import get_db
from models.product_model import RobotProduct, SportProduct
from typing import Optional, List, Dict, Type # 导入 Type 用于类型注解
from models.category_model import Category
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy.orm import DeclarativeMeta

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
    robot_type: str = Field(default="", description="机器人类型")
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
    robot_type: str = Field(default="")
    # 控制器特有
    name: Optional[str] = Field(None, description="控制器名称")
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
    robot_type: str
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
    product_type: str = "robot"

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
    name: Optional[str] = None
    detail: Optional[str]
    img: Optional[str]
    line1: Optional[str]
    line2: Optional[str]
    line3: Optional[str]
    sport_pram: Optional[dict]
    sport_pram_two: Optional[dict]

    # 额外标记类型
    product_type: str = "sport" # 注意：这里的 product_type 值可以根据需要决定是否同步修改

    if PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True

# 产品类型映射 后面通过类型查询时候增加类型到这里
PRODUCT_TYPE_MAPPING: Dict[str, Dict] = {
    "robot": {
        "model": RobotProduct,
        "response_schema": RobotDetailResponse
    },
    "sport": {
        "model": SportProduct,
        "response_schema": SportDetailResponse
    },
    # 当未来需要添加新产品类型时，只需在这里追加一行：
    # "new_type_name": { # 小写形式
    #     "model": NewProductModel,
    #     "response_schema": NewProductDetailResponse
    # }
}


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
@product_router.get("/detail/{product_type}/{product_id}", summary="获取产品详情 (按类型区分)")
def get_product_detail(product_type: str, product_id: int, db: Session = Depends(get_db)):
    # 1. 从映射字典中查找对应的模型和响应类
    product_info = PRODUCT_TYPE_MAPPING.get(product_type.lower()) # 使用 .lower() 来匹配映射字典中的小写键

    # 2. 如果找不到对应的类型，则抛出 404 错误
    if not product_info:
        raise HTTPException(status_code=404, detail=f"Unknown product type: {product_type}")

    # 3. 获取模型和响应类
    ModelClass: Type[DeclarativeMeta] = product_info["model"]
    ResponseSchema = product_info["response_schema"]

    # 4. 根据获取到的模型进行查询
    item = db.query(ModelClass).filter(ModelClass.id == product_id).first()

    # 5. 如果没找到具体条目，则抛出 404 错误
    if not item:
        raise HTTPException(status_code=404, detail=f"{product_type} 产品不存在 (ID: {product_id})")

    # 6. 使用获取到的响应类进行序列化
    response_data = ResponseSchema.model_validate(item)  # 使用 model_validate

    return {"code": 200, "msg": "success", "data": response_data}


# --- 🤖 机器人保存 ---
@product_router.post("/robot/save", summary="保存机器人 (新增/更新)")
def save_robot(request: RobotSaveRequest, db: Session = Depends(get_db)):
    category_path = get_category_path(db, request.category_id)

    if request.id is None:
        # 新增
        new_item = RobotProduct(
            product_name=request.product_name,
            model_number=request.model_number,
            robot_type=request.robot_type,
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
        item.robot_type = request.robot_type
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
            robot_type=request.robot_type,
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
        item.robot_type = request.robot_type
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


@product_router.get("/list", summary="获取产品列表")
def get_product_list(
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=100),
        keyword: Optional[str] = Query(None, description="搜索产品名称"),  # 保持原有逻辑，专用于名称
        model_number: Optional[str] = Query(None, description="搜索产品型号"),  # [新增] 专用于型号搜索
        category_id: Optional[int] = Query(None),
        product_type: Optional[str] = Query(None),
        db: Session = Depends(get_db)
):
    # 1. 确定要查询的模型列表
    models_to_query = []
    if product_type == "robot": # 查询时也用小写
        models_to_query.append(RobotProduct)
    elif product_type == "sport": # 查询时也用小写
        models_to_query.append(SportProduct)
    else:
        models_to_query = [RobotProduct, SportProduct]

    all_items = []
    total_count = 0

    # 2. 循环查询每个模型
    for model in models_to_query:
        q = db.query(model)

        # --- 筛选逻辑 ---

        # 构建搜索条件列表
        search_conditions = []

        # 1. 如果传了 keyword，加入名称搜索条件
        if keyword:
            search_conditions.append(model.product_name.contains(keyword))

        # 2. [新增] 如果传了 model_number，加入型号搜索条件
        if model_number:
            search_conditions.append(model.model_number.contains(model_number))

        # 3. 应用搜索条件 (使用 or_ 连接，表示满足任意一个即可)
        if search_conditions:
            q = q.filter(or_(*search_conditions))

        # 分类筛选
        if category_id:
            q = q.filter(model.category_id == category_id)

        # --- 统计总数 ---
        count = q.count()
        total_count += count

        # --- 获取数据 ---
        items = q.order_by(desc(model.created_at)).all()
        all_items.extend(items)

    # 3. 内存中合并排序
    all_items.sort(key=lambda x: x.created_at, reverse=True)

    # 4. 内存中分页切片
    start = (page - 1) * page_size
    end = start + page_size
    paginated_items = all_items[start:end]

    # 5. 构建返回数据
    data_list = []
    for item in paginated_items:
        p_type = "robot" if isinstance(item, RobotProduct) else "sport"

        data_list.append({
            "id": item.id,
            "productName": item.product_name,
            "modelNumber": item.model_number,
            "mainImageUrl": item.main_image_url,
            "categoryId": item.category_id,
            "categoryPath": item.category_path,
            "robotType": item.robot_type,
            "productType": p_type,
            "isActive": item.is_active,
            "createTime": item.created_at.strftime("%Y-%m-%d %H:%M:%S") if item.created_at else None
        })

    return {
        "code": 200,
        "msg": "success",
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "data": data_list
    }

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