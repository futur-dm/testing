from sqlalchemy import Column, Integer, VARCHAR, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.settings import URL

engine = create_engine(URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Users(Base):
    __tablename__ = "users"

    id_user = Column(Integer, primary_key=True, comment='user id')
    username = Column(VARCHAR(250), unique=True, nullable=False)
    hashed_password = Column(VARCHAR(250))

Base.metadata.create_all(bind=engine)
