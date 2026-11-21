"""Crea y puebla el esquema relacional de 3 tablas (categories, users, orders)
para el Escenario E2 (CRUD real con SQL y llaves foraneas).

Uso:
  python schema_seed.py --db-url sqlite:///benchmarks_crud.db
  python schema_seed.py --db-url mysql+pymysql://user:pass@localhost:3306/bench_apy
  python schema_seed.py --db-url postgresql+psycopg2://user:pass@localhost:5432/bench_apy
"""

import argparse
import datetime
import random
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    text,
)


def seed_database(db_url: str, n_categories: int = 50, n_users: int = 1000, n_orders: int = 10000):
    engine = create_engine(db_url, echo=False)
    metadata = MetaData()

    categories = Table(
        "categories",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("name", String(100), nullable=False),
        Column("description", Text, nullable=True),
    )

    users = Table(
        "users",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("full_name", String(120), nullable=False),
        Column("email", String(150), nullable=False, unique=True),
        Column("created_at", DateTime, default=datetime.datetime.utcnow),
    )

    orders = Table(
        "orders",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
        Column("category_id", Integer, ForeignKey("categories.id"), nullable=False),
        Column("total_amount", Float, nullable=False),
        Column("status", String(30), nullable=False),
        Column("created_at", DateTime, default=datetime.datetime.utcnow),
    )

    metadata.drop_all(engine)
    metadata.create_all(engine)

    rng = random.Random(42)
    now = datetime.datetime(2026, 1, 1, 12, 0, 0)
    statuses = ["pending", "confirmed", "shipped", "delivered"]

    with engine.begin() as conn:
        conn.execute(
            categories.insert(),
            [
                {"name": f"Category {i}", "description": f"Benchmark category description #{i}"}
                for i in range(1, n_categories + 1)
            ],
        )
        conn.execute(
            users.insert(),
            [
                {
                    "full_name": f"User {i}",
                    "email": f"user{i}@example.org",
                    "created_at": now + datetime.timedelta(minutes=i),
                }
                for i in range(1, n_users + 1)
            ],
        )
        batch = []
        for i in range(1, n_orders + 1):
            batch.append(
                {
                    "user_id": rng.randint(1, n_users),
                    "category_id": rng.randint(1, n_categories),
                    "total_amount": round(rng.uniform(10.0, 999.99), 2),
                    "status": rng.choice(statuses),
                    "created_at": now + datetime.timedelta(seconds=i * 30),
                }
            )
            if len(batch) == 2000:
                conn.execute(orders.insert(), batch)
                batch.clear()
        if batch:
            conn.execute(orders.insert(), batch)

        count_orders = conn.execute(text("SELECT COUNT(*) FROM orders")).scalar()
        print(f"[OK] Base de datos lista ({db_url}): {n_categories} categories, {n_users} users, {count_orders} orders.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default="sqlite:///benchmarks_crud.db")
    parser.add_argument("--orders", type=int, default=10000)
    args = parser.parse_args()
    seed_database(args.db_url, n_orders=args.orders)
