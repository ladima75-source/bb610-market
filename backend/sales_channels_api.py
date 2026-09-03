
from typing import Optional
import os
from fastapi import APIRouter,Header,HTTPException
from .services.sales_channels import channels_status

router=APIRouter()

def auth(a):
    token=os.getenv('BB610_ADMIN_TOKEN')
    if not token or a!='Bearer '+token:raise HTTPException(401,'Unauthorized')

@router.get('/api/v1/admin/sales-channels')
def status_route(authorization:Optional[str]=Header(None)):
    auth(authorization);return channels_status()
