from typing import Optional
import os

from fastapi import APIRouter, UploadFile, File, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from .services.catalog_import import (
    preview, apply, rollback, history, provenance, export_csv, export_xlsx, template_csv
)
from .services import product_cards_v3_catalog_import as pcv3_import

router = APIRouter()


def auth(a):
    if not os.getenv('BB610_ADMIN_TOKEN') or a != 'Bearer ' + os.getenv('BB610_ADMIN_TOKEN'):
        raise HTTPException(401, 'Unauthorized')


class ApplyBody(BaseModel):
    token: str
    mode: str = 'content'
    rebuild: bool = True


class RollbackBody(BaseModel):
    backup_id: Optional[str] = None


class PCV3ApplyBody(BaseModel):
    token: str


class PCV3RollbackBody(BaseModel):
    backup_id: str


@router.get('/api/v1/admin/catalog-import/template.csv')
def template(authorization: Optional[str] = Header(None)):
    auth(authorization)
    return Response(
        template_csv(),
        media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=bb610-catalog-template.csv'},
    )


@router.get('/api/v1/admin/catalog-import/export.csv')
def csvx(authorization: Optional[str] = Header(None)):
    auth(authorization)
    return Response(
        export_csv(),
        media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=bb610-catalog-export.csv'},
    )


@router.get('/api/v1/admin/catalog-import/export.xlsx')
def xlsx(authorization: Optional[str] = Header(None)):
    auth(authorization)
    return Response(
        export_xlsx(),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=bb610-catalog-export.xlsx'},
    )


@router.post('/api/v1/admin/catalog-import/preview')
async def prev(file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    auth(authorization)
    raw = await file.read()
    if len(raw) > 80 * 1024 * 1024:
        raise HTTPException(413, 'max 80 MB')
    try:
        return preview(file.filename or 'catalog.csv', raw)
    except Exception as e:
        raise HTTPException(422, str(e))


@router.post('/api/v1/admin/catalog-import/apply')
def app(body: ApplyBody, authorization: Optional[str] = Header(None)):
    auth(authorization)
    if body.mode not in ('content', 'commerce', 'all'):
        raise HTTPException(422, 'mode')
    try:
        return apply(body.token, body.mode, body.rebuild)
    except Exception as e:
        raise HTTPException(422, str(e))


@router.post('/api/v1/admin/catalog-import/rollback')
def rb(body: RollbackBody, authorization: Optional[str] = Header(None)):
    auth(authorization)
    try:
        return rollback(body.backup_id)
    except Exception as e:
        raise HTTPException(422, str(e))


@router.get('/api/v1/admin/catalog-import/history')
def hist(authorization: Optional[str] = Header(None)):
    auth(authorization)
    return {'items': history()}


@router.get('/api/v1/admin/catalog-import/provenance')
def prov(authorization: Optional[str] = Header(None)):
    auth(authorization)
    return {'items': provenance()}


# Main CSV/XLSX importer for Product Card v3 + exact commerce bindings/prices.
# It never fuzzy-matches prices: commerce changes are applied only by explicit
# commerce_product_key / commerce_sku_key or deterministic keys for new SKUs.
@router.get('/api/v1/admin/product-card-import/template.csv')
def pcv3_template_csv(authorization: Optional[str] = Header(None)):
    auth(authorization)
    return Response(
        pcv3_import.template_csv(),
        media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=bb610-product-catalog-v3-template.csv'},
    )


@router.get('/api/v1/admin/product-card-import/template.xlsx')
def pcv3_template_xlsx(authorization: Optional[str] = Header(None)):
    auth(authorization)
    return Response(
        pcv3_import.template_xlsx(),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=bb610-product-catalog-v3-template.xlsx'},
    )


@router.get('/api/v1/admin/product-card-import/export.csv')
def pcv3_export_csv(authorization: Optional[str] = Header(None)):
    auth(authorization)
    return Response(
        pcv3_import.export_csv(),
        media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=bb610-product-catalog-v3-export.csv'},
    )


@router.get('/api/v1/admin/product-card-import/export.xlsx')
def pcv3_export_xlsx(authorization: Optional[str] = Header(None)):
    auth(authorization)
    return Response(
        pcv3_import.export_xlsx(),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=bb610-product-catalog-v3-export.xlsx'},
    )


@router.post('/api/v1/admin/product-card-import/preview')
async def pcv3_preview(file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    auth(authorization)
    raw = await file.read()
    if len(raw) > 40 * 1024 * 1024:
        raise HTTPException(413, 'max 40 MB')
    try:
        return pcv3_import.preview(file.filename or 'product-catalog-v3.xlsx', raw)
    except Exception as e:
        raise HTTPException(422, str(e))


@router.post('/api/v1/admin/product-card-import/apply')
def pcv3_apply(body: PCV3ApplyBody, authorization: Optional[str] = Header(None)):
    auth(authorization)
    try:
        return pcv3_import.apply(body.token)
    except Exception as e:
        raise HTTPException(422, str(e))


@router.get('/api/v1/admin/product-card-import/history')
def pcv3_history(authorization: Optional[str] = Header(None)):
    auth(authorization)
    return {'items': pcv3_import.history()}


@router.post('/api/v1/admin/product-card-import/rollback')
def pcv3_rollback(body: PCV3RollbackBody, authorization: Optional[str] = Header(None)):
    auth(authorization)
    try:
        return pcv3_import.rollback(body.backup_id)
    except Exception as e:
        raise HTTPException(422, str(e))
