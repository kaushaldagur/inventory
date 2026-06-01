from decimal import Decimal
import os

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from . import models, schemas
from .database import Base, engine, get_db
from .deps import get_current_user
from .security import create_access_token, verify_password


app = FastAPI(title="Inventory & Order Management API", version="1.0.0")

if os.getenv("ENV", "development") != "production":
    Base.metadata.create_all(bind=engine)

frontend_origin = os.getenv("FRONTEND_ORIGIN")
default_origins = ["http://localhost:3000", "http://localhost:5173"]
extra_origins = [origin.strip() for origin in os.getenv("EXTRA_CORS_ORIGINS", "").split(",") if origin.strip()]
allowed_origins = list(dict.fromkeys([*default_origins, *extra_origins, *([frontend_origin] if frontend_origin else [])]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Inventory API", "health": "/health", "docs": "/docs"}


def not_found(resource: str):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{resource} not found")


def get_owned_product(db: Session, owner_id: int, product_id: int) -> models.Product | None:
    return (
        db.query(models.Product)
        .filter(models.Product.id == product_id, models.Product.owner_id == owner_id)
        .first()
    )


def get_owned_customer(db: Session, owner_id: int, customer_id: int) -> models.Customer | None:
    return (
        db.query(models.Customer)
        .filter(models.Customer.id == customer_id, models.Customer.owner_id == owner_id)
        .first()
    )


def get_owned_order(db: Session, owner_id: int, order_id: int) -> models.Order | None:
    return (
        db.query(models.Order)
        .options(joinedload(models.Order.customer), joinedload(models.Order.items).joinedload(models.OrderItem.product))
        .filter(models.Order.id == order_id, models.Order.owner_id == owner_id)
        .first()
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/login", response_model=schemas.AuthResponse)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_salt, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return schemas.AuthResponse(access_token=create_access_token(user.id), user=user)


@app.get("/auth/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.post("/products", response_model=schemas.ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: schemas.ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    product = models.Product(owner_id=current_user.id, **payload.model_dump())
    db.add(product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product SKU already exists")
    db.refresh(product)
    return product


@app.get("/products", response_model=list[schemas.ProductOut])
def list_products(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return (
        db.query(models.Product)
        .filter(models.Product.owner_id == current_user.id)
        .order_by(models.Product.id.desc())
        .all()
    )


@app.get("/products/{product_id}", response_model=schemas.ProductOut)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    product = get_owned_product(db, current_user.id, product_id)
    if not product:
        not_found("Product")
    return product


@app.put("/products/{product_id}", response_model=schemas.ProductOut)
def update_product(
    product_id: int,
    payload: schemas.ProductUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    product = get_owned_product(db, current_user.id, product_id)
    if not product:
        not_found("Product")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product SKU already exists")
    db.refresh(product)
    return product


@app.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    product = get_owned_product(db, current_user.id, product_id)
    if not product:
        not_found("Product")
    db.delete(product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product cannot be deleted while it is referenced by an order",
        )
    return None


@app.post("/customers", response_model=schemas.CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: schemas.CustomerCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    customer = models.Customer(owner_id=current_user.id, **payload.model_dump())
    db.add(customer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Customer email already exists")
    db.refresh(customer)
    return customer


@app.get("/customers", response_model=list[schemas.CustomerOut])
def list_customers(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return (
        db.query(models.Customer)
        .filter(models.Customer.owner_id == current_user.id)
        .order_by(models.Customer.id.desc())
        .all()
    )


@app.get("/customers/{customer_id}", response_model=schemas.CustomerOut)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    customer = get_owned_customer(db, current_user.id, customer_id)
    if not customer:
        not_found("Customer")
    return customer


@app.delete("/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    customer = get_owned_customer(db, current_user.id, customer_id)
    if not customer:
        not_found("Customer")
    db.delete(customer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer cannot be deleted while they have orders",
        )
    return None


@app.post("/orders", response_model=schemas.OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    customer = get_owned_customer(db, current_user.id, payload.customer_id)
    if not customer:
        not_found("Customer")

    product_quantities: dict[int, int] = {}
    for item in payload.items:
        product_quantities[item.product_id] = product_quantities.get(item.product_id, 0) + item.quantity

    products = (
        db.query(models.Product)
        .filter(
            models.Product.owner_id == current_user.id,
            models.Product.id.in_(product_quantities.keys()),
        )
        .with_for_update()
        .all()
    )
    products_by_id = {product.id: product for product in products}

    missing_ids = set(product_quantities) - set(products_by_id)
    if missing_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Products not found: {sorted(missing_ids)}")

    for product_id, quantity in product_quantities.items():
        product = products_by_id[product_id]
        if product.quantity_in_stock < quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Insufficient inventory for SKU {product.sku}",
            )

    total_amount = Decimal("0.00")
    order = models.Order(owner_id=current_user.id, customer_id=payload.customer_id, total_amount=total_amount)
    db.add(order)
    db.flush()

    for product_id, quantity in product_quantities.items():
        product = products_by_id[product_id]
        line_total = product.price * quantity
        total_amount += line_total
        product.quantity_in_stock -= quantity
        db.add(
            models.OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=product.price,
                line_total=line_total,
            )
        )

    order.total_amount = total_amount
    db.commit()
    order = get_owned_order(db, current_user.id, order.id)
    assert order is not None
    return order


@app.get("/orders", response_model=list[schemas.OrderOut])
def list_orders(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return (
        db.query(models.Order)
        .options(joinedload(models.Order.customer), joinedload(models.Order.items).joinedload(models.OrderItem.product))
        .filter(models.Order.owner_id == current_user.id)
        .order_by(models.Order.id.desc())
        .all()
    )


@app.get("/orders/{order_id}", response_model=schemas.OrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    order = get_owned_order(db, current_user.id, order_id)
    if not order:
        not_found("Order")
    return order


@app.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    order = (
        db.query(models.Order)
        .options(joinedload(models.Order.items))
        .filter(models.Order.id == order_id, models.Order.owner_id == current_user.id)
        .first()
    )
    if not order:
        not_found("Order")

    product_ids = [item.product_id for item in order.items]
    products = (
        db.query(models.Product)
        .filter(models.Product.owner_id == current_user.id, models.Product.id.in_(product_ids))
        .with_for_update()
        .all()
    )
    products_by_id = {product.id: product for product in products}
    for item in order.items:
        product = products_by_id.get(item.product_id)
        if product:
            product.quantity_in_stock += item.quantity

    db.delete(order)
    db.commit()
    return None


@app.get("/dashboard", response_model=schemas.DashboardSummary)
def dashboard(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    owner_id = current_user.id
    return schemas.DashboardSummary(
        total_products=db.query(models.Product).filter(models.Product.owner_id == owner_id).count(),
        total_customers=db.query(models.Customer).filter(models.Customer.owner_id == owner_id).count(),
        total_orders=db.query(models.Order).filter(models.Order.owner_id == owner_id).count(),
        low_stock_products=db.query(models.Product)
        .filter(models.Product.owner_id == owner_id, models.Product.quantity_in_stock <= 5)
        .count(),
    )
