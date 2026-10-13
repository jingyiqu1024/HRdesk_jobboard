import json
import re
from pathlib import Path
from pipeline.common import DATA_DATE, OUT
from pipeline.loader import load_raw
from pipeline.aggregator import aggregate
from pipeline.overrides import sync_csv, load_override_map, apply_overrides

BASE = Path(__file__).resolve().parent
CSS = (BASE / 'templates' / 'main.css').read_text(encoding='utf-8')
BODY = (BASE / 'templates' / 'body.html').read_text(encoding='utf-8')
JS_LOGIC = (BASE / 'templates' / 'logic.js').read_text(encoding='utf-8')

print('📂 读取 Excel …')
raw = load_raw()
print('📊 聚合各大厂数据 …')
# 先读人工修正（manual_note 非空的行），传入 aggregate 内部在生成最终 JOBS 后立即应用
overrides = load_override_map()
ctx = aggregate(raw, override_map=overrides)

# 同步刷新 CSV（以本次脚本打标为准，保留人工修正行）
stat = sync_csv(ctx['JOBS'])
print(f'📝 CSV 同步完成：共 {stat["total"]} 条，刷新 {stat["fresh"]} 条，保留人工修正 {stat["kept_manual"]} 条，topic 变化 {stat["changed"]} 条')

companies = ctx['companies']
unicorns = ctx['unicorns']
COMPANIES = ctx['COMPANIES']
UNICORNS = ctx['UNICORNS']
TOPICS = ctx['TOPICS']
HEATMAP = ctx['HEATMAP']
KEYWORDS = ctx['KEYWORDS']
CATEGORIES = ctx['CATEGORIES']
JOBS = ctx['JOBS']
JD_DETAIL = ctx['JD_DETAIL']
EMERGING_GROUPS = ctx['EMERGING_GROUPS']

