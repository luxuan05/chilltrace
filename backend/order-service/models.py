from database import db


class Orders(db.Model):
    __tablename__ = "Orders"

    ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    CustomerID = db.Column(db.Integer, nullable=False)
    SupplierId = db.Column(db.Integer, nullable=False)
    OrderStatus = db.Column(db.String(50), nullable=False, default="PENDING")
    TotalPrice = db.Column(db.Float, nullable=False, default=0.0)
    ScheduledDate = db.Column(db.Date, nullable=True)

    order_items = db.relationship(
        "OrderItem",
        backref="order",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "ID": self.ID,
            "CustomerID": self.CustomerID,
            "SupplierId": self.SupplierId,
            "OrderStatus": self.OrderStatus,
            "TotalPrice": self.TotalPrice,
            "ScheduledDate": self.ScheduledDate.isoformat() if self.ScheduledDate else None,
            "OrderItems": [item.to_dict() for item in self.order_items]
        }


class OrderItem(db.Model):
    __tablename__ = "OrderItem"

    ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrderID = db.Column(db.Integer, db.ForeignKey("Orders.ID"), nullable=False)
    ItemID = db.Column(db.Integer, nullable=False)
    Quantity = db.Column(db.Integer, nullable=False)
    UnitPrice = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            "ID": self.ID,
            "OrderID": self.OrderID,
            "ItemID": self.ItemID,
            "Quantity": self.Quantity,
            "UnitPrice": self.UnitPrice
        }