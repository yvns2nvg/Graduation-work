"""생성 작업(Generation) 데이터베이스 모델"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Generation(Base):
    """generations 테이블 - 이미지 및 3D 모델 생성 작업 이력"""

    __tablename__ = "generations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    prompt_text = Column(Text, nullable=False)
    status = Column(
        String(20),
        default="pending",
        nullable=False,
        comment="pending | generating | image_done | converting | done | failed",
    )
    image_url = Column(String(500), nullable=True)
    model_3d_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계 설정
    user = relationship("User", back_populates="generations")

    def __repr__(self):
        return f"<Generation(id={self.id}, status={self.status})>"
