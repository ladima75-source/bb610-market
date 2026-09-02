#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from pathlib import Path

ROOT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
PATH=ROOT/'data'/'catalog.master.json'
master=json.loads(PATH.read_text(encoding='utf-8'))

# Customer-facing Ukrainian titles. Pack size is displayed by the SKU/variant,
# so the family title stays readable and is not duplicated.
PRODUCT_CONTENT = {
 'control-dmp': {
   'title':'Control DMP (Контроль ДМП), регулятор кислотності та прилипач',
   'brand':'Valagro',
   'query':'Control DMP Контроль ДМП 100 мл Valagro',
   'source_url':'https://organicplanet.com.ua/katalog/zasobi-zahistu-roslin/control-dmp-kontrol-dmp-pidkyslyuvach-prylypach-100-ml-valagro'
 },
 'pekacid-0-60-20': {
   'title':'PeKacid (Пекацид) NPK 0-60-20, фосфорно-калійне добриво',
   'brand':'ICL',
   'query':'PeKacid Пекацид NPK 0-60-20 1 кг',
   'source_url':'https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/pekacid-pekacyd-mineralne-dobryvo-npk-0-60-20-1-kg'
 },
 'kendal': {
   'title':'Kendal (Кендал), біостимулятор для підтримки імунної системи рослин',
   'brand':'Valagro',
   'query':'Kendal Кендал біостимулятор 100 мл Valagro',
   'source_url':'https://organicplanet.com.ua/katalog/biostymulyatory/kendal-kendal-biostymulyator-profilaktyka-hvorob-100-ml-valagro'
 },
 'megafol': {
   'title':'Megafol (Мегафол), біостимулятор-антистрес',
   'brand':'Valagro',
   'query':'Megafol Мегафол біостимулятор антистрес 100 мл Valagro',
   'source_url':'https://organicplanet.com.ua/katalog/biostymulyatory/megafol-megafol-biostimulyator-antistress-100-ml-valagro'
 },
 'radifarm': {
   'title':'Radifarm (Радіфарм), біостимулятор росту кореневої системи (укорінювач)',
   'brand':'Valagro',
   'query':'Radifarm Радіфарм біостимулятор кореневої системи 25 мл Valagro',
   'source_url':'https://organicplanet.com.ua/katalog/biostymulyatory/biodobryva-biologichni/radifarm-radifarm-biostimulyator-rosta-kornevoj-sistemy-ukor4'
 },
 'viva': {
   'title':'Viva (Віва), біостимулятор та активатор ґрунтової мікрофлори',
   'brand':'Valagro',
   'query':'Viva Віва біостимулятор активатор ґрунтової мікрофлори 100 мл Valagro',
   'source_url':'https://organicplanet.com.ua/katalog/biostymulyatory/viva-viva-organicheskoe-udobrenie-biostimulyator-100-ml-vala'
 },
 'osmocote-landscape-16-9-12': {
   'title':'Osmocote Landscape 16-9-12, добриво контрольованої дії 3–4 міс.',
   'brand':'ICL',
   'query':'Osmocote Landscape 16-9-12 200 г'
 },
 'osmocote-quick-start-22-5-6': {
   'title':'Osmocote Quick Start 22-5-6, добриво контрольованої дії 4–5 міс.',
   'brand':'ICL',
   'query':'Osmocote Quick Start 22-5-6 200 г'
 },
 'plantafol-10-54-10': {
   'title':'Plantafol (Плантафол) NPK 10-54-10, мінеральне добриво для позакореневого живлення',
   'brand':'Valagro',
   'query':'Plantafol Плантафол NPK 10-54-10 250 г Valagro',
   'source_url':'https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-udobrenie-1-kg-npk-10-54-10-v'
 },
 'plantafol-30-10-10': {
   'title':'Plantafol (Плантафол) NPK 30-10-10, мінеральне добриво для позакореневого живлення',
   'brand':'Valagro',
   'query':'Plantafol Плантафол NPK 30-10-10 250 г Valagro',
   'source_url':'https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-udobrenie-1-kg-npk-30-10-10-v'
 },
 'plantafol-5-15-45': {
   'title':'Plantafol (Плантафол) NPK 5-15-45, мінеральне добриво для позакореневого живлення',
   'brand':'Valagro',
   'query':'Plantafol Плантафол NPK 5-15-45 250 г Valagro',
   'source_url':'https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralne-dobryvo-250-g-npk-5-15-45-valagro'
 },
 'plantafol-0-25-50': {
   'title':'Plantafol (Плантафол) NPK 0-25-50, мінеральне добриво для позакореневого живлення',
   'brand':'Valagro',
   'query':'Plantafol Плантафол NPK 0-25-50 250 г Valagro'
 },
 'plantafol-20-20-20': {
   'title':'Plantafol (Плантафол) NPK 20-20-20, мінеральне добриво для позакореневого живлення',
   'brand':'Valagro',
   'query':'Plantafol Плантафол NPK 20-20-20 250 г Valagro'
 },
 'haifa-mkp-0-52-34': {
   'title':'Haifa MKP 0-52-34, монокалійфосфат — водорозчинне добриво',
   'brand':'Haifa Group',
   'query':'Haifa MKP 0-52-34 200 г монокалійфосфат'
 },
 'solupotasse': {
   'title':'SoluPotasse (Солюпотас), сульфат калію',
   'brand':'SoluPotasse',
   'query':'SoluPotasse Солюпотас сульфат калію 1 кг',
   'source_url':'https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/solupotasse-solyupotass-sulfat-kaliyu-1-kg'
 },
 'magnesium-sulfate': {
   'title':'Сульфат магнію, водорозчинне магнієво-сірчане добриво',
   'brand':'ALVENTA',
   'query':'Сульфат магнію 1 кг ALVENTA'
 },
 'boroplus': {
   'title':'Boroplus (Бороплюс), хелат бору',
   'brand':'Valagro',
   'query':'Boroplus Бороплюс хелат бору 100 мл Valagro',
   'source_url':'https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/boroplus-boroplyus-helat-boru-100-ml-valagro'
 },
 'brexil-combi': {
   'title':'Brexil Combi (Брексіл Комбі), мікроелементи в хелатній формі',
   'brand':'Valagro',
   'query':'Brexil Combi Брексіл Комбі 15 г Valagro',
   'source_url':'https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/brexil-combi-breksil-kombi-mikroelementy-15-g-valagro'
 },
 'brexil-fe': {
   'title':'Brexil Fe (Брексіл Залізо), мікроелементи в хелатній формі',
   'brand':'Valagro',
   'query':'Brexil Fe Брексіл Залізо 15 г Valagro',
   'source_url':'https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/brexil-fe-breksil-zalizo-mikroelementy-v-helatnij-formi-15-g-valagro'
 },
 'brexil-ca': {
   'title':'Brexil Ca (Брексіл Кальцій), мікроелементи в хелатній формі',
   'brand':'Valagro',
   'query':'Brexil Ca Брексіл Кальцій 15 г Valagro',
   'source_url':'https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/brexil-ca-breksil-kalcij-mikroelementy-15-g-valagro'
 },
 'brexil-zn': {
   'title':'Brexil Zn (Брексіл Цинк), мікроелементи в хелатній формі',
   'brand':'Valagro',
   'query':'Brexil Zn Брексіл Цинк 15 г Valagro',
   'source_url':'https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/brexil-zn-breksil-cynk-mikroelementy-v-helatnij-formi-15-g-valagro'
 },
 'ferrilene': {
   'title':'Ferrilene (Феррілен) 4,8% ortho-ortho, хелат заліза EDDHA',
   'brand':'Valagro',
   'query':'Ferrilene Феррілен 4,8 ortho ortho 10 г Valagro',
   'source_url':'https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/ferrilene-ferrilen-48-orto-orto-helat-zheleza-10-g-valagro'
 },
 'master-13-40-13': {
   'title':'Master (Мастер) NPK 13-40-13, водорозчинне мінеральне добриво',
   'brand':'Valagro',
   'query':'Master Мастер NPK 13-40-13 1 кг Valagro',
   'source_url':'https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralne-dobryvo-1-kg-npk-13-40-13-valagro'
 },
 'master-15-5-30': {
   'title':'Master (Мастер) NPK 15-5-30, водорозчинне мінеральне добриво',
   'brand':'Valagro',
   'query':'Master Мастер NPK 15-5-30 250 г Valagro',
   'source_url':'https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralne-dobryvo-250-g-npk-15-5-30-valagro'
 },
 'master-20-20-20': {
   'title':'Master (Мастер) NPK 20-20-20, водорозчинне мінеральне добриво',
   'brand':'Valagro',
   'query':'Master Мастер NPK 20-20-20 1 кг Valagro',
   'source_url':'https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralne-dobryvo-1-kg-npk-20-20-20-valagro'
 },
 'master-3-11-38': {
   'title':'Master (Мастер) NPK 3-11-38, водорозчинне мінеральне добриво',
   'brand':'Valagro',
   'query':'Master Мастер NPK 3-11-38 250 г Valagro',
   'source_url':'https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralne-dobryvo-250-g-npk-3-11-38-valagro'
 },
 'kemira-rooter': {
   'title':'Кеміра Укорінювач, біостимулятор розвитку кореневої системи',
   'brand':'Organic Planet',
   'query':'Кеміра Укорінювач 100 мл Organic Planet'
 },
 'benefit-pz': {
   'title':'Benefit PZ (Бенефіт ПЗ), біостимулятор збільшення плодів',
   'brand':'Valagro',
   'query':'Benefit Pz Бенефіт ПЗ 25 г Valagro',
   'source_url':'https://organicplanet.com.ua/katalog/biostymulyatory/benefit-pz-benefit-pz-biostimulyator-uvelicheniya-plodov-25'
 },
 'blackjak': {
   'title':'BlackJak (БлекДжек), біостимулятор розвитку кореневої системи',
   'brand':'Valagro',
   'query':'BlackJak БлекДжек біостимулятор 100 мл Valagro'
 },
 'maxicrop-cream': {
   'title':'Maxicrop Cream (Максікроп Крем), біостимулятор на основі екстракту водоростей',
   'brand':'Valagro',
   'query':'Maxicrop Cream Максікроп Крем 25 г Valagro',
   'source_url':'https://organicplanet.com.ua/katalog/biostymulyatory/maxicrop-cream-maksikrop-krem-biostimulyator-25-ml-valagro'
 },
 'neocore': {
   'title':'NeoCore (НеоКор), біостимулятор росту кореневої системи, біоактивний екстракт торфу',
   'brand':'Neova',
   'query':'NeoCore НеоКор 30 мл Neova',
   'source_url':'https://organicplanet.com.ua/katalog/biostymulyatory/neocore-neokor-biostymulyator-rostu-korenevoyi-systemy-bioaktyvnyj-ekstrakt-torfu-30-ml-neova'
 },
 'sweet': {
   'title':'Sweet (Світ), біостимулятор дозрівання та забарвлення плодів',
   'brand':'Valagro',
   'query':'Sweet Світ біостимулятор 100 мл Valagro',
   'source_url':'https://organicplanet.com.ua/katalog/biostymulyatory/sweet-svit-biostimulyator-okraski-plodov-100-ml-valagro'
 },
 'osmocote-potassium-12-8-19': {
   'title':'Osmocote Potassium 12-8-19, добриво контрольованої дії 3–4 міс.',
   'brand':'ICL',
   'query':'Osmocote Potassium 12-8-19 200 г'
 },
 'osmocote-flowering-12-7-18': {
   'title':'Osmocote Flowering 12-7-18, добриво контрольованої дії 2–3 міс.',
   'brand':'ICL',
   'query':'Osmocote Flowering 12-7-18 200 г'
 },
}

