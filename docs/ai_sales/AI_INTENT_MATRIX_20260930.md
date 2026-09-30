# BB610 Market — AI Intent Matrix

Updated: 2026-09-30
Status: Stage 2 validated; used for Stage 4/5 discovery tests.

Cross-engine rule: every commercial intent is prepared for ChatGPT, Google Gemini and Claude in Ukraine. The platform column no longer means exclusivity; all three engines are mandatory coverage targets.

| ID | Intent type | Example query | Priority platform | Expected answer | Target source | Readiness | Next action |
|---|---|---|---|---|---|---|---|
| AI-01 | direct product | де купити MASTER 13-40-13 в Україні | ChatGPT / Gemini / Claude | product + seller + offer range | /products/master-13-40-13/ | OPTIMIZED · UNVERIFIED | AggregateOffer live; verify citation/product appearance |
| AI-02 | direct product | купити MASTER 20-20-20 з доставкою по Україні | ChatGPT / Gemini / Claude | product + price/availability | /products/master-20-20-20/ | OPTIMIZED · UNVERIFIED | family commerce parity live; verify discovery |
| AI-03 | direct product | де купити Plantafol 20-20-20 | ChatGPT / Gemini / Claude | product + seller + offer range | /products/plantafol-20-20-20/ | OPTIMIZED · UNVERIFIED | family commerce parity live; verify discovery |
| AI-04 | direct product | купити Megafol в Україні | ChatGPT / Gemini / Claude | product + seller + offer range | /products/megafol/ | OPTIMIZED · UNVERIFIED | AggregateOffer + intent guides live; verify discovery |
| AI-05 | direct product | купити Radifarm в Україні | ChatGPT / Gemini / Claude | product + seller + offer range | /products/radifarm/ | OPTIMIZED · UNVERIFIED | AggregateOffer + intent guides live; verify discovery |
| AI-06 | problem/solution | що використовують після пересадки для підтримки кореневої системи | ChatGPT / Gemini / Claude | explanatory + product context | /guides/before-planting-seedlings-product-selection/ | OPTIMIZED | verify citation/indexing |
| AI-07 | problem/solution | що застосовують при абіотичному стресі рослин | ChatGPT / Gemini / Claude | explanatory + product context | /guides/abiotic-stress-and-megafol/ | OPTIMIZED | verify citation/indexing |
| AI-08 | comparison | MASTER 13-40-13 чи 20-20-20 у чому різниця | ChatGPT / Gemini / Claude | comparison | /guides/master-13-40-13-vs-20-20-20/ | OPTIMIZED | verify citation/indexing |
| AI-09 | comparison | Plantafol 20-20-20 чи MASTER 20-20-20 різниця | ChatGPT / Gemini / Claude | comparison | /guides/plantafol-20-20-20-vs-master-20-20-20/ | OPTIMIZED | verify citation/indexing |
| AI-10 | technical selection | яке NPK добриво має високий фосфор | ChatGPT / Gemini / Claude | shortlist with application-method caveat | /guides/high-phosphorus-alternatives-master-13-40-13/ | OPTIMIZED | verify citation/indexing |
| AI-11 | technical selection | водорозчинне NPK 15-5-30 купити Україна | ChatGPT / Gemini / Claude | product + offer range | /products/master-15-5-30/ | OPTIMIZED · UNVERIFIED | family V5 parity fixed: from 170 UAH, 3 active offers; verify discovery |
| AI-12 | technical selection | добриво 0-60-20 для фертигації Україна | ChatGPT / Gemini / Claude | product + offer range | /products/pekacid-0-60-20/ | OPTIMIZED · UNVERIFIED | commerce family page + comparison context ready; verify discovery |
| AI-13 | technical selection | сульфат калію водорозчинний де купити | ChatGPT / Gemini / Claude | exact purchasable offer | /products/solupotasse-sulfat-kaliyu-1kg/ | OPTIMIZED · UNVERIFIED | canonical V5 product is solupotasse-sulfat-kaliyu; legacy /solupotasse/ is not the commerce source |
| AI-14 | technical selection | хелат заліза для рослин купити Україна | ChatGPT / Gemini / Claude | product options by application method | /guides/ferrilene-vs-brexil-fe/ | OPTIMIZED | verify citation/indexing |
| AI-15 | price | ціна Megafol 100 мл Україна | ChatGPT / Gemini / Claude | exact offer | /products/megafol-100ml/ | OPTIMIZED · UNVERIFIED | current discovery test returned competitors, not BB610 |
| AI-16 | price | ціна Radifarm 25 мл | ChatGPT / Gemini / Claude | exact offer | /products/radifarm-25ml/ | OPTIMIZED · UNVERIFIED | current discovery test returned no BB610 exact result |
| AI-17 | price | MASTER 13-40-13 1 кг ціна | ChatGPT / Gemini / Claude | exact offer | /products/master-13-40-13-1kg/ | OPTIMIZED · UNVERIFIED | current discovery test returned competitors, not BB610 |
| AI-18 | local | де купити професійні добрива у Дніпрі | ChatGPT / Gemini / Claude | local seller | /dnipro/ + /contacts.html | OPTIMIZED · UNVERIFIED | dedicated factual Dnipro landing live; verify local citation/indexing |
| AI-19 | local | магазин добрив Дніпро доставка по Україні | ChatGPT / Gemini / Claude | local seller | /dnipro/ + /delivery.html | OPTIMIZED · UNVERIFIED | local pickup/delivery facts live; verify local citation/indexing |
| AI-20 | alternative | аналог MASTER 13-40-13 з високим фосфором | ChatGPT / Gemini / Claude | alternatives with non-equivalence caveat | /guides/high-phosphorus-alternatives-master-13-40-13/ | OPTIMIZED | verify citation/indexing |
| AI-21 | best-fit | яке добриво вибрати перед посадкою саджанців | ChatGPT / Gemini / Claude | educational decision support | /guides/before-planting-seedlings-product-selection/ | OPTIMIZED | verify citation/indexing |
| AI-22 | best-fit | як вибрати фасування добрива для кількох рослин | ChatGPT / Gemini / Claude | educational + exact SKU paths | /guides/how-to-choose-pack-size/ | OPTIMIZED | verify citation/indexing + exact SKU landing |
| AI-23 | B2B/lead | професійні горщики для лохини 25 30 40 л Україна | ChatGPT / Gemini / Claude | product family + inquiry | /categories/containers/ | LEAD-GEN READY | test PlantLogic discovery |
| AI-24 | B2B/lead | горщики PlantLogic для лохини купити Україна | ChatGPT / Gemini / Claude | product family + seller/inquiry | /categories/containers/ | LEAD-GEN READY | test citation + inquiry flow; price is not public |
| AI-25 | comparison | горщик 25 л чи 40 л для лохини різниця | ChatGPT / Gemini / Claude | technical comparison + inquiry | /guides/blueberry-pot-25l-vs-40l/ | OPTIMIZED | verify citation/indexing |
| AI-26 | where to buy | де замовити професійні товари для вирощування в Україні | ChatGPT / Gemini / Claude | seller + catalog | /catalog.html + / | OPTIMIZED · UNVERIFIED | Organization + WebSite entity ready; verify generic brand discovery |