print('📄 生成 HTML …')
grand_total  = sum(c['total'] for c in COMPANIES) + sum(c['total'] for c in UNICORNS)
grand_ai     = sum(c['ai'] for c in COMPANIES) + sum(c['ai'] for c in UNICORNS)
grand_user   = sum(c.ai_user for c in companies) + sum(c.ai_user for c in unicorns.values())
grand_ai_all = grand_ai + grand_user
body = BODY.replace('2026-10-10', DATA_DATE)
body = re.sub(r'<div class="ov-val">20,852</div>', f'<div class="ov-val">{sum(c["total"] for c in COMPANIES)+sum(c["total"] for c in UNICORNS):,}</div>', body)
body = re.sub(r'覆盖 7 大厂 \+ 6 家 AI 独角兽 · 社招 16,779 / 校招 4,073', f'覆盖 7 大厂 + 6 家 AI 独角兽 · 社招 {sum(s.social for s in companies)+sum(s.social for s in unicorns.values()):,} / 校招 {sum(s.campus for s in companies)+sum(s.campus for s in unicorns.values()):,}', body)
body = re.sub(r'<div class="ov-val up">4,936</div>', f'<div class="ov-val up">{grand_ai_all:,}</div>', body)
body = re.sub(r'占比 24% · 社招 3,075 / 校招 1,861', f'占比 {round(grand_ai_all/max(1,grand_total)*100)}% · Builder {grand_ai:,} / User {grand_user:,}', body)
html = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>竞品岗位情报看板</title>
<style>{CSS}</style>
</head>
<body>
{body}
<script>
function escapeHtml(s){{return String(s||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');}}
function renderBars(elId,data,opts){{const o=opts||{{}};const max=Math.max(...data.map(d=>d[1]))||1;const el=document.getElementById(elId);if(!el)return;el.innerHTML=data.map(([label,val,extra])=>{{const pct=(val/max*100).toFixed(1);const right=o.percent?`<div class="bar-num">${{extra||''}}${{val}}%</div>`:`<div class="bar-num">${{val.toLocaleString()}}</div>`;return `<div class="bar-row"><div style="color:#334155">${{escapeHtml(label)}}</div><div class="bar-track"><div class="bar-fill" style="width:${{pct}}%"></div></div>${{right}}</div>`;}}).join('');}}
function drawSparkline(id,vals,color){{const canvas=document.getElementById(id);if(!canvas)return;const dpr=window.devicePixelRatio||1;canvas.width=100*dpr;canvas.height=40*dpr;const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);const w=100,h=40,pad=4;const min=Math.min(...vals),max=Math.max(...vals),range=(max-min)||1;const xs=vals.map((_,i)=>pad+i*(w-pad*2)/(vals.length-1));const ys=vals.map(v=>h-pad-((v-min)/range)*(h-pad*2));const grad=ctx.createLinearGradient(0,0,0,h);grad.addColorStop(0,color+'40');grad.addColorStop(1,color+'00');ctx.beginPath();ctx.moveTo(xs[0],h-pad);xs.forEach((x,i)=>ctx.lineTo(x,ys[i]));ctx.lineTo(xs[xs.length-1],h-pad);ctx.closePath();ctx.fillStyle=grad;ctx.fill();ctx.beginPath();ctx.moveTo(xs[0],ys[0]);xs.forEach((x,i)=>ctx.lineTo(x,ys[i]));ctx.strokeStyle=color;ctx.lineWidth=2;ctx.lineJoin='round';ctx.stroke();ctx.beginPath();ctx.arc(xs[xs.length-1],ys[ys.length-1],3,0,Math.PI*2);ctx.fillStyle=color;ctx.fill();}}
function drawTrend(id,totalArr,aiArr){{const canvas=document.getElementById(id);if(!canvas)return;const dpr=window.devicePixelRatio||1;const cssW=canvas.clientWidth||600,cssH=190;canvas.width=cssW*dpr;canvas.height=cssH*dpr;const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);const padL=48,padR=16,padT=14,padB=26;const w=cssW,h=cssH,iw=w-padL-padR,ih=h-padT-padB;const all=totalArr.concat(aiArr);const min=Math.min(...all),max=Math.max(...all),range=(max-min)||1;const yOf=v=>padT+ih-((v-min)/range)*ih;const xOf=(i,arr)=>padL+i*iw/(arr.length-1);ctx.font='10px -apple-system,sans-serif';ctx.fillStyle='#94a3b8';ctx.textAlign='right';for(let g=0;g<=4;g++){{const v=min+(range*g/4),y=yOf(v);ctx.beginPath();ctx.moveTo(padL,y);ctx.lineTo(w-padR,y);ctx.strokeStyle='#f1f5f9';ctx.lineWidth=1;ctx.stroke();const label=v>=1000?(v/1000).toFixed(1)+'k':Math.round(v);ctx.fillText(label,padL-8,y+3);}}ctx.textAlign='center';ctx.fillStyle='#94a3b8';['W14','W15','W16','W17','W18','本期'].forEach((lb,i)=>{{ctx.fillText(lb,xOf(i,totalArr),h-8);}});ctx.beginPath();ctx.setLineDash([4,4]);totalArr.forEach((v,i)=>{{const x=xOf(i,totalArr),y=yOf(v);i?ctx.lineTo(x,y):ctx.moveTo(x,y);}});ctx.strokeStyle='#94a3b8';ctx.lineWidth=1.6;ctx.stroke();ctx.setLineDash([]);const aiPts=aiArr.map((v,i)=>[xOf(i,aiArr),yOf(v)]);const grad=ctx.createLinearGradient(0,padT,0,h-padB);grad.addColorStop(0,'rgba(37,99,235,.22)');grad.addColorStop(1,'rgba(37,99,235,0)');ctx.beginPath();ctx.moveTo(aiPts[0][0],h-padB);aiPts.forEach(p=>ctx.lineTo(p[0],p[1]));ctx.lineTo(aiPts[aiPts.length-1][0],h-padB);ctx.closePath();ctx.fillStyle=grad;ctx.fill();ctx.beginPath();aiPts.forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.strokeStyle='#2563eb';ctx.lineWidth=2.4;ctx.lineJoin='round';ctx.stroke();aiPts.forEach(p=>{{ctx.beginPath();ctx.arc(p[0],p[1],3,0,Math.PI*2);ctx.fillStyle='#2563eb';ctx.fill();}});}}
const COMPANIES = {json.dumps(COMPANIES, ensure_ascii=False)};
const UNICORNS = {json.dumps(UNICORNS, ensure_ascii=False)};
const TOPICS = {json.dumps(TOPICS, ensure_ascii=False)};
const HEATMAP = {json.dumps(HEATMAP, ensure_ascii=False)};
const KEYWORDS = {json.dumps(KEYWORDS, ensure_ascii=False)};
const CATEGORIES = {json.dumps(CATEGORIES, ensure_ascii=False)};
const JOBS = {json.dumps(JOBS, ensure_ascii=False)};
const JOB_DETAILS = {json.dumps(JD_DETAIL, ensure_ascii=False)};
const EMERGING_GROUPS = {json.dumps(EMERGING_GROUPS, ensure_ascii=False)};
{JS_LOGIC}
function renderIndustry(){{
  const el=document.getElementById('coGrid');
  if(!el) return;
  el.innerHTML=COMPANIES.map(c=>`<div class="co-card" onclick="openCompanyPage('${{c.name}}')"><div class="co-name"><span>${{c.name}}</span><span class="co-jump">查看详情 →</span></div><div class="co-mini-grid"><div class="mini-kpi"><div class="mini-label">在招总量</div><div class="mini-value">${{c.total.toLocaleString()}}</div><div class="mini-trend" style="color:#64748b">本期快照</div></div><div class="mini-kpi"><div class="mini-label">AI 岗位</div><div class="mini-value">${{(c.ai+(c.ai_user||0)).toLocaleString()}}</div><div class="mini-trend" style="color:#2563eb">占比 ${{c.ai_ratio}}%</div></div></div></div>`).join('');
}}

function renderCpRows(items){{
  return items.map(j => {{
    const tags=(j.tags||[]).slice(0,3).map(t=>`<span class="l-tag">${{escapeHtml(t)}}</span>`).join('');
    const typePill=j.type?`<span class="type-pill type-${{escapeHtml(j.type)}}">${{escapeHtml(j.type)}}</span>`:'';
    return `<tr>
      <td><div class="job-name">${{escapeHtml(j.title)}}</div><div class="job-tags">${{tags}}</div></td>
      <td style="color:#475569">${{escapeHtml(j.direction||'-')}}</td>
      <td style="color:#475569">${{escapeHtml(j.city||'-')}}</td>
      <td>${{typePill}}</td>
      <td style="color:#64748b">${{escapeHtml(j.date||'-')}}</td>
      <td>${{renderJobAction(j, 'btn-ghost', '查看')}}</td>
    </tr>`;
  }}).join('');
}}
</script>
</body>
</html>'''
html = re.sub(r'/\[\\n([^\]]*?)\]/', lambda m: '/[\\\\n' + m.group(1) + ']/', html)
html = html.replace("split(/[\\n；;。]/)", "split(/[\\n\\u3002\\uff1b;]/)")

def fix_regex_literals(src):
    result = []
    i = 0
    while i < len(src):
        if src[i:i+2] == '//':
            end = src.find('\n', i+2)
            result.append(src[i:end+1] if end != -1 else src[i:])
            i = end+1 if end != -1 else len(src)
        elif src[i] == '/' and i > 0 and src[i-1] in ' =(!,;[\n\t:|&|^~?':
            j = i+1
            in_class = False
            while j < len(src):
                c = src[j]
                if c == '[': in_class = True
                elif c == ']': in_class = False
                elif c == '\\': j += 1
                elif c == '/' and not in_class: break
                elif c == '\n' and in_class: src = src[:j] + '\\n' + src[j+1:]
                j += 1
            result.append(src[i:j+1]); i = j+1
        else:
            result.append(src[i]); i += 1
    return ''.join(result)

html = fix_regex_literals(html)
for bad, good in [('/[\n；;。]/', '/[\\n\\u3002\\uff1b;]/'),('/[\n;；。]/', '/[\\n;\\uff1b\\u3002]/')]:
    html = html.replace(bad, good)
OUT.write_text(html, encoding='utf-8')
print(f'✅ 成功生成：{OUT}')
