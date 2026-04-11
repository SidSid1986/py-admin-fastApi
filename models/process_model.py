from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from datetime import datetime
from database import Base


class Process(Base):
    __tablename__ = "process"

    # --- 主键 ---
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # --- 基础信息 ---
    title = Column(String(200), nullable=False, comment="方案标题")

    # --- 图片资源 ---
    cover1 = Column(String(500), nullable=True, comment="封面图1 (主图)")
    cover2 = Column(String(500), nullable=True, comment="封面图2 (副图/悬停图)")

    # --- 富文本内容 ---
    content = Column(Text, nullable=False, comment="方案详情富文本内容")

    # --- 状态与控制 ---
    is_active = Column(Boolean, default=True, comment="是否启用")
    sort = Column(Integer, default=0, comment="排序权重")

    # --- 时间戳 ---
    create_time = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")


    def __repr__(self):
        return f"<Process(id={self.id}, title='{self.title}')>"