# Existing non-launch cards visible in the old catalogue are also normalised.
LEGACY = [
 ('brexil mix','Brexil Mix (Брексіл Мікс), мікроелементи в хелатній формі','Valagro','Brexil Mix Брексіл Мікс 15 г Valagro'),
 ('kendal root','Kendal Root (Кендал Рут), біостимулятор-антистрес для кореневої системи','Valagro','Kendal Root Кендал Рут 100 мл Valagro'),
 ('світч','Світч 62,5 WG, в. г., фунгіцид','Syngenta','Світч 62,5 WG фунгіцид 10 г Syngenta'),
 ('switch','Світч 62,5 WG, в. г., фунгіцид','Syngenta','Світч 62,5 WG фунгіцид 10 г Syngenta'),
 ('актара','Актара 25 WG, в. г., системний інсектицид','Syngenta','Актара 25 WG інсектицид Syngenta'),
 ('aktara','Актара 25 WG, в. г., системний інсектицид','Syngenta','Актара 25 WG інсектицид Syngenta'),
 ('new 25 liter round pot','Plantlogic NEW 25 Liter Round Pot, контейнер 25 л для субстратного вирощування','Plantlogic','Plantlogic NEW 25 Liter Round Pot 1308125'),
 ('40 liters round pot','Plantlogic 40 Liter Round Pot with U-Grooves, контейнер 40 л для субстратного вирощування','Plantlogic','Plantlogic 40 Liter Round Pot U-Grooves 1308041'),
 ('40 liter round pot','Plantlogic 40 Liter Round Pot with U-Grooves, контейнер 40 л для субстратного вирощування','Plantlogic','Plantlogic 40 Liter Round Pot U-Grooves 1308041'),
]

