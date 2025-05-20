from sqlalchemy.orm import Session
from src.models.core import Sale, SaleStatus
from src.database.connection import SessionLocal
db = SessionLocal()


new_sale = Sale(
    listing_id=1,
    buyer_id=1,
    seller_id=2,
    item_id=1,
    price=100.0,
    status=SaleStatus.PENDING  # ORM сам возьмёт .value
)
print("Enum repr:", repr(new_sale.status))
print("Enum type:", type(new_sale.status))

db.add(new_sale)
db.commit()
