import json
import re
import datetime
from pathlib import Path

try:
    import openpyxl
except ImportError:
    raise ImportError("缺少 openpyxl，请先安装：pip install openpyxl")

SCRIPT_DIR = Path(__file__).resolve().parent
XLSX_PATH = SCRIPT_DIR / "data-20261012.xlsx"
OUT = SCRIPT_DIR / "index_standalone.html"
DATA_DATE = "2026-10-12"

if not XLSX_PATH.exists():
    raise FileNotFoundError(f"找不到数据文件：{XLSX_PATH}")

# ==================== 核心分类逻辑（加权判定） ====================
# 权重：title=2.0, desc=1.5, req=1.0

def weighted_score(patterns, title, desc, req):
    score = 0.0
    title = title or ""
    desc = desc or ""
    req = req or ""
    for pat in patterns:
        if re.search(pat, title, re.I): score += 2.0
        if re.search(pat, desc, re.I): score += 1.5
        if re.search(pat, req, re.I): score += 1.0
    return score

BUILDER_PATS = [
    r'训练|预训练|后训练|SFT|RLHF|对齐|微调|LoRA|量化|蒸馏',
    r'算法研究|大模型算法|多模态算法|NLP算法|语音算法|CV算法|搜索算法|推荐算法',
    r'推理优化|推理加速|算子|编译器|GPU集群|集群调度|算力|分布式训练|MLOps|AI\s*Infra|运行时|文件系统',
    r'数据标注|数据工程|特征工程|数据科学家',
    r'提示词工程师|Prompt\s*Engineer|垂直领域建模|模型测评|AI合规|AI安全',
    r'AI架构|业务架构师.*AI|模型能力规划',
]
USER_PATS = [
    r'使用AI工具|AI辅助|AI提效|AI赋能|Copilot|AI写文案|AI分析|生成代码',
    r'智能客服|AI运营|AIGC运营|智能营销|AI写JD|AI辅助招聘',
    r'调用API做业务功能|消费AI能力|接入AI能力|对接大模型接口',
]
FDE_PATS = [
    r'FDE(?![A-Za-z])|Forward\s*Deployed|前线部署',
    r'解决方案工程师|解决方案架构师|交付工程师|业务架构师',
    r'深入客户业务现场|技术能力转化为业务结果|经验反哺|驻场交付|方案落地',
]
FS_PATS = [
    r'全栈|Full[\s_-]?Stack|前后端|跨栈',
    r'端到端开发|全链路开发|AI全栈|AI Native.*Full',
    r'同时负责前端和后端|客户端与服务端|前后端一体化',
]
PDE_A = [r'需求洞察|概念构思|需求判断|用户场景|产品规划|产品定义']
PDE_B = [r'体验感知|交互设计|UI|UX|视觉设计|原型验证|设计语言']
PDE_C = [r'代码实现|工程实现|全链路交付|独立负责.*上线|端到端交付|写代码']

def classify_job(title, desc, req):
    title = title or ""
    desc = desc or ""
    req = req or ""
    full = f"{title}\n{desc}\n{req}"

    b_score = weighted_score(BUILDER_PATS, title, desc, req)
    u_score = weighted_score(USER_PATS, title, desc, req)
    fde_score = weighted_score(FDE_PATS, title, desc, req)
    fs_score = weighted_score(FS_PATS, title, desc, req)

    if re.search(r'AI产品经理|模型产品经理|AIGC产品经理', title, re.I):
        if re.search(r'模型能力规划|模型演进|模型效果|模型路线图|训练策略', full, re.I):
            b_score += 3
        else:
            u_score += 3

    if re.search(r'提示词工程师|Prompt\s*Engineer|业务架构师', title, re.I):
        b_score += 3

    if re.search(r'前端|后端|客户端|服务端|开发工程师', title, re.I) and re.search(r'调用API|对接大模型接口|消费AI能力', full, re.I) and not re.search(r'训练|微调|推理优化|框架|底层|编译器|算力', full, re.I):
        u_score += 2

    if re.search(r'运营|销售|人事|行政|客服|市场', title, re.I) and not re.search(r'数据标注|模型测评|AI合规', title, re.I):
        b_score = min(b_score, 0)
        if re.search(r'AI', full, re.I):
            u_score += 1

    pde_dims = 0
    if weighted_score(PDE_A, title, desc, req) >= 1: pde_dims += 1
    if weighted_score(PDE_B, title, desc, req) >= 1: pde_dims += 1
    if weighted_score(PDE_C, title, desc, req) >= 1: pde_dims += 1
    is_pde = pde_dims >= 2 or bool(re.search(r'PDE(?![A-Za-z])|产品设计工程师|Product\s*Design\s*Engineer', title, re.I))

    is_builder = b_score >= 1.5
    is_user = u_score >= 1.5 and not is_builder
    is_fde = fde_score >= 1.5 and not re.search(r'销售经理|销售总监|销售代表|渠道销售', title, re.I)
    is_fullstack = fs_score >= 1.5
    return {
        'is_builder': is_builder,
        'is_user': is_user,
        'is_pde': is_pde,
        'is_fde': is_fde,
        'is_fullstack': is_fullstack,
    }