| AI-27 | technical selection | PLANTAFOL 30-10-10 чи 20-20-20 чи 10-54-10 яку формулу вибрати | ChatGPT / Gemini / Claude | formula comparison + exact offers | /guides/plantafol-formulas-comparison/ | OPTIMIZED | new comparison source; verify citation/indexing |
| AI-28 | technical selection | PLANTAFOL з високим калієм 5-15-45 чи 0-25-50 | ChatGPT / Gemini / Claude | compare N-P-K ratios + exact offers | /guides/plantafol-formulas-comparison/ | OPTIMIZED | new comparison source; verify citation/indexing |
| AI-29 | comparison | Osmocote 1.5M 2-3M 3-4M 4-5M 5-6M різниця | ChatGPT / Gemini / Claude | release-duration + N-P-K comparison | /guides/osmocote-release-duration-comparison/ | OPTIMIZED | new comparison source; verify citation/indexing |
| AI-30 | technical selection | яке Osmocote вибрати за строком дії | ChatGPT / Gemini / Claude | shortlist by declared duration | /guides/osmocote-release-duration-comparison/ | OPTIMIZED | new comparison source; verify citation/indexing |
| AI-31 | direct product | борне мікродобриво Boroplus купити Україна | ChatGPT / Gemini / Claude | product + seller + exact offers | /products/boroplus/ | READY | strengthen direct-product discovery |
| AI-32 | direct product | Brexil Ca кальцій купити Україна | ChatGPT / Gemini / Claude | product + seller + exact offers | /products/brexil-ca/ | READY | strengthen direct-product discovery |
| AI-33 | direct product | Brexil Zn цинк купити Україна | ChatGPT / Gemini / Claude | product + seller + exact offers | /products/brexil-zn/ | READY | strengthen direct-product discovery |
| AI-34 | direct product | Sweet Valagro купити Україна | ChatGPT / Gemini / Claude | product + seller + exact offers | /products/sweet/ | READY | add uncovered commercial product intent |
| AI-35 | direct product | Viva Valagro купити Україна | ChatGPT / Gemini / Claude | product + seller + exact offers | /products/viva/ | READY | add uncovered commercial product intent |
| AI-36 | direct product | MASTER 3-11-38 купити Україна | ChatGPT / Gemini / Claude | product + seller + exact offers | /products/master-3-11-38/ | READY | add uncovered commercial NPK intent |

