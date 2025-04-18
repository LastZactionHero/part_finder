from sqlalchemy import Column, Integer, String, TIMESTAMP, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

# Define the base class for SQLAlchemy models
Base = declarative_base()

class MouserApiCache(Base):
    __tablename__ = 'mouser_api_cache'

    cache_id = Column(Integer, primary_key=True)
    search_term = Column(String, nullable=False)
    search_type = Column(String(50), nullable=False)
    response_data = Column(JSONB)
    cached_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index('idx_mouser_cache_term_type', 'search_term', 'search_type', unique=True),
        Index('idx_mouser_cache_cached_at', 'cached_at'),
    ) 