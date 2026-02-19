"""
LocationName model.

시대별 위치 명칭을 관리.
같은 좌표의 장소가 시대별로 다른 이름을 가질 수 있음.

예시:
- London (410~현재) = Londinium (43~410)
- Seoul (1945~) = Gyeongseong (1910~1945) = Hanseong (1394~1910)
- Istanbul (1930~) = Constantinople (330~1930) = Byzantium (~330)
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.models.base import Base


class LocationName(Base):
    """위치의 시대별 명칭"""

    __tablename__ = "location_names"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(
        Integer,
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 명칭
    name = Column(String(255), nullable=False, index=True)
    name_ko = Column(String(255))
    name_ja = Column(String(255))
    language = Column(String(10), default='en')  # en, ko, ja, zh, la, ar, gr

    # 유효 기간 (연도, BCE는 음수)
    valid_from = Column(Integer)   # 시작 연도 (NULL = 기원 이전부터)
    valid_until = Column(Integer)  # 종료 연도 (NULL = 현재까지)

    # 명칭 유형
    is_primary = Column(Boolean, default=False)  # 해당 시기 대표 명칭
    name_type = Column(String(30), default='official')
    # name_type 값:
    #   official: 공식 명칭
    #   alternate: 대안 명칭 (한양/한성 동시 사용)
    #   vernacular: 토착/구어 명칭
    #   colonial: 식민지 시대 명칭
    #   ancient: 고대 명칭

    # 출처
    source = Column(String(100))  # wikidata, manual, wikipedia
    wikidata_id = Column(String(50), index=True)  # 해당 명칭의 Wikidata QID

    created_at = Column(DateTime, server_default=func.now())

    # Relationship
    location = relationship("Location", back_populates="names")

    def __repr__(self):
        period = ""
        if self.valid_from or self.valid_until:
            fr = self.valid_from or "?"
            to = self.valid_until or "present"
            period = f" ({fr}~{to})"
        return f"<LocationName('{self.name}'{period})>"

    def is_valid_in(self, year: int) -> bool:
        """특정 연도에 이 명칭이 유효한지 확인"""
        if self.valid_from is not None and year < self.valid_from:
            return False
        if self.valid_until is not None and year > self.valid_until:
            return False
        return True
