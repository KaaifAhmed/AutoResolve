# database.py
from sqlalchemy import create_engine, Column, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timedelta

DB_FILE = "ecommerce.db"
engine = create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Minimal Declarative Mapping so SQLAlchemy understands your existing database structure
class Customer(Base):
    __tablename__ = "customers"
    id = Column(String, primary_key=True)
    name = Column(String)
    email = Column(String)

class Order(Base):
    __tablename__ = "orders"
    id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey("customers.id"))
    status = Column(String)
    amount = Column(Float)
    created_at = Column(DateTime)
    item_summary = Column(String)

# Context manager helper to ensure database sessions open and close safely
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def reset_mock_database():
    """Drops the database and rebuilds the default mock data."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    now = datetime.utcnow()
    customers = [
        Customer(id="cust_001", name="Kaaif Ahmed", email="kaaif@example.com"),
        Customer(id="cust_002", name="Alex Mercer", email="alex@example.com"),
        Customer(id="cust_003", name="Sara Khan", email="sara@example.com")
    ]
    orders = [
        Order(id="#10001", customer_id="cust_001", status="processing", amount=120.50, created_at=now - timedelta(days=1), item_summary="Wireless Mechanical Keyboard"),
        Order(id="#10002", customer_id="cust_001", status="processing", amount=45.00, created_at=now - timedelta(days=2), item_summary="Ergonomic Vertical Mouse"),
        Order(id="#10003", customer_id="cust_001", status="shipped", amount=15.00, created_at=now - timedelta(days=3), item_summary="Ultra Wide Mousepad"),

        # Customer 2 (Alex) - Shipped order, candidate for refund testing
        Order(id="#20001", customer_id="cust_002", status="shipped", amount=350.00, created_at=now - timedelta(days=5), item_summary="27-inch 144Hz Gaming Monitor"),
        Order(id="#20002", customer_id="cust_002", status="processing", amount=25.99, created_at=now - timedelta(days=2), item_summary="HDMI 2.1 Braided Cable"),

        # Customer 3 (Sara) - Old processing order (simulating an edge case)
        Order(id="#30001", customer_id="cust_003", status="processing", amount=89.99, created_at=now - timedelta(days=1), item_summary="Noise Cancelling Earbuds")
    ]
    db.add_all(customers)
    db.add_all(orders)
    db.commit()
    db.close()

"""

# Customer 1 (Kaaif) - Active and Past Orders
Order(id="#10001", customer_id="cust_001", status="processing", amount=120.50, created_at=two_hours_ago, item_summary="Wireless Mechanical Keyboard"),
Order(id="#10002", customer_id="cust_001", status="shipped", amount=45.00, created_at=three_days_ago, item_summary="Ergonomic Vertical Mouse"),
Order(id="#10003", customer_id="cust_001", status="cancelled", amount=15.00, created_at=five_days_ago, item_summary="Ultra Wide Mousepad"),

# Customer 2 (Alex) - Shipped order, candidate for refund testing
Order(id="#20001", customer_id="cust_002", status="shipped", amount=350.00, created_at=three_days_ago, item_summary="27-inch 144Hz Gaming Monitor"),
Order(id="#20002", customer_id="cust_002", status="processing", amount=25.99, created_at=two_hours_ago, item_summary="HDMI 2.1 Braided Cable"),

# Customer 3 (Sara) - Old processing order (simulating an edge case)
Order(id="#30001", customer_id="cust_003", status="processing", amount=89.99, created_at=three_days_ago, item_summary="Noise Cancelling Earbuds")
"""