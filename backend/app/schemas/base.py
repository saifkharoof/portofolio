from pydantic import BaseModel

class BaseResponse(BaseModel):
    id: str
    created_at: str
    updated_at: str
