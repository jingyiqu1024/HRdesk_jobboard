import csv
from .common import LABELED_CSV

FIELDS = ['job_key','row_id','company','title','topic','tags','direction','emerging_group','manual_note']

def _job_key(r):
    return f"{r.get('company','')}::{r.get('row_id') or r.get('title','')}"

def _row_of(r):
    return {
        'job_key': _job_key(r),
        'row_id': r.get('row_id',''),
        'company': r.get('company',''),
        'title': r.get('title',''),
        'topic': r.get('topic',''),
        'tags': ' | '.join(r.get('tags',[])),
        'direction': r.get('direction',''),
        'emerging_group': r.get('emerging_group',''),
        'manual_note': '',
    }

def _read_manual():
    """读取 CSV 中人工改过的行（manual_note 非空），这些行不允许被脚本覆盖。"""
    if not LABELED_CSV.exists():
        return {}
    manual = {}
    with LABELED_CSV.open('r', encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            key = (row.get('job_key') or '').strip()
            if key and (row.get('manual_note') or '').strip():
                manual[key] = row
    return manual

def sync_csv(rows):
    """以脚本本次打标结果为准刷新 CSV；人工改过的行（manual_note 非空）原样保留。

    这样脚本逻辑升级后，自动打标结果会同步更新，不会出现“新逻辑被旧 CSV 打回”的问题；
    同时人工修正的结论也不会被覆盖。
    """
    LABELED_CSV.parent.mkdir(parents=True, exist_ok=True)
    manual = _read_manual()
    stat = {'total': len(rows), 'fresh': 0, 'kept_manual': 0, 'stale_removed': 0, 'changed': 0}

    old_auto = {}
    if LABELED_CSV.exists():
        with LABELED_CSV.open('r', encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                key = (row.get('job_key') or '').strip()
                if key and not (row.get('manual_note') or '').strip():
                    old_auto[key] = row

    with LABELED_CSV.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        live_keys = set()
        for r in rows:
            key = _job_key(r)
            live_keys.add(key)
            if key in manual:
                w.writerow({k: manual[key].get(k, '') for k in FIELDS})
                stat['kept_manual'] += 1
                continue
            fresh = _row_of(r)
            prev = old_auto.get(key)
            if prev and prev.get('topic','') != fresh['topic']:
                stat['changed'] += 1
            w.writerow(fresh)
            stat['fresh'] += 1
        stat['stale_removed'] = len(set(old_auto) - live_keys)
    return stat

def load_override_map():
    if not LABELED_CSV.exists():
        return {}
    out = {}
    with LABELED_CSV.open('r', encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            key = (row.get('job_key') or '').strip()
            if not key: continue
            if not (row.get('manual_note') or '').strip():
                continue  # 未人工修改的行不再作为 override，统一以脚本结果为准
            out[key] = row
    return out

def apply_overrides(rows, override_map):
    for r in rows:
        ov = override_map.get(_job_key(r))
        if not ov: continue
        if ov.get('topic'):
            r['topic'] = ov['topic']
        if ov.get('direction'):
            r['direction'] = ov['direction']
        if ov.get('emerging_group') is not None:
            r['emerging_group'] = ov.get('emerging_group','')
        if ov.get('tags'):
            r['tags'] = [x.strip() for x in ov['tags'].split('|') if x.strip()]
    return rows
