#!/usr/bin/env python3
"""Import DDR4 Kingston/Samsung/Micron/Crucial community DMI observations.

Read a local linuxhw/DMI clone; never copy serial numbers or raw DMI.
Output is observational, NOT manufacturer authentication.
"""
import argparse, collections, csv, pathlib, re
COLS=['brand','part_number','capacity_gb','memory_type','form_factor','observed_speed_mt_s','observed_count','seen_on_oem','source_url','source_type']
BAD={'','UNKNOWN','NOT SPECIFIED','DEFAULT STRING','NO MODULE INSTALLED','TO BE FILLED BY O.E.M.'}
def vendor(name,part):
    v=name.strip().upper()
    known={'KINGSTON':'Kingston','SAMSUNG':'Samsung','MICRON':'Micron','CRUCIAL':'Crucial'}
    for word,brand in known.items():
        if word in v:return brand
    if re.match(r'M(?:471|378|393|386)A[0-9A-Z-]+$',part):return 'Samsung'
    if re.match(r'(?:MTA|[0-9]+AT[FS])[0-9A-Z-]+$',part):return 'Micron'
    if re.match(r'(?:KVR|KHX|KSM|KF[0-9])[0-9A-Z./-]+$',part):return 'Kingston'
    if re.match(r'CT[0-9]+G4[0-9A-Z./-]+$',part):return 'Crucial'
    # OEM ACR codes alone do not establish that Kingston made a module.
    return ''
def parse(text,oem):
    for chunk in re.split(r'(?=^Handle 0x[0-9A-Fa-f]+, DMI type 17,)',text,flags=re.M):
        if not re.match(r'^Handle 0x[0-9A-Fa-f]+, DMI type 17,',chunk):continue
        d=dict((k.strip(),v.strip()) for k,v in re.findall(r'^\s+([^:\n]+):\s*(.*)$',chunk,flags=re.M))
        if d.get('Type','').upper()!='DDR4':continue
        part=re.sub(r'\s+','',d.get('Part Number','')).upper()
        if not 7<=len(part)<=64 or part in BAD or not re.fullmatch(r'[A-Z0-9][A-Z0-9./_-]+',part):continue
        m=re.match(r'(\d+(?:\.\d+)?)\s*(GB|MB|TB)\b',d.get('Size',''),re.I)
        if not m:continue
        size=float(m[1])*({'GB':1,'MB':1/1024,'TB':1024}[m[2].upper()])
        brand=vendor(d.get('Manufacturer',''),part)
        if brand not in ('Kingston','Samsung','Micron','Crucial'):continue
        s=re.search(r'\d+',d.get('Speed',''))
        speed=int(s[0]) if s else 0
        form=d.get('Form Factor','').upper()
        yield (brand,part,f'{size:g}','DDR4',form if form in ('SODIMM','DIMM') else '',
               str(speed) if 1600<=speed<=4266 else '',1,oem,
               'https://github.com/linuxhw/DMI','community_dmi_report')
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',required=True,type=pathlib.Path)
    p.add_argument('--out',default='catalog/observed_ddr4_full.csv',type=pathlib.Path)
    a=p.parse_args()
    if not a.root.is_dir():p.error('Missing DMI repo: '+str(a.root))
    agg={}
    n=0
    for path in a.root.rglob('*'):
        if not path.is_file() or path.name in ('README.md','LICENSE'):continue
        try: raw=path.read_text(encoding='utf-8',errors='replace')
        except OSError:continue
        if 'DMI type 17' not in raw:continue
        n+=1
        if n%10000==0:print('DMI reports scanned:',n,flush=True)
        rel=path.relative_to(a.root)
        oem=rel.parts[1] if len(rel.parts)>1 else ''
        for row in parse(raw,oem):
            k=row[1]
            if k not in agg:agg[k]={'row':list(row),'sizes':collections.Counter(),'speeds':collections.Counter(),'oems':collections.Counter()}
            item=agg[k]
            if item['row'][0]!=row[0]:item['row'][0]='CONFLICT'
            item['sizes'][row[2]]+=1
            if row[5]:item['speeds'][row[5]]+=1
            if oem:item['oems'][oem]+=1
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(COLS)
        for key,item in sorted(agg.items()):
            row=item['row']
            if row[0]=='CONFLICT':continue
            row[2]=item['sizes'].most_common(1)[0][0]
            row[5]=item['speeds'].most_common(1)[0][0] if item['speeds'] else ''
            row[6]=sum(item['sizes'].values())
            row[7]=';'.join(k for k,_ in item['oems'].most_common(6))
            w.writerow(row)
    print('Reports scanned:',n,'Unique DDR4 part numbers:',sum(i['row'][0]!='CONFLICT' for i in agg.values()))
    print('Community observations are NOT proof of genuine RAM.')
if __name__=='__main__':main()
