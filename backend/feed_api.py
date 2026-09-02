from __future__ import annotations
from fastapi import APIRouter
from fastapi.responses import Response, JSONResponse
from .services.catalog_feeds import google_csv, meta_csv, feed_status

router=APIRouter()

@router.get('/api/v1/catalog/feeds/google-merchant.csv')
def google_merchant_feed():
    return Response(content=google_csv(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="bb610-google-merchant.csv"','Cache-Control':'no-store'})

@router.get('/api/v1/catalog/feeds/meta-catalog.csv')
def meta_catalog_feed():
    return Response(content=meta_csv(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="bb610-meta-catalog.csv"','Cache-Control':'no-store'})

@router.get('/api/v1/catalog/feeds/feed-status.json')
def catalog_feed_status():
    return JSONResponse(feed_status(),headers={'Cache-Control':'no-store'})
