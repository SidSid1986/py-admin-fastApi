# models.py (假设文件名是 models.py)
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from sqlalchemy.dialects.mysql import JSON as MySQLJSON

# 导入 Base
from database import Base


# =============================================================================
# 1. 机器人产品表 (RobotProduct)
# 对应数据库表名: robots
# =============================================================================
class RobotProduct(Base):
    __tablename__ = "robots"

    # --- 主键 ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)

    # --- 关联分类 (外键) ---
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="所属分类ID (叶子节点)"
    )

    category_path: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="分类路径快照")

    # --- 基础状态 ---
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否上架")
    if_main: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否首页展示")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now,
                                                 comment="更新时间")

    # --- 通用产品信息 ---
    product_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="产品名称")
    model_number: Mapped[str] = mapped_column(String(100), nullable=False, comment="产品型号")
    robot_type: Mapped[str] = mapped_column(String(50), nullable=False, default="", comment="机器人类型")
    main_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="产品主图URL")

    # 原有单图字段
    img: Mapped[str | None] = mapped_column(String(500), nullable=True, default="", comment="表单内上传的主图")

    #  新增：多图数组字段
    images: Mapped[list[str] | None] = mapped_column(
        MySQLJSON,
        nullable=True,
        comment="产品多图数组，例如 ['/upload/1.png', '/upload/2.png']"
    )

    # --- 核心机械参数 ---
    max_arm_span: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="最大臂展")
    max_weight: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="最大负载")
    switch_num: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="轴数")
    weight: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="本体重量")

    # --- 自定义多表格数据 ---
    custom_tables: Mapped[list | None] = mapped_column(
        MySQLJSON,
        nullable=True,
        comment="自定义多表格数据"
    )

# =============================================================================
# 2. 运动控制器产品表 (SportProduct)
# 对应数据库表名: sport
# =============================================================================
class SportProduct(Base):
    __tablename__ = "sport"

    # --- 主键 ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)

    # --- 关联分类 (外键) ---
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="所属分类ID (叶子节点)"
    )
    category_path: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="分类路径快照")

    # --- 基础状态 ---
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否上架")
    if_main: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否首页展示")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now,
                                                 comment="更新时间")

    # --- 通用产品信息 ---
    product_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="产品名称")
    model_number: Mapped[str] = mapped_column(String(100), nullable=False, comment="产品型号")
    robot_type: Mapped[str] = mapped_column(String(50), nullable=False, default="", comment="机器人类型")
    main_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="产品主图URL")

    # 原有单图字段
    img: Mapped[str | None] = mapped_column(String(500), nullable=True, default="", comment="表单内上传的主图")

    #  新增：多图数组字段
    images: Mapped[list[str] | None] = mapped_column(
        MySQLJSON,
        nullable=True,
        comment="产品多图数组，例如 ['/upload/1.png', '/upload/2.png']"
    )

    # --- 运动控制器特有参数 ---
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="控制器型号名称")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True, comment="产品详情描述")

    # --- 核心卖点列表 ---
    selling_points: Mapped[list | None] = mapped_column(
        MySQLJSON,
        nullable=True,
        comment="核心卖点列表"
    )

    # --- 自定义多表格数据 ---
    custom_tables: Mapped[list | None] = mapped_column(
        MySQLJSON,
        nullable=True,
        comment="自定义多表格数据"
    )

    # --- 索引优化 ---
    __table_args__ = (
        Index('idx_sport_category', 'category_id'),
        Index('idx_sport_active', 'is_active'),
        Index('idx_sport_main', 'if_main'),
        Index('idx_sport_model', 'model_number'),
    )