| AI-37 | comparison | Brexil Fe чи Ca чи Zn чи Multi різниця | ChatGPT / Gemini / Claude | element-focused comparison + product paths | /guides/brexil-fe-ca-zn-multi-comparison/ | OPTIMIZED | new cross-engine comparison source |
| AI-38 | technical selection | яке мікродобриво Brexil вибрати Fe Ca Zn Multi | ChatGPT / Gemini / Claude | shortlist by declared element focus | /guides/brexil-fe-ca-zn-multi-comparison/ | OPTIMIZED | new cross-engine selection source |
| AI-39 | comparison | MASTER 3-11-38 чи 15-5-30 чи 17-6-18 чи 18-18-18 | ChatGPT / Gemini / Claude | N-P-K comparison + exact offers | /guides/master-formulas-comparison/ | OPTIMIZED | new cross-engine comparison source |
| AI-40 | technical selection | MASTER з високим калієм яку формулу вибрати | ChatGPT / Gemini / Claude | formula shortlist with caveat | /guides/master-formulas-comparison/ | OPTIMIZED | new cross-engine selection source |
| AI-41 | direct product | Brexil Multi купити Україна | ChatGPT / Gemini / Claude | product + seller + exact offers | /products/brexil-multi-250g/ | READY | exact-SKU target; family PDP absent |
| AI-42 | direct product | Osmocote купити Україна 200 г 1 кг | ChatGPT / Gemini / Claude | product family + exact offers | /guides/osmocote-release-duration-comparison/ | READY | connect generic product query to comparison + offers |

| AI-43 | comparison | Viva чи Benefit PZ чи Sweet чи Kendal чи NeoCore різниця | ChatGPT / Gemini / Claude | compare declared purpose + product paths | /guides/biostimulants-by-declared-purpose/ | OPTIMIZED | new cross-engine comparison source |
| AI-44 | technical selection | який біостимулятор вибрати для кореневої системи чи ризосфери | ChatGPT / Gemini / Claude | shortlist by declared purpose | /guides/biostimulants-by-declared-purpose/ | OPTIMIZED | routes to Viva / NeoCore without dosage claims |
| AI-45 | technical selection | який біостимулятор для росту плодів чи достигання | ChatGPT / Gemini / Claude | distinguish Benefit PZ vs Sweet | /guides/biostimulants-by-declared-purpose/ | OPTIMIZED | new fruit-stage selection source |
| AI-46 | direct product | Benefit PZ купити Україна | ChatGPT / Gemini / Claude | product + seller + exact offers | /products/benefit-pz/ | READY | uncovered direct-product intent |
| AI-47 | direct product | Kendal Valagro купити Україна | ChatGPT / Gemini / Claude | product + seller + exact offers | /products/kendal/ | READY | uncovered direct-product intent |
| AI-48 | direct product | NeoCore купити Україна | ChatGPT / Gemini / Claude | product + seller + exact offers | /products/neocore/ | READY | uncovered direct-product intent |

