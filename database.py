from sqlalchemy import create_engine, Column, String, Date, Float
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class Farmer(Base):
    __tablename__ = "farmers"
    
    user_id       = Column(String, primary_key=True)
    planting_date = Column(String)   # วันที่หว่านเมล็ด
    latitude      = Column(Float)    # พิกัด
    longitude     = Column(Float)
    rice_variety  = Column(String)   # สายพันธุ์ข้าว
    province      = Column(String)   # จังหวัด

engine = create_engine("sqlite:///nasmart.db")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)