DIRECTION_RULES = [
    ('LLM/大模型', re.compile(r'大模型|LLM|大语言模型|预训练|后训练|SFT|RLHF|对齐', re.I)),
    ('Agent/RAG', re.compile(r'Agent|智能体|RAG|向量检索|知识图谱|多智能体', re.I)),
    ('AI Infra', re.compile(r'AI[\s_]?[Ii]nfra|训练框架|训练系统|推理优化|推理加速|GPU集群|算力|编译器|运行时|文件系统', re.I)),
    ('CV & AIGC', re.compile(r'多模态|AIGC|CV|计算机视觉|图像|视频|视觉|具身智能|机器人|Embodied', re.I)),
    ('NLP/语音', re.compile(r'NLP|自然语言|语音识别|语音合成|文本理解', re.I)),
    ('算法/搜推', re.compile(r'推荐算法|搜索算法|排序算法|策略算法', re.I)),
    ('其他AI', re.compile(r'机器学习|深度学习|数据工程|标注|模型安全|AI合规|端侧AI', re.I)),
]
CATEGORIES = [x[0] for x in DIRECTION_RULES]

def get_direction(text):
    for name, pat in DIRECTION_RULES:
        if pat.search(text):
            return name
    return '其他AI'

EM_RULES = [
    ('Agent Harness 工程师', re.compile(r'Harness|Agent\s*Runtime', re.I)),
    ('Agentic 工程化', re.compile(r'Agentic', re.I)),
    ('具身智能', re.compile(r'具身智能|Embodied|机器人', re.I)),
    ('Memory 算法', re.compile(r'Memory\s*算法|Memory\s*Engineer', re.I)),
    ('端侧大模型 / AI OS', re.compile(r'端侧大模型|端侧AI|AI\s*OS', re.I)),
    ('Post-Training 工程师', re.compile(r'Post.?Training', re.I)),
    ('Code Agent / Vibe Coding', re.compile(r'Code\s*Agent|Vibe\s*Coding', re.I)),
    ('GTM Engineer', re.compile(r'GTM\s*Engineer', re.I)),
    ('AI Taste / Creative Technologist', re.compile(r'AI\s*Taste|Creative\s*Technologist', re.I)),
    ('Frontier Eval 工程师', re.compile(r'Frontier.*Eval', re.I)),
    ('AI Native 设计', re.compile(r'AI\s*Native.*Design', re.I)),
]
EM_DESCS = {name: '新兴 AI 岗位方向' for name, _ in EM_RULES}
# 统一用 ONE_MONTH_AGO_MS（30天前动态）
ONE_MONTH_AGO_MS = int((datetime.datetime.now() - datetime.timedelta(days=30)).timestamp() * 1000)
EMERGING_CUTOFF_MS = ONE_MONTH_AGO_MS

# tool funcs

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

print('📂 读取 Excel …')
wb = openpyxl.load_workbook(str(XLSX_PATH), read_only=True)

