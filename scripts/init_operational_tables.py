"""创建 NL2SQL 演示运营表并写入可重复执行的少量数据。"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.db.database import engine


_TABLE_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY,
        name VARCHAR(200) NOT NULL,
        category_id INTEGER NOT NULL REFERENCES categories(id),
        price NUMERIC(12, 2) NOT NULL,
        stock INTEGER NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        gender VARCHAR(20),
        age INTEGER,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY,
        customer_id INTEGER NOT NULL REFERENCES customers(id),
        total_amount NUMERIC(12, 2) NOT NULL,
        status VARCHAR(30) NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY,
        order_id INTEGER NOT NULL REFERENCES orders(id),
        product_id INTEGER NOT NULL REFERENCES products(id),
        quantity INTEGER NOT NULL,
        price NUMERIC(12, 2) NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_products_category_id ON products(category_id)",
    "CREATE INDEX IF NOT EXISTS ix_orders_customer_id ON orders(customer_id)",
    "CREATE INDEX IF NOT EXISTS ix_order_items_order_id ON order_items(order_id)",
)

_DEMO_ROWS: tuple[tuple[str, dict[str, object]], ...] = (
    (
        "INSERT INTO categories (id, name) VALUES (:id, :name) ON CONFLICT (id) DO NOTHING",
        {"id": 1, "name": "演示分类"},
    ),
    (
        "INSERT INTO products (id, name, category_id, price, stock) VALUES (:id, :name, :category_id, :price, :stock) ON CONFLICT (id) DO NOTHING",
        {"id": 1, "name": "演示商品A", "category_id": 1, "price": 99, "stock": 20},
    ),
    (
        "INSERT INTO products (id, name, category_id, price, stock) VALUES (:id, :name, :category_id, :price, :stock) ON CONFLICT (id) DO NOTHING",
        {"id": 2, "name": "演示商品B", "category_id": 1, "price": 199, "stock": 10},
    ),
    (
        "INSERT INTO customers (id, name, gender, age) VALUES (:id, :name, :gender, :age) ON CONFLICT (id) DO NOTHING",
        {"id": 1, "name": "演示客户", "gender": "未知", "age": 30},
    ),
    (
        "INSERT INTO orders (id, customer_id, total_amount, status) VALUES (:id, :customer_id, :total_amount, :status) ON CONFLICT (id) DO NOTHING",
        {"id": 1, "customer_id": 1, "total_amount": 99, "status": "completed"},
    ),
    (
        "INSERT INTO order_items (id, order_id, product_id, quantity, price) VALUES (:id, :order_id, :product_id, :quantity, :price) ON CONFLICT (id) DO NOTHING",
        {"id": 1, "order_id": 1, "product_id": 1, "quantity": 1, "price": 99},
    ),
)


def initialize_operational_tables(connection: Connection) -> None:
    """创建运营演示表和数据；重复运行不会删除或重复插入已有记录。"""
    _execute_statements(connection, _TABLE_STATEMENTS)
    for statement, params in _DEMO_ROWS:
        connection.execute(text(statement), params)


def _execute_statements(connection: Connection, statements: Iterable[str]) -> None:
    """按顺序执行建表和索引语句。"""
    for statement in statements:
        connection.execute(text(statement))


def main() -> None:
    """在项目 DATABASE_URL 指向的数据库中初始化演示运营数据。"""
    with engine.begin() as connection:
        initialize_operational_tables(connection)
    print("运营演示表和数据初始化完成。")


if __name__ == "__main__":
    main()
