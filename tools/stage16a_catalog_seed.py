#!/usr/bin/env python3
from __future__ import annotations
import json, sys, re
from pathlib import Path
from datetime import date

TODAY='2026-09-02'
ROOT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
PATH=ROOT/'data'/'catalog.master.json'
master=json.loads(PATH.read_text(encoding='utf-8'))

# Stage 16A source boundary:
# - product/pack/name/launch role come from the approved BB610 Organic Planet launch matrix;
# - prices/stock are deliberately NOT imported;
# - technical claims are conservative unless already verified in the existing catalog.

BRANDS=[
 ('icl','ICL'),('haifa','Haifa Group'),('alventa','ALVENTA'),('neova','Neova'),('maxicrop','Maxicrop')
]
existing_brand_names={str(x.get('name','')).lower() for x in master.get('brands',[])}
for bid,bname in BRANDS:
    if bname.lower() not in existing_brand_names:
        master.setdefault('brands',[]).append({'id':bid,'name':bname,'enabled':True})
        existing_brand_names.add(bname.lower())

PLACEHOLDER={'nutrition':'assets/img/product-npk.svg','biostimulation':'assets/img/product-biostim.svg','protection':'assets/img/product-protection.svg'}
REAL_IMAGES={
 'master-13-40-13':'assets/img/real/master-13-40-13.webp',
 'megafol':'assets/img/real/megafol.webp',
 'radifarm':'assets/img/real/radifarm.webp',
 'plantafol-20-20-20':'assets/img/real/plantafol-20-20-20.webp',
}