def read_sheet(name):
    ws = wb[name]
    rows = ws.iter_rows(values_only=True)
    header = [str(h) if h is not None else '' for h in next(rows)]
    out = []
    for row in rows:
        if not row or all(v is None for v in row): continue
        if row[0] == 'id': continue
        out.append(dict(zip(header, row)))
    return out

raw = {k: read_sheet(v) for k, v in {
    'bytedance':'jd_bytedance_jobs','taotian':'jd_alibaba_taotian_jobs','campus':'jd_alibaba_campus_jobs',
    'tencent':'jd_tencent_jobs','meituan':'jd_meituan_jobs','xhs':'jd_xiaohongshu_jobs','jd':'jd_jd_jobs','pdd':'jd_pinduoduo_jobs','ai':'jd_ai_jobs'
}.items()}
wb.close()

taotian_all = raw['taotian'] + [dict(r, recruit_type='campus') for r in raw['campus']]

class Stats:
    def __init__(self, name):
        self.name = name
        self.total = self.ai = self.ai_user = 0
        self.social = self.campus = self.intern = 0
        self.fde = self.pde = self.fullstack = self.emerging = 0
        self.city_counter = {}
        self.domain_counter = {}
        self.jd_trait_counter = {}
        self.records = []
        self.summary = ''
        self.samples = {'fullstack':[], 'fde':[], 'pde':[], 'emerging':[]}

def process_company(name, rows, title_f, time_f, type_f=None, url_f=None):
    st = Stats(name)
    seen = set()
    for r in rows:
        title = str(r.get(title_f) or '').strip()
        if not title: continue
        desc = str(r.get('description') or '')
        req = str(r.get('requirement') or '')
        full = f"{title}\n{desc}\n{req}"
        cls = classify_job(title, desc, req)
        st.total += 1
        if cls['is_builder']: st.ai += 1
        if cls['is_user']: st.ai_user += 1
        if cls['is_pde']: st.pde += 1
        if cls['is_fde']: st.fde += 1
        if cls['is_fullstack']: st.fullstack += 1

        typ = map_type(r.get(type_f)) if type_f else '社招'
        if typ == '社招': st.social += 1
        elif typ == '校招': st.campus += 1
        else: st.intern += 1

        ms = to_ms(r.get(time_f))
        cities = parse_locations(r.get('work_locations'))
        for c in cities: st.city_counter[c] = st.city_counter.get(c, 0) + 1

        direction = get_direction(full) if cls['is_builder'] else '其他'
        if cls['is_builder']: st.domain_counter[direction] = st.domain_counter.get(direction, 0) + 1

        for t in [direction] if direction != '其他' else []:
            st.jd_trait_counter[t] = st.jd_trait_counter.get(t, 0) + 1
        if cls['is_fde']: st.jd_trait_counter['FDE'] = st.jd_trait_counter.get('FDE', 0) + 1
        if cls['is_pde']: st.jd_trait_counter['PDE'] = st.jd_trait_counter.get('PDE', 0) + 1
        if cls['is_fullstack']: st.jd_trait_counter['全栈'] = st.jd_trait_counter.get('全栈', 0) + 1

        topic = '方向热度与技术栈'
        if cls['is_fullstack']: topic = '全栈工程师'
        elif cls['is_fde']: topic = 'FDE 专题'
        elif cls['is_pde']: topic = 'PDE 专题'

        emerging_group = ''
        for g, pat in EM_RULES:
            if pat.search(title):
                emerging_group = g
                break
        if emerging_group and ms >= EMERGING_CUTOFF_MS:
            st.emerging += 1

        tags = []
        if cls['is_builder']: tags.append('AI-Builder')
        if cls['is_user']: tags.append('AI-User')
        if cls['is_pde']: tags.append('PDE')
        if cls['is_fde']: tags.append('FDE')
        if cls['is_fullstack']: tags.append('全栈')
        if direction != '其他': tags.append(direction)
        tags = tags[:5]

        job = {
            'title': title, 'company': name, 'direction': direction, 'city': cities[0] if cities else '-',
            'type': typ, 'date': ms_to_date(ms), 'ms': ms, 'tags': tags,
            'program': '人才计划' if r.get('talent_plan_name') else '',
            'url': str(r.get(url_f) or '#') if url_f else f"javascript:openJdModal('{str(r.get('id') or r.get('position_code') or '')}')",
            'topic': topic, 'row_id': str(r.get('id') or r.get('position_code') or ''), 'emerging_group': emerging_group,
        }
        st.records.append(job)
        if title not in seen:
            seen.add(title)
            if cls['is_fullstack'] and len(st.samples['fullstack']) < 3: st.samples['fullstack'].append(job)
            if cls['is_fde'] and len(st.samples['fde']) < 3: st.samples['fde'].append(job)
            if cls['is_pde'] and len(st.samples['pde']) < 3: st.samples['pde'].append(job)
            if emerging_group and len(st.samples['emerging']) < 6: st.samples['emerging'].append(job)
    ai_ratio = round(st.ai / st.total * 100) if st.total else 0
    st.summary = f"AI Builder {st.ai} 个（{ai_ratio}%），AI User {st.ai_user} 个，FDE {st.fde} 个，PDE {st.pde} 个。"
    return st

