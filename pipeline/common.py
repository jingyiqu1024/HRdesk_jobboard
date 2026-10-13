import json
import re
import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
XLSX_PATH = SCRIPT_DIR / "data-20261012.xlsx"
OUT = SCRIPT_DIR / "index_standalone_v3.html"
DATA_DATE = "2026-10-12"
LABELED_CSV = SCRIPT_DIR / "data" / "labeled_jobs.csv"

ONE_MONTH_AGO_MS = int((datetime.datetime.now() - datetime.timedelta(days=30)).timestamp() * 1000)
EMERGING_CUTOFF_MS = ONE_MONTH_AGO_MS

def to_ms(v):
    if v is None: return 0
    if isinstance(v, datetime.datetime): return int(v.timestamp() * 1000)
    if isinstance(v, datetime.date): return int(datetime.datetime(v.year, v.month, v.day).timestamp() * 1000)
    if isinstance(v, str):
        s = v.strip()
        try: return int(datetime.datetime.strptime(s[:10], '%Y-%m-%d').timestamp() * 1000)
        except: return 0
    if isinstance(v, (int, float)):
        n = int(v)
        return n if n > 1_000_000_000_000 else n * 1000
    return 0

def ms_to_date(ms):
    if not ms: return '-'
    try: return datetime.datetime.fromtimestamp(ms / 1000).strftime('%Y-%m-%d')
    except: return '-'

def parse_locations(raw):
    if not raw: return []
    s = str(raw).strip()
    if s in ('null','None','[]',''): return []
    out = []
    def push(x):
        x = re.sub(r'[市省区]$', '', str(x).strip().strip('"').strip("'"))
        if x and x not in out: out.append(x[:6])
    try:
        val = json.loads(s)
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict): push(item.get('provinceName') or item.get('cityName') or '')
                else: push(item)
        elif isinstance(val, str): push(val)
    except:
        push(s)
    return out

def map_type(v):
    s = str(v or '').lower()
    if 'campus' in s or '校' in s: return '校招'
    if 'intern' in s or '实习' in s: return '实习'
    return '社招'

def topn(d, n):
    return sorted(d.items(), key=lambda x:(-x[1], x[0]))[:n]