# id, display name, brand, manufacturer, country, category, product type, form, npk, short description, purpose, priority
PRODUCTS=[
 ('control-dmp','Control DMP (Контроль ДМП), регулятор кислотності та прилипач','Valagro','Valagro / Syngenta Biologicals','Італія','protection','Регулятор кислотності / ад’ювант','Рідкий','—','Засіб для коригування кислотності робочого розчину та покращення якості обробки.','якість води / pH / ад’ювант','A'),
 ('pekacid-0-60-20','PeKacid (Пекацид) 0-60-20, фосфорно-калійне добриво','ICL','ICL','Ізраїль','nutrition','Водорозчинне фосфорно-калійне добриво з підкислювальним ефектом','Порошкове водорозчинне','0-60-20','Концентроване водорозчинне добриво для фосфорно-калійного живлення та роботи з лужною/жорсткою водою.','підкислення / фосфор / калій','A'),
 ('kendal','Kendal (Кендал), біостимулятор','Valagro','Valagro / Syngenta Biologicals','Італія','biostimulation','Біостимулятор','Рідкий','—','Біостимулятор для підтримки рослин у технологіях вирощування; застосування звіряється з актуальною етикеткою.','біостимуляція / підтримка рослин','A'),
 ('megafol','Megafol (Мегафол), біостимулятор-антистрес','Valagro','Valagro S.p.A. / Syngenta Biologicals','Італія','biostimulation','Рідкий біостимулятор','Рідкий','—','Біостимулятор-антистрес для підтримки рослин за абіотичного стресу.','антистрес / біостимуляція','A'),
 ('radifarm','Radifarm (Радіфарм), біостимулятор розвитку кореневої системи','Valagro','Valagro / Syngenta Biologicals','Італія','biostimulation','Біостимулятор кореневої системи','Рідкий','—','Біостимулятор для старту рослин і підтримки розвитку кореневої системи.','коренева система / укорінення','A'),
 ('viva','Viva (Віва), біостимулятор та активатор ґрунтової мікрофлори','Valagro','Valagro / Syngenta Biologicals','Італія','biostimulation','Біостимулятор','Рідкий','—','Біостимулятор для підтримки кореневої зони та ґрунтової біологічної активності.','ґрунт / корені / біостимуляція','A'),
 ('osmocote-landscape-16-9-12','Osmocote Landscape 16-9-12 (3–4 міс.), добриво контрольованої дії','ICL','ICL','—','nutrition','Добриво контрольованої дії','Гранули','16-9-12','Гранульоване добриво контрольованої дії для тривалого живлення.','тривале живлення','A'),
 ('osmocote-quick-start-22-5-6','Osmocote Quick Start 22-5-6 (4–5 міс.), добриво контрольованої дії','ICL','ICL','—','nutrition','Добриво контрольованої дії','Гранули','22-5-6','Гранульоване добриво контрольованої дії з акцентом на стартове живлення.','старт / тривале живлення','A'),
 ('plantafol-10-54-10','Plantafol (Плантафол) 10-54-10, добриво для позакореневого живлення','Valagro','Valagro / Syngenta Biologicals','Італія','nutrition','Мінеральне водорозчинне добриво для листкового живлення','Водорозчинне','10-54-10','Фосфорна формула Plantafol для позакореневого живлення у відповідні фази розвитку.','листкове живлення / фосфор','A'),
 ('plantafol-30-10-10','Plantafol (Плантафол) 30-10-10, добриво для позакореневого живлення','Valagro','Valagro / Syngenta Biologicals','Італія','nutrition','Мінеральне водорозчинне добриво для листкового живлення','Водорозчинне','30-10-10','Азотна формула Plantafol для позакореневого живлення та вегетативного росту.','листкове живлення / вегетативний ріст','A'),
 ('plantafol-5-15-45','Plantafol (Плантафол) 5-15-45, добриво для позакореневого живлення','Valagro','Valagro / Syngenta Biologicals','Італія','nutrition','Мінеральне водорозчинне добриво для листкового живлення','Водорозчинне','5-15-45','Калійна формула Plantafol для позакореневого живлення у період формування та достигання плодів.','листкове живлення / калій','A'),
 ('haifa-mkp-0-52-34','Haifa MKP (Хайфа) 0-52-34, монокалійфосфат','Haifa Group','Haifa Group','Ізраїль','nutrition','Водорозчинне фосфорно-калійне добриво','Кристалічне водорозчинне','0-52-34','Монокалійфосфат для забезпечення рослин фосфором і калієм.','фосфор / калій / фертигація','A'),
 ('solupotasse','SoluPotasse (Солюпотас), сульфат калію','SoluPotasse','','—','nutrition','Калійне мінеральне добриво','Водорозчинне','—','Сульфат калію для калійного живлення культур.','калій / плодоношення','A'),
 ('magnesium-sulfate','Сульфат магнію, водорозчинне добриво','ALVENTA','ALVENTA','Польща','nutrition','Магнієво-сірчане водорозчинне добриво','Порошкове','—','Водорозчинне джерело магнію та сірки для живлення рослин.','магній / сірка','A'),
 ('boroplus','Boroplus (Бороплюс), борне добриво','Valagro','Valagro / Syngenta Biologicals','Італія','nutrition','Мікродобриво з бором','Рідкий','—','Борне мікродобриво для технологій живлення рослин.','бор / цвітіння','A'),
 ('brexil-combi','Brexil Combi (Брексіл Комбі), комплекс мікроелементів','Valagro','Valagro / Syngenta Biologicals','Італія','nutrition','Комплексне мікродобриво','Водорозчинні мікрогранули','—','Комплекс мікроелементів для позакореневого живлення.','мікроелементи','A'),
 ('brexil-fe','Brexil Fe (Брексіл Залізо), мікродобриво із залізом','Valagro','Valagro / Syngenta Biologicals','Італія','nutrition','Мікродобриво із залізом','Водорозчинні мікрогранули','—','Спеціалізоване мікродобриво із залізом для технологій живлення.','залізо / хлороз','A'),
 ('ferrilene','Ferrilene (Феррілен) 4,8% ortho-ortho, хелат заліза','Valagro','Valagro / Syngenta Biologicals','Італія','nutrition','Хелат заліза','Водорозчинне','—','Хелат заліза для кореневого внесення та корекції залізного живлення.','залізо / хлороз','A'),
 ('master-13-40-13','Master (Мастер) 13-40-13, водорозчинне мінеральне добриво','Valagro','Valagro S.p.A. / Syngenta Biologicals','Італія','nutrition','Водорозчинне комплексне добриво','Мікрокристалічне','13-40-13','Фосфорна формула лінійки Master для фертигації та стартових фаз розвитку.','фертигація / старт / фосфор','A'),
 ('master-15-5-30','Master (Мастер) 15-5-30, водорозчинне мінеральне добриво','Valagro','Valagro / Syngenta Biologicals','Італія','nutrition','Водорозчинне комплексне добриво','Мікрокристалічне','15-5-30','Калійна формула лінійки Master для фертигації у продуктивні фази.','фертигація / калій','A'),
 ('master-20-20-20','Master (Мастер) 20-20-20, водорозчинне мінеральне добриво','Valagro','Valagro / Syngenta Biologicals','Італія','nutrition','Водорозчинне комплексне добриво','Мікрокристалічне','20-20-20','Збалансована формула лінійки Master для фертигації.','фертигація / збалансоване живлення','A'),
 ('master-3-11-38','Master (Мастер) 3-11-38, водорозчинне мінеральне добриво','Valagro','Valagro / Syngenta Biologicals','Італія','nutrition','Водорозчинне комплексне добриво','Мікрокристалічне','3-11-38','Висококалійна формула лінійки Master для фертигації.','фертигація / калій / плодоношення','A'),
 ('kemira-rooter','Кеміра Укорінювач, біостимулятор розвитку кореневої системи','Кеміра','','—','biostimulation','Біостимулятор кореневої системи','Рідкий','—','Продукт для підтримки укорінення та розвитку кореневої системи.','коренева система / укорінення','A'),
 ('benefit-pz','Benefit PZ (Бенефіт ПЗ), біостимулятор збільшення плодів','Valagro','Valagro / Syngenta Biologicals','Італія','biostimulation','Біостимулятор','Рідкий','—','Біостимулятор для технологій формування та росту плодів.','формування / ріст плодів','B'),
 ('blackjak','BlackJak (Блекджек), біостимулятор розвитку кореневої системи','Valagro','Valagro / Syngenta Biologicals','Італія','biostimulation','Біостимулятор кореневої системи','Рідкий','—','Біостимулятор для підтримки кореневої системи.','коренева система','B'),
 ('maxicrop-cream','Maxicrop Cream (Максікроп Крем), біостимулятор','Maxicrop','Maxicrop / Syngenta Biologicals','—','biostimulation','Біостимулятор','Рідкий','—','Біостимулятор для загальної підтримки росту та розвитку рослин.','біостимуляція','B'),
 ('neocore','NeoCore (НеоКор), біостимулятор розвитку кореневої системи','Neova','Neova','—','biostimulation','Біостимулятор кореневої системи','Рідкий','—','Біостимулятор для підтримки розвитку кореневої системи.','коренева система','B'),
 ('sweet','Sweet (Світ), біостимулятор достигання та забарвлення плодів','Valagro','Valagro / Syngenta Biologicals','Італія','biostimulation','Біостимулятор','Рідкий','—','Біостимулятор для технологій достигання та формування забарвлення плодів.','достигання / забарвлення плодів','B'),
 ('osmocote-potassium-12-8-19','Osmocote Potassium 12-8-19 (3–4 міс.), добриво контрольованої дії','ICL','ICL','—','nutrition','Добриво контрольованої дії','Гранули','12-8-19','Калійна формула добрива контрольованої дії для тривалого живлення.','тривале живлення / калій','B'),
 ('osmocote-flowering-12-7-18','Osmocote Flowering 12-7-18 (2–3 міс.), добриво контрольованої дії','ICL','ICL','—','nutrition','Добриво контрольованої дії','Гранули','12-7-18','Формула добрива контрольованої дії для квітучих культур.','тривале живлення / цвітіння','B'),
 ('plantafol-0-25-50','Plantafol (Плантафол) 0-25-50, добриво для позакореневого живлення','Valagro','Valagro / Syngenta Biologicals','Італія','nutrition','Мінеральне водорозчинне добриво для листкового живлення','Водорозчинне','0-25-50','Висококалійна формула Plantafol для позакореневого живлення.','листкове живлення / калій','B'),
 ('plantafol-20-20-20','Plantafol (Плантафол) 20-20-20, добриво для позакореневого живлення','Valagro','Valagro S.p.A. / Syngenta Biologicals','Італія','nutrition','Мінеральне водорозчинне добриво для листкового живлення','Водорозчинне','20-20-20','Збалансована формула Plantafol для позакореневого живлення.','листкове живлення / збалансоване живлення','B'),
 ('brexil-ca','Brexil Ca (Брексіл Кальцій), мікродобриво з кальцієм','Valagro','Valagro / Syngenta Biologicals','Італія','nutrition','Кальцієве мікродобриво','Водорозчинні мікрогранули','—','Спеціалізоване мікродобриво з кальцієм.','кальцій','B'),
 ('brexil-zn','Brexil Zn (Брексіл Цинк), мікродобриво з цинком','Valagro','Valagro / Syngenta Biologicals','Італія','nutrition','Цинкове мікродобриво','Водорозчинні мікрогранули','—','Спеціалізоване мікродобриво з цинком.','цинк','B'),
]