products={p.get('id'):p for p in master.get('products',[])}

def update_title(p,title,brand,query,source_url=''):
    p['name']=title
    # Stage 16A preserved old official_name for existing cards; catalogue cards
    # use that field in several code paths. Stage 16B intentionally replaces it.
    p['official_name']=title
    if brand: p['brand']=brand
    p['image_alt']=title
    p.setdefault('seo',{})
    p['seo']['title']=(f"{title} — {brand}" if brand else title)[:180]
    desc=(p.get('short_description') or p.get('manufacturer_use') or p.get('product_type') or '').strip()
    if desc:
        p['seo']['description']=(desc + ' Ціна та наявність — для вибраної фасовки в BB610 Market.')[:320]
    p.setdefault('feed',{})
    p['feed']['title']=f"{title} — {brand}" if brand else title
    if desc: p['feed']['description']=desc
    p['stage16b_image_query']=query
    if source_url: p['stage16b_source_url']=source_url
    p['stage16b_content_status']='title-ready-image-pending'

for pid,info in PRODUCT_CONTENT.items():
    p=products.get(pid)
    if not p: continue
    update_title(p,info['title'],info.get('brand',''),info.get('query',''),info.get('source_url',''))

# Normalise the visible legacy cards without changing commercial state/prices.
for p in master.get('products',[]):
    hay=' '.join(str(p.get(k,'') or '') for k in ('id','name','official_name','slug')).lower()
    if p.get('id') in PRODUCT_CONTENT: continue
    for needle,title,brand,query in LEGACY:
        if needle in hay:
            update_title(p,title,brand,query,'')
            # regulated protection products are NOT automatically ad-feed allowed.
            if needle in ('світч','switch','актара','aktara'):
                p['feed_policy']='review-required'
            break

# Build SKU-specific feed titles: product + exact pack + brand.
for s in master.get('skus',[]):
    p=products.get(s.get('product_id'))
    if not p: continue
    pack=str(s.get('variant') or '').strip()
    brand=str(p.get('brand') or '').strip()
    title=str(p.get('official_name') or p.get('name') or '').strip()
    if title:
        s.setdefault('feed',{})
        s['feed']['title']=' — '.join(x for x in [f"{title}, {pack}" if pack else title, brand] if x)[:150]
        s['image_alt']=f"{title}, {pack}" if pack else title

PATH.write_text(json.dumps(master,ensure_ascii=False,indent=2)+"\n",encoding='utf-8')
print(f"Stage 16B content: {sum(1 for p in master.get('products',[]) if p.get('stage16b_content_status'))} product cards normalised")
