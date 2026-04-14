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
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="所属分类ID (叶子节点)"
    )

    category_path: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="分类路径快照")

    # --- 基础状态 ---
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否上架")
    if_main: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否首页展示")  # ✅ 已加
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now,
                                                 comment="更新时间")

    # --- 通用产品信息 ---
    product_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="产品名称")
    model_number: Mapped[str] = mapped_column(String(100), nullable=False, comment="产品型号")
    robot_type: Mapped[str] = mapped_column(String(50), nullable=False, default="", comment="机器人类型")
    main_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="产品主图URL")

    # --- 机器人特有参数 ---
    robot_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="机器人型号标识")
    max_arm_span: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="最大臂展")
    max_weight: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="最大负载")
    switch_num: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="轴数")
    weight: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="本体重量")
    perprecision: Mapped[str | None] = mapped_column(Text, nullable=True, comment="重复定位精度")
    ip_level: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="防护等级")
    ins_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="安装形式")
    drive_type: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="驱动方式")
    auth_support: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="支持认证")
    ins_require: Mapped[str | None] = mapped_column(Text, nullable=True, comment="安装条件")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注说明")
    detail_img: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="详情图片")

    # --- 索引优化 ---
    __table_args__ = (
        Index('idx_robot_category', 'category_id'),
        Index('idx_robot_active', 'is_active'),
        Index('idx_robot_main', 'if_main'),  # ✅ 索引也加了
        Index('idx_robot_model', 'model_number'),
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
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="所属分类ID (叶子节点)"
    )
    category_path: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="分类路径快照")

    # --- 基础状态 ---
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否上架")
    if_main: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否首页展示")  # ✅ 已加
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now,
                                                 comment="更新时间")

    # --- 通用产品信息 ---
    product_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="产品名称")
    model_number: Mapped[str] = mapped_column(String(100), nullable=False, comment="产品型号")
    robot_type: Mapped[str] = mapped_column(String(50), nullable=False, default="", comment="机器人类型")
    main_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="产品主图URL")

    # --- 运动控制器特有参数 ---
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="控制器型号名称")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True, comment="产品详情描述")
    img: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="表单内上传的主图")

    # 卖点
    line1: Mapped[str | None] = mapped_column(Text, nullable=True, comment="卖点1")
    line2: Mapped[str | None] = mapped_column(Text, nullable=True, comment="卖点2")
    line3: Mapped[str | None] = mapped_column(Text, nullable=True, comment="卖点3")

    # JSON 字段
    sport_pram: Mapped[dict | list | None] = mapped_column(MySQLJSON, nullable=True, comment="配件列表 (JSON)")
    sport_pram_two: Mapped[dict | list | None] = mapped_column(MySQLJSON, nullable=True, comment="轴配置选项 (JSON)")

    # --- 索引优化 ---
    __table_args__ = (
        Index('idx_sport_category', 'category_id'),
        Index('idx_sport_active', 'is_active'),
        Index('idx_sport_main', 'if_main'),
        Index('idx_sport_model', 'model_number'),
    )