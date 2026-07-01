from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pydantic import BaseModel
from typing import Optional

# ==========================================
# 1. إعداد قاعدة البيانات (PostgreSQL السحابية)
# ==========================================
# الرابط الخاص بقاعدتك على Neon.tech
SQLALCHEMY_DATABASE_URL = "postgresql://neondb_owner:npg_4PzpC8lXGebh@ep-jolly-frost-atdxycc8.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require"

# إنشاء الاتصال بالسيرفر السحابي
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# 2. تصميم جدول "القطفات"
# ==========================================
class DBRecord(Base):
    __tablename__ = "records"

    id = Column(Integer, primary_key=True, index=True)
    section = Column(String, index=True)
    date = Column(String)
    day = Column(String)
    product = Column(String)
    qty = Column(Float)
    unit = Column(String)
    price = Column(Float, nullable=True)
    total = Column(Float)
    buyer = Column(String)
    accounted = Column(String)
    notes = Column(String, nullable=True)

# إنشاء الجداول في قاعدة البيانات السحابية
Base.metadata.create_all(bind=engine)

# ==========================================
# 3. مخطط البيانات (Pydantic)
# ==========================================
class RecordCreate(BaseModel):
    section: str
    date: str
    day: str
    product: str
    qty: float
    unit: str
    price: Optional[float] = None
    buyer: str
    accounted: str
    notes: Optional[str] = ""

class RecordResponse(RecordCreate):
    id: int
    total: float

    class Config:
        from_attributes = True

# ==========================================
# 4. بناء السيرفر (API)
# ==========================================
app = FastAPI(title="Harvex API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "مرحباً بك في سيرفر Harvex السحابي!"}

@app.post("/records/", response_model=RecordResponse)
def create_record(record: RecordCreate, db: Session = Depends(get_db)):
    calc_total = (record.qty * record.price) if record.price else 0.0

    new_record = DBRecord(
        section=record.section,
        date=record.date,
        day=record.day,
        product=record.product,
        qty=record.qty,
        unit=record.unit,
        price=record.price,
        total=calc_total,
        buyer=record.buyer,
        accounted=record.accounted,
        notes=record.notes
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record

@app.get("/records/", response_model=list[RecordResponse])
def get_all_records(db: Session = Depends(get_db)):
    records = db.query(DBRecord).order_by(DBRecord.id.desc()).all()
    return records