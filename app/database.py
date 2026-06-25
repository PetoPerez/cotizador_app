from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

# pool_pre_ping: verifica que la conexión siga viva antes de usarla (evita
#   "SSL SYSCALL error: EOF detected" cuando Postgres/Railway cierra conexiones inactivas).
# pool_recycle: recicla conexiones con más de 30 min para no toparse con timeouts del servidor.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()