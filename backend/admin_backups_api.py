
from typing import Optional
import os
from fastapi import APIRouter, Header, HTTPException
from .services.admin_backups import backups

router=APIRouter()

def auth(a):
    token=os.getenv("BB610_ADMIN_TOKEN")
    if not token or a!="Bearer "+token:
        raise HTTPException(401,"Unauthorized")

@router.get("/api/v1/admin/backups")
def list_backups(authorization:Optional[str]=Header(None)):
    auth(authorization)
    return {"items":backups()}
