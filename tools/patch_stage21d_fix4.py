#!/usr/bin/env python3
from pathlib import Path
import json,re,sys
root=Path(sys.argv[1]).resolve()
idx=root/"index.html"
tpl=root/"assets/js/home-stage21d-fix4.template.js"
out=root/"assets/js/home-stage21d-fix4.js"
mapping=json.loads((root/"data/stage21d4-culture-images.json").read_text(encoding="utf-8"))
out.write_text(tpl.read_text(encoding="utf-8").replace("__CULTURE_MAP__",json.dumps(mapping,ensure_ascii=False)),encoding="utf-8")

s=idx.read_text(encoding="utf-8")
# remove previous FIX3 and previous FIX4 mounts; keep FIX2 underneath as fallback
patterns=[
 r'\s*<script[^>]+src=["\']/assets/js/home-stage21d-fix3\.js\?v=[^"\']+["\'][^>]*></script>\s*',
 r'\s*<link[^>]+href=["\']/assets/css/home-stage21d-fix3\.css\?v=[^"\']+["\'][^>]*>\s*',
 r'\s*<script[^>]+src=["\']/assets/js/home-stage21d-fix4\.js\?v=[^"\']+["\'][^>]*></script>\s*',
 r'\s*<link[^>]+href=["\']/assets/css/home-stage21d-fix4\.css\?v=[^"\']+["\'][^>]*>\s*',
]
for p in patterns: s=re.sub(p,'\n',s,flags=re.I)
s=s.replace('</head>','<link rel="stylesheet" href="/assets/css/home-stage21d-fix4.css?v=21d-fix4">\n</head>',1)
s=s.replace('</body>','<script src="/assets/js/home-stage21d-fix4.js?v=21d-fix4"></script>\n</body>',1)
idx.write_text(s,encoding="utf-8")
print("OK: Stage 21D FIX4 mounted")
