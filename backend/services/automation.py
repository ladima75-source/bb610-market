from __future__ import annotations
import json, os, uuid
from datetime import datetime, timezone
from ..db import connect

VALID_JOB_STATUSES={'queued','blocked','running','completed','failed','cancelled'}
VALID_APPROVAL_STATUSES={'pending','approved','rejected','expired','cancelled'}

def now(): return datetime.now(timezone.utc).isoformat()

def _json(v): return json.dumps(v or {},ensure_ascii=False,separators=(',',':'))

def audit(action:str,target_type:str|None=None,target_id:str|None=None,details:dict|None=None,actor_type:str='system',actor_id:str|None=None,event_id:str|None=None,con=None):
    own=con is None; con=con or connect()
    try:
        con.execute('INSERT INTO automation_audit_log(actor_type,actor_id,action,target_type,target_id,event_id,details_json,created_at) VALUES(?,?,?,?,?,?,?,?)',
                    (actor_type,actor_id,action,target_type,target_id,event_id,_json(details),now()))
        if own: con.commit()
    finally:
        if own: con.close()

def _ai_configured():
    provider=(os.getenv('BB610_AI_PROVIDER') or '').strip().lower()
    return bool(provider and provider not in {'disabled','none','off'})

def _queue_ai_job(con,rule,event):
    cfg=json.loads(rule['action_json'] or '{}')
    jid=str(uuid.uuid4()); configured=_ai_configured(); status='queued' if configured else 'blocked'
    # Event payload intentionally remains privacy-minimized. Workers may fetch only the scope explicitly allowed by the rule.
    input_payload={
      'event':{'event_id':event['event_id'],'event_type':event['event_type'],'aggregate_type':event['aggregate_type'],'aggregate_id':event['aggregate_id']},
      'event_payload':json.loads(event['payload_json'] or '{}')
    }
    con.execute('''INSERT INTO ai_jobs(id,job_type,event_id,aggregate_type,aggregate_id,context_scope,input_json,status,provider,model,requires_approval,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',(
        jid,cfg.get('job_type','generic'),event['event_id'],event['aggregate_type'],event['aggregate_id'],cfg.get('context_scope','minimal_no_pii'),_json(input_payload),status,
        (os.getenv('BB610_AI_PROVIDER') or None),(os.getenv('BB610_AI_MODEL') or None),1 if cfg.get('requires_approval',True) else 0,now()))
    audit('ai_job.queued','ai_job',jid,{'status':status,'job_type':cfg.get('job_type','generic'),'context_scope':cfg.get('context_scope','minimal_no_pii')},'automation_rule',rule['id'],event['event_id'],con)

def _create_approval(con,rule,event):
    cfg=json.loads(rule['action_json'] or '{}'); aid=str(uuid.uuid4())
    con.execute('''INSERT INTO approval_requests(id,source_type,source_id,action_type,risk_level,title,summary,payload_json,status,requested_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)''',(
        aid,'event',event['event_id'],cfg.get('action_type','review'),cfg.get('risk_level','medium'),cfg.get('title',rule['name']),cfg.get('summary'),_json({'aggregate_type':event['aggregate_type'],'aggregate_id':event['aggregate_id']}),'pending',now()))
    audit('approval.requested','approval',aid,{'action_type':cfg.get('action_type','review')},'automation_rule',rule['id'],event['event_id'],con)

def _process_event(con,event):
    rules=con.execute('SELECT * FROM automation_rules WHERE enabled=1 AND event_type=? ORDER BY id',(event['event_type'],)).fetchall()
    for rule in rules:
        if rule['action_type']=='agent_job': _queue_ai_job(con,rule,event)
        elif rule['action_type']=='approval_request': _create_approval(con,rule,event)
        elif rule['action_type']=='audit_only':
            cfg=json.loads(rule['action_json'] or '{}')
            audit(cfg.get('action','automation.event'),'event',event['event_id'],{'event_type':event['event_type'],'aggregate_id':event['aggregate_id']},'automation_rule',rule['id'],event['event_id'],con)
    con.execute('UPDATE commerce_events SET processed_at=? WHERE event_id=?',(now(),event['event_id']))

def emit(event_type:str,aggregate_type:str,aggregate_id:str,payload:dict|None=None,source='system',event_id:str|None=None):
    eid=event_id or f'evt_{uuid.uuid4()}'
    with connect() as con:
        exists=con.execute('SELECT * FROM commerce_events WHERE event_id=?',(eid,)).fetchone()
        if exists:return eid
        con.execute('INSERT INTO commerce_events(event_id,event_type,aggregate_type,aggregate_id,payload_json,source,created_at) VALUES(?,?,?,?,?,?,?)',
                    (eid,event_type,aggregate_type,aggregate_id,_json(payload),source,now()))
        event=con.execute('SELECT * FROM commerce_events WHERE event_id=?',(eid,)).fetchone()
        _process_event(con,event); con.commit()
    return eid

def list_rules():
    with connect() as con:return [dict(x) for x in con.execute('SELECT * FROM automation_rules ORDER BY event_type,id')]

def set_rule_enabled(rule_id:str,enabled:bool,actor='admin'):
    with connect() as con:
        row=con.execute('SELECT * FROM automation_rules WHERE id=?',(rule_id,)).fetchone()
        if not row:return None
        con.execute('UPDATE automation_rules SET enabled=?,updated_at=? WHERE id=?',(1 if enabled else 0,now(),rule_id))
        audit('automation_rule.enabled' if enabled else 'automation_rule.disabled','automation_rule',rule_id,{},'admin',actor,None,con);con.commit()
        return dict(con.execute('SELECT * FROM automation_rules WHERE id=?',(rule_id,)).fetchone())

def list_jobs(status:str|None=None,limit=100):
    with connect() as con:
        sql='SELECT * FROM ai_jobs'; args=[]
        if status: sql+=' WHERE status=?';args.append(status)
        sql+=' ORDER BY created_at DESC LIMIT ?';args.append(limit)
        return [dict(x) for x in con.execute(sql,args)]

def list_approvals(status:str|None='pending',limit=100):
    with connect() as con:
        sql='SELECT * FROM approval_requests';args=[]
        if status:sql+=' WHERE status=?';args.append(status)
        sql+=' ORDER BY requested_at DESC LIMIT ?';args.append(limit)
        return [dict(x) for x in con.execute(sql,args)]

def decide_approval(approval_id:str,decision:str,note:str|None=None,actor='admin'):
    if decision not in {'approved','rejected'}: raise ValueError('INVALID_APPROVAL_DECISION')
    with connect() as con:
        r=con.execute('SELECT * FROM approval_requests WHERE id=?',(approval_id,)).fetchone()
        if not r:return None
        if r['status']!='pending':raise ValueError('APPROVAL_ALREADY_DECIDED')
        ts=now();con.execute('UPDATE approval_requests SET status=?,decided_at=?,decided_by=?,decision_note=? WHERE id=?',(decision,ts,actor,note,approval_id))
        audit(f'approval.{decision}','approval',approval_id,{'note':note,'action_type':r['action_type']},'admin',actor,None,con);con.commit()
        return dict(con.execute('SELECT * FROM approval_requests WHERE id=?',(approval_id,)).fetchone())

def list_audit(limit=200):
    with connect() as con:return [dict(x) for x in con.execute('SELECT * FROM automation_audit_log ORDER BY id DESC LIMIT ?',(limit,))]

def summary():
    with connect() as con:
        def c(sql,args=()):return con.execute(sql,args).fetchone()[0]
        return {
          'events_total':c('SELECT count(*) FROM commerce_events'),
          'rules_enabled':c('SELECT count(*) FROM automation_rules WHERE enabled=1'),
          'ai_jobs_queued':c("SELECT count(*) FROM ai_jobs WHERE status='queued'"),
          'ai_jobs_blocked':c("SELECT count(*) FROM ai_jobs WHERE status='blocked'"),
          'approvals_pending':c("SELECT count(*) FROM approval_requests WHERE status='pending'"),
          'ai_provider_configured':_ai_configured()
        }

def get_approval(approval_id:str):
    with connect() as con:
        r=con.execute('SELECT * FROM approval_requests WHERE id=?',(approval_id,)).fetchone()
        return dict(r) if r else None

def approval_for_source(source_id:str):
    with connect() as con:
        r=con.execute('SELECT * FROM approval_requests WHERE source_id=? ORDER BY requested_at DESC LIMIT 1',(source_id,)).fetchone()
        return dict(r) if r else None
