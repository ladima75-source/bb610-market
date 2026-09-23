from __future__ import annotations
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from .integration_secrets import configured, get_value, source_for

API='https://api.checkbox.ua'

def status():
    login_ok=configured('checkbox.cashier_login')
    password_ok=configured('checkbox.cashier_password')
    return {
      'id':'checkbox','label':'Checkbox ПРРО',
      'configured':login_ok and password_ok,
      'cashier_login':{'configured':login_ok,'masked':'••••••••' if login_ok else '','source':source_for('checkbox.cashier_login')},
      'cashier_password':{'configured':password_ok,'masked':'••••••••' if password_ok else '','source':source_for('checkbox.cashier_password')},
      'mode':'webapi',
      'automation_ready':login_ok and password_ok,
      'trigger':'mono_paid_webhook'
    }

def _request(method,path,payload=None,token=None):
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
    headers={'Accept':'application/json','Content-Type':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    req=Request(API+path,data=data,method=method,headers=headers)
    try:
        with urlopen(req,timeout=15) as r:return json.loads(r.read().decode() or '{}')
    except HTTPError as e:
        try: detail=e.read().decode()
        except Exception: detail=''
        raise RuntimeError('Checkbox API error '+str(e.code)+((': '+detail[:300]) if detail else '')) from e
    except URLError as e:raise RuntimeError('Checkbox API unavailable') from e

def signin():
    login=get_value('checkbox.cashier_login','')
    password=get_value('checkbox.cashier_password','')
    if not login or not password:raise RuntimeError('Checkbox cashier credentials are not configured')
    d=_request('POST','/api/v1/cashier/signin',{'login':login,'password':password})
    token=d.get('access_token')
    if not token:raise RuntimeError('Checkbox did not return access_token')
    return token,d

def test():
    token,d=signin()
    return {'ok':True,'cashier':d.get('cashier') or {},'token_received':bool(token)}