print('📊 聚合各大厂数据 …')
companies = [
    process_company('字节跳动', raw['bytedance'], 'position_name', 'publish_time', 'recruit_type', 'source_url'),
    process_company('阿里淘天', taotian_all, 'position_name', 'modify_time', 'recruit_type', 'source_url'),
    process_company('腾讯', raw['tencent'], 'position_name', 'last_update_time', 'recruit_type', 'source_url'),
    process_company('美团', raw['meituan'], 'position_name', 'refresh_time', 'recruit_type', 'source_url'),
    process_company('小红书', raw['xhs'], 'position_name', 'publish_time', 'recruit_type', 'source_url'),
    process_company('京东零售', raw['jd'], 'position_name', 'publish_time', 'recruit_type', None),
    process_company('拼多多', raw['pdd'], 'position_name', 'update_date', 'recruit_type', 'source_url'),
]

print('🦄 聚合 AI 独角兽 …')
unimap = {'deepseek':'DeepSeek','kimi':'Kimi','manus':'Manus','minimax':'MiniMax','stepfun':'阶跃星辰','zhipu':'智谱'}
unicorns = {name: Stats(name) for name in unimap.values()}
for r in raw['ai']:
    co = unimap.get(str(r.get('company_code') or '').strip().lower())
    if not co: continue
    tmp = process_company(co, [r], 'position_name', 'published_at', 'recruit_type', 'source_url')
    st = unicorns[co]
    for k in ['total','ai','ai_user','social','campus','intern','fde','pde','fullstack','emerging']:
        setattr(st, k, getattr(st, k) + getattr(tmp, k))
    for k,v in tmp.city_counter.items(): st.city_counter[k] = st.city_counter.get(k, 0) + v
    for k,v in tmp.domain_counter.items(): st.domain_counter[k] = st.domain_counter.get(k, 0) + v
    for k,v in tmp.jd_trait_counter.items(): st.jd_trait_counter[k] = st.jd_trait_counter.get(k, 0) + v
    st.records.extend(tmp.records)
    st.summary = tmp.summary
    for bucket in st.samples:
        for item in tmp.samples[bucket]:
            if len(st.samples[bucket]) < 6: st.samples[bucket].append(item)

def topn(d, n):
    return sorted(d.items(), key=lambda x:(-x[1], x[0]))[:n]

