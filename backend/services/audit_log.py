
from __future__ import annotations
import csv, io, json, sqlite3, subprocess, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

JSON_SOURCES = [
  ('catalog_import', ROOT/'var'/'catalog-import'/'history.json'),
  ('catalog_import_provenance', ROOT/'var'/'catalog-import'/'provenance.json'),
  ('product_maintenance', ROOT/'var'/'product-maintenance'/'history.json'),
  ('catalog_workbench', ROOT/'var'/'catalog-workbench'/'history.json'),
  ('catalog_order', ROOT/'var'/'catalog-order'/'history.json'),
  ('homepage_showcase', ROOT/'var'/'homepage-showcase'/'history.json'),
  ('category_manager', ROOT/'var'/'category-manager'/'history.json'),
  ('media_manager', ROOT/'var'/'media-manager'/'history.json'),
  ('shop_settings', ROOT/'var'/'shop-settings'/'history.json'),
  ('catalog_health', ROOT/'data'/'catalog-health.overrides.json'),
]

ORDER_DB = ROOT/'var'/'order-center'/'order_center.db'

def _load_json(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except:
        return default

def _ts(v):
    if v is None:return 0.0
    if isinstance(v,(int,float)):
        x=float(v)
        if x>10_000_000_000:x/=1000
        return x
    s=str(v).strip()
    if not s:return 0.0
    try:
        from datetime import datetime
        z=s.replace('Z','+00:00')
        return datetime.fromisoformat(z).timestamp()
    except:
        return 0.0

def _summary(module, action, obj, detail):
    bits=[x for x in (action,obj,detail) if x]
    return ' · '.join(str(x) for x in bits) or module

def _event(module, raw, idx=0):
    action=str(raw.get('action') or raw.get('event_type') or raw.get('type') or 'event')
    obj=(raw.get('sku_id') or raw.get('product_id') or raw.get('order_id') or
         raw.get('category_id') or raw.get('media_id') or raw.get('filename') or
         raw.get('title') or raw.get('batch_id') or '')
    ts=_ts(raw.get('time') or raw.get('created_at') or raw.get('updated_at') or raw.get('timestamp'))
    publish=raw.get('publish') if isinstance(raw.get('publish'),dict) else {}
    commit=publish.get('commit') or raw.get('commit') or ''
    detail=raw.get('reason') or raw.get('note') or raw.get('detail') or ''
    actor=str(raw.get('actor') or raw.get('user') or raw.get('source') or 'admin/system')
    eid=str(raw.get('action_id') or raw.get('id') or f'{module}-{idx}-{int(ts)}')
    return {
      'id':eid,'time':ts,'module':module,'action':action,'object':str(obj),
      'actor':actor,'commit':str(commit),'summary':_summary(module,action,obj,detail),
      'raw':raw
    }

def _json_events():
    out=[]
    for module,path in JSON_SOURCES:
        if not path.exists():continue
        data=_load_json(path,[])
        if module=='catalog_health':
            for i,key in enumerate(data.get('ignored_duplicate_keys',[]) if isinstance(data,dict) else []):
                out.append({
                  'id':f'catalog-health-ignore-{i}','time':path.stat().st_mtime,
                  'module':'catalog_health','action':'ignore_duplicate','object':str(key),
                  'actor':'admin/system','commit':'',
                  'summary':f'ignore_duplicate · {key}',
                  'raw':{'key':key}
                })
            continue
        if module=='catalog_import_provenance' and isinstance(data,dict):
            # provenance may be map keyed by SKU
            for i,(key,val) in enumerate(data.items()):
                if isinstance(val,dict):
                    raw=dict(val); raw.setdefault('sku_id',key)
                    out.append(_event(module,raw,i))
            continue
        if isinstance(data,list):
            for i,raw in enumerate(data):
                if isinstance(raw,dict):out.append(_event(module,raw,i))
        elif isinstance(data,dict):
            out.append(_event(module,data,0))
    return out

def _order_events():
    out=[]
    if not ORDER_DB.exists():return out
    try:
        con=sqlite3.connect(ORDER_DB);con.row_factory=sqlite3.Row
        for table in ('order_events','order_notes'):
            try:rows=[dict(r) for r in con.execute(f'SELECT * FROM {table} ORDER BY id DESC LIMIT 5000')]
            except:continue
            for i,r in enumerate(rows):
                raw=dict(r)
                raw['action']='note' if table=='order_notes' else raw.get('event_type','order_event')
                raw['order_id']=raw.get('order_key','')
                out.append(_event('orders',raw,i))
        con.close()
    except:pass
    return out

def _git_events(limit=250):
    out=[]
    try:
        p=subprocess.run(
          ['git','log',f'-n{limit}','--pretty=format:%H%x1f%ct%x1f%an%x1f%s'],
          cwd=ROOT,capture_output=True,text=True,check=True
        )
        for i,line in enumerate(p.stdout.splitlines()):
            parts=line.split('\x1f')
            if len(parts)!=4:continue
            commit,ts,actor,msg=parts
            out.append({
              'id':'git-'+commit[:12],'time':float(ts),'module':'git',
              'action':'commit','object':commit[:12],'actor':actor,'commit':commit[:12],
              'summary':msg,'raw':{'commit':commit,'message':msg,'actor':actor}
            })
    except:pass
    return out

def all_events(limit=5000):
    rows=_json_events()+_order_events()+_git_events()
    rows.sort(key=lambda x:x.get('time',0),reverse=True)
    return rows[:limit]

def audit_data():
    rows=all_events()
    modules={}
    actions={}
    for x in rows:
        modules[x['module']]=modules.get(x['module'],0)+1
        actions[x['action']]=actions.get(x['action'],0)+1
    return {
      'generated_at':time.time(),
      'events':rows,
      'count':len(rows),
      'modules':modules,
      'actions':actions
    }

def export_csv():
    rows=all_events()
    buf=io.StringIO()
    w=csv.writer(buf)
    w.writerow(['time','module','action','object','actor','commit','summary'])
    from datetime import datetime
    for x in rows:
        dt=datetime.fromtimestamp(x['time']).isoformat(sep=' ') if x['time'] else ''
        w.writerow([dt,x['module'],x['action'],x['object'],x['actor'],x['commit'],x['summary']])
    return buf.getvalue()