SKU_ROWS=[
 ('control-dmp','100 мл','BB610-VLG-CONTROLDMP-100ML','A'),
 ('pekacid-0-60-20','1 кг','BB610-ICL-PEKACID-1KG','A'),('pekacid-0-60-20','100 г','BB610-ICL-PEKACID-100G','A'),
 ('kendal','25 мл','BB610-VLG-KENDAL-25ML','A'),
 ('megafol','100 мл','BB610-VLG-MEGAFOL-100ML','A'),('megafol','25 мл','BB610-VLG-MEGAFOL-25ML','A'),
 ('radifarm','25 мл','BB610-VLG-RADIFARM-25ML','A'),('viva','100 мл','BB610-VLG-VIVA-100ML','A'),
 ('osmocote-landscape-16-9-12','200 г','BB610-ICL-OSMOCOTE-LANDSCAPE-200G','A'),('osmocote-quick-start-22-5-6','200 г','BB610-ICL-OSMOCOTE-QUICKSTART-200G','A'),
 ('plantafol-10-54-10','250 г','BB610-VLG-PLANTAFOL105410-250G','A'),('plantafol-30-10-10','250 г','BB610-VLG-PLANTAFOL301010-250G','A'),('plantafol-5-15-45','250 г','BB610-VLG-PLANTAFOL51545-250G','A'),
 ('haifa-mkp-0-52-34','200 г','BB610-HAIFA-MKP005234-200G','A'),('solupotasse','1 кг','BB610-SOLUPOTASSE-K2SO4-1KG','A'),('magnesium-sulfate','1 кг','BB610-ALVENTA-MGSO4-1KG','A'),
 ('boroplus','100 мл','BB610-VLG-BOROPLUS-100ML','A'),('brexil-combi','15 г','BB610-VLG-BREXILCOMBI-15G','A'),('brexil-fe','15 г','BB610-VLG-BREXILFE-15G','A'),('ferrilene','10 г','BB610-VLG-FERRILENE-10G','A'),
 ('master-13-40-13','1 кг','BB610-VLG-MASTER134013-1KG','A'),('master-13-40-13','250 г','BB610-VLG-MASTER134013-250G','A'),
 ('master-15-5-30','1 кг','BB610-VLG-MASTER15530-1KG','A'),('master-15-5-30','250 г','BB610-VLG-MASTER15530-250G','A'),
 ('master-20-20-20','1 кг','BB610-VLG-MASTER202020-1KG','A'),('master-20-20-20','250 г','BB610-VLG-MASTER202020-250G','A'),
 ('master-3-11-38','1 кг','BB610-VLG-MASTER31138-1KG','A'),('master-3-11-38','250 г','BB610-VLG-MASTER31138-250G','A'),
 ('kemira-rooter','100 мл','BB610-KEMIRA-ROOTER-100ML','A'),
 ('benefit-pz','25 мл','BB610-VLG-BENEFITPZ-25ML','B'),('blackjak','100 мл','BB610-VLG-BLACKJAK-100ML','B'),('maxicrop-cream','25 мл','BB610-MAXICROP-CREAM-25ML','B'),('neocore','30 мл','BB610-NEOVA-NEOCORE-30ML','B'),('sweet','25 мл','BB610-VLG-SWEET-25ML','B'),
 ('osmocote-potassium-12-8-19','200 г','BB610-ICL-OSMOCOTE-POTASSIUM-200G','B'),('osmocote-flowering-12-7-18','200 г','BB610-ICL-OSMOCOTE-FLOWERING-200G','B'),
 ('plantafol-0-25-50','250 г','BB610-VLG-PLANTAFOL02550-250G','B'),('plantafol-20-20-20','250 г','BB610-VLG-PLANTAFOL202020-250G','B'),('brexil-ca','15 г','BB610-VLG-BREXILCA-15G','B'),('brexil-zn','15 г','BB610-VLG-BREXILZN-15G','B'),
]
assert len(SKU_ROWS)==40