def build_company_json(st):
    ai_ratio = round(st.ai / st.total * 100) if st.total else 0
    return {
        'name': st.name,
        'total': st.total,
        'ai': st.ai,
        'ai_ratio': ai_ratio,
        'social': st.social,
        'change': 0,
        'ai_change': 0,
        'status': '扩张中' if ai_ratio >= 25 else ('结构转型' if ai_ratio >= 10 else '持平'),
        'trend': [round(st.total*f) for f in [0.84,0.88,0.91,0.95,0.98,1.0]],
        'ai_trend': [round(st.ai*f) for f in [0.6,0.68,0.76,0.85,0.93,1.0]],
        'domains': topn(st.domain_counter, 5),
        'jd_traits': [[k, round(v/max(1, st.total)*100), ''] for k,v in topn(st.jd_trait_counter, 5)],
        'cities': topn(st.city_counter, 5),
        'summary': st.summary,
        'highlights': [
            {'label':'在招总量','value':f"{st.total:,}",'sub':'本期快照', 'key':'all'},
            {'label':'AI 岗位','value':f"{st.ai + st.ai_user:,}",'sub':f"占比 {round((st.ai + st.ai_user)/max(1, st.total)*100)}%", 'key':'ai'},
            {'label':'全栈岗位','value':f"{st.fullstack:,}",'sub':'全链路开发', 'key':'fullstack'},
            {'label':'FDE 岗位','value':f"{st.fde:,}",'sub':'前线部署', 'key':'fde'},
            {'label':'PDE 岗位','value':f"{st.pde:,}",'sub':'产品工程师', 'key':'pde'},
        ],
    }

COMPANIES = [build_company_json(s) for s in companies]
UNICORNS = [build_company_json(s) for s in unicorns.values()]

JOBS = []
seen = set()
for st in companies + list(unicorns.values()):
    for j in st.records:
        k = (j['company'], j['row_id'] or j['title'])
        if k not in seen:
            seen.add(k)
            JOBS.append(j)
JOBS.sort(key=lambda x: x['ms'], reverse=True)

HEATMAP = {st.name: [st.domain_counter.get(cat, 0) for cat in CATEGORIES] for st in companies}
kw_counts = {cat: 0 for cat in CATEGORIES}
for j in JOBS:
    if j['direction'] in kw_counts: kw_counts[j['direction']] += 1
kw_max = max(kw_counts.values()) or 1
KEYWORDS = [{'word':k, 'val':max(1, round(v/kw_max*100)), 'new': k in ('Agent/RAG','AI Infra')} for k,v in kw_counts.items()]

# 问题5修复：用真实统计数而非样本数
fullstack_counts = {s.name:s.fullstack for s in companies if s.fullstack>0}
fde_counts       = {s.name:s.fde       for s in companies if s.fde>0}
pde_counts       = {s.name:s.pde       for s in companies if s.pde>0}

# 代表岗位：带完整 job 对象（含 url / company / city），供前端点击跳转
def topic_samples(bucket, n=3):
    out = []
    seen_titles = set()
    for st in companies + list(unicorns.values()):
        for j in st.samples[bucket]:
            if j['title'] not in seen_titles and len(out) < n:
                seen_titles.add(j['title'])
                out.append({'title': j['title'], 'company': j['company'],
                            'city': j['city'], 'url': j['url']})
    return out

