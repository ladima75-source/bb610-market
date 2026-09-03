
from __future__ import annotations
import json, os, shutil, subprocess, time, uuid, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CENTER = ROOT/'var'/'backup-center'
CENTER_BACKUPS = CENTER/'backups'
HISTORY = CENTER/'history.json'
CENTER_BACKUPS.mkdir(parents=True, exist_ok=True)

# We only restore known, project-controlled paths.
ALLOWED_TOP = {
  'data',
  'admin',
  'assets',
  'backend',
}

def _load_json(p, default):
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except:
        return default

def _save_json(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def _history(add=None):
    h=_load_json(HISTORY,[])
    if add:
        h.insert(0,add)
        _save_json(HISTORY,h[:500])
    return h

def _safe_rel(rel:str):
    rel=rel.replace('\\','/').lstrip('/')
    parts=[p for p in rel.split('/') if p not in ('','.')]
    if not parts:return None
    if '..' in parts:return None
    if parts[0] not in ALLOWED_TOP:return None
    return '/'.join(parts)

def _human_size(n):
    n=float(n)
    for u in ('B','KB','MB','GB'):
        if n<1024:return f'{n:.1f} {u}'
        n/=1024
    return f'{n:.1f} TB'

def _dir_size(p):
    total=0
    if p.is_file():
        try:return p.stat().st_size
        except:return 0
    for x in p.rglob('*'):
        if x.is_file():
            try:total+=x.stat().st_size
            except:pass
    return total

def _source_label(p:Path):
    n=p.name
    if n.startswith('.stage'):
        return n.split('-backup-')[0].lstrip('.').replace('stage','Stage ')
    if p.parent==CENTER_BACKUPS:
        return 'Backup Center'
    return 'Project backup'

def _scan_backup_dir(p:Path):
    files=[]
    if not p.exists():return files
    for x in p.rglob('*'):
        if not x.is_file():continue
        rel=x.relative_to(p).as_posix()
        safe=_safe_rel(rel)
        if safe:
            files.append({'path':safe,'size':x.stat().st_size})
    return files

def _center_manifest(p:Path):
    m=p/'manifest.json'
    if not m.exists():return None
    return _load_json(m,None)

def _backup_record(p:Path):
    manifest=_center_manifest(p)
    if manifest:
        files=manifest.get('files',[])
        size=sum(int(f.get('size',0)) for f in files)
        created=float(manifest.get('created_at') or p.stat().st_mtime)
        source=manifest.get('source','Backup Center')
        label=manifest.get('label') or p.name
        kind='center'
    else:
        files=_scan_backup_dir(p)
        size=sum(int(f.get('size',0)) for f in files)
        created=p.stat().st_mtime
        source=_source_label(p)
        label=p.name
        kind='legacy'
    return {
      'id':p.name,
      'path':str(p),
      'label':label,
      'source':source,
      'kind':kind,
      'created_at':created,
      'size':size,
      'size_human':_human_size(size),
      'file_count':len(files),
      'files':files[:250]
    }

def list_backups():
    found=[]
    # Existing stage backups at project root.
    for p in ROOT.glob('.stage*-backup-*'):
        if p.is_dir():
            found.append(_backup_record(p))
    # Backups created by this center.
    for p in CENTER_BACKUPS.iterdir():
        if p.is_dir():
            found.append(_backup_record(p))
    found.sort(key=lambda x:x['created_at'], reverse=True)
    return found

def create_backup(label='Manual backup', source='Backup Center', include=None):
    bid=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
    dest=CENTER_BACKUPS/bid
    dest.mkdir(parents=True,exist_ok=False)

    default_paths=[
      'data',
      'admin',
      'assets',
      'backend/app.py',
    ]
    wanted=include or default_paths
    files=[]

    for rel in wanted:
        safe=_safe_rel(rel)
        if not safe:continue
        src=ROOT/safe
        if not src.exists():continue
        dst=dest/safe
        if src.is_dir():
            for f in src.rglob('*'):
                if not f.is_file():continue
                frel=f.relative_to(ROOT).as_posix()
                fsafe=_safe_rel(frel)
                if not fsafe:continue
                out=dest/fsafe
                out.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(f,out)
                files.append({'path':fsafe,'size':f.stat().st_size})
        else:
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(src,dst)
            files.append({'path':safe,'size':src.stat().st_size})

    manifest={
      'id':bid,'created_at':time.time(),'label':label,'source':source,
      'files':files
    }
    _save_json(dest/'manifest.json',manifest)

    row={'time':time.time(),'action':'create_backup','backup_id':bid,'label':label,'source':source,'files':len(files)}
    _history(row)
    return {'ok':True,'backup':_backup_record(dest)}

def _resolve_backup(backup_id):
    candidates=[CENTER_BACKUPS/backup_id, ROOT/backup_id]
    for p in candidates:
        if p.exists() and p.is_dir():
            return p
    raise ValueError('Backup not found')

def backup_detail(backup_id):
    return _backup_record(_resolve_backup(backup_id))

def create_zip(backup_id):
    p=_resolve_backup(backup_id)
    out=CENTER/f'{backup_id}.zip'
    if out.exists():out.unlink()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for f in p.rglob('*'):
            if f.is_file():
                z.write(f,arcname=f'{backup_id}/{f.relative_to(p).as_posix()}')
    return out

def _git_publish(message):
    subprocess.run(['git','add','-A'],cwd=ROOT,check=True)
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode!=0:
        subprocess.run(['git','commit','-m',message],cwd=ROOT,check=True)
    commit=subprocess.run(['git','rev-parse','--short','HEAD'],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()
    subprocess.run(['git','push'],cwd=ROOT,check=True)
    return commit

def restore_backup(backup_id, confirm_text, publish_git=False):
    if confirm_text != 'RESTORE':
        raise ValueError('Confirmation text must be RESTORE')

    src=_resolve_backup(backup_id)
    rec=_backup_record(src)
    if not rec['files']:
        raise ValueError('Backup contains no restorable project files')

    safety=create_backup(
      label=f'Safety before restore {backup_id}',
      source='Automatic pre-restore safety backup'
    )['backup']

    restored=[]
    for item in rec['files']:
        rel=_safe_rel(item.get('path',''))
        if not rel:continue
        fsrc=src/rel
        if not fsrc.exists() or not fsrc.is_file():
            continue
        dst=ROOT/rel
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(fsrc,dst)
        restored.append(rel)

    commit=None
    if publish_git:
        commit=_git_publish(f'Restore backup {backup_id}')

    row={
      'time':time.time(),'action':'restore_backup','backup_id':backup_id,
      'safety_backup_id':safety['id'],'restored_files':len(restored),
      'publish_git':bool(publish_git),'commit':commit
    }
    _history(row)
    return {
      'ok':True,'backup_id':backup_id,'safety_backup_id':safety['id'],
      'restored_files':len(restored),'commit':commit
    }

def center_data():
    return {'backups':list_backups(),'history':_history()[:100]}
