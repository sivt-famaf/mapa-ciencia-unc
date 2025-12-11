from fastapi import Header, HTTPException
from ..config import INTERNAL_SWAGGER_KEY

def validate_internal_key(x_internal_key: str = Header(...)):
    if x_internal_key is None:
        raise HTTPException(status_code=422, detail="Missing internal key")
     
    if x_internal_key != INTERNAL_SWAGGER_KEY:
        raise HTTPException(status_code=403, detail="Invalid internal key")