products_by_id={p['id']:p for p in master.get('products',[])}
prod_defs={r[0]:r for r in PRODUCTS}

supplier_source={'title':'Organic Planet — стартова матриця BB610: назва та фасування','url':'https://organicplanet.com.ua/','verifiedAt':TODAY,'primary':False}

def clean_desc(name,short):
    return f"{short} Купити в BB610 Market з доставкою по Україні. Фактичні ціна та наявність відображаються для конкретної фасовки."

def alt_for(name):
    return re.sub(r'\s+',' ',name).strip()

for row in PRODUCTS:
    pid,name,brand,manufacturer,country,cat,ptype,form,npk,short,purpose,priority=row
    p=products_by_id.get(pid)
    is_new=p is None
    if is_new:
        p={'id':pid,'slug':pid}
        master.setdefault('products',[]).append(p); products_by_id[pid]=p
    # Keep already-verified manufacturer technical content. Curated commercial-facing fields are refreshed.
    p.update({
      'slug':p.get('slug') or pid,
      'name':name,'official_name':p.get('official_name') or name.split(',')[0],
      'brand':brand,'manufacturer':manufacturer,'country':country,
      'category_id':cat,'product_type':ptype,'form':form,'npk':npk,
      'short_description':short,
      'selected_by_bb610':True,
      'launch_matrix_priority':priority,
      'launch_matrix_2026':True,
      'feed_policy':'allowed',
      'seo':{
        'title':f"{name} — {brand}" if brand else name,
        'description':clean_desc(name,short),
      },
      'feed':{
        'title':f"{name} — {brand}" if brand else name,
        'description':short,
        'brand_required':bool(brand),
      },
      'image_alt':alt_for(name),
    })
    p.setdefault('active_ingredient','—'); p.setdefault('concentration','')
    p.setdefault('composition',[]); p.setdefault('cultures',[]); p.setdefault('purposes',[purpose])
    if not p.get('purposes'): p['purposes']=[purpose]
    p.setdefault('manufacturer_use',short)
    if not p.get('manufacturer_use'): p['manufacturer_use']=short
    p.setdefault('application','Застосовувати відповідно до актуальної етикетки/інструкції для конкретної культури та способу внесення.')
    p.setdefault('rate','Норма внесення залежить від культури, фази розвитку та способу застосування; звіряти з актуальною етикеткою.')
    p.setdefault('restrictions','Перед застосуванням перевірити актуальну етикетку, сумісність та локальні вимоги. Не перевищувати регламент виробника.')
    p.setdefault('target',''); p.setdefault('waiting_period',''); p.setdefault('hazard_class',''); p.setdefault('registration','')
    p.setdefault('factory_packs',[]); p.setdefault('documents',[])
    if not p.get('source'):
        p['source']=dict(supplier_source)
    if not p.get('verification'):
        p['verification']={'status':'supplier-matrix-verified','verified':False,'verifiedAt':TODAY,'scope':'Назва та фасування підтверджені матрицею постачальника; технічні твердження потребують первинного джерела','note':'BB610 не вигадує технічні характеристики, GTIN або MPN.'}
    # Real-photo readiness is an explicit feed gate. Placeholder cards can be sold but not exported to ad feeds.
    real=REAL_IMAGES.get(pid)
    if real:
        cur=p.get('image')
        if not cur or not (isinstance(cur,dict) and cur.get('local')):
            p['image']={'local':real,'officialSourceUrl':'','status':'local-imported-photo'}
        p['feed_image_ready']=True
    else:
        if not p.get('image'):
            p['image']={'local':PLACEHOLDER[cat],'officialSourceUrl':'','status':'category-placeholder'}
        # Existing real product photos may already exist under /assets/img/real or CMS media.
        loc=(p.get('image') or {}).get('local','') if isinstance(p.get('image'),dict) else str(p.get('image') or '')
        p['feed_image_ready']=('/real/' in loc or loc.startswith('/media/products/') or loc.startswith('https://'))
    p['canonical_product_url']=f"/products/{p['slug']}/"
    p['legacy_url']=f"product.html?id={pid}"
    p['store_content_status']='launch-card-ready'

