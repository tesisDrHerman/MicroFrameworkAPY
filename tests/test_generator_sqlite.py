import unittest
import sys
import os
import sqlalchemy
from sqlalchemy import Table, Column, Integer, String, MetaData, create_engine, select, insert

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "venv", "Lib", "site-packages")))

from sqltypes import sqltypes, mapped_sqltypes
from generator import Database, get_db_folder


class TestGeneratorAndSQLTypes(unittest.TestCase):
    """Pruebas para tipos SQL, mapeos y reflexion con base de datos de prueba."""

    def test_database_sqlite_native_support(self):
        """Verifica que la clase Database soporte SQLite y SQLite en memoria sin echo bloqueante."""
        db = Database(database=":memory:", db_type="sqlite", echo=False)
        self.assertIsNotNone(db.engine(), "Fallo al inicializar engine SQLite nativo")
        with db.connection() as conn:
            res = conn.execute(sqlalchemy.text("SELECT 100")).scalar()
            self.assertEqual(res, 100)

    def test_get_db_folder_sanitization(self):
        """Verifica que get_db_folder genere nombres de directorio validos sin caracteres ilegales."""
        engine = create_engine("sqlite:///:memory:")
        folder = get_db_folder(engine)
        self.assertNotIn(":", folder, "El nombre de carpeta contiene dos puntos ilegales en Windows")
        self.assertIn("memory", folder)
        self.assertIn("sqlite", folder)

    def test_sqltypes_completeness(self):
        """Verifica que los tipos SQL estandar esten definidos y mapeados a SQLAlchemy."""
        required_types = ["INTEGER", "VARCHAR", "TEXT", "BOOLEAN", "DATETIME", "FLOAT", "JSON"]
        for t in required_types:
            self.assertIn(t, sqltypes, f"Tipo SQL {t} no esta definido en sqltypes.py")
            self.assertIn(t, mapped_sqltypes, f"Tipo SQL {t} no esta mapeado en mapped_sqltypes")

    def test_mapped_sqltypes_python_types(self):
        """Verifica que los tipos mapeados correspondan a tipos nativos de Python."""
        self.assertEqual(mapped_sqltypes["INTEGER"], int)
        self.assertEqual(mapped_sqltypes["VARCHAR"], str)
        self.assertEqual(mapped_sqltypes["BOOLEAN"], bool)
        self.assertEqual(mapped_sqltypes["FLOAT"], float)

    def test_sqlite_in_memory_crud_reflection(self):
        """
        Prueba la reflexion automatizada y operaciones CRUD basicas
        en una base de datos SQLite en memoria (simulando el motor de reflexion de APY).
        """
        engine = create_engine("sqlite:///:memory:", echo=False)
        metadata = MetaData()

        # Crear tabla de prueba
        usuarios = Table(
            "usuarios",
            metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("nombre", String(100), nullable=False),
            Column("email", String(100), nullable=False)
        )
        metadata.create_all(engine)

        with engine.connect() as conn:
            # Insertar registro
            conn.execute(insert(usuarios), [{"nombre": "Herman Ayala", "email": "hayala@uas.edu.mx"}])
            conn.commit()

            # Consultar registro
            result = conn.execute(select(usuarios).where(usuarios.c.id == 1)).fetchone()
            self.assertIsNotNone(result)
            self.assertEqual(result.nombre, "Herman Ayala")
            self.assertEqual(result.email, "hayala@uas.edu.mx")

        # Reflexion de esquema (como lo hace generator.py)
        reflected_meta = MetaData()
        reflected_table = Table("usuarios", reflected_meta, autoload_with=engine)
        self.assertEqual(len(reflected_table.columns), 3)
        self.assertIn("id", reflected_table.columns)
        self.assertIn("nombre", reflected_table.columns)


if __name__ == "__main__":
    unittest.main()