| AI-49 | comparison | Radifarm чи Kendal Root чи NeoCore що вибрати для кореневої системи | ChatGPT / Gemini / Claude | compare declared root-zone purpose + product paths | /guides/root-biostimulants-comparison/ | OPTIMIZED | new cross-engine root-zone comparison |
| AI-50 | technical selection | що використовують після пересадки для коренів Radifarm чи інше | ChatGPT / Gemini / Claude | distinguish transplant vs general root support | /guides/root-biostimulants-comparison/ | OPTIMIZED | intent linked to active products |
| AI-51 | technical selection | біостимулятор для кореневої системи при стресових умовах | ChatGPT / Gemini / Claude | Kendal Root / NeoCore context | /guides/root-biostimulants-comparison/ | OPTIMIZED | factual task routing |
| AI-52 | direct product | Кеміра Укорінювач купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/kemira-ukorinyuvach-100ml/ | READY | direct purchase intent |
| AI-53 | direct product | Actiwave Valagro купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/actiwave-1l/ | READY | direct purchase intent |
| AI-54 | direct product | Kendal Root купити Україна | ChatGPT / Gemini / Claude | product + seller + offers | /products/kendal-root/ | READY | direct purchase intent |
| AI-55 | direct product | BlackJak купити Україна | ChatGPT / Gemini / Claude | product + seller + offers | /products/blackjak/ | READY | direct purchase intent |
| AI-56 | comparison | гумінові чи фульвові кислоти Agriflex Humic Fulvix Bio різниця | ChatGPT / Gemini / Claude | composition comparison + product paths | /guides/humic-fulvic-products-comparison/ | OPTIMIZED | new cross-engine humic/fulvic source |
| AI-57 | direct product | Agriflex Humic гумат калію купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/agriflex-humic-humat-kaliyu-1kg/ | READY | direct purchase intent |
| AI-58 | direct product | Agriflex Fulvix купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/agriflex-fulvix-fulvokysloty-50-1kg/ | READY | direct purchase intent |
| AI-59 | direct product | Agriflex Bio купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/agriflex-bio-1kg/ | READY | direct purchase intent |
| AI-60 | comparison | Ferrilene 4.8 чи Ferrilene Trium чи EDTA Fe чи Brexil Fe різниця | ChatGPT / Gemini / Claude | iron-form comparison + product paths | /guides/iron-chelates-comparison/ | OPTIMIZED | new cross-engine iron source |
| AI-61 | direct product | Ferrilene Trium купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/ferrilen-trium-1kg/ | READY | direct purchase intent |
| AI-62 | direct product | Valagro EDTA Fe 13 купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/valagro-edta-fe-13-5kg/ | READY | direct purchase intent |
| AI-63 | direct product | Ferrilene 4.8 ortho ortho купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/ferrilene-4-8-orto-orto-10g/ | READY | direct purchase intent |
| AI-64 | comparison | Haifa MKP чи PeKacid чи сульфат калію SoluPotasse різниця | ChatGPT / Gemini / Claude | P/K composition comparison with non-equivalence caveat | /guides/pk-potassium-phosphorus-comparison/ | OPTIMIZED | new cross-engine PK source |
| AI-65 | direct product | Haifa MKP 0-52-34 купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/haifa-mkp-0-52-34-200g/ | READY | direct purchase intent |
| AI-66 | comparison | MKP 0-52-34 чи PeKacid 0-60-20 що відрізняється | ChatGPT / Gemini / Claude | PK comparison + acidification caveat | /guides/pk-potassium-phosphorus-comparison/ | OPTIMIZED | task-oriented comparison |
| AI-67 | technical selection | сульфат калію чи монокалійфосфат що вибрати | ChatGPT / Gemini / Claude | distinguish K+S vs P+K products | /guides/pk-potassium-phosphorus-comparison/ | OPTIMIZED | non-equivalent selection source |
| AI-68 | direct product | сульфат магнію водорозчинний купити Україна | ChatGPT / Gemini / Claude | exact product offer | /products/sulfat-mahniyu-1kg/ | READY | uncovered direct-product intent |

