from pydantic import BaseModel, Field
from enum import Enum


class TransactionType(str, Enum):
    deposit = "deposit"
    withdrawal = "withdrawal"


class Transaction(BaseModel):
    id: str
    account_id: str
    type: TransactionType
    amount: float = Field(gt=0)
    status: str = "completed"
