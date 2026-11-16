from pydantic import BaseModel  # import the class our data templates are built from
 
class Account(BaseModel):  # this defines the 'shape' of an Account
    id: str  # every account must have a text ID
    owner_name: str  # the name of the account holder
    balance: float  # the account balance, as a decimal number
