from sqlalchemy import Column, Integer, String, DateTime
from database import Base
from datetime import datetime

class Analysis(Base):
    __tablename__ = "analysis"

    id = Column(Integer, primary_key=True, index=True)
    language = Column(String)
    code = Column(String)
    error = Column(String)
    explanation = Column(String)
    suggestion = Column(String)
    date = Column(DateTime, default=datetime.utcnow)