| AI-69 | comparison | Brexil Mix чи Combi чи Multi чи Nutre різниця | ChatGPT / Gemini / Claude | compare complex micronutrient products | /guides/brexil-complex-products-comparison/ | OPTIMIZED | new cross-engine Brexil source |
| AI-70 | technical selection | яке комплексне мікродобриво Brexil вибрати | ChatGPT / Gemini / Claude | shortlist by declared product type | /guides/brexil-complex-products-comparison/ | OPTIMIZED | task-oriented micronutrient selection |
| AI-71 | direct product | Brexil Mix купити Україна | ChatGPT / Gemini / Claude | product + seller + offers | /products/brexil-mix/ | READY | direct purchase intent |
| AI-72 | direct product | Brexil Combi купити Україна | ChatGPT / Gemini / Claude | product + seller + offers | /products/brexil-combi/ | READY | direct purchase intent |
| AI-73 | direct product | Brexil Nutre купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/brexil-nutre-1kg/ | READY | direct purchase intent |
| AI-74 | direct product | Brexil Mn купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/brexil-mn-5kg/ | READY | direct purchase intent |
| AI-75 | comparison | Megafol чи NeoVivo чи Terra-Sorb чи Speedfol Amino різниця | ChatGPT / Gemini / Claude | compare declared anti-stress/amino contexts | /guides/antistress-amino-seaweed-comparison/ | OPTIMIZED | new cross-engine anti-stress source |
| AI-76 | technical selection | амінокислотний біостимулятор для листкового внесення купити | ChatGPT / Gemini / Claude | shortlist with application-method caveat | /guides/antistress-amino-seaweed-comparison/ | OPTIMIZED | task-oriented amino selection |
| AI-77 | direct product | Terra-Sorb купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/terra-sorb-100ml/ | READY | direct purchase intent |
| AI-78 | direct product | NeoVivo купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/neovivo-1l/ | READY | direct purchase intent |
| AI-79 | direct product | Speedfol Amino Vegetative купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/spidfol-amino-vehetatsiya-20ml/ | READY | direct purchase intent |
| AI-80 | direct product | Maxicrop Extra MC Extra купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/maxicrop-extra-1kg/ | READY | direct purchase intent |
| AI-81 | comparison | Benefit PZ чи Sweet що вибрати для плодів | ChatGPT / Gemini / Claude | distinguish fruit growth vs ripening/coloring | /guides/fruit-growth-ripening-biostimulants-comparison/ | OPTIMIZED | commercial fruit-stage comparison |
| AI-82 | comparison | Benefit PZ Sweet Maxicrop Set Maxicrop Cream різниця | ChatGPT / Gemini / Claude | declared-purpose comparison | /guides/fruit-growth-ripening-biostimulants-comparison/ | OPTIMIZED | broader product comparison |
| AI-83 | direct product | Maxicrop Set купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/maxicrop-set-maksikrop-zav-yaz-100ml/ | READY | direct purchase intent |
| AI-84 | direct product | Maxicrop Cream купити Україна | ChatGPT / Gemini / Claude | product + seller + offers | /products/maxicrop-cream/ | READY | direct purchase intent |
| AI-85 | comparison | Кеміра 12-46-8 чи 18-18-18 різниця | ChatGPT / Gemini / Claude | N-P-K comparison | /guides/kemira-npk-formulas-comparison/ | OPTIMIZED | new cross-engine Kemira source |
| AI-86 | comparison | Кеміра Люкс 14-11-25 чи Кеміра Ґрунт 11-11-21 різниця | ChatGPT / Gemini / Claude | N-P-K + format comparison | /guides/kemira-npk-formulas-comparison/ | OPTIMIZED | product-family comparison |
| AI-87 | direct product | Кеміра 12-46-8 купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/kemira-npk-12-46-8-1kg/ | READY | direct purchase intent |
| AI-88 | direct product | Кеміра 18-18-18 купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/kemira-npk-18-18-18-1kg/ | READY | direct purchase intent |

