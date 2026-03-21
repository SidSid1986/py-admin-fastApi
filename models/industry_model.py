from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Industry(Base):
    __tablename__ = "industries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 行业名称
    name = Column(String(50), unique=True, index=True, nullable=False, comment="行业名称")

    # [新增] 图标路径 (存储相对路径，如 /static/uploads/icons/xxx.png)
    icon1 = Column(String(500), nullable=True, comment="行业图标URL1")
    icon2 = Column(String(500), nullable=True, comment="行业图标URL2")

    # 排序权重
    sort = Column(Integer, default=0, nullable=False, comment="排序权重")

    # 是否启用
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")

    # 时间字段
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="最后更新时间")

    # 【新增】反向关系：一个行业拥有多个解决方案
    # back_populates 必须与 Solution 模型中的字段名一致
    solutions = relationship("Solution", back_populates="industry", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Industry(id={self.id}, name='{self.name}', icon='{self.icon}')>"