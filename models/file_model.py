# models/file_model.py
from sqlalchemy import Column, Integer, String, BigInteger, DateTime
from datetime import datetime
from database import Base


class FileRecord(Base):
    __tablename__ = "file_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 原始文件名 (例如: "报告.pdf")
    original_name = Column(String(255), nullable=False, index=True, comment="原始文件名")

    # 存储的文件名 (UUID + 后缀，防止重名，例如: "a1b2c3.pdf")
    stored_name = Column(String(255), nullable=False, unique=True, comment="存储文件名")

    # 文件相对路径 (例如: "/static/uploads/files/a1b2c3.pdf")
    file_path = Column(String(500), nullable=False, comment="文件访问路径")

    # 文件大小 (单位：字节)
    file_size = Column(BigInteger, nullable=False, comment="文件大小(字节)")

    # 文件类型/MIME (例如: "application/pdf")
    content_type = Column(String(100), nullable=True, comment="文件MIME类型")

    # 上传时间
    upload_time = Column(DateTime, default=datetime.now, comment="上传时间")

    def __repr__(self):
        return f"<FileRecord(id={self.id}, name={self.original_name})>"