| AI-89 | comparison | NeoCore чи NeoVivo чи NeoFlora різниця | ChatGPT / Gemini / Claude | compare Neova products by declared task | /guides/neova-biostimulants-comparison/ | OPTIMIZED | new Neova cross-engine source |
| AI-90 | technical selection | який біостимулятор Neova вибрати для коренів стресу або цвітіння | ChatGPT / Gemini / Claude | task-based shortlist | /guides/neova-biostimulants-comparison/ | OPTIMIZED | task routing without dosage claims |
| AI-91 | direct product | NeoFlora купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/neoflora-1l/ | READY | direct purchase intent |
| AI-92 | comparison | MC Extra чи Maxicrop Cream чи MAX 600 SeaSailer різниця | ChatGPT / Gemini / Claude | compare seaweed products by format/context | /guides/seaweed-biostimulants-comparison/ | OPTIMIZED | new seaweed comparison source |
| AI-93 | technical selection | біостимулятор з Ascophyllum nodosum купити Україна | ChatGPT / Gemini / Claude | shortlist + exact offers | /guides/seaweed-biostimulants-comparison/ | OPTIMIZED | generic seaweed intent |
| AI-94 | direct product | MAX 600 SeaSailer купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/max-600-seasailer-1kg/ | READY | direct purchase intent |
| AI-95 | comparison | NeoTerra Organic-C чи Aquafix різниця | ChatGPT / Gemini / Claude | soil-conditioner comparison | /guides/soil-conditioners-neoterra-comparison/ | OPTIMIZED | new soil conditioner source |
| AI-96 | technical selection | органічний кондиціонер ґрунту для водоутримання | ChatGPT / Gemini / Claude | factual product shortlist | /guides/soil-conditioners-neoterra-comparison/ | OPTIMIZED | task-oriented soil conditioner intent |
| AI-97 | direct product | NeoTerra Organic-C купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/neoterra-organic-c-25kg/ | READY | direct purchase intent |
| AI-98 | direct product | NeoTerra Aquafix купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/neoterra-aqua-25kg/ | READY | direct purchase intent |
| AI-99 | comparison | Spray-Aide чи PeKacid що вибрати для підкислення | ChatGPT / Gemini / Claude | distinguish adjuvant vs PK fertilizer | /guides/acidifier-vs-pk-fertilizer-comparison/ | OPTIMIZED | prevent false equivalence |
| AI-100 | technical selection | підкислювач робочого розчину купити Україна | ChatGPT / Gemini / Claude | adjuvant/product routing | /guides/acidifier-vs-pk-fertilizer-comparison/ | OPTIMIZED | generic acidification intent |
| AI-101 | direct product | Spray-Aide Miller купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/sprei-eid-100ml/ | READY | direct purchase intent |
| AI-102 | comparison | Agroblen Granula-MAX чи Osmocote 5 5-6M різниця | ChatGPT / Gemini / Claude | compare controlled-release formula + format | /guides/controlled-release-5-6m-comparison/ | OPTIMIZED | new CRF comparison source |
| AI-103 | technical selection | добриво контрольованого вивільнення 5-6 місяців | ChatGPT / Gemini / Claude | shortlist by duration + formula caveat | /guides/controlled-release-5-6m-comparison/ | OPTIMIZED | generic duration intent |
| AI-104 | direct product | Agroblen Granula-MAX 5-6M купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/agroblen-granula-max-14-20-5-te-56m-20pcs/ | READY | direct purchase intent |
| AI-105 | direct product | Osmocote 5 16-8-12 5-6M купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/osmocote-decor-16-8-12-56m-1kg/ | READY | direct purchase intent |
| AI-106 | direct product | Micro NP Valagro купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/micro-np-10kg/ | READY | uncovered direct-product intent |
| AI-107 | direct product | Actiwin 20-5-10 купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/actiwin-20-5-10-22-7kg/ | READY | uncovered direct-product intent |
| AI-108 | direct product | Nitrate Balancer Kemira Баланс купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/kemira-balans-nitrate-balancer-100ml/ | READY | uncovered direct-product intent |

