from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from database import get_db
from models.category_model import Category
from pydantic import BaseModel, Field
from models import RobotProduct, SportProduct
category_router = APIRouter(prefix="/category", tags=["产品分类管理"])

# --- 类型映射字典 ---
TYPE_MAP: Dict[str, str] = {
    "robot": "机器人",
    "sport": "运动控制器",
    "servo": "伺服驱动器",
    "sensor": "传感器"
}


def get_type_name(type_code: Optional[str]) -> str:
    """辅助函数：获取中文类型名"""
    if not type_code:
        return "未知类型"
    return TYPE_MAP.get(type_code, type_code)


# --- Pydantic 模型 ---

class CategorySaveRequest(BaseModel):
    id: Optional[int] = Field(None, description="分类ID")
    name: str = Field(..., min_length=1, max_length=50, description="分类名称")
    parent_id: Optional[int] = Field(None, description="父分类ID")
    sort_order: int = Field(0, description="排序权重")
    is_active: bool = Field(True, description="是否启用")
    category_type: Optional[str] = Field(None, max_length=50, description="产品类型代码")
    img: Optional[str] = Field(None, description="分类图片")

class CategoryResponse(BaseModel):
    """统一响应模型，包含中文名称"""
    id: int
    label: str
    value: int
    parentId: Optional[int]
    sort: int
    status: int
    createTime: Optional[str]

    # 原始代码
    category_type: Optional[str]

    # === 中文名称 ===
    type_name: str

    children: List['CategoryResponse'] = []

    class Config:
        from_attributes = True


# --- 辅助函数 (构建树) ---

def build_tree(nodes: List[Category], parent_id: Optional[int] = None) -> List[dict]:
    tree = []
    children = [node for node in nodes if node.parent_id == parent_id]

    for node in children:
        node_dict = {
            "id": node.id,
            "label": node.name,
            "value": node.id,
            "parentId": node.parent_id,
            "sort": node.sort_order,
            "status": 1 if node.is_active else 0,
            "createTime": node.create_time.strftime("%Y-%m-%d %H:%M:%S") if node.create_time else None,
            "category_type": node.category_type,
            "type_name": get_type_name(node.category_type),
            "img": node.img,
            "children": build_tree(nodes, node.id)
        }
        tree.append(node_dict)

    tree.sort(key=lambda x: x.get("sort", 0))
    return tree


# --- 接口定义 ---

@category_router.get("/tree", summary="获取分类树")
def get_category_tree(db: Session = Depends(get_db)):
    all_categories = db.query(Category).filter(Category.is_active == True).all()
    tree_data = build_tree(all_categories, parent_id=None)
    return {"code": 200, "msg": "success", "data": tree_data}


@category_router.get("/list", summary="获取分类列表")
def get_category_list(
        parent_id: Optional[int] = Query(None, description="筛选特定父ID下的子分类"),
        db: Session = Depends(get_db)
):
    query = db.query(Category)
    if parent_id is not None:
        query = query.filter(Category.parent_id == parent_id)
    else:
        query = query.filter(Category.parent_id == None)

    categories = query.order_by(Category.sort_order, Category.id).all()

    # === 注入 type_name ===
    data_list = []
    for cat in categories:
        item = cat.to_dict(include_children=False)
        # 注入中文名称
        item["type_name"] = get_type_name(cat.category_type)
        data_list.append(item)

    return {"code": 200, "msg": "success", "data": data_list}


@category_router.post("/save", summary="保存分类 (新增或更新)")
def save_category(req: CategorySaveRequest, db: Session = Depends(get_db)):
    # 一级分类必须传类型
    if req.parent_id is None:
        if not req.category_type:
            raise HTTPException(status_code=400, detail="一级分类必须指定 category_type")

    # 有父级 → 自动继承顶级分类的类型
    if req.parent_id is not None:
        parent = db.query(Category).filter(Category.id == req.parent_id).first()
        if not parent:
            raise HTTPException(status_code=400, detail="父分类不存在")

        # 向上查找顶级分类
        top_parent = parent
        while top_parent.parent_id is not None:
            top_parent = db.query(Category).filter(Category.id == top_parent.parent_id).first()
            if not top_parent:
                break

        # 自动继承顶级类型 ✅
        req.category_type = top_parent.category_type

    # 不能选自己当父级
    if req.id and req.id == req.parent_id:
        raise HTTPException(status_code=400, detail="不能设为自己的父级")

    if req.id is not None:
        category = db.query(Category).filter(Category.id == req.id).first()
        if not category:
            raise HTTPException(status_code=404, detail="分类不存在")

        # 提升为一级分类必须指定类型
        if category.parent_id is not None and req.parent_id is None and not req.category_type:
            raise HTTPException(status_code=400, detail="提升为一级分类需指定类型")

        category.name = req.name
        category.parent_id = req.parent_id
        category.sort_order = req.sort_order
        category.is_active = req.is_active
        category.category_type = req.category_type
        category.img = req.img
        action_msg = "更新成功"
    else:
        existing = db.query(Category).filter(Category.name == req.name, Category.parent_id == req.parent_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="同名分类已存在")

        category = Category(
            name=req.name,
            parent_id=req.parent_id,
            sort_order=req.sort_order,
            is_active=req.is_active,
            category_type=req.category_type,
            img = req.img,
        )
        db.add(category)
        action_msg = "新增成功"

    db.commit()
    db.refresh(category)

    result = category.to_dict()
    result["type_name"] = get_type_name(category.category_type)

    return {"code": 200, "msg": action_msg, "data": result}


@category_router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    # 1. 找到分类
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(404, "分类不存在")

    # 2. 强制把所有使用该分类的产品 category_id 设为 NULL
    db.query(RobotProduct).filter(RobotProduct.category_id == category_id).update({RobotProduct.category_id: None})
    db.query(SportProduct).filter(SportProduct.category_id == category_id).update({SportProduct.category_id: None})

    # 3. 直接删除分类（不管有没有子分类，直接删）
    db.delete(cat)
    db.commit()

    return {"code": 200, "msg": "删除成功"}