variants_by_id={v['id']:v for v in master.get('variants',[])}
skus_by_id={s['id']:s for s in master.get('skus',[])}
launch_by_product={}

def pack_parts(label):
    m=re.match(r'([0-9]+(?:[.,][0-9]+)?)\s*(мл|л|г|кг)$',label.strip(),re.I)
    if not m:return (1,'pcs')
    val=float(m.group(1).replace(',','.')); unit={'мл':'ml','л':'l','г':'g','кг':'kg'}[m.group(2).lower()]
    return (int(val) if val.is_integer() else val,unit)

def pack_slug(label):
    return label.lower().replace(' ','').replace('мл','ml').replace('кг','kg').replace('г','g').replace('л','l').replace(',','-')

for pid,pack,sku_id,priority in SKU_ROWS:
    p=products_by_id[pid]
    slug=f"{p['slug']}-{pack_slug(pack)}"
    vid=f"{pid}--{pack_slug(pack)}"
    val,unit=pack_parts(pack)
    v=variants_by_id.get(vid)
    if v is None:
        v={'id':vid,'product_id':pid}; master.setdefault('variants',[]).append(v); variants_by_id[vid]=v
    v.update({'label':pack,'quantity':val,'unit':unit,'status':'supplier-matrix-confirmed'})
    s=skus_by_id.get(sku_id)
    if s is None:
        s={'id':sku_id,'sku':sku_id}; master.setdefault('skus',[]).append(s); skus_by_id[sku_id]=s
    # Never import supplier/RRP prices. Admin DB is the live authority for price/stock.
    s.update({
      'sku':sku_id,'product_id':pid,'variant_id':vid,'slug':slug,'variant':pack,
      'volume_weight':{'value':val,'unit':unit},
      'gtin_ean':s.get('gtin_ean'), 'mpn':s.get('mpn'),
      'price':None,'currency':'UAH','availability':'unknown','stock_label':'Наявність уточнюється',
      'offer_status':'draft','feed_eligible':False,
      'url':f"/products/{slug}/",
      'supplier':s.get('supplier'),'importer':s.get('importer'),'packer':s.get('packer'),
      'shipping':['Доставка по Україні згідно з умовами BB610 Market'],
      'commercial_status':'not-configured',
      'commercial_note':'Stage 16A: картка підготовлена; ціну, фактичну наявність, кількість і Продаж оператор задає вручну в адмінці.',
      'pack_source_status':'supplier-matrix-confirmed',
      'launch_matrix_priority':priority,'launch_matrix_2026':True,
      'feed_policy':'allowed',
      'identifier_status':'unverified',
    })
    if pid=='megafol' and pack=='25 мл': s['image']='assets/img/real/megafol-25ml.png'; s['feed_image_ready']=True
    elif pid=='megafol' and pack=='100 мл': s['image']='assets/img/real/megafol-100ml.png'; s['feed_image_ready']=True
    else:
        curimg=str(s.get('image') or '')
        # Keep a SKU-specific real photo if one already exists; otherwise inherit the product image dynamically.
        s['image']=curimg if (('/real/' in curimg or curimg.startswith('/media/products/') or curimg.startswith('https://')) and not curimg.endswith('.svg')) else None
        s.pop('feed_image_ready',None)
    launch_by_product.setdefault(pid,[]).append(sku_id)

for pid,ids in launch_by_product.items():
    products_by_id[pid]['default_sku_id']=ids[0]
    products_by_id[pid]['launch_sku_ids']=ids

master.setdefault('launch_matrices',{})['organic_planet_2026']={
 'name':'BB610 Market — стартова матриця Organic Planet 2026',
 'updated_at':TODAY,'sku_count':40,'priority_a_count':29,'priority_b_count':11,
 'pricing':'manual-admin','stock':'manual-admin',
 'note':'Stage 16A does not import supplier wholesale/RRP values into live commerce.'
}

# Ensure no accidental duplicate product/variant/SKU identities were introduced.
for key in ('products','variants','skus'):
    vals=[x['id'] for x in master.get(key,[])]
    dup=sorted({x for x in vals if vals.count(x)>1})
    if dup: raise SystemExit(f'duplicate {key}: {dup}')

PATH.write_text(json.dumps(master,ensure_ascii=False,indent=2)+"\n",encoding='utf-8')
print(f"Stage 16A catalog seed: 34 product families curated; 40 launch SKU guaranteed; prices/stock NOT imported")
