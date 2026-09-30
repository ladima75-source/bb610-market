from __future__ import annotations
from fastapi import APIRouter
from fastapi.responses import Response, JSONResponse
from .services.catalog_feeds import google_csv, meta_csv, feed_status
from .services.openai_commerce_feed import csv_feed as openai_csv_feed, jsonl_feed as openai_jsonl_feed

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


@router.get('/api/v1/catalog/feeds/openai-products.csv')
def openai_products_csv():
    return Response(
        content=openai_csv_feed(),
        media_type='text/csv; charset=utf-8',
        headers={
            'Content-Disposition': 'attachment; filename="bb610-openai-products.csv"',
            'Cache-Control': 'no-store',
        },
    )


@router.get('/api/v1/catalog/feeds/openai-products.jsonl')
def openai_products_jsonl():
    return Response(
        content=openai_jsonl_feed(),
        media_type='application/x-ndjson; charset=utf-8',
        headers={
            'Content-Disposition': 'attachment; filename="bb610-openai-products.jsonl"',
            'Cache-Control': 'no-store',
        },
    )
