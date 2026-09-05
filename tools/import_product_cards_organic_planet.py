#!/usr/bin/env python3
from pathlib import Path
import argparse, copy, datetime as dt, json, re, unicodedata

def slugify(s):
    tr=str.maketrans({
        'а':'a','б':'b','в':'v','г':'h','ґ':'g','д':'d','е':'e','є':'ye','ж':'zh','з':'z','и':'y','і':'i','ї':'yi','й':'i',
        'к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch',
        'ш':'sh','щ':'shch','ь':'','ю':'yu','я':'ya','ы':'y','э':'e','ъ':''
    })
    s=str(s or '').lower().translate(tr)
    s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode('ascii')
    return re.sub(r'[^a-z0-9]+','-',s).strip('-')

def norm_pack(s):
    return str(s or '').lower().replace(' ','').replace(',','.')

def alt_ids(cid):
    out={cid,cid.replace('-npk-','-'),cid.replace('npk-',''),cid.replace('-orto-orto','-ortho-ortho')}
    return {x.strip('-') for x in out if x}

def load_collection(obj):
    if isinstance(obj,list): return ('list',None,obj)
    if not isinstance(obj,dict): raise RuntimeError('Unsupported product_cards master root type')
    for key in ('products','cards','items'):
        v=obj.get(key)
        if isinstance(v,list): return ('list-key',key,v)
        if isinstance(v,dict): return ('dict-key',key,v)
    vals=[v for v in obj.values() if isinstance(v,dict)]
    if vals and len(vals)>=max(1,len(obj)//2): return ('dict-direct',None,obj)
    raise RuntimeError('Could not identify card collection in product_cards master')

def iter_cards(kind,coll):
    if kind in ('list','list-key'):
        for i,c in enumerate(coll):
            if isinstance(c,dict): yield i,c
    else:
        for k,c in coll.items():
            if isinstance(c,dict): yield k,c

def get_id(key,card):
    return str(card.get('id') or card.get('product_id') or card.get('slug') or key or '').strip()
def get_name(card):
    return str(card.get('name') or card.get('title') or card.get('product_name') or '').strip()

def find_match(kind,coll,source):
    ids=alt_ids(source['canonical_id'])
    exact=[]; names=[]
    for key,c in iter_cards(kind,coll):
        cid=slugify(get_id(key,c))
        if cid in ids or cid.replace('-npk-','-') in ids:
            exact.append((key,c,'id')); continue
        nm=slugify(get_name(c))
        if nm in ids or nm.replace('-npk-','-') in ids:
            names.append((key,c,'name'))
    cand=exact or names
    if len(cand)==1: return cand[0]
    if len(cand)>1: return ('AMBIGUOUS',cand,None)
    return None

def card_variants(card):
    for key in ('variants','skus','options'):
        if isinstance(card.get(key),list): return key,card[key]
    card['variants']=[]; return 'variants',card['variants']

def var_label(v):
    if isinstance(v,str): return v
    if not isinstance(v,dict): return ''
    return str(v.get('label') or v.get('variant') or v.get('pack') or v.get('volume_weight') or v.get('size') or '').strip()

def new_variant(v):
    return {'sku':v['sku'],'label':v['label'],'image':'','enabled':False,'import_source':'Organic Planet structure import 2026'}

def new_card(src):
    today=dt.date.today().isoformat()
    return {
        'id':src['canonical_id'],'version':'2.0','enabled':True,
        'publication_status':'draft','feed_policy':'blocked',
        'category':'','brand':'','eyebrow':'','name':src['name'],
        'subtitle':'','lead':'','short_description':'','full_description':'',
        'why':[],'how':[],'applications':[],'characteristics':[],
        'origin':{},'documents':[],
        'sources':{'source':src.get('source',''),'revision':'mass structure import','verified_date':today},
        'variants':[new_variant(v) for v in src['variants']],
        'import_meta':{'source_row':src['source_row'],'source_note':src.get('note',''),'structure_only':True}
    }

def append_card(kind,coll,card):
    if kind in ('list','list-key'):
        coll.append(card)
    else:
        key=card['id']
        if key in coll:
            base=key; i=2
            while f'{base}-{i}' in coll: i+=1
            key=f'{base}-{i}'; card['id']=key
        coll[key]=card

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',default='/opt/bb610-market')
    ap.add_argument('--source',required=True)
    ap.add_argument('--apply',action='store_true')
    args=ap.parse_args()
    root=Path(args.root).resolve()
    source=json.loads(Path(args.source).read_text(encoding='utf-8'))['cards']

    candidates=[root/'data/product_cards.master.json',root/'data/product-cards.master.json']
    master=next((p for p in candidates if p.exists()),None)
    if not master: raise SystemExit('ERROR: product_cards master not found')

    obj=json.loads(master.read_text(encoding='utf-8'))
    kind,key,coll=load_collection(obj)

    report={
        'source_cards':len(source),'source_variants':sum(len(x['variants']) for x in source),
        'matched_existing_cards':0,'created_cards':0,'variants_already_present':0,'variants_added':0,
        'ambiguous_existing':[],'existing_extra_variants':[],'created_ids':[],'matched_ids':[],
        'mode':'apply' if args.apply else 'dry-run'
    }

    for src in source:
        match=find_match(kind,coll,src)
        if match and match[0]=='AMBIGUOUS':
            cand=match[1]
            report['ambiguous_existing'].append({'source_row':src['source_row'],'name':src['name'],
                                                 'candidates':[get_id(k,c) for k,c,_ in cand]})
            card=new_card(src); append_card(kind,coll,card)
            report['created_cards']+=1; report['created_ids'].append(card['id'])
            report['variants_added']+=len(src['variants'])
            continue

        if match:
            k,card,why=match
            report['matched_existing_cards']+=1
            report['matched_ids'].append(get_id(k,card))
            _,vars_=card_variants(card)
            existing={norm_pack(var_label(v)):v for v in vars_ if var_label(v)}
            wanted={norm_pack(v['label']) for v in src['variants']}
            for v in src['variants']:
                np=norm_pack(v['label'])
                if np in existing:
                    report['variants_already_present']+=1
                else:
                    vars_.append(new_variant(v)); report['variants_added']+=1
            extras=[var_label(v) for v in vars_ if var_label(v) and norm_pack(var_label(v)) not in wanted]
            if extras:
                report['existing_extra_variants'].append({'card_id':get_id(k,card),'name':src['name'],'extras':extras})
            meta=card.setdefault('import_meta',{})
            meta['organic_planet_source_row']=src['source_row']
            meta['organic_planet_structure_checked']=dt.date.today().isoformat()
            if src.get('note'): meta['organic_planet_note']=src['note']
        else:
            card=new_card(src); append_card(kind,coll,card)
            report['created_cards']+=1; report['created_ids'].append(card['id'])
            report['variants_added']+=len(src['variants'])

    reports=root/'var/import-reports'; reports.mkdir(parents=True,exist_ok=True)
    stamp=dt.datetime.now().strftime('%Y%m%d-%H%M%S')
    report_path=reports/f'organic_planet_product_cards_{stamp}.json'
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

    if args.apply:
        master.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

    print('MASTER:',master)
    print('MODE:',report['mode'])
    print('Cards source:',report['source_cards'])
    print('Variants source:',report['source_variants'])
    print('Matched existing cards:',report['matched_existing_cards'])
    print('Created cards:',report['created_cards'])
    print('Variants already present:',report['variants_already_present'])
    print('Variants added:',report['variants_added'])
    print('Ambiguous existing:',len(report['ambiguous_existing']))
    print('Cards with untouched extra variants:',len(report['existing_extra_variants']))
    print('REPORT:',report_path)

if __name__=='__main__':
    main()
