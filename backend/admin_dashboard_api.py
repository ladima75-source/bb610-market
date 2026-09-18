from typing import Optional
import os
from fastapi import APIRouter,Header,HTTPException
from .services.admin_dashboard import dashboard, attention_summary

router=APIRouter()

def auth(a):
    token=os.getenv('BB610_ADMIN_TOKEN')
    if not token or a!='Bearer '+token:
        raise HTTPException(401,'Unauthorized')

@router.get('/api/v1/admin/dashboard')
def dashboard_route(authorization:Optional[str]=Header(None)):
    auth(authorization)
    return dashboard()


@router.get('/api/v1/admin/attention-summary')
def attention_summary_route(authorization:Optional[str]=Header(None)):
    auth(authorization)
    return attention_summary()
