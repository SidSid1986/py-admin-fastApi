from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models.category_model import Category
from pydantic import BaseModel, Field

category_router = APIRouter(prefix="/category", tags=["产品分类管理"])


# --- Pydantic 模型 (请求/响应) ---

class CategorySaveRequest(BaseModel):
    """
    统一的保存请求模型：
    - 如果 id 存在：执行更新操作
    - 如果 id 不存在：执行新增操作
    """
    id: Optional[int] = Field(None, description="分类ID (存在则更新，不存在则新增)")
    name: str = Field(..., min_length=1, max_length=50, description="分类名称")
    parent_id: Optional[int] = Field(None, description="父分类ID (不传则为一级分类)")
    sort_order: int = Field(0, description="排序权重")
    is_active: bool = Field(True, description="是否启用")


# --- 辅助函数 ---

def build_tree(nodes: List[Category], parent_id: Optional[int] = None) -> List[dict]:
    """将扁平列表构建成树形结构"""
    tree = []
    children = [node for node in nodes if node.parent_id == parent_id]

    for node in children:
        node_dict = node.to_dict()
        node_dict["children"] = build_tree(nodes, node.id)
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
    data_list = [cat.to_dict(include_children=False) for cat in categories]

    return {"code": 200, "msg": "success", "data": data_list}


@category_router.post("/save", summary="保存分类 (新增或更新)")
def save_category(
        req: CategorySaveRequest,
        db: Session = Depends(get_db)
):
    """
    根据 ID 是否存在自动判断是新增还是更新。
    方法：POST
    路径：/category/save
    """

    # 1. 公共校验：如果指定了父级，必须检查父级是否存在且有效
    if req.parent_id is not None:
        parent = db.query(Category).filter(Category.id == req.parent_id).first()
        if not parent:
            raise HTTPException(status_code=400, detail="指定的父分类不存在")
        if not parent.is_active:
            raise HTTPException(status_code=400, detail="不能在已禁用的分类下新增或移动子分类")

        # 额外校验：如果是更新操作，不能将自己设置为自己的子节点
        if req.id is not None and req.id == req.parent_id:
            raise HTTPException(status_code=400, detail="分类不能将自己设为父级")

    # 2. 分支逻辑：更新 vs 新增
    if req.id is not None:
        # === 更新模式 ===
        category = db.query(Category).filter(Category.id == req.id).first()
        if not category:
            raise HTTPException(status_code=404, detail="分类不存在，无法更新")

        # 更新字段
        category.name = req.name
        category.parent_id = req.parent_id
        category.sort_order = req.sort_order
        category.is_active = req.is_active

        action_msg = "更新成功"
    else:
        # === 新增模式 ===
        # 检查同级名称是否重复 (优化体验)
        existing = db.query(Category).filter(
            Category.name == req.name,
            Category.parent_id == req.parent_id
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="该父级分类下已存在同名分类")

        category = Category(
            name=req.name,
            parent_id=req.parent_id,
            sort_order=req.sort_order,
            is_active=req.is_active
        )
        db.add(category)
        action_msg = "新增成功"

    # 3. 提交事务
    db.commit()
    db.refresh(category)

    return {
        "code": 200,
        "msg": action_msg,
        "data": category.to_dict()
    }


@category_router.delete("/{category_id}", summary="删除分类")
def delete_category(
        category_id: int,
        db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")

    # 检查子分类
    children_count = db.query(Category).filter(Category.parent_id == category_id).count()
    if children_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"无法删除：该分类下还有 {children_count} 个子分类。"
        )

    # 检查关联产品 (预留接口，需确保 Category 模型中有 products 关系)
    if hasattr(category, 'products') and len(category.products) > 0:
        raise HTTPException(
            status_code=400,
            detail=f"无法删除：该分类下已有 {len(category.products)} 个产品关联。"
        )

    db.delete(category)
    db.commit()

    return {"code": 200, "msg": "删除成功"}