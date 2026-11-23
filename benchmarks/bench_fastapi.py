"""Servidor equivalente en FastAPI + SQLAlchemy 2.0 + Pydantic v2
para comparacion justa en E1 (Echo), E2 (CRUD + JOINs) y E4 (SLOC/Mantenibilidad).

Arranque recomendado (paridad 1 worker):
  uvicorn benchmarks.bench_fastapi:app --host 0.0.0.0 --port 4202 --workers 1 --no-access-log
"""

import datetime
import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
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

app = FastAPI(title="FastAPI Benchmark Equivalent")


@app.on_event("startup")
def configure_threads():
    try:
        import anyio.to_thread
        threads = int(os.getenv("FASTAPI_THREADS", "4"))
        limiter = anyio.to_thread.current_default_thread_limiter()
        limiter.total_tokens = threads
        print(f"[FastAPI PID={os.getpid()}] AnyIO threadpool estrictamente limitado a {limiter.total_tokens} tokens (hilos).")
    except Exception as e:
        print(f"[FastAPI] Advertencia al configurar limiter de AnyIO: {e}")


class OrderIn(BaseModel):
    user_id: int
    category_id: int
    total_amount: float
    status: str = "confirmed"


class OrderPatch(BaseModel):
    total_amount: Optional[float] = None
    status: Optional[str] = None


# --- Escenario E1: Echo ---
@app.get("/echo/get")
def echo_get(value: str = "hello"):
    return {"value": value}


@app.post("/echo/post")
def echo_post(payload: Dict[str, Any]):
    return payload


@app.put("/echo/put")
def echo_put(value: str = "updated"):
    return {"value": value}


@app.delete("/echo/delete")
def echo_delete(value: str = "deleted"):
    return {"value": value}


@app.patch("/echo/patch")
def echo_patch(value: str = "patched"):
    return {"value": value}


# --- Escenario E2: CRUD + JOIN (expansion FK) ---
@app.get("/api/orders/get")
def get_order(id: int):
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
        .where(orders.c.id == id)
    )
    with engine.connect() as conn:
        row = conn.execute(stmt).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "id": row["id"],
        "total_amount": row["total_amount"],
        "status": row["status"],
        "created_at": str(row["created_at"]),
        "user": {"id": row["user_id"], "full_name": row["full_name"], "email": row["email"]},
        "category": {"id": row["category_id"], "name": row["category_name"]},
    }


@app.post("/api/orders/post")
def create_order(order: OrderIn):
    with engine.begin() as conn:
        res = conn.execute(
            insert(orders).values(
                user_id=order.user_id,
                category_id=order.category_id,
                total_amount=order.total_amount,
                status=order.status,
                created_at=datetime.datetime.utcnow(),
            )
        )
        new_id = res.inserted_primary_key[0]
    return {"id": new_id, "status": order.status}


@app.put("/api/orders/put")
def update_order(id: int, order: OrderIn):
    with engine.begin() as conn:
        conn.execute(
            update(orders)
            .where(orders.c.id == id)
            .values(
                user_id=order.user_id,
                category_id=order.category_id,
                total_amount=order.total_amount,
                status=order.status,
            )
        )
    return {"id": id, "updated": True}


@app.patch("/api/orders/patch")
def patch_order(id: int, patch: OrderPatch):
    vals = {k: v for k, v in patch.model_dump().items() if v is not None}
    if vals:
        with engine.begin() as conn:
            conn.execute(update(orders).where(orders.c.id == id).values(**vals))
    return {"id": id, "patched": True}


@app.delete("/api/orders/delete")
def delete_order(id: int):
    with engine.begin() as conn:
        conn.execute(delete(orders).where(orders.c.id == id))
    return {"id": id, "deleted": True}
