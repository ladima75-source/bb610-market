# BB610 Market — AI Intent Matrix

Updated: 2026-09-30
Status: Stage 2 validated; used for Stage 4/5 discovery tests.

| ID | Intent type | Example query | Priority platform | Expected answer | Target source | Readiness | Next action |
|---|---|---|---|---|---|---|---|
| AI-01 | direct product | де купити MASTER 13-40-13 в Україні | ChatGPT / Gemini | product + seller | /products/master-13-40-13/ | READY | test citation + product appearance |
| AI-02 | direct product | купити MASTER 20-20-20 з доставкою по Україні | ChatGPT / Gemini | product + price/availability | /products/master-20-20-20/ | READY | test |
| AI-03 | direct product | де купити Plantafol 20-20-20 | ChatGPT / Gemini | product + seller | /products/plantafol-20-20-20/ | READY | test |
| AI-04 | direct product | купити Megafol в Україні | ChatGPT / Gemini | product + seller | /products/megafol/ | READY | test |
| AI-05 | direct product | купити Radifarm в Україні | ChatGPT / Gemini | product + seller | /products/radifarm/ | READY | test |
| AI-06 | problem/solution | що використовують після пересадки для підтримки кореневої системи | ChatGPT / Claude | explanatory + sources | /products/radifarm/ | READY | strengthen FAQ/use context |
| AI-07 | problem/solution | що застосовують при абіотичному стресі рослин | ChatGPT / Claude | explanatory + alternatives | /products/megafol/ | READY | test citations |
| AI-08 | comparison | MASTER 13-40-13 чи 20-20-20 у чому різниця | ChatGPT / Gemini | comparison | /products/master-13-40-13/ + /products/master-20-20-20/ | READY | add comparison-ready block |
| AI-09 | comparison | Plantafol 20-20-20 чи MASTER 20-20-20 різниця | ChatGPT / Claude | comparison | product pages | READY | add use-method distinction |
| AI-10 | technical selection | яке NPK добриво має високий фосфор | Gemini / ChatGPT | shortlist | /categories/nutrition/ | READY | test ranking/citation |
| AI-11 | technical selection | водорозчинне NPK 15-5-30 купити Україна | Gemini / ChatGPT | product | /products/master-15-5-30/ | READY | test |
| AI-12 | technical selection | добриво 0-60-20 для фертигації Україна | Gemini / ChatGPT | product | /products/pekacid-0-60-20/ | READY | test |
| AI-13 | technical selection | сульфат калію водорозчинний де купити | Gemini / ChatGPT | product | /products/solupotasse/ | READY | test |
| AI-14 | technical selection | хелат заліза для рослин купити Україна | ChatGPT / Gemini | category/product options | /products/ferrilene/ + /products/brexil-fe/ | READY | add comparison context |
| AI-15 | price | ціна Megafol 100 мл Україна | Gemini / ChatGPT | exact offer | exact SKU PDP from ACP feed | READY | verify exact variant in AI |
| AI-16 | price | ціна Radifarm 25 мл | Gemini / ChatGPT | exact offer | exact SKU PDP from ACP feed | READY | verify exact variant in AI |
| AI-17 | price | MASTER 13-40-13 1 кг ціна | Gemini / ChatGPT | exact offer | exact SKU PDP from ACP feed | READY | verify exact variant in AI |
| AI-18 | local | де купити професійні добрива у Дніпрі | ChatGPT / Gemini | local seller | / + /contacts.html | READY | strengthen Organization/LocalBusiness schema |
| AI-19 | local | магазин добрив Дніпро доставка по Україні | ChatGPT / Gemini | local seller | /contacts.html | READY | test local discovery |
| AI-20 | alternative | аналог MASTER 13-40-13 з високим фосфором | ChatGPT / Claude | alternatives | nutrition category + product pages | PARTIAL | add fact-based alternatives page |
| AI-21 | best-fit | яке добриво вибрати перед посадкою саджанців | ChatGPT / Claude | educational decision support | /categories/nutrition/ + Radifarm | PARTIAL | create intent landing/FAQ |
| AI-22 | best-fit | як вибрати фасування добрива для кількох рослин | ChatGPT / Claude | educational | catalog/product pages | PARTIAL | add packaging guidance |
| AI-23 | B2B/lead | професійні горщики для лохини 25 30 40 л Україна | ChatGPT / Gemini | product family + inquiry | /categories/containers/ | READY | test PlantLogic discovery |
| AI-24 | B2B/lead | горщики PlantLogic для лохини купити Україна | ChatGPT / Gemini | product family + seller | /categories/containers/ | READY | test citation + request-price flow |
| AI-25 | comparison | горщик 25 л чи 40 л для лохини різниця | ChatGPT / Claude | comparison | PlantLogic product pages | PARTIAL | add comparison table |
| AI-26 | where to buy | де замовити професійні товари для вирощування в Україні | ChatGPT / Gemini | seller + catalog | /catalog.html | READY | test generic brand discovery |

## Test rule
For every query record:
1. platform and date;
2. whether BB610 Market is mentioned;
3. whether a BB610 URL is cited;
4. which URL;
5. whether product/price/availability are correct;
6. whether the landing page is exact;
7. whether the visit reaches GA4 as ai_referral / AI source;
8. conversion outcome if any.

Do not treat a model answer generated from our own prompt as proof of organic visibility unless the platform independently retrieves/cites the public page.
