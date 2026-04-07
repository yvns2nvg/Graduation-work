"""models 패키지 초기화 - 모든 모델을 import하여 Base에 등록"""

from app.database import Base  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.generation import Generation  # noqa: F401
