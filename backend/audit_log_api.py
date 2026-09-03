
from typing import Optional
import os
from fastapi import APIRouter,Header,HTTPException
from fastapi.responses import Response
from .services.audit_log import audit_data,export_csv

router=APIRouter()
def auth(a):
    token=os.getenv('BB610_ADMIN_TOKEN')
    if not token or a!='Bearer '+token:raise HTTPException(401,'Unauthorized')

@router.get('/api/v1/admin/audit-log')
def audit_route(authorization:Optional[str]=Header(None)):
    auth(authorization);return audit_data()

@router.get('/api/v1/admin/audit-log.csv')
def csv_route(authorization:Optional[str]=Header(None)):
    auth(authorization)
    return Response(content=export_csv(),media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition':'attachment; filename=bb610-audit-log.csv'})
