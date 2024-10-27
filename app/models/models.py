from datetime import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = 'user'
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    hashed_password = Column(String)

class Bank(Base):
    __tablename__ = 'bank'
    __table_args__ = {'schema': 'public'}

    id_bank = Column(Integer, primary_key=True)
    bank_name = Column(String, unique=True)

class Transaction(Base):
    __tablename__ = 'transaction'
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True)

    from_user = Column(String)
    to_user = Column(String)

    from_bank = Column(Integer, ForeignKey(Bank.id_bank))
    to_bank = Column(Integer, ForeignKey(Bank.id_bank))

    from_card_number = Column(String)
    to_card_number = Column(String)

    transaction_amount = Column(Integer)

    transaction_time = Column(DateTime, default=datetime.utcnow())

    from_bank_relation = relationship("Bank", primaryjoin="Bank.id_bank == Transaction.from_bank")
    to_bank_relation = relationship("Bank", primaryjoin="Bank.id_bank == Transaction.to_bank")
