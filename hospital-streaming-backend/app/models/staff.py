from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.db.database import Base

class Staff(Base):
    """Staff model for hospital personnel"""
    __tablename__ = "staff"
    
    id = Column(String(255), primary_key=True, index=True)
    staffId = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    department = Column(String(100), nullable=False)
    nfcId = Column(String(100), unique=True, index=True)
    passwordHash = Column(String(255))
    pinHash = Column(String(255))
    phone = Column(String(20))
    email = Column(String(255))
    isActive = Column(Boolean, default=True)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())