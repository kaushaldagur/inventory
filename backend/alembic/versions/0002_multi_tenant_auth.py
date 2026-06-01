"""multi-tenant auth

Revision ID: 0002_multi_tenant_auth
Revises: 0001_initial
Create Date: 2026-06-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0002_multi_tenant_auth"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _table_exists(insp, name: str) -> bool:
    return name in insp.get_table_names()


def _column_exists(insp, table: str, column: str) -> bool:
    return column in {col["name"] for col in insp.get_columns(table)}


def _constraint_exists(insp, table: str, name: str) -> bool:
    return name in {c["name"] for c in insp.get_unique_constraints(table)}


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    if not _table_exists(insp, "users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("full_name", sa.String(length=160), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("password_hash", sa.String(length=128), nullable=False),
            sa.Column("password_salt", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("email"),
        )
        op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
        op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    if not _column_exists(insp, "products", "owner_id"):
        op.add_column("products", sa.Column("owner_id", sa.Integer(), nullable=True))
    if not _column_exists(insp, "customers", "owner_id"):
        op.add_column("customers", sa.Column("owner_id", sa.Integer(), nullable=True))
    if not _column_exists(insp, "orders", "owner_id"):
        op.add_column("orders", sa.Column("owner_id", sa.Integer(), nullable=True))

    insp = inspect(bind)

    if _constraint_exists(insp, "products", "products_sku_key"):
        op.drop_constraint("products_sku_key", "products", type_="unique")
    if _constraint_exists(insp, "customers", "customers_email_key"):
        op.drop_constraint("customers_email_key", "customers", type_="unique")

    for index_name, table in [("ix_products_sku", "products"), ("ix_customers_email", "customers")]:
        indexes = {idx["name"] for idx in insp.get_indexes(table)}
        if index_name in indexes:
            op.drop_index(index_name, table_name=table)

    insp = inspect(bind)
    fks = {fk["name"] for fk in insp.get_foreign_keys("products")}
    if "fk_products_owner_id" not in fks:
        op.create_foreign_key("fk_products_owner_id", "products", "users", ["owner_id"], ["id"], ondelete="CASCADE")
    fks = {fk["name"] for fk in insp.get_foreign_keys("customers")}
    if "fk_customers_owner_id" not in fks:
        op.create_foreign_key("fk_customers_owner_id", "customers", "users", ["owner_id"], ["id"], ondelete="CASCADE")
    fks = {fk["name"] for fk in insp.get_foreign_keys("orders")}
    if "fk_orders_owner_id" not in fks:
        op.create_foreign_key("fk_orders_owner_id", "orders", "users", ["owner_id"], ["id"], ondelete="CASCADE")

    insp = inspect(bind)
    if not _constraint_exists(insp, "products", "uq_products_owner_sku"):
        op.create_unique_constraint("uq_products_owner_sku", "products", ["owner_id", "sku"])
    if not _constraint_exists(insp, "customers", "uq_customers_owner_email"):
        op.create_unique_constraint("uq_customers_owner_email", "customers", ["owner_id", "email"])

  # Clear orphan rows without owner before NOT NULL
    op.execute("DELETE FROM order_items")
    op.execute("DELETE FROM orders")
    op.execute("DELETE FROM customers")
    op.execute("DELETE FROM products")

    op.alter_column("products", "owner_id", nullable=False)
    op.alter_column("customers", "owner_id", nullable=False)
    op.alter_column("orders", "owner_id", nullable=False)


def downgrade():
    op.alter_column("orders", "owner_id", nullable=True)
    op.alter_column("customers", "owner_id", nullable=True)
    op.alter_column("products", "owner_id", nullable=True)

    op.drop_constraint("uq_customers_owner_email", "customers", type_="unique")
    op.drop_constraint("uq_products_owner_sku", "products", type_="unique")
    op.drop_constraint("fk_orders_owner_id", "orders", type_="foreignkey")
    op.drop_constraint("fk_customers_owner_id", "customers", type_="foreignkey")
    op.drop_constraint("fk_products_owner_id", "products", type_="foreignkey")

    op.drop_column("orders", "owner_id")
    op.drop_column("customers", "owner_id")
    op.drop_column("products", "owner_id")

    op.create_unique_constraint("customers_email_key", "customers", ["email"])
    op.create_unique_constraint("products_sku_key", "products", ["sku"])

    op.drop_table("users")