| AI-109 | comparison | Brexil Duo чи Kendal TE чи Valagro EDTA 5SG різниця | ChatGPT / Gemini / Claude | compare specialized micronutrient products | /guides/specialized-micronutrients-comparison/ | OPTIMIZED | new specialized micronutrient source |
| AI-110 | direct product | Brexil Duo купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/brexil-duo-5kg/ | READY | direct purchase intent |
| AI-111 | direct product | Kendal TE купити Україна | ChatGPT / Gemini / Claude | product + seller | /products/kendal-te/ | READY | direct purchase intent |
| AI-112 | direct product | Valagro EDTA 5SG купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/valagro-edta-5sg-1kg/ | READY | direct purchase intent |
| AI-113 | comparison | Кеміра Зав'язь 0-52-34 чи Haifa MKP 0-52-34 різниця | ChatGPT / Gemini / Claude | same-formula product comparison | /guides/npk-0-52-34-comparison/ | OPTIMIZED | new 0-52-34 comparison source |
| AI-114 | direct product | Кеміра Зав'язь 0-52-34 купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/kemira-zav-yaz-5g/ | READY | direct purchase intent |
| AI-115 | comparison | Osmocote Granula-MAX чи Agroblen Granula-MAX 5-6M різниця | ChatGPT / Gemini / Claude | compare formula + portion format | /guides/controlled-release-tablets-5-6m-comparison/ | OPTIMIZED | new controlled-release tablet source |
| AI-116 | direct product | Osmocote Granula-MAX 14-8-11 5-6M купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/osmocote-granula-max-14-8-11-te-56m-10pcs/ | READY | direct purchase intent |
| AI-117 | direct product | MASTER 18-18-18 купити Україна | ChatGPT / Gemini / Claude | product + seller + offers | /products/master-npk-18-18-18-1kg/ | READY | direct purchase intent |
| AI-118 | direct product | MASTER 17-6-18 купити Україна | ChatGPT / Gemini / Claude | product + seller + offers | /products/master-npk-17-6-18-1kg/ | READY | direct purchase intent |
| AI-119 | direct product | PLANTAFOL 10-54-10 купити Україна | ChatGPT / Gemini / Claude | product + seller + offers | /products/plantafol-10-54-10-1kg/ | READY | direct purchase intent |
| AI-120 | direct product | PLANTAFOL 5-15-45 купити Україна | ChatGPT / Gemini / Claude | product + seller + offers | /products/plantafol-5-15-45-1kg/ | READY | direct purchase intent |
| AI-121 | direct product | PLANTAFOL 0-25-50 купити Україна | ChatGPT / Gemini / Claude | product + seller + offers | /products/plantafol-0-25-50-25g/ | READY | direct purchase intent |
| AI-122 | direct product | Osmocote Potassium 12-8-19 3-4M купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/osmocote-potassium-12-8-19-34m-1kg/ | READY | direct purchase intent |
| AI-123 | direct product | Osmocote Landscape 16-9-12 3-4M купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/osmocote-landscape-16-9-12-34m-1kg/ | READY | direct purchase intent |
| AI-124 | direct product | Osmocote Start 11-11-17 1.5M купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/osmocote-start-11-11-17-1-5m-1kg/ | READY | direct purchase intent |
| AI-125 | direct product | Osmocote Bloom 12-7-18 2-3M купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/osmocote-bloom-12-7-18-23m-1kg/ | READY | direct purchase intent |
| AI-126 | direct product | Osmocote Quick Start 22-5-6 4-5M купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/osmocote-quick-start-22-5-6-45m-1kg/ | READY | direct purchase intent |
| AI-127 | direct product | Кеміра для газону 12-11-18 купити Україна | ChatGPT / Gemini / Claude | exact sellable offer | /products/kemira-dlya-hazonu-npk-12-11-18-1kg/ | READY | direct purchase intent |
| AI-128 | direct product | Ерайз Miller регулятор росту купити Україна | ChatGPT / Gemini / Claude | exact sellable offer with label caveat | /products/eraiz-100ml/ | READY | direct purchase intent |

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
