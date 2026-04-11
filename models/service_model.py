from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func
from database import Base


class ServiceContent(Base):
    __tablename__ = "service_contents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    content = Column(Text, nullable=True, default="暂无服务内容")

    # 强制生成 CURRENT_TIMESTAMP
    updated_at = Column(
        DateTime,
        server_default='CURRENT_TIMESTAMP',
        onupdate=func.now()
    )

    def __repr__(self):
        return f"<ServiceContent(id={self.id}, content='{self.content[:20]}...')>"