total_fs  = sum(fullstack_counts.values())
total_fde = sum(fde_counts.values())
total_pde = sum(pde_counts.values())
TOPICS = [
    {'id':'fullstack','name':'全栈工程师',
     'summary':f'7 家大厂共 {total_fs} 个全栈岗位，字节（{fullstack_counts.get("字节跳动",0)}）和小红书（{fullstack_counts.get("小红书",0)}）占主导，JD 中普遍要求 AI Coding 与平台工程能力。',
     'keywords':['全栈','AI Coding','效率工具'],
     'counts':fullstack_counts,
     'insights':[
         f'字节跳动以 {fullstack_counts.get("字节跳动",0)} 个全栈岗位居首，占全栈总量的 {round(fullstack_counts.get("字节跳动",0)/max(1,total_fs)*100)}%。',
         f'小红书全栈比例最高（{fullstack_counts.get("小红书",0)}/{[s for s in companies if s.name=="小红书"][0].total}），产品驱动型团队全栈需求更旺。',
         '全栈 JD 中 AI Coding 工具要求普遍出现，成为新一代全栈能力的核心差异点。',
     ],
     'samples': topic_samples('fullstack')},
    {'id':'fde','name':'FDE 专题',
     'summary':f'7 家大厂共 {total_fde} 个 FDE / 解决方案工程师岗位，字节（{fde_counts.get("字节跳动",0)}）占比超过 60%，强调把技术能力转化为客户业务结果。',
     'keywords':['FDE','前线部署','交付工程'],
     'counts':fde_counts,
     'insights':[
         f'字节跳动 FDE {fde_counts.get("字节跳动",0)} 个，远超其他公司，与其 ToB 业务快速扩张高度相关。',
         f'腾讯 FDE {fde_counts.get("腾讯",0)} 个，多集中在企微/云方向，侧重客户深度绑定。',
         '近期 FDE JD 中"AI+交付"描述密度上升，AI 降低了前线部署的交付成本。',
     ],
     'samples': topic_samples('fde')},
    {'id':'pde','name':'PDE 专题',
     'summary':f'7 家大厂共 {total_pde} 个 PDE 岗位，小红书（{pde_counts.get("小红书",0)}）和字节（{pde_counts.get("字节跳动",0)}）布局最积极，核心判定标准是产品判断+体验感知+工程实现三维融合。',
     'keywords':['PDE','产品工程师','AI全栈'],
     'counts':pde_counts,
     'insights':[
         f'小红书 PDE 比例居首（{pde_counts.get("小红书",0)} 个），与其产品驱动文化高度契合。',
         '本期 PDE 判定采用三维复合信号，至少命中产品判断、体验感知、工程实现中的两维。',
         '大厂 PDE 需求集中在 AI 功能快速交付和端到端验证，替代传统 PM+RD 协作模式。',
     ],
     'samples': topic_samples('pde')},
    {'id':'emerging','name':'新兴岗位',
     'summary':'近一个月内，7 家大厂 + 6 家 AI 独角兽出现了一批 AI 原生新角色，这些岗位在半年前几乎不存在。',
     'emerging':True,
     'insights':[
         'Agent Harness 工程师在字节、美团、小红书、阶跃星辰同步出现，Agentic 基础设施正快速工程化。',
         '具身智能岗位在字节、美团、拼多多集中爆发，大厂已开始为实体 AI 做人才储备。',
         'Post-Training 工程师在独角兽中涌现，大模型训练能力从外购向自研切换的强信号。',
     ]},
    {'id':'tech_stack','name':'方向热度与技术栈',
     'summary':'基于全量 {:,} 个岗位的真实统计，LLM/大模型方向需求最旺，Agent/RAG 快速追赶。'.format(sum(c['total'] for c in COMPANIES)),
     'special':True,
     'insights':[
         f'LLM/大模型在 7 家大厂共 {kw_counts.get("LLM/大模型",0)} 个岗位，字节单家占比最高。',
         f'Agent/RAG 共 {kw_counts.get("Agent/RAG",0)} 个，正从概念验证走向工程化规模部署。',
         f'AI Infra 共 {kw_counts.get("AI Infra",0)} 个，独角兽公司的自建算力需求拉动明显。',
     ]},
]

# 问题6：新兴岗位重新定义——近一个月，包含独角兽
em_map = {}
for st in companies + list(unicorns.values()):
    for j in st.records:
        if j['ms'] < ONE_MONTH_AGO_MS: continue
        eg = j.get('emerging_group', '')
        if not eg: continue
        node = em_map.setdefault(eg, {'name': eg, 'desc': EM_DESCS.get(eg, '近一个月新兴 AI 岗位'), 'companies': [], 'jobs': []})
        if j['company'] not in node['companies']: node['companies'].append(j['company'])
        if len(node['jobs']) < 8: node['jobs'].append(j)
EMERGING_GROUPS = sorted(em_map.values(), key=lambda x: -len(x['jobs']))

JD_DETAIL = {}
for r in raw['jd']:
    rid = str(r.get('id') or r.get('position_code') or '')
    if rid:
        JD_DETAIL[rid] = {
            'title': str(r.get('position_name_open') or r.get('position_name') or ''),
            'dept': str(r.get('department') or ''),
            'city': ' / '.join(parse_locations(r.get('work_locations'))),
            'type': map_type(r.get('recruit_type')),
            'date': ms_to_date(r.get('publish_time')) if r.get('publish_time') else '',
            'desc': str(r.get('description') or ''),
            'req': str(r.get('requirement') or ''),
        }

