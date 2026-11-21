"""Servidor equivalente en Flask + SQLAlchemy 2.0
para comparacion justa en E1 (Echo), E2 (CRUD + JOINs) y E4 (SLOC/Mantenibilidad).

Arranque recomendado (Linux/Oracle Cloud):
  gunicorn -w 1 --threads 4 -b 0.0.0.0:4203 benchmarks.bench_flask:app
Arranque recomendado (Windows):
  waitress-serve --host=0.0.0.0 --port=4203 --threads=4 benchmarks.bench_flask:app
"""

import datetime
import os
from flask import Flask, jsonify, request
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
    delete,
    insert,
    select,
    update,
)

DB_URL = os.getenv("DB_URL", "sqlite:///benchmarks_crud.db")
connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
engine = create_engine(DB_URL, echo=False, connect_args=connect_args)
metadata = MetaData()

categories = Table(
    "categories",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100), nullable=False),
    Column("description", Text),
)
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("full_name", String(120), nullable=False),
    Column("email", String(150), nullable=False),
    Column("created_at", DateTime),
)
orders = Table(
    "orders",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("category_id", Integer, ForeignKey("categories.id"), nullable=False),
    Column("total_amount", Float, nullable=False),
    Column("status", String(30), nullable=False),
    Column("created_at", DateTime),
)

app = Flask(__name__)


# --- Escenario E1: Echo ---
@app.get("/echo/get")
def echo_get():
    return jsonify({"value": request.args.get("value", "hello")})


@app.post("/echo/post")
def echo_post():
    return jsonify(request.get_json(silent=True) or {"status": "ok"})


@app.put("/echo/put")
def echo_put():
    return jsonify({"value": request.args.get("value", "updated")})


@app.delete("/echo/delete")
def echo_delete():
    return jsonify({"value": request.args.get("value", "deleted")})


@app.patch("/echo/patch")
def echo_patch():
    return jsonify({"value": request.args.get("value", "patched")})


# --- Escenario E2: CRUD + JOIN (expansion FK) ---
@app.get("/api/orders/get")
def get_order():
    oid = request.args.get("id", type=int)
    stmt = (
        select(
            orders.c.id,
            orders.c.total_amount,
            orders.c.status,
            orders.c.created_at,
            users.c.id.label("user_id"),
            users.c.full_name,
            users.c.email,
            categories.c.id.label("category_id"),
            categories.c.name.label("category_name"),
        )
        .select_from(orders.join(users, orders.c.user_id == users.c.id).join(categories, orders.c.category_id == categories.c.id))
        .where(orders.c.id == oid)
    )
    with engine.connect() as conn:
        row = conn.execute(stmt).mappings().first()
    if not row:
        return jsonify({"detail": "Order not found"}), 404
    return jsonify(
        {
            "id": row["id"],
            "total_amount": row["total_amount"],
            "status": row["status"],
            "created_at": str(row["created_at"]),
            "user": {"id": row["user_id"], "full_name": row["full_name"], "email": row["email"]},
            "category": {"id": row["category_id"], "name": row["category_name"]},
        }
    )


@app.post("/api/orders/post")
def create_order():
    data = request.get_json(force=True)
    with engine.begin() as conn:
        res = conn.execute(
            insert(orders).values(
                user_id=data["user_id"],
                category_id=data["category_id"],
                total_amount=data["total_amount"],
                status=data.get("status", "confirmed"),
                created_at=datetime.datetime.utcnow(),
            )
        )
        new_id = res.inserted_primary_key[0]
    return jsonify({"id": new_id, "status": data.get("status", "confirmed")})


@app.put("/api/orders/put")
def update_order():
    oid = request.args.get("id", type=int)
    data = request.get_json(force=True)
    with engine.begin() as conn:
        conn.execute(
            update(orders)
            .where(orders.c.id == oid)
            .values(
                user_id=data["user_id"],
                category_id=data["category_id"],
                total_amount=data["total_amount"],
                status=data.get("status", "confirmed"),
            )
        )
    return jsonify({"id": oid, "updated": True})


@app.patch("/api/orders/patch")
def patch_order():
    oid = request.args.get("id", type=int)
    data = request.get_json(force=True)
    vals = {k: v for k, v in data.items() if k in ("total_amount", "status")}
    if vals:
        with engine.begin() as conn:
            conn.execute(update(orders).where(orders.c.id == oid).values(**vals))
    return jsonify({"id": oid, "patched": True})


@app.delete("/api/orders/delete")
def delete_order():
    oid = request.args.get("id", type=int)
    with engine.begin() as conn:
        conn.execute(delete(orders).where(orders.c.id == oid))
    return jsonify({"id": oid, "deleted": True})
