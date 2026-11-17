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
    id: str = Field(pattern=r'"^[A-Za-z0-9] {4,12}$')
    owner_name: str = Field(min_length=5, max_length=50 )
    balance: float = Field(ge=0)  # must be zero or greater
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

