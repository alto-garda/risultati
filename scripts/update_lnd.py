#!/usr/bin/env python3
"""Importa il girone di andata delle quattro squadre Attività di Base da Gare LND."""
import html, json, re, sys, time
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
import requests

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; BASE='https://gare.lnd.it/competizione/lombardia'
COMPETITIONS={
 'esordienti-u13':{'campionato':'E2','girone':'E','name':'Esordienti U13'},
 'esordienti-misti':{'campionato':'N2','girone':'A','name':'Esordienti Misti'},
 'pulcini-u11':{'campionato':'P2','girone':'H','name':'Pulcini U11'},
 'pulcini-u10':{'campionato':'R2','girone':'D','name':'Pulcini U10'},
}
S=requests.Session(); S.headers.update({'User-Agent':'Mozilla/5.0 (compatible; AltoGardaResultsBot/1.0)','Accept':'text/html,application/xhtml+xml,application/json'})

def get(d,*keys):
 if isinstance(d,dict):
  for k in keys:
   if d.get(k) is not None:return d[k]
 return None

def team_name(v):
 if isinstance(v,str):return v
 if isinstance(v,dict):return get(v,'name','denomination','description','label','teamName') or ''
 return ''

def norm(v):return re.sub(r'\s+',' ',str(v or '')).strip().upper()
def parse_date(v):
 if not v:return None
 m=re.search(r'(20\d{2}-\d{2}-\d{2})',str(v))
 if m:return m.group(1)
 m=re.search(r'(\d{2})/(\d{2})/(20\d{2})',str(v))
 return f'{m.group(3)}-{m.group(2)}-{m.group(1)}' if m else None
def parse_time(v):
 m=re.search(r'(\d{1,2}:\d{2})',str(v or ''))
 return m.group(1) if m else None

def scan_matches(node,out):
 if isinstance(node,dict):
  if any(k in node for k in ('home','homeTeam','teamHome','localTeam')) and any(k in node for k in ('away','awayTeam','teamAway','visitorTeam')):out.append(node)
  for v in node.values():scan_matches(v,out)
 elif isinstance(node,list):
  for v in node:scan_matches(v,out)

def page_json(response):
 try:return response.json()
 except ValueError:
  m=re.search(r'data-page="([^\"]+)"',response.text)
  if not m:raise RuntimeError('Payload LND non riconosciuto')
  return json.loads(html.unescape(m.group(1)))

def current_version(url):
 r=S.get(url,timeout=30);r.raise_for_status()
 m=re.search(r'data-page="([^\"]+)"',r.text)
 if m:
  try:return json.loads(html.unescape(m.group(1))).get('version')
  except Exception:pass
 return '86832c128bce74e5c6ae58b71f469bfd'

def parse_matches(payload):
 raw=[];scan_matches(payload,raw);unique={}
 for m in raw:
  h=team_name(get(m,'home','homeTeam','teamHome','localTeam','home_name','homeTeamName'))
  a=team_name(get(m,'away','awayTeam','teamAway','visitorTeam','away_name','awayTeamName'))
  if h or a:
   mid=get(m,'id','matchId','garaId'); key=str(mid) if mid is not None else f'{h}|{a}|{get(m,"date","matchDate")}'
   unique[key]=m
 return list(unique.values())

def normalize(m,round_no):
 h=team_name(get(m,'home','homeTeam','teamHome','localTeam','home_name','homeTeamName','local'))
 a=team_name(get(m,'away','awayTeam','teamAway','visitorTeam','away_name','awayTeamName','ospite'))
 rest=bool(get(m,'isRest','rest')) or (norm(h)=='ALTO GARDA' and not norm(a)) or (norm(a)=='ALTO GARDA' and not norm(h))
 if 'ALTO GARDA' not in (norm(h),norm(a)) and not rest:return None
 field=get(m,'field','fieldName','facility','ground','campo'); address=get(m,'fieldAddress','address','facilityAddress','groundAddress')
 if isinstance(field,dict):field=team_name(field)
 return {'id':get(m,'id','matchId','garaId'),'giornata':round_no,'date':parse_date(get(m,'date','matchDate','datetime','startDate','data','dateTime')),'time':parse_time(get(m,'time','matchTime','hour','orario','startTime')),'home':h or 'ALTO GARDA','away':a or '', 'homeGoals':get(m,'homeGoals','homeScore','goalsHome','scoreHome','localGoals'),'awayGoals':get(m,'awayGoals','awayScore','goalsAway','scoreAway','visitorGoals'),'field':field,'fieldAddress':address,'isRest':rest,'isPlayed':bool(get(m,'isPlayed','played','isFinished')),'resultState':get(m,'resultState','status','state'),'variation':get(m,'variation','change','variationStatus')}

def fetch_round(cfg,n,version):
 params={'campionato':cfg['campionato'],'giornata':n,'girone':cfg['girone'],'leg':'first','stagione':'2026'};url=BASE+'?'+urlencode(params)
 headers={'X-Inertia':'true','X-Requested-With':'XMLHttpRequest','Accept':'text/html, application/xhtml+xml','Referer':BASE,'X-Inertia-Partial-Component':'QuadroGare/Home','X-Inertia-Partial-Data':'matches,currentMatchday'}
 if version:headers['X-Inertia-Version']=version
 r=S.get(url,headers=headers,timeout=30)
 if r.status_code==409:
  v=current_version(BASE+'?'+urlencode({'campionato':cfg['campionato'],'girone':cfg['girone'],'stagione':'2026'}))
  if v:headers['X-Inertia-Version']=v
  r=S.get(url,headers=headers,timeout=30)
 r.raise_for_status();return page_json(r)

def import_one(slug,cfg):
 base=BASE+'?'+urlencode({'campionato':cfg['campionato'],'girone':cfg['girone'],'stagione':'2026'});version=current_version(base)
 fixtures=[];seen=set();empty=0
 for n in range(1,19):
  payload=fetch_round(cfg,n,version); round_f=[]
  for m in parse_matches(payload):
   f=normalize(m,n)
   if f:
    key=str(f['id']) if f['id'] is not None else str((f['date'],f['home'],f['away']))
    if key not in seen:seen.add(key);round_f.append(f)
  if round_f:fixtures.extend(round_f);empty=0
  else:
   empty+=1
   if n>=9 and empty>=2:break
  time.sleep(.25)
 if len(fixtures)<5:raise RuntimeError(f'Solo {len(fixtures)} appuntamenti trovati: file precedente conservato')
 fixtures.sort(key=lambda f:(f['giornata'],f['date'] or ''))
 return {'source':'Gare LND','competition':cfg['name'],'campionato':cfg['campionato'],'girone':cfg['girone'],'season':'2026/2027','phase':'Andata','team':'ALTO GARDA','updatedAt':date.today().isoformat(),'fixtures':fixtures}

def main():
 DATA.mkdir(exist_ok=True);errors=[]
 for slug,cfg in COMPETITIONS.items():
  try:
   obj=import_one(slug,cfg);out=DATA/(slug+'.json');tmp=out.with_suffix('.json.tmp')
   tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(out)
   print(f"OK {cfg['name']}: {len(obj['fixtures'])} gare/appuntamenti")
  except Exception as e:
   errors.append(f"{cfg['name']}: {e}");print(f"ERRORE {cfg['name']}: {e}",file=sys.stderr)
 if len(errors)==len(COMPETITIONS):sys.exit('Import LND fallito per tutte le squadre; nessun dato precedente è stato sovrascritto.')
 if errors:print('Avvisi: '+'; '.join(errors),file=sys.stderr)
if __name__=='__main__':main()
