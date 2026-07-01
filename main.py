from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pydantic import BaseModel
from typing import Optional, List

# ==========================================
# 1. إعداد الاتصال بقاعدة البيانات السحابية (Neon)
# ==========================================
SQLALCHEMY_DATABASE_URL = "postgresql://neondb_owner:npg_4PzpC8lXGebh@ep-jolly-frost-atdxycc8.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# 2. تصميم الجداول (القطفات + السلف والخصومات)
# ==========================================

# جدول القطفات
class DBRecord(Base):
    __tablename__ = "records"
    id = Column(Integer, primary_key=True, index=True)
    section = Column(String, index=True)  # motez / waleed
    date = Column(String)
    day = Column(String)
    product = Column(String)
    qty = Column(Float)
    unit = Column(String)
    price = Column(Float, nullable=True)
    total = Column(Float)
    buyer = Column(String)
    accounted = Column(String) # "محاسب" / "باقي"
    notes = Column(String, nullable=True)

# جدول السلف والخصومات
class DBAdvance(Base):
    __tablename__ = "advances"
    id = Column(Integer, primary_key=True, index=True)
    section = Column(String, index=True) # الاسم أو القسم (وليد مثلاً)
    product = Column(String) # المحصول المرتبط بالسلفة
    date = Column(String)
    amount = Column(Float)
    reason = Column(String)
    notes = Column(String, nullable=True)

# إنشاء الجداول في السيرفر
Base.metadata.create_all(bind=engine)

# ==========================================
# 3. مخططات البيانات (Pydantic schemas)
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

class AdvanceCreate(BaseModel):
    section: str
    product: str
    date: str
    amount: float
    reason: str
    notes: Optional[str] = ""

class AdvanceResponse(AdvanceCreate):
    id: int
    class Config:
        from_attributes = True

# مخطط حسابات الشركاء (معتز ووليد)
class FinancialSummary(BaseModel):
    total_sales: float
    motez_own_sales: float
    waleed_section_sales: float
    waleed_share_raw: float  # حصة وليد 33.33% قبل السلف
    motez_share_from_waleed: float # حصة معتز 66.67% من قسم وليد
    motez_total_gross: float # إجمالي مستحق معتز
    total_advances: float # سلف وليد
    waleed_net: float # صافي وليد النهائي بعد خصم السلف
    motez_net: float # صافي معتز النهائي بعد خصم المصاريف (إن وجدت)

# ==========================================
# 4. بناء السيرفر والروابط
# ==========================================
app = FastAPI(title="Harvex Ultimate API")

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
    return {"message": "سيرفر Harvex المتكامل يعمل بنجاح!"}

# --- روابط القطفات (Records) ---

@app.post("/records/", response_model=RecordResponse)
def create_record(record: RecordCreate, db: Session = Depends(get_db)):
    calc_total = (record.qty * record.price) if record.price else 0.0
    new_record = DBRecord(
        section=record.section, date=record.date, day=record.day,
        product=record.product, qty=record.qty, unit=record.unit,
        price=record.price, total=calc_total, buyer=record.buyer,
        accounted=record.accounted, notes=record.notes
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record

@app.get("/records/", response_model=List[RecordResponse])
def get_records(db: Session = Depends(get_db)):
    return db.query(DBRecord).order_by(DBRecord.id.desc()).all()

@app.delete("/records/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db)):
    rec = db.query(DBRecord).filter(DBRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="السجل غير موجود")
    db.delete(rec)
    db.commit()
    return {"status": "success", "message": "تم حذف السجل"}

# --- روابط السلف والخصومات (Advances) ---

@app.post("/advances/", response_model=AdvanceResponse)
def create_advance(advance: AdvanceCreate, db: Session = Depends(get_db)):
    new_adv = DBAdvance(
        section=advance.section, product=advance.product, date=advance.date,
        amount=advance.amount, reason=advance.reason, notes=advance.notes
    )
    db.add(new_adv)
    db.commit()
    db.refresh(new_adv)
    return new_adv

@app.get("/advances/", response_model=List[AdvanceResponse])
def get_advances(db: Session = Depends(get_db)):
    return db.query(DBAdvance).order_by(DBAdvance.id.desc()).all()

@app.delete("/advances/{advance_id}")
def delete_advance(advance_id: int, db: Session = Depends(get_db)):
    adv = db.query(DBAdvance).filter(DBAdvance.id == advance_id).first()
    if not adv:
        raise HTTPException(status_code=404, detail="السلفة غير موجودة")
    db.delete(adv)
    db.commit()
    return {"status": "success", "message": "تم حذف السلفة"}

# --- رابط التقارير الحسابية الذكي (مطابق تماماً لمنطق بايثون القديم) ---

@app.get("/financial-summary/", response_model=FinancialSummary)
def get_financial_summary(db: Session = Depends(get_db)):
    records = db.query(DBRecord).all()
    advances = db.query(DBAdvance).all()

    # حساب مبيعات معتز الخاصة وقسم وليد
    motez_own = sum((r.total for r in records if r.section == "motez"), 0.0)
    waleed_section = sum((r.total for r in records if r.section == "waleed"), 0.0)
    
    total_sales = motez_own + waleed_section

    # تطبيق منطق النسب (وليد الثلث 1/3 ومعتز الثلثين 2/3)
    waleed_share = waleed_section * (1/3)
    motez_share_from_waleed = waleed_section * (2/3)
    
    motez_gross = motez_own + motez_share_from_waleed
    
    # حساب إجمالي السلف
    total_adv = sum((a.amount for a in advances), 0.0)

    # الصافي النهائي
    waleed_net = waleed_share - total_adv
    motez_net = motez_gross # يمكن خصم المصاريف العامة هنا مستقبلاً

    return {
        "total_sales": total_sales,
        "motez_own_sales": motez_own,
        "waleed_section_sales": waleed_section,
        "waleed_share_raw": waleed_share,
        "motez_share_from_waleed": motez_share_from_waleed,
        "motez_total_gross": motez_gross,
        "total_advances": total_adv,
        "waleed_net": waleed_net,
        "motez_net": motez_net
    }
