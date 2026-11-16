from enum import Enum
from typing import Optional
 
from pydantic import BaseModel, Field
 
 
class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    CLOSED = "CLOSED"
 
 
class AccountType(str, Enum):
    SAVINGS = "SAVINGS"
    CHECKING = "CHECKING"
 
 
class Currency(str, Enum):
    INR = "INR"
    USD = "USD"
    EUR = "EUR"
 
 
class Account(BaseModel):
    id: str
    owner_name: str = Field(min_length=1)
    balance: float = Field(ge=0)
    status: AccountStatus = AccountStatus.ACTIVE
    account_type: AccountType = AccountType.SAVINGS
    currency: Currency = Currency.INR
 
 
class AccountUpdate(BaseModel):
    balance: Optional[float] = Field(
        default=None,
        ge=0
    )
    status: Optional[AccountStatus] = None
    account_type: Optional[AccountType] = None
 
 
class AccountStatusUpdate(BaseModel):
    status: AccountStatus

