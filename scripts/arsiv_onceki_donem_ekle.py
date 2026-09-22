#!/usr/bin/env python3
"""1 Ocak - 8 Şubat 2026 kayıtlarını arşivin BAŞINA, mevcut blok formatında ekler."""
import json, re, sys, datetime
SP='/tmp/claude-0/-home-user-siberguvenlik/61b9d5e9-c2d1-51dd-a994-2a5c523b5018/scratchpad/'
sys.path.insert(0, SP)
from etiket import ETIKET

ARSIV='data/haberler_arsiv.txt'
AY_EN={1:'JANUARY',2:'FEBRUARY'}
SRC=re.compile(r'^\((.*?),\s*AÇIK\s*[–-]\s*([^,]+),\s*(\d{2})/(\d{2})/(\d{4})\)\s*$')

gunler=json.load(open(SP+'parsed.json'))
parcalar=[]
n=0
for d,hs in gunler:
    g=datetime.date.fromisoformat(d)
    parcalar.append('\n\n'+'='*80)
    parcalar.append(f'📅 {g.day:02d} {AY_EN[g.month]} {g.year} - EN ÖNEMLİ {len(hs)} HABER (SEÇİLMİŞ)')
    parcalar.append('='*80+'\n')
    for i,h in enumerate(hs,1):
        n+=1
        baslik=h[0].lstrip('* ').strip()
        para=' '.join(x.strip() for x in h[1:-1])
        m=SRC.match(h[-1])
        kaynak, alan, gg, aa, yy = m.group(1), m.group(2).strip(), m.group(3), m.group(4), m.group(5)
        ad='XXXXXXX' if set(kaynak.strip().lower())<= {'x'} else kaynak.strip().upper()
        kat, onem = ETIKET[n]
        parcalar.append(f'[{i:2d}] {baslik}')
        parcalar.append('─'*57)
        parcalar.append(para)
        parcalar.append(f'({ad}, AÇIK -{alan}, {gg}.{aa}.{yy})')
        parcalar.append(f'» sonradan | kategori={kat} | onem={onem} | rubrik=v1')
        parcalar.append('')
        parcalar.append('─'*80)
        parcalar.append('')
yeni='\n'.join(parcalar).lstrip('\n')
mevcut=open(ARSIV,encoding='utf-8').read()
open(ARSIV,'w',encoding='utf-8').write(yeni+'\n'+mevcut)
print(f'{len(gunler)} gün, {n} haber eklendi.')
