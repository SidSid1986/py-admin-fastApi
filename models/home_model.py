from sqlalchemy import Column, Integer, String, DateTime, Boolean
from database import Base
from datetime import datetime


class HomeImage(Base):
    __tablename__ = "home_images"

    id = Column(Integer, primary_key=True, index=True)
    img_url = Column(String(255), nullable=False, comment="图片地址")
    sort = Column(Integer, default=0, comment="排序")
    type = Column(String(20), nullable=False, comment="类型")
    is_active = Column(Boolean, default=True, comment="是否启用")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    original_name = Column(String(255), nullable=True, comment="原始文件名")


