from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from database import Base


class Category(Base):
    __tablename__ = "categories"

    # --- 基础字段 ---
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False, comment="分类名称")

    # --- 树形结构核心字段 (自关联) ---
    parent_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=True, index=True,
                       comment="父分类ID")

    # 自关联关系：父 -> 子
    children = relationship("Category", back_populates="parent", lazy="selectin", cascade="all, delete-orphan")
    # 自关联关系：子 -> 父
    parent = relationship("Category", back_populates="children", remote_side=[id])

    # --- 其他业务字段 ---
    sort_order = Column(Integer, default=0, comment="排序权重")
    is_active = Column(Boolean, default=True, comment="是否启用")
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # ==========================================
    # 【关键】预留与 Product 模型的关联关系
    # ==========================================
    # 1. 这里使用字符串 "Product" 而不是直接导入类，避免循环导入错误
    # 2. back_populates="category" 意味着未来的 Product 模型中必须有一个名为 'category' 的关系属性
    # 3. lazy="dynamic" 或 "selectin"：如果产品很多，建议用 dynamic 以便分页查询；如果不多，selectin 性能更好
    products = relationship(
        "Product",
        back_populates="category",
        lazy="selectin",
        cascade="all, delete-orphan",  # 【重要策略】：当分类被删除时，自动删除该分类下的所有产品
        # 或者使用 cascade="all, delete-orphan, expunge"
        # 如果你的业务逻辑是“禁止删除有产品的分类”，则不要在 Model 层设 cascade，而在 Router 层做校验（推荐）
    )

    __table_args__ = (
        Index('idx_parent_sort', 'parent_id', 'sort_order'),
    )

    def to_dict(self, include_children: bool = False, include_product_count: bool = False):
        """转换为字典"""
        data = {
            "id": self.id,
            "label": self.name,
            "value": self.id,
            "parentId": self.parent_id,
            "sort": self.sort_order,
            "status": 1 if self.is_active else 0,
            "createTime": self.create_time.strftime("%Y-%m-%d %H:%M:%S") if self.create_time else None,
        }

        # 可选：返回该分类下的产品数量（前端展示很有用，例如：机器人 (12)）
        if include_product_count:
            # 注意：如果使用了 lazy="dynamic"，这里可以直接 len(self.products)
            # 如果使用了 lazy="selectin"，products 已经加载，直接 len 即可
            data["productCount"] = len(self.products) if self.products else 0

        if include_children and self.children:
            data["children"] = [child.to_dict(include_children=True, include_product_count=include_product_count)
                                for child in sorted(self.children, key=lambda x: x.sort_order)]
        else:
            data["children"] = []

        return data