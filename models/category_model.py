# models/category_model.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base



class Category(Base):
    __tablename__ = "categories"

    # --- 基础字段 ---
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False, comment="分类名称")

    # --- 树形结构 (自关联) ---
    # ondelete="CASCADE": 当父分类被删除时，数据库层面会自动删除子分类
    parent_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=True, index=True,
                       comment="父分类ID (NULL表示一级分类)")

    # 自关联关系：父 -> 子
    children = relationship("Category", back_populates="parent", lazy="selectin", cascade="all, delete-orphan")
    # 自关联关系：子 -> 父
    parent = relationship("Category", back_populates="children", remote_side=[id])

    # --- 产品类型标识字段 ---
    # 仅当 parent_id 为 NULL (一级分类) 时填写此字段
    # 子分类自动继承父级的 type
    # 枚举值示例: "robot", "sport", "servo", "sensor"
    category_type = Column(String(50), nullable=True, index=True, comment="产品类型标识 (仅一级分类有效)")
    img = Column(String(255), nullable=True, comment="分类图片")

    # --- 其他业务字段 ---
    sort_order = Column(Integer, default=0, comment="排序权重")
    is_active = Column(Boolean, default=True, comment="是否启用")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # ==========================================
    # 关联说明
    # ==========================================
    #  直接关联 Product 表， 产品分散在不同表中。
    __table_args__ = (
        #加速按父级和排序的查询
        Index('idx_parent_sort', 'parent_id', 'sort_order'),
        # 加速按类型筛选分类
        Index('idx_category_type', 'category_type'),
    )

    def to_dict(self, include_children: bool = False, include_product_count: bool = False):
        """
        将模型转换为字典，供 API 返回
        :param include_children: 是否递归包含子节点
        :param include_product_count: 是否包含产品数量统计 (需外部注入或单独查询)
        """
        data = {
            "id": self.id,
            "label": self.name,  # 前端 el-cascader 需要的 label
            "value": self.id,  # 前端 el-cascader 需要的 value
            "parentId": self.parent_id,  # 前端用于判断层级
            "sort": self.sort_order,
            "status": 1 if self.is_active else 0,
            "createTime": self.create_time.strftime("%Y-%m-%d %H:%M:%S") if self.create_time else None,

            # === 返回类型字段 ===
            "category_type": self.category_type,
            "img": self.img,  # <-- 分类图片

        }

        # 如果需要统计产品数量，这里暂时返回 0
        if include_product_count:
            data["productCount"] = 0

            # 递归处理子节点
        if include_children and self.children:
            # 按 sort_order 排序子节点
            sorted_children = sorted(self.children, key=lambda x: x.sort_order)
            data["children"] = [
                child.to_dict(
                    include_children=True,
                    include_product_count=False
                )
                for child in sorted_children
            ]
        else:
            data["children"] = []

        return data