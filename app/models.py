from pydantic import BaseModel, Field
 
class Account(BaseModel):
    id: str
    owner_name: str = Field(min_length=1)
    balance: float = Field(ge=0)  # must be zero or greater
