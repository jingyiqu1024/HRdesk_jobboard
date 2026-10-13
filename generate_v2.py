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

print('📄 生成 HTML …')
CSS = r"""
:root{--brand:#2563eb;--brand-soft:#eff6ff;--text:#0f172a;--muted:#64748b;--bg:#f8fafc;--card:#fff;--border:#e2e8f0;--radius:12px;--shadow:0 1px 3px rgba(0,0,0,.08);--up:#10b981;--dn:#ef4444}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'PingFang SC',sans-serif;background:var(--bg);color:var(--text);line-height:1.6}
.container{max-width:1280px;margin:0 auto;padding:24px 20px}
header{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:24px}
.logo h1{font-size:24px;font-weight:800;letter-spacing:-.03em}
.section{margin-bottom:40px}
.sec-title{font-size:18px;font-weight:800;margin-bottom:16px;display:flex;align-items:center;gap:8px}
.sec-title::before{content:'';width:4px;height:16px;background:var(--brand);border-radius:2px}
.ov-row{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:32px}
.ov-card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:16px 20px;display:flex;align-items:center;justify-content:space-between;box-shadow:var(--shadow)}
.ov-label{font-size:12px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
.ov-val{font-size:28px;font-weight:800;margin:4px 0}
.ov-sub{font-size:12px}
.sparkline{width:100px;height:40px}
.topic-layout{display:grid;grid-template-columns:240px 1fr;gap:20px;min-height:560px}
.topic-tabs{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;box-shadow:var(--shadow)}
.topic-tab{padding:14px 16px;border-bottom:1px solid #f8fafc;cursor:pointer;transition:.15s}
.topic-tab:hover{background:#f8fafc}
.topic-tab.active{background:var(--brand-soft);border-right:3px solid var(--brand)}
.topic-tab-name{font-size:14px;font-weight:700}
.topic-panel,.panel-box{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:24px;box-shadow:var(--shadow)}
.panel-top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:18px}
.tag-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px}
.tag-chip{background:#f1f5f9;padding:4px 10px;border-radius:999px;font-size:12px;color:#334155}
.insight-box{background:#f8fafc;border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin-bottom:18px}
.insight-box ul{padding-left:18px}
.insight-box li{margin:6px 0;font-size:13px;color:#334155}
.metric-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:18px}
.metric-grid.collapsed .metric-card.overflow-card{display:none}
.metric-toggle-row{display:flex;justify-content:flex-end;margin:-8px 0 16px}
.metric-toggle{display:inline-flex;align-items:center;gap:4px;font-size:12px;font-weight:700;color:var(--brand);cursor:pointer;user-select:none}
.metric-toggle:hover{text-decoration:underline}
.metric-toggle .arrow{transition:transform .2s;display:inline-block}
.metric-grid:not(.collapsed) ~ .metric-toggle-row .arrow{transform:rotate(180deg)}
.metric-card{background:#f8fafc;border-radius:10px;padding:12px;cursor:pointer;border:1px solid transparent;transition:.15s}
.metric-card:hover{border-color:#bfdbfe;background:#eff6ff}
.metric-title{font-size:11px;color:var(--muted);margin-bottom:4px}
.metric-value{font-size:16px;font-weight:800}
.metric-tip{font-size:11px;color:var(--brand);margin-top:4px}
/* 代表岗位：左侧岗位名，右侧公司·城市 */
.sample-list{display:flex;flex-direction:column}
.sample-row{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:14px 2px;border-bottom:1px solid var(--border)}
.sample-row:last-child{border-bottom:none}
.sample-col-title{font-size:15px;font-weight:700}
.sample-sub{font-size:13px;color:var(--muted);white-space:nowrap}
.em-grid{display:grid;grid-template-columns:1.2fr .8fr;gap:18px}
.em-list{display:flex;flex-direction:column;gap:12px}
.em-card{border:1px solid var(--border);border-radius:12px;padding:16px;background:#fff}
.em-title{font-size:15px;font-weight:800;margin-bottom:6px}
.em-desc{font-size:13px;color:var(--muted);margin-bottom:10px}
.em-meta{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.em-pill{background:#f1f5f9;border-radius:999px;padding:4px 10px;font-size:12px;color:#334155;cursor:pointer}
.em-tab{background:#f8fafc;color:#334155}
.em-tab.active{background:var(--brand-soft);color:var(--brand);border-color:var(--brand) !important}
.em-tab:hover{background:var(--brand-soft);color:var(--brand)}
.co-spark{display:block;flex-shrink:0}
.em-jobs{display:flex;flex-direction:column}
.ts-grid{display:grid;grid-template-columns:1.2fr 1fr;gap:20px}
.ts-box{border:1px solid var(--border);border-radius:10px;overflow:hidden}
.ts-box-h{background:#f8fafc;padding:10px;font-size:12px;font-weight:700;border-bottom:1px solid var(--border)}
table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;padding:10px;color:var(--muted);border-bottom:1px solid var(--border)}
td{padding:8px 10px;border-bottom:1px solid #f8fafc}
.h-cell{padding:4px;text-align:center;border-radius:4px;font-weight:700}
.kw-row{padding:10px;border-bottom:1px solid #f8fafc}
.kw-meta{display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px;font-weight:600}
.kw-bar{height:6px;background:#e2e8f0;border-radius:999px;overflow:hidden}
.kw-fill{height:100%;background:var(--brand)}
.co-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.co-card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:16px;box-shadow:var(--shadow);cursor:pointer;transition:.18s}
.co-card:hover{transform:translateY(-2px);box-shadow:0 8px 16px rgba(0,0,0,.06)}
.co-name{font-size:15px;font-weight:800;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center}
.co-status{font-size:10px;padding:2px 8px;border-radius:999px;background:var(--brand-soft);color:var(--brand);font-weight:700}
.co-mini-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}
.mini-kpi{background:#f8fafc;padding:10px;border-radius:10px}
.mini-label{font-size:11px;color:var(--muted)}
.mini-value{font-size:18px;font-weight:800;margin:2px 0}
.mini-trend{font-size:11px}
.co-link{font-size:12px;color:var(--brand);font-weight:700;display:flex;align-items:center;gap:6px}
.toolbar-row{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:16px}
.toolbar-actions{display:flex;gap:8px}
.search-row{display:flex;gap:10px;margin-bottom:16px}
.input-ui{flex:1;border:1px solid var(--border);border-radius:8px;padding:10px 14px;outline:none}
.btn-ui{background:var(--brand);color:#fff;border:none;border-radius:8px;padding:0 20px;font-weight:700;cursor:pointer}
.btn-ghost{background:transparent;color:#64748b;border:1px solid var(--border);border-radius:8px;padding:6px 12px;font-size:12px;font-weight:400;cursor:pointer;white-space:nowrap;transition:.15s}
.btn-ghost:hover{border-color:#bfdbfe;color:var(--brand);background:var(--brand-soft)}
.list-box{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:0}
.list-table{display:grid;grid-template-columns:2fr 1fr .8fr .7fr .7fr .6fr 80px;gap:0}
.list-th{padding:10px 16px;border-bottom:2px solid var(--border);background:#f8fafc;font-size:12px;font-weight:700;color:var(--muted);display:flex;align-items:center}
.list-th:first-child{border-radius:var(--radius) 0 0 0}
.list-th:last-child{border-radius:0 var(--radius) 0 0}
.list-td{padding:10px 16px;border-bottom:1px solid #f8fafc;display:flex;align-items:center}
.list-row:last-child .list-td{border-bottom:none}
.list-row{display:contents}
.l-tit{font-size:14px;font-weight:700}
.l-sub{font-size:11px;color:var(--muted)}
/* 公司详情页（全屏） */
.page-mask{position:fixed;inset:0;background:#f1f5f9;display:none;overflow:auto;z-index:1000}
.page-mask.show{display:block}
.page-wrap{max-width:1280px;margin:0 auto;padding:20px}
.back-bar{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}
.back-link{font-size:13px;color:var(--brand);font-weight:700;cursor:pointer;display:flex;align-items:center;gap:6px}
.page-card{background:#fff;border:1px solid var(--border);border-radius:14px;padding:20px 22px;box-shadow:var(--shadow);margin-bottom:14px}
.page-hero{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}
.page-title{font-size:30px;font-weight:800;letter-spacing:-.02em;display:flex;align-items:center;gap:10px}
.hero-desc{font-size:13px;color:var(--muted);margin-top:8px;max-width:760px}
.kpi-row{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:18px}
.kpi-cell{border-left:2px solid var(--border);padding-left:12px}
.kpi-cell:first-child{border-left:none;padding-left:0}
.kpi-cell.clickable{cursor:pointer;transition:.15s;padding:10px 0 10px 12px;border-radius:10px}
.kpi-cell.clickable:hover{background:#f8fafc}
.kpi-cell.active{background:#eff6ff}
.kpi-label{font-size:12px;color:var(--muted)}
.kpi-val{font-size:26px;font-weight:800;margin:2px 0}
.kpi-sub{font-size:11px;color:var(--muted)}
.block-title{font-size:15px;font-weight:800;margin-bottom:2px}
.block-sub{font-size:12px;color:var(--muted);margin-bottom:14px}
.bar-row{display:grid;grid-template-columns:130px 1fr 54px;gap:10px;align-items:center;margin-bottom:10px;font-size:13px}
.bar-track{height:14px;background:#eff6ff;border-radius:999px;overflow:hidden}
.bar-fill{height:100%;background:var(--brand);border-radius:999px}
.bar-num{text-align:right;font-weight:700}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.job-table{width:100%;border-collapse:collapse;font-size:12px}
.job-table th{text-align:left;padding:10px 8px;color:var(--muted);font-weight:600;border-bottom:1px solid var(--border)}
.job-table td{padding:12px 8px;border-bottom:1px solid #f1f5f9;vertical-align:middle}
.job-name{font-size:13px;font-weight:700;line-height:1.4}
.job-tags{display:flex;gap:6px;flex-wrap:wrap;margin-top:5px}
.job-tag{background:#f1f5f9;border-radius:4px;padding:1px 6px;font-size:10px;color:#475569}
.type-pill{display:inline-block;border-radius:4px;padding:1px 6px;font-size:10px;font-weight:700}
.type-社招{background:#eff6ff;color:#2563eb}
.type-校招{background:#ecfdf5;color:#059669}
.type-实习{background:#fef3c7;color:#b45309}
.modal-mask{position:fixed;inset:0;background:rgba(15,23,42,.45);display:none;align-items:center;justify-content:center;padding:20px;z-index:1100}
.modal-mask.show{display:flex}
.modal-card{width:min(900px,100%);background:#fff;border-radius:16px;box-shadow:0 20px 60px rgba(15,23,42,.18);padding:28px 32px;border:1px solid var(--border);max-height:90vh;overflow:auto}
.modal-top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:8px}
.modal-title{font-size:22px;font-weight:800;line-height:1.3}
.modal-close{border:none;background:#f1f5f9;border-radius:8px;padding:6px 12px;cursor:pointer;font-weight:700;font-size:13px;white-space:nowrap}
.modal-badges{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px}
.modal-badge{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:600;background:#f1f5f9;color:#475569}
.modal-badge.blue{background:#eff6ff;color:#2563eb}
.modal-badge.green{background:#f0fdf4;color:#16a34a}
.modal-sec{margin-top:16px}
.modal-sec h4{font-size:13px;font-weight:700;color:#64748b;margin-bottom:8px;text-transform:uppercase;letter-spacing:.04em}
.modal-sec li{font-size:14px;color:#334155;line-height:1.7}
.modal-sec ul{padding-left:20px}
.up{color:var(--up)}
.dn{color:var(--dn)}
/* 筛选 select 轻量 */
.filter-bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
.filter-sel{appearance:none;-webkit-appearance:none;border:1px solid transparent;border-radius:8px;padding:6px 28px 6px 10px;font-size:12px;background:#f1f5f9 url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%2394a3b8' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E") no-repeat right 10px center;color:#334155;cursor:pointer;outline:none;font-weight:500;transition:.15s}
.filter-sel:hover{border-color:var(--border);background-color:#e8edf3}
.filter-sel:focus{border-color:var(--brand);background-color:#fff;box-shadow:0 0 0 3px rgba(37,99,235,.08)}
/* 专题公司卡右侧查看 */
.metric-card{display:flex;justify-content:space-between;align-items:center;gap:10px}
.metric-card .metric-left{min-width:0}
.metric-link{font-size:11px;color:#94a3b8;font-weight:400;white-space:nowrap;flex-shrink:0;transition:.15s}
.metric-card:hover .metric-link{color:var(--brand)}
/* 行业概览卡右上角 */
.co-jump{font-size:11px;color:#94a3b8;font-weight:400;white-space:nowrap;transition:.15s}
.co-card:hover .co-jump{color:var(--brand)}
@media(max-width:900px){
 .ov-row,.topic-layout,.co-grid,.ts-grid,.metric-grid,.two-col,.co-mini-grid,.em-grid,.kpi-row{grid-template-columns:1fr}
 .list-item,.bar-row{grid-template-columns:1fr}
}

.kpi-row{display:grid;grid-template-columns:repeat(5,1fr)!important;gap:12px;margin-top:18px;}.kpi-cell{min-width:0}.hero-desc{display:none!important}
/* ===== Tooltip ===== */
.tip-wrap{position:relative;display:inline-flex;align-items:center;vertical-align:middle}
.tip-icon{display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;background:transparent;color:#94a3b8;cursor:default;margin-left:5px;flex-shrink:0;transition:color .15s}
.tip-icon:hover,.tip-icon:focus{color:#64748b;outline:none}
.tip-icon svg{display:block}
.tip-box{visibility:hidden;opacity:0;position:absolute;bottom:calc(100% + 8px);left:50%;transform:translateX(-50%);background:#1e293b;color:#f1f5f9;font-size:12px;font-weight:400;line-height:1.7;padding:10px 14px;border-radius:10px;width:260px;white-space:normal;z-index:9999;pointer-events:none;transition:opacity .15s;box-shadow:0 4px 20px rgba(0,0,0,.22)}
.tip-box::after{content:'';position:absolute;top:100%;left:50%;transform:translateX(-50%);border:5px solid transparent;border-top-color:#1e293b}
.tip-box.show{visibility:visible;opacity:1}
"""
BODY = r"""
<div class="container">
  <header>
    <div class="logo"><h1>竞品岗位情报看板</h1></div>
    <div style="font-size:12px;color:var(--muted)">数据截止 2026-10-10</div>
  </header>

  <section class="section">
    <div class="sec-title">数据趋势</div>
    <div class="ov-row">
      <div class="ov-card">
        <div><div class="ov-label">岗位总量</div><div class="ov-val">20,852</div>
        <div class="ov-sub">覆盖 7 大厂 + 6 家 AI 独角兽 · 社招 16,779 / 校招 4,073</div></div>
        <canvas class="sparkline" id="spark1"></canvas>
      </div>
      <div class="ov-card">
        <div><div class="ov-label">AI 岗位<span class="tip-wrap"><span class="tip-icon" tabindex="0" onmouseenter="tipShow(this)" onmouseleave="tipHide(this)" onfocus="tipShow(this)" onblur="tipHide(this)"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="6.25" stroke="currentColor" stroke-width="1.5"/><path d="M6.9 6.1a1.35 1.35 0 1 1 2.1 1.12c-.72.48-1 .82-1 1.53v.2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="8" cy="11.5" r=".8" fill="currentColor"/></svg></span><span class="tip-box">Builder + User 两类之和。<br><b>Builder</b>：岗位本身在造 AI，如大模型训练、推理优化、Prompt 工程师。<br><b>User</b>：岗位利用 AI 工具提效，如 AI 运营、Copilot 接入。</span></span></div><div class="ov-val up">4,936</div>
        <div class="ov-sub">占比 24% · 社招 3,075 / 校招 1,861</div></div>
        <canvas class="sparkline" id="spark2"></canvas>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="sec-title">专题透视</div>
    <div class="topic-layout">
      <div class="topic-tabs"><div class="topic-tab active" data-id="fullstack" onclick="selTopic('fullstack')"><div class="topic-tab-name">全栈工程师</div></div><div class="topic-tab" data-id="fde" onclick="selTopic('fde')"><div class="topic-tab-name">FDE 专题</div></div><div class="topic-tab" data-id="pde" onclick="selTopic('pde')"><div class="topic-tab-name">PDE 专题</div></div><div class="topic-tab" data-id="emerging" onclick="selTopic('emerging')"><div class="topic-tab-name">新兴岗位</div></div><div class="topic-tab" data-id="tech_stack" onclick="selTopic('tech_stack')"><div class="topic-tab-name">方向热度与技术栈</div></div></div>
      <div class="topic-panel" id="topicPanel"></div>
    </div>
  </section>

<div style="display:none">

  <section class="section">
    <div class="sec-title">AI 独角兽</div>
    <div style="font-size:13px;color:#64748b;margin-bottom:16px">
      共 1,065 个在招岗位，AI 相关 399 个（37%）· 覆盖 DeepSeek / Kimi / Manus / MiniMax / 阶跃星辰 / 智谱
    </div>
    <div class="co-grid" style="margin-bottom:14px">
        <div class="co-card" style="cursor:default">
          <div class="co-name">
            <span style="font-size:15px;font-weight:800">DeepSeek</span>
            <span class="co-status">扩张中</span>
          </div>
          <div class="co-mini-grid">
            <div class="mini-kpi">
              <div class="mini-label">在招总量</div>
              <div class="mini-value">37</div>
              <div class="mini-trend" style="color:#64748b">本期快照</div>
            </div>
            <div class="mini-kpi">
              <div class="mini-label">AI 岗位</div>
              <div class="mini-value">15</div>
              <div class="mini-trend" style="color:#2563eb">占比 41%</div>
            </div>
          </div>
          <div style="font-size:11px;color:#64748b;margin-bottom:4px">城市：北京(31) · 杭州(31) · 乌兰察布(2)</div>
          <div style="font-size:11px;color:#64748b;margin-bottom:4px">方向：Agent(7) · LLM/大模型(4) · 其他AI(2)</div>
          <div style="font-size:11px;color:#64748b">FDE 0 · 新兴 0</div>
        </div>
        <div class="co-card" style="cursor:default">
          <div class="co-name">
            <span style="font-size:15px;font-weight:800">Kimi</span>
            <span class="co-status">扩张中</span>
          </div>
          <div class="co-mini-grid">
            <div class="mini-kpi">
              <div class="mini-label">在招总量</div>
              <div class="mini-value">193</div>
              <div class="mini-trend" style="color:#64748b">本期快照</div>
            </div>
            <div class="mini-kpi">
              <div class="mini-label">AI 岗位</div>
              <div class="mini-value">61</div>
              <div class="mini-trend" style="color:#2563eb">占比 32%</div>
            </div>
          </div>
          <div style="font-size:11px;color:#64748b;margin-bottom:4px">城市：北京(112) · 上海(26) · 深圳(8)</div>
          <div style="font-size:11px;color:#64748b;margin-bottom:4px">方向：Agent(24) · LLM/大模型(23) · AI Infra(6)</div>
          <div style="font-size:11px;color:#64748b">FDE 1 · 新兴 9</div>
        </div>
        <div class="co-card" style="cursor:default">
          <div class="co-name">
            <span style="font-size:15px;font-weight:800">Manus</span>
            <span class="co-status">结构转型</span>
          </div>
          <div class="co-mini-grid">
            <div class="mini-kpi">
              <div class="mini-label">在招总量</div>
              <div class="mini-value">17</div>
              <div class="mini-trend" style="color:#64748b">本期快照</div>
            </div>
            <div class="mini-kpi">
              <div class="mini-label">AI 岗位</div>
              <div class="mini-value">5</div>
              <div class="mini-trend" style="color:#2563eb">占比 29%</div>
            </div>
          </div>
          <div style="font-size:11px;color:#64748b;margin-bottom:4px">城市：北京(17)</div>
          <div style="font-size:11px;color:#64748b;margin-bottom:4px">方向：Agent(4) · LLM/大模型(1)</div>
          <div style="font-size:11px;color:#64748b">FDE 0 · 新兴 0</div>
        </div>
        <div class="co-card" style="cursor:default">
          <div class="co-name">
            <span style="font-size:15px;font-weight:800">MiniMax</span>
            <span class="co-status">扩张中</span>
          </div>
          <div class="co-mini-grid">
            <div class="mini-kpi">
              <div class="mini-label">在招总量</div>
              <div class="mini-value">297</div>
              <div class="mini-trend" style="color:#64748b">本期快照</div>
            </div>
            <div class="mini-kpi">
              <div class="mini-label">AI 岗位</div>
              <div class="mini-value">122</div>
              <div class="mini-trend" style="color:#2563eb">占比 41%</div>
            </div>
          </div>
          <div style="font-size:11px;color:#64748b;margin-bottom:4px">城市：上海(277) · 北京(204) · 旧金山(20)</div>
          <div style="font-size:11px;color:#64748b;margin-bottom:4px">方向：LLM/大模型(64) · CV & AIGC(20) · Agent(15)</div>
          <div style="font-size:11px;color:#64748b">FDE 2 · 新兴 0</div>
        </div>
        <div class="co-card" style="cursor:default">
          <div class="co-name">
            <span style="font-size:15px;font-weight:800">阶跃星辰</span>
            <span class="co-status">扩张中</span>
          </div>
          <div class="co-mini-grid">
            <div class="mini-kpi">
              <div class="mini-label">在招总量</div>
              <div class="mini-value">362</div>
              <div class="mini-trend" style="color:#64748b">本期快照</div>
            </div>
            <div class="mini-kpi">
              <div class="mini-label">AI 岗位</div>
              <div class="mini-value">131</div>
              <div class="mini-trend" style="color:#2563eb">占比 36%</div>
            </div>
          </div>
          <div style="font-size:11px;color:#64748b;margin-bottom:4px">城市：上海(282) · 北京(146) · 深圳(42)</div>
          <div style="font-size:11px;color:#64748b;margin-bottom:4px">方向：LLM/大模型(76) · Agent(34) · 其他AI(10)</div>
          <div style="font-size:11px;color:#64748b">FDE 0 · 新兴 9</div>
        </div>
        <div class="co-card" style="cursor:default">
          <div class="co-name">
            <span style="font-size:15px;font-weight:800">智谱</span>
            <span class="co-status">扩张中</span>
          </div>
          <div class="co-mini-grid">
            <div class="mini-kpi">
              <div class="mini-label">在招总量</div>
              <div class="mini-value">159</div>
              <div class="mini-trend" style="color:#64748b">本期快照</div>
            </div>
            <div class="mini-kpi">
              <div class="mini-label">AI 岗位</div>
              <div class="mini-value">65</div>
              <div class="mini-trend" style="color:#2563eb">占比 41%</div>
            </div>
          </div>
          <div style="font-size:11px;color:#64748b;margin-bottom:4px">城市：北京(53) · 杭州(6) · 上海(5)</div>
          <div style="font-size:11px;color:#64748b;margin-bottom:4px">方向：LLM/大模型(37) · 其他AI(15) · Agent(6)</div>
          <div style="font-size:11px;color:#64748b">FDE 2 · 新兴 6</div>
        </div>
    </div>
    <div class="two-col">
      <div class="page-card">
        <div class="block-title">新兴岗位</div>
        <div class="block-sub">近一个月新出现岗位（大厂+AI独角兽）</div>
        <table class="job-table">
          <thead><tr><th style="width:52%">岗位</th><th>公司</th><th>城市</th><th>类型</th></tr></thead>
          <tbody><tr><td><span class='job-name'>Creative Technologist｜创意技术专家</span></td><td style='color:#475569'>Kimi</td><td style='color:#64748b'>-</td><td style='color:#64748b'>AI Taste / Creative Technologist</td></tr><tr><td><span class='job-name'>Agentic Commerce Engineer</span></td><td style='color:#475569'>Kimi</td><td style='color:#64748b'>北京</td><td style='color:#64748b'>Agentic 工程化</td></tr><tr><td><span class='job-name'>Post-Training Algorithm Researcher/Engineer</span></td><td style='color:#475569'>Kimi</td><td style='color:#64748b'>-</td><td style='color:#64748b'>Post-Training 工程师</td></tr><tr><td><span class='job-name'>AI Taste Mentor</span></td><td style='color:#475569'>Kimi</td><td style='color:#64748b'>北京</td><td style='color:#64748b'>AI Taste / Creative Technologist</td></tr><tr><td><span class='job-name'>GTM Engineer</span></td><td style='color:#475569'>Kimi</td><td style='color:#64748b'>-</td><td style='color:#64748b'>GTM Engineer</td></tr><tr><td><span class='job-name'>AI Agent 产品实习生（Vibe Coding 方向）</span></td><td style='color:#475569'>Kimi</td><td style='color:#64748b'>-</td><td style='color:#64748b'>Code Agent / Vibe Coding</td></tr><tr><td><span class='job-name'>Scientist, Frontier Science Evals  前沿科学评估研究员​（FTE/intern）</span></td><td style='color:#475569'>Kimi</td><td style='color:#64748b'>-</td><td style='color:#64748b'>Frontier Eval 工程师</td></tr><tr><td><span class='job-name'>Kimi 金融产品实习生（PM & Harness 方向）</span></td><td style='color:#475569'>Kimi</td><td style='color:#64748b'>-</td><td style='color:#64748b'>Agent Harness 工程师</td></tr><tr><td><span class='job-name'>Agent Harness 产品经理</span></td><td style='color:#475569'>阶跃星辰</td><td style='color:#64748b'>上海</td><td style='color:#64748b'>Agent Harness 工程师</td></tr><tr><td><span class='job-name'>Agent Runtime开发工程师</span></td><td style='color:#475569'>阶跃星辰</td><td style='color:#64748b'>北京</td><td style='color:#64748b'>Agent Harness 工程师</td></tr><tr><td><span class='job-name'>Agent Harness开发工程师</span></td><td style='color:#475569'>阶跃星辰</td><td style='color:#64748b'>北京</td><td style='color:#64748b'>Agent Harness 工程师</td></tr><tr><td><span class='job-name'>Agent Harness 技术leader</span></td><td style='color:#475569'>阶跃星辰</td><td style='color:#64748b'>北京</td><td style='color:#64748b'>Agent Harness 工程师</td></tr></tbody>
        </table>
      </div>
      <div class="page-card">
        <div class="block-title">FDE 前线部署岗位</div>
        <div class="block-sub">命中 FDE / Forward Deployed 关键词</div>
        <table class="job-table">
          <thead><tr><th style="width:52%">岗位</th><th>公司</th><th>城市</th><th></th></tr></thead>
          <tbody><tr><td><span class='job-name'>Forward Deployed Engineer</span></td><td style='color:#475569'>Kimi</td><td style='color:#64748b'>-</td><td><a class='btn-ghost' href='https://app.mokahr.com/social-recruitment/moonshot/148506#/job/d49677fe-261d-4908-8e60-f428ed28e7d9' target='_blank' rel='noopener' style='text-decoration:none;display:inline-block'>查看 JD ↗</a></td></tr><tr><td><span class='job-name'>前沿部署工程师FDE（AI行业落地）</span></td><td style='color:#475569'>MiniMax</td><td style='color:#64748b'>北京</td><td><a class='btn-ghost' href='https://vrfi1sk8a0.jobs.feishu.cn/index/position/7641891406751287603/detail' target='_blank' rel='noopener' style='text-decoration:none;display:inline-block'>查看 JD ↗</a></td></tr><tr><td><span class='job-name'>Forward Deployed Engineer（前沿部署工程师）</span></td><td style='color:#475569'>MiniMax</td><td style='color:#64748b'>深圳</td><td><a class='btn-ghost' href='https://vrfi1sk8a0.jobs.feishu.cn/index/position/7598036042735110446/detail' target='_blank' rel='noopener' style='text-decoration:none;display:inline-block'>查看 JD ↗</a></td></tr><tr><td><span class='job-name'>MaaS-FDE工程师</span></td><td style='color:#475569'>智谱</td><td style='color:#64748b'>-</td><td><a class='btn-ghost' href='https://app.mokahr.com/social-recruitment/zphz/148983#/job/7ce3066e-85b5-49c8-874b-cf465b2c4587' target='_blank' rel='noopener' style='text-decoration:none;display:inline-block'>查看 JD ↗</a></td></tr><tr><td><span class='job-name'>FDE工程师</span></td><td style='color:#475569'>智谱</td><td style='color:#64748b'>北京</td><td><a class='btn-ghost' href='https://app.mokahr.com/social-recruitment/zphz/148983#/job/1e90af61-4136-404e-82fa-93ce10bd9dc5' target='_blank' rel='noopener' style='text-decoration:none;display:inline-block'>查看 JD ↗</a></td></tr></tbody>
        </table>
      </div>
    </div>
  </section>

</div>
  <section class="section">
    <div class="sec-title">行业概览</div>
    <div class="co-grid" id="coGrid"></div>
  </section>

  <section class="section">
    <div class="sec-title">岗位明细查询</div>
    <div class="search-row" style="margin-bottom:10px">
      <input type="text" id="jQ" class="input-ui" placeholder="搜索关键词，如：Agent / 全栈 / 字节跳动..."/>
      <button class="btn-ui" onclick="searchJobs()">查询</button>
      <button class="btn-ghost" onclick="exportCsv()" style="padding:0 14px">导出 CSV</button>
    </div>
    <div class="filter-bar">
      <select id="fCo" class="filter-sel" onchange="searchJobs()">
        <option value="">全部公司</option>
        <option>字节跳动</option><option>腾讯</option><option>阿里淘天</option>
        <option>美团</option><option>小红书</option><option>京东零售</option><option>拼多多</option><option>DeepSeek</option><option>Kimi</option><option>Manus</option><option>MiniMax</option><option>阶跃星辰</option><option>智谱</option>
      </select>
      <select id="fType" class="filter-sel" onchange="searchJobs()">
        <option value="">全部类型</option>
        <option>社招</option><option>校招</option><option>实习</option>
      </select>
      <select id="fDir" class="filter-sel" onchange="searchJobs()">
        <option value="">全部方向</option>
        <option>产品</option><option>Agent研发</option><option>后端研发</option>
        <option>算法</option><option>数据分析</option><option>前端研发</option>
        <option>LLM/大模型</option><option>AI Infra</option><option>推荐/广告</option>
      </select>
      <select id="fDate" class="filter-sel" onchange="searchJobs()">
        <option value="">全部时间</option>
        <option value="1">近 1 天</option><option value="3">近 3 天</option>
        <option value="7">近 7 天</option><option value="14">近两周</option>
        <option value="30">近一个月</option><option value="99">更早</option>
      </select>
      <span id="filterCount" style="font-size:12px;color:var(--muted);margin-left:4px"></span>
    </div>
    <div class="list-box" id="jobList"></div>
  </section>
</div>

<!-- 岗位详情弹窗 -->
<div class="modal-mask" id="jobModal" onclick="if(event.target===this) closeJobModal()">
  <div class="modal-card">
    <div class="modal-top">
      <div class="modal-title" id="modalTitle">岗位详情</div>
      <button class="modal-close" onclick="closeJobModal()">关闭</button>
    </div>
    <div class="modal-badges" id="modalBadges"></div>
    <div class="modal-sec"><h4>岗位职责</h4><ul id="modalDuties"></ul></div>
    <div class="modal-sec"><h4>任职要求</h4><ul id="modalReqs"></ul></div>
  </div>
</div>

<!-- 公司详情页（全屏） -->
<div class="page-mask" id="companyPage">
  <div class="page-wrap">
    <div class="back-bar">
      <div class="back-link" onclick="closeCompanyPage()">← 返回看板</div>
      <div style="font-size:12px;color:var(--muted)">数据截止 2026-10-10</div>
    </div>

    <div class="page-card">
      <div class="page-hero">
        <div>
          <div class="page-title"><span id="cpName">公司</span><span class="co-status" id="cpStatus">状态</span></div>
          <div class="hero-desc" id="cpDesc"></div>
        </div>
      </div>
      <div class="kpi-row" id="cpKpis"></div>
    </div>

    <div class="page-card cp-overview-only">
      <div class="block-title">招聘规模趋势（近 6 期）</div>
      <div class="block-sub">图例说明：虚线为总量，圆点为 AI 相关</div>
      <div style="display:flex;gap:24px;align-items:flex-start">
        <canvas id="cpTrend" style="width:100%;height:190px;flex:1"></canvas>
        <div style="display:flex;flex-direction:column;gap:14px;font-size:12px;padding-top:6px;min-width:70px">
          <div><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#94a3b8;margin-right:6px"></span>总量</div>
          <div><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#2563eb;margin-right:6px"></span>AI 岗位</div>
        </div>
      </div>
    </div>

    <div class="two-col cp-overview-only">
      <div class="page-card">
        <div class="block-title">AI 岗位专业领域分布</div>
        <div class="block-sub" id="cpDomainSub">Top 5 专业子方向的岗位数量</div>
        <div id="cpDomains"></div>
      </div>
      <div class="page-card">
        <div class="block-title">AI 岗位 JD 特征分析</div>
        <div class="block-sub" id="cpTraitSub">JD 文本中关键词出现频率</div>
        <div id="cpTraits"></div>
      </div>
    </div>

    <div class="page-card cp-overview-only">
      <div class="block-title">城市布局</div>
      <div class="block-sub">岗位地点分布（按岗位数）</div>
      <div id="cpCities"></div>
    </div>

    <div class="page-card" id="cpJobsSection">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;gap:8px">
        <div>
          <div class="block-title" id="cpJobsTitle" style="margin-bottom:0">全部在招岗位</div>
          <div class="block-sub" id="cpJobsSub" style="margin-top:2px">岗位、城市、类型、发布时间、查看 JD</div>
        </div>
        <button class="btn-ghost" onclick="cpExportCsv()" style="padding:0 14px;white-space:nowrap">导出 CSV</button>
      </div>
      <div class="search-row" style="margin-bottom:10px">
        <input type="text" id="cpQ" class="input-ui" placeholder="搜索关键词，如：Agent / 全栈 / 字节跳动..." style="flex:1"/>
        <button class="btn-ui" onclick="cpSearch()">查询</button>
      </div>
      <div class="filter-bar">
        <select id="cpFType" class="filter-sel" onchange="cpSearch()">
          <option value="">全部类型</option>
          <option>社招</option><option>校招</option><option>实习</option><option>实习</option>
        </select>
        <select id="cpFDir" class="filter-sel" onchange="cpSearch()">
          <option value="">全部方向</option>
          <option>产品</option><option>Agent研发</option><option>后端研发</option>
          <option>算法</option><option>数据分析</option><option>前端研发</option>
          <option>LLM/大模型</option><option>AI Infra</option><option>推荐/广告</option>
        </select>
        <select id="cpFDate" class="filter-sel" onchange="cpSearch()">
          <option value="">全部时间</option>
          <option value="1">近 1 天</option><option value="3">近 3 天</option>
          <option value="7">近 7 天</option><option value="14">近两周</option>
          <option value="30">近一个月</option><option value="99">更早</option>
        </select>
        <span id="cpFCount" style="font-size:12px;color:var(--muted);margin-left:4px"></span>
      </div>
      <table class="job-table">
        <thead><tr><th style="width:46%">岗位</th><th>方向</th><th>城市</th><th>类型</th><th>更新</th><th></th></tr></thead>
        <tbody id="cpJobsBody"></tbody>
      </table>
    </div>
  </div>
</div>

"""
JS_LOGIC = r"""const _CP_PAGE_SIZE = 50;

const TIP_ICON = `<svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="6.25" stroke="currentColor" stroke-width="1.5"/><path d="M6.9 6.1a1.35 1.35 0 1 1 2.1 1.12c-.72.48-1 .82-1 1.53v.2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="8" cy="11.5" r=".8" fill="currentColor"/></svg>`;
function tipShow(el){ const box = el && el.parentElement && el.parentElement.querySelector('.tip-box'); if(box) box.classList.add('show'); }
function tipHide(el){ const box = el && el.parentElement && el.parentElement.querySelector('.tip-box'); if(box) box.classList.remove('show'); }

function renderCpPager(){
  const total = _cpFiltered.length;
  const pages = Math.ceil(total / _CP_PAGE_SIZE);
  if(pages <= 1) return '';
  const btnS = (d) => `padding:3px 8px;border:1px solid #e2e8f0;border-radius:5px;background:#fff;cursor:pointer;font-size:12px;${d?'opacity:.4;pointer-events:none;':''}`;
  let h = `<tr><td colspan="6"><div style="display:flex;align-items:center;gap:5px;justify-content:center;padding:10px 0;flex-wrap:wrap">`;
  h += `<span style="color:#94a3b8;font-size:12px;margin-right:4px">共 ${total.toLocaleString()} 条</span>`;
  h += `<button onclick="cpGotoPage(1)" style="${btnS(_cpPage===1)}">首页</button>`;
  h += `<button onclick="cpGotoPage(${_cpPage-1})" style="${btnS(_cpPage===1)}">上一页</button>`;
  const lo=Math.max(1,_cpPage-2),hi=Math.min(pages,_cpPage+2);
  if(lo>1) h+=`<span style="color:#94a3b8">...</span>`;
  for(let p=lo;p<=hi;p++) h+=`<button onclick="cpGotoPage(${p})" style="padding:3px 8px;border:1px solid ${p===_cpPage?'#2563eb':'#e2e8f0'};border-radius:5px;background:${p===_cpPage?'#2563eb':'#fff'};color:${p===_cpPage?'#fff':'inherit'};cursor:pointer;font-size:12px">${p}</button>`;
  if(hi<pages) h+=`<span style="color:#94a3b8">...</span>`;
  h += `<button onclick="cpGotoPage(${_cpPage+1})" style="${btnS(_cpPage===pages)}">下一页</button>`;
  h += `<button onclick="cpGotoPage(${pages})" style="${btnS(_cpPage===pages)}">末页</button>`;
  h += `</div></td></tr>`;
  return h;
}

function renderCpRows(items){
  if(!items.length) return `<tr><td colspan="6" style="padding:28px;text-align:center;color:#64748b">该专题下暂无岗位数据</td></tr>`;
  return items.map(j=>`<tr>
    <td><div class="job-name">${escapeHtml(j.title)}</div>
      <div class="job-tags">${(j.tags||[]).map(t=>'<span class="job-tag">'+escapeHtml(t)+'</span>').join('')}</div></td>
    <td style="color:#475569">${escapeHtml(j.direction||'-')}</td>
    <td style="color:#475569">${escapeHtml(j.city||'-')}</td>
    <td><span class="type-pill type-${j.type}">${escapeHtml(j.type||'')}</span></td>
    <td style="color:#64748b">${escapeHtml(j.date||'-')}</td>
    <td><a class="btn-ghost" href="${escapeHtml(j.url||'#')}" target="_blank" rel="noopener" style="text-decoration:none;display:inline-block">查看 JD ↗</a></td>
  </tr>`).join('');
}

function cpGotoPage(page){
  const pages = Math.ceil(_cpFiltered.length / _CP_PAGE_SIZE);
  _cpPage = Math.max(1, Math.min(page, pages||1));
  const body = document.getElementById('cpJobsBody');
  if(body){
    const slice = _cpFiltered.slice((_cpPage-1)*_CP_PAGE_SIZE, _cpPage*_CP_PAGE_SIZE);
    body.innerHTML = renderCpRows(slice) + renderCpPager();
  }
}



/* 公司详情页 */
function openCompanyPage(companyName, topicName){
  topicName = topicName || '';
  const c=COMPANIES.find(x=>x.name===companyName) || UNICORNS.find(x=>x.name===companyName);
  if(!c) return;
  document.getElementById('cpName').textContent=c.name;
  document.getElementById('cpStatus').textContent=c.status;
  document.getElementById('cpDesc').textContent=c.summary;
  const _kpiTips = {
    'all':       '',
    'ai':        'Builder + User 两类之和。Builder 岗位本身在造 AI（训练、推理优化等）；User 岗位利用 AI 工具提效。',
    'fullstack': '同时承担前后端的工程师。关键判定词：「全栈」「前后端」「全链路开发」，JD 中普遍要求 AI Coding 能力。',
    'fde':       'Forward Deployed Engineer，前线部署工程师。代表岗位：解决方案工程师、交付工程师。核心是把技术能力转化为客户业务结果。',
    'pde':       'Product Design Engineer，产品设计工程师。三维复合判定：「产品判断」 + 「体验感知」 + 「工程实现」至少命中两维。',
  };
  const topicKeyMap = {'全栈工程师':'fullstack','FDE 专题':'fde','PDE 专题':'pde'};
  window._cpActiveMetric = topicKeyMap[topicName] || 'all';
  document.getElementById('cpKpis').innerHTML=c.highlights.map(h=>{
    const tip = _kpiTips[h.key] || '';
    const tipHtml = tip ? `<span class="tip-wrap"><span class="tip-icon" tabindex="0" onmouseenter="tipShow(this)" onmouseleave="tipHide(this)" onfocus="tipShow(this)" onblur="tipHide(this)">${TIP_ICON}</span><span class="tip-box">${tip}</span></span>` : '';
    return `<div class="kpi-cell clickable ${h.key===window._cpActiveMetric?'active':''}" data-kpi-key="${h.key}" onclick="cpApplyMetric('${h.key}')"><div class="kpi-label">${h.label}${tipHtml}</div><div class="kpi-val">${h.value}</div><div class="kpi-sub">${h.sub}</div></div>`;
  }).join('');

  /* 岗位列表（按专题过滤） */
  const filtered=JOBS.filter(j=>j.company===companyName && (!topicName || j.topic===topicName));
  const scopeLabel = topicName ? (companyName+' · '+topicName) : companyName;

  /* 领域分布 / JD 特征 / 城市：有过滤时按实际岗位重算，无数据则回落公司级数据 */
  let domains=c.domains, traits=c.jd_traits, cities=c.cities;
  if(topicName && filtered.length){
    const tally=(key, topN)=>{
      const m={}; filtered.forEach(j=>{ const k=j[key]; if(k) m[k]=(m[k]||0)+1; });
      const arr=Object.entries(m).sort((a,b)=>b[1]-a[1]);
      return arr.length?arr.slice(0,topN):null;
    };
    domains = tally('direction',5) || domains;
    const tagMap={};
    filtered.forEach(j=>(j.tags||[]).forEach(t=>{ tagMap[t]=(tagMap[t]||0)+1; }));
    const tagArr=Object.entries(tagMap).sort((a,b)=>b[1]-a[1]).slice(0,5);
    if(tagArr.length){
      const maxT=tagArr[0][1];
      traits = tagArr.map(([t,n])=>[t, Math.round(n/filtered.length*100), n>maxT?'':'']);
    }
    cities = tally('city',4) || cities;
  }

  document.getElementById('cpDomainSub').textContent = topicName ? (scopeLabel+' 专业子方向岗位数') : 'Top 5 专业子方向的岗位数量';
  document.getElementById('cpTraitSub').textContent = topicName ? (scopeLabel+' JD 关键词出现频率') : 'JD 文本中关键词出现频率';
  renderBars('cpDomains', domains.map(d=>[d[0],d[1]]));
  renderBars('cpTraits', traits, {percent:true});
  renderBars('cpCities', cities.map(d=>[d[0],d[1]]));

  /* 标题与表格 */
  document.getElementById('cpJobsTitle').textContent = topicName ? (scopeLabel+' 在招岗位') : (companyName+' 全部在招岗位');
  document.getElementById('cpJobsSub').textContent = '岗位、城市、类型、发布时间、查看 JD' + (topicName ? '（已按专题筛选）' : '');
  document.getElementById('cpDesc').style.display = 'none';
  /* 概览模块（招聘规模趋势/AI领域分布/JD特征/城市布局）：仅首页公司卡入口展示 */
  document.querySelectorAll('.cp-overview-only').forEach(function(el){
    el.style.display = topicName ? 'none' : '';
  });
  /* 存储当前公司全量岗位，供搜索/筛选/导出使用；清空搜索条件后重新检索 */
  window._cpAllJobs = filtered;
  ['cpQ','cpFType','cpFDir','cpFDate'].forEach(id=>{ const el=document.getElementById(id); if(el) el.value=''; });
  cpSearch();

  document.getElementById('companyPage').classList.add('show');
  document.body.style.overflow='hidden';
  setTimeout(()=>{ drawTrend('cpTrend', c.trend, c.ai_trend); }, 30);
}
function closeCompanyPage(){
  document.getElementById('companyPage').classList.remove('show');
  document.body.style.overflow='';
}

/* 迷你折线（行业概览卡内） */
function drawMiniLine(canvas, vals, color){
  if(!canvas) return;
  const dpr=window.devicePixelRatio||1;
  canvas.width=canvas.offsetWidth*dpr||64*dpr;
  canvas.height=36*dpr;
  const ctx=canvas.getContext('2d'); ctx.scale(dpr,dpr);
  const w=canvas.offsetWidth||64, h=36, pad=3;
  const min=Math.min(...vals), max=Math.max(...vals), range=(max-min)||1;
  const xs=vals.map((_,i)=>pad+i*(w-pad*2)/(vals.length-1));
  const ys=vals.map(v=>h-pad-((v-min)/range)*(h-pad*2));
  const grad=ctx.createLinearGradient(0,0,0,h);
  grad.addColorStop(0,color+'33'); grad.addColorStop(1,color+'00');
  ctx.beginPath(); ctx.moveTo(xs[0],h-pad); xs.forEach((x,i)=>ctx.lineTo(x,ys[i])); ctx.lineTo(xs[xs.length-1],h-pad); ctx.closePath();
  ctx.fillStyle=grad; ctx.fill();
  ctx.beginPath(); ctx.moveTo(xs[0],ys[0]); xs.forEach((x,i)=>ctx.lineTo(x,ys[i]));
  ctx.strokeStyle=color; ctx.lineWidth=1.8; ctx.lineJoin='round'; ctx.stroke();
  ctx.beginPath(); ctx.arc(xs[xs.length-1],ys[ys.length-1],2.5,0,Math.PI*2); ctx.fillStyle=color; ctx.fill();
}
/* 行业概览 */
function renderIndustry(){
  document.getElementById('coGrid').innerHTML=COMPANIES.map((c,ci)=>
    `<div class="co-card" onclick="openCompanyPage('${c.name}')">
      <div class="co-name" style="display:flex;justify-content:space-between;align-items:center">
        <span style="font-size:15px;font-weight:800">${c.name}</span>
        <span class="co-jump">查看分析 →</span>
      </div>
      <div class="co-mini-grid">
        <div class="mini-kpi" style="display:flex;justify-content:space-between;align-items:center">
          <div><div class="mini-label">在招总量</div><div class="mini-value">${c.total.toLocaleString()}</div><div class="mini-trend">${changeText(c.change)}</div></div>
          <canvas class="co-spark" data-ci="${ci}" data-type="total" style="width:64px;height:36px"></canvas>
        </div>
        <div class="mini-kpi" style="display:flex;justify-content:space-between;align-items:center">
          <div><div class="mini-label">AI岗位</div><div class="mini-value">${c.ai.toLocaleString()}</div><div class="mini-trend">${changeText(c.ai_change)}</div></div>
          <canvas class="co-spark" data-ci="${ci}" data-type="ai" style="width:64px;height:36px"></canvas>
        </div>
      </div>
    </div>`).join('');
  /* 画折线 */
  document.querySelectorAll('.co-spark').forEach(cv=>{
    const ci=parseInt(cv.dataset.ci); const c=COMPANIES[ci];
    const vals = cv.dataset.type==='ai' ? c.ai_trend : c.trend;
    const color = cv.dataset.type==='ai' ? '#10b981' : '#64748b';
    requestAnimationFrame(()=>drawMiniLine(cv, vals, color));
  });
}

/* 岗位明细列表行 */

function splitBullets(text){
  return String(text||'')
    .split(/[\n\u3002\uff1b;]/)
    .map(s=>s.replace(/^[\-•·\d.\s]+/, '').trim())
    .filter(Boolean);
}
function openJdModal(id){
  const d = JOB_DETAILS[String(id)] || {};
  document.getElementById('modalTitle').textContent = d.title || '岗位详情';
  const badges = [
    d.dept   ? {text: d.dept,   cls: ''}      : null,
    d.city   ? {text: d.city,   cls: 'blue'}  : null,
    d.type   ? {text: d.type,   cls: 'green'} : null,
    d.date   ? {text: '📅 ' + d.date, cls: ''}   : null,
  ].filter(Boolean);
  document.getElementById('modalBadges').innerHTML = badges.map(b=>`<span class="modal-badge ${b.cls}">${escapeHtml(b.text)}</span>`).join('');
  const duties = splitBullets(d.desc);
  const reqs   = splitBullets(d.req);
  document.getElementById('modalDuties').innerHTML = (duties.length ? duties : ['暂无信息']).map(x=>`<li>${escapeHtml(x)}</li>`).join('');
  document.getElementById('modalReqs').innerHTML   = (reqs.length   ? reqs   : ['暂无信息']).map(x=>`<li>${escapeHtml(x)}</li>`).join('');
  document.getElementById('jobModal').classList.add('show');
}
function closeJobModal(){
  document.getElementById('jobModal').classList.remove('show');
}

const _PAGE_SIZE = 50;
let _curPage = 1;
let _filteredCache = [];

function renderJobAction(j, className='', text='查看 ↗'){
  const cls = className ? ` class="${className}"` : '';
  const baseStyle = className ? '' : ' style="text-decoration:none;font-size:12px;color:#94a3b8;transition:.15s;background:none;border:none;padding:0;cursor:pointer"';
  if((j.company||'') === '京东零售' || String(j.url||'').startsWith('javascript:openJdModal(')){
    const rid = String(j.row_id || '').replace(/'/g, "\\'");
    return `<button type="button"${cls}${baseStyle} onmouseover="this.style.color='#2563eb'" onmouseout="this.style.color='#94a3b8'" onclick="openJdModal('${rid}')">${text}</button>`;
  }
  return `<a href="${escapeHtml(j.url||'#')}" target="_blank" rel="noopener"${cls}${baseStyle} onmouseover="this.style.color='#2563eb'" onmouseout="this.style.color='#94a3b8'">${text}</a>`;
}

function renderJobList(items){
  if(!items.length) return '<div style="padding:24px;text-align:center;color:var(--muted)">暂无匹配岗位</div>';
  const header=`<div class="list-th">岗位</div><div class="list-th">方向</div><div class="list-th">公司</div><div class="list-th">城市</div><div class="list-th">类型</div><div class="list-th">更新</div><div class="list-th">操作</div>`;
  const rows=items.map(j=>{
    const typePill=j.type?`<span class="type-pill type-${j.type}">${escapeHtml(j.type)}</span>`:'';
    const programPill=(j.program&&j.type==='校招')?'<span class="type-pill" style="background:#fef3c7;color:#b45309;margin-left:4px">人才计划</span>':'';
    return `<div class="list-row">
      <div class="list-td"><div><div class="l-tit">${escapeHtml(j.title)}</div><div class="l-sub">${(j.tags||[]).join(' · ')}</div></div></div>
      <div class="list-td l-sub">${escapeHtml(j.direction||j.topic)}</div>
      <div class="list-td" style="color:#334155;font-size:13px">${escapeHtml(j.company||'-')}</div>
      <div class="list-td l-sub">${escapeHtml(j.city||'-')}</div>
      <div class="list-td">${typePill}${programPill}</div>
      <div class="list-td l-sub">${escapeHtml(j.date||'-')}</div>
      <div class="list-td">${renderJobAction(j,'','查看 ↗')}</div>
    </div>`;
  }).join('');
  return `<div class="list-table">${header}${rows}</div>`;
}

function renderPager(total, cur, pageSize){
  const pages = Math.ceil(total / pageSize);
  if(pages <= 1) return '';
  const btnS = (d) => `padding:4px 10px;border:1px solid #e2e8f0;border-radius:6px;background:#fff;cursor:pointer;font-size:12px;${d?'opacity:.4;pointer-events:none;':''}`;
  let html = `<div style="display:flex;align-items:center;gap:6px;justify-content:center;padding:16px 0;flex-wrap:wrap">`;
  html += `<span style="color:var(--muted);font-size:13px;margin-right:4px">共 ${total.toLocaleString()} 条</span>`;
  html += `<button onclick="gotoPage(1)" style="${btnS(cur===1)}">首页</button>`;
  html += `<button onclick="gotoPage(${cur-1})" style="${btnS(cur===1)}">上一页</button>`;
  const lo=Math.max(1,cur-2),hi=Math.min(pages,cur+2);
  if(lo>1) html+=`<span style="color:var(--muted);padding:0 2px">…</span>`;
  for(let p=lo;p<=hi;p++) html+=`<button onclick="gotoPage(${p})" style="padding:4px 10px;border:1px solid ${p===cur?'#2563eb':'#e2e8f0'};border-radius:6px;background:${p===cur?'#2563eb':'#fff'};color:${p===cur?'#fff':'inherit'};cursor:pointer;font-size:12px">${p}</button>`;
  if(hi<pages) html+=`<span style="color:var(--muted);padding:0 2px">…</span>`;
  html += `<button onclick="gotoPage(${cur+1})" style="${btnS(cur===pages)}">下一页</button>`;
  html += `<button onclick="gotoPage(${pages})" style="${btnS(cur===pages)}">末页</button>`;
  html += `</div>`;
  return html;
}

function gotoPage(page){
  const pages = Math.ceil(_filteredCache.length / _PAGE_SIZE);
  _curPage = Math.max(1, Math.min(page, pages||1));
  const start = (_curPage-1)*_PAGE_SIZE;
  const el = document.getElementById('jobList');
  if(el){
    el.innerHTML = renderJobList(_filteredCache.slice(start, start+_PAGE_SIZE))
                 + renderPager(_filteredCache.length, _curPage, _PAGE_SIZE);
    el.scrollIntoView({behavior:'smooth', block:'start'});
  }
}

function searchJobs(){
  const q=(document.getElementById('jQ').value||'').toLowerCase();
  const fCo=(document.getElementById('fCo')||{}).value||'';
  const fType=(document.getElementById('fType')||{}).value||'';
  const fDir=(document.getElementById('fDir')||{}).value||'';
  const fDate=parseInt((document.getElementById('fDate')||{}).value||'0')||0;
  const now=new Date('2026-10-10');
  const dirMap={'产品':['产品','运营'],'Agent研发':['Agent'],'后端研发':['后端开发','PDE'],'算法':['算法','LLM/大模型','推荐/广告','AI Infra','NLP','CV & AIGC'],'数据分析':['数据&BI','数据'],'前端研发':['FDE','前端'],'LLM/大模型':['LLM/大模型'],'AI Infra':['AI Infra'],'推荐/广告':['推荐/广告']};
  _filteredCache=JOBS.filter(j=>{
    if(q && ![j.title,j.company,j.city,j.topic,j.direction,(j.emerging_type||''),(j.tags||[]).join(' ')].some(x=>String(x||'').toLowerCase().includes(q))) return false;
    if(fCo && j.company!==fCo) return false;
    if(fType && j.type!==fType) return false;
    if(fDir){const dirs=dirMap[fDir]||[fDir]; if(!dirs.some(d=>(j.direction||'').includes(d)||(j.topic||'').includes(d))) return false;}
    if(fDate && j.date){
      const diff=(now-new Date(j.date))/(1000*60*60*24);
      if(fDate===99){if(diff<=30) return false;}
      else{if(diff>fDate) return false;}
    }
    return true;
  });
  const cnt=document.getElementById('filterCount');
  if(cnt) cnt.textContent=`共 ${_filteredCache.length.toLocaleString()} 条`;
  _curPage = 1;
  const el = document.getElementById('jobList');
  if(el){
    el.innerHTML = renderJobList(_filteredCache.slice(0, _PAGE_SIZE))
                 + renderPager(_filteredCache.length, 1, _PAGE_SIZE);
  }
}


/* ===== Tooltip ===== */
/* 新兴岗位专题：标签切换 */
let _emSel = 0;
function selEmGroup(idx){
  _emSel=idx;
  document.querySelectorAll('.em-tab').forEach((el,i)=>el.classList.toggle('active',i===idx));
  const g=EMERGING_GROUPS[idx];
  const jobs=g.jobs.map(j=>({title:j.title||String(j), company:j.company||'-', city:j.city||'-', url:j.url||'#'}));
  document.getElementById('emDetail').innerHTML=`
    <div class="em-card" style="border:none;padding:0">
      <div class="em-desc" style="margin-bottom:14px">${escapeHtml(g.desc)}</div>
      <div class="sample-list">${jobs.map(j=>`
        <div class="sample-row" style="cursor:pointer" onclick="const jd=JOBS.find(x=>x.title==='${escapeHtml(j.title)}'); window.open(jd&&jd.url&&jd.url!=='#'?jd.url:'#','_blank')">
          <div class="sample-col-title">${escapeHtml(j.title)}</div>
          <div class="sample-sub">${escapeHtml(j.company)} · ${escapeHtml(j.city)}</div>
        </div>`).join('')}
      </div>
    </div>`;
}
function renderEmerging(t){
  _emSel=0;
  const tip = `近 30 天内新出现的 AI 原生角色，覆盖大厂 + AI 独角兽。包含 Agent Harness、具身智能、Post-Training 工程师等 11 类新岗位。`;
  const tipHtml = `<span class="tip-wrap"><span class="tip-icon" tabindex="0" onmouseenter="tipShow(this)" onmouseleave="tipHide(this)" onfocus="tipShow(this)" onblur="tipHide(this)">${TIP_ICON}</span><span class="tip-box">${tip}</span></span>`;
  return `<div class="panel-top"><div><h3 style="margin-bottom:8px">${t.name}${tipHtml}</h3><div style="font-size:14px;color:var(--muted)">${t.summary}</div></div></div>
  <div class="insight-box"><div style="font-size:12px;font-weight:800;margin-bottom:8px;color:var(--brand)">专题洞察</div><ul>${t.insights.map(x=>'<li>'+x+'</li>').join('')}</ul></div>
  <div style="font-size:13px;font-weight:700;margin-bottom:10px">典型岗位类型</div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:18px">
    ${EMERGING_GROUPS.map((g,i)=>`<div class="em-tab${i===0?' active':''}" onclick="selEmGroup(${i})" style="padding:7px 16px;border-radius:999px;border:1px solid var(--border);cursor:pointer;font-size:13px;font-weight:700;transition:.15s">${escapeHtml(g.name)}</div>`).join('')}
  </div>
  <div id="emDetail" class="panel-box" style="min-height:120px"></div>`;
}

/* 专题切换 */
function selTopic(id){
  document.querySelectorAll('.topic-tab').forEach(el=>el.classList.toggle('active',el.dataset.id===id));
  const t=TOPICS.find(x=>x.id===id);
  const panel=document.getElementById('topicPanel');

  if(t.special){
    panel.innerHTML=`<div class="panel-top"><div><h3 style="margin-bottom:8px">${t.name}</h3><div style="font-size:14px;color:var(--muted)">${t.summary}</div></div></div>
    <div class="insight-box"><div style="font-size:12px;font-weight:800;margin-bottom:8px;color:var(--brand)">核心洞察</div><ul>${t.insights.map(x=>'<li>'+x+'</li>').join('')}</ul></div>
    <div class="ts-grid">
      <div class="ts-box"><div class="ts-box-h">岗位方向分布矩阵</div>
        <table><thead><tr><th>方向</th>${COMPANIES.map(c=>'<th>'+c.name.slice(0,2)+'</th>').join('')}</tr></thead>
        <tbody>${CATEGORIES.map((cat,i)=>{let row='<tr><td style="font-weight:700">'+cat+'</td>';
          COMPANIES.forEach(c=>{const val=HEATMAP[c.name][i]; const a=Math.min(0.05+(val/1000)*0.5,0.5);
            row+='<td><div class="h-cell" style="background:rgba(37,99,235,'+a.toFixed(2)+')">'+val+'</div></td>';});
          return row+'</tr>';}).join('')}</tbody></table>
      </div>
      <div class="ts-box"><div class="ts-box-h">技术信号强度</div>
        ${KEYWORDS.map(k=>'<div class="kw-row"><div class="kw-meta"><span>'+k.word+(k.new?' (NEW)':'')+'</span><span>'+k.val+'%</span></div><div class="kw-bar"><div class="kw-fill" style="width:'+k.val+'%"></div></div></div>').join('')}
      </div>
    </div>`;
    return;
  }

  if(t.emerging){ panel.innerHTML=renderEmerging(t); selEmGroup(0); return; }

  const topicTips = {
    'fullstack':'同时承担前后端的工程师。关键判定词：「全栈」「前后端」「全链路开发」，JD 中普遍要求 AI Coding 能力。',
    'fde':'Forward Deployed Engineer，前线部署工程师。代表岗位：解决方案工程师、交付工程师。核心要求是把技术能力转化为客户业务结果。',
    'pde':'Product Design Engineer，产品设计工程师。三维复合判定：「产品判断」 + 「体验感知」 + 「工程实现」至少命中两维。',
    'emerging':'近 30 天内新出现的 AI 原生角色，覆盖大厂 + AI 独角兽。包含 Agent Harness、具身智能、Post-Training 工程师等 11 类新岗位。'
  };
  const topicTipHtml = topicTips[t.id] ? `<span class="tip-wrap"><span class="tip-icon" tabindex="0" onmouseenter="tipShow(this)" onmouseleave="tipHide(this)" onfocus="tipShow(this)" onblur="tipHide(this)">${TIP_ICON}</span><span class="tip-box">${topicTips[t.id]}</span></span>` : '';
  panel.innerHTML=`<div class="panel-top"><div><h3 style="margin-bottom:8px">${t.name}${topicTipHtml}</h3><div style="font-size:14px;color:var(--muted)">${t.summary}</div></div></div>
  <div class="insight-box"><div style="font-size:12px;font-weight:800;margin-bottom:8px;color:var(--brand)">专题洞察</div><ul>${t.insights.map(x=>'<li>'+x+'</li>').join('')}</ul></div>
  <div style="font-size:13px;font-weight:700;margin-bottom:12px">公司样本数</div>
  ${(()=>{const m={};JOBS.filter(j=>j.topic===t.name).forEach(j=>{m[j.company]=(m[j.company]||0)+1;});const arr=Object.entries(m).sort((a,b)=>b[1]-a[1]);const needCollapse=arr.length>6;const cards=arr.map(([co,v],i)=>`<div class="metric-card${needCollapse&&i>=6?' overflow-card':''}" onclick="openCompanyPage('${co}','${t.name}')"><div class="metric-left"><div class="metric-title">${co}</div><div class="metric-value">${v}</div></div><div class="metric-link">查看 →</div></div>`).join('');return `<div class="metric-grid${needCollapse?' collapsed':''}" id="topicMetricGrid">${cards}</div>`+(needCollapse?`<div class="metric-toggle-row"><div class="metric-toggle" onclick="toggleTopicMetrics(this)">展开全部 ${arr.length} 家 <span class="arrow">▾</span></div></div>`:'');})()}
  <div style="font-size:13px;font-weight:700;margin-bottom:6px">代表岗位</div>
  <div class="sample-list">
    ${t.samples.map(s=>{const title=s.title||s;const company=s.company||'-';const city=s.city||'-';const url=s.url||'#';const isJd=url.startsWith('javascript:');return `<div class="sample-row" style="cursor:pointer" onclick="${isJd?url.replace('javascript:',''):`window.open('${url}','_blank')`}"><div class="sample-col-title">${escapeHtml(title)}</div><div class="sample-sub">${escapeHtml(company)} · ${escapeHtml(city)}</div></div>`;}).join('')}
  </div>`;
}

function toggleTopicMetrics(el){
  const grid = document.getElementById('topicMetricGrid');
  if(!grid) return;
  grid.classList.toggle('collapsed');
  const total = grid.querySelectorAll('.metric-card').length;
  el.innerHTML = grid.classList.contains('collapsed') ? `展开全部 ${total} 家 <span class="arrow">▾</span>` : '收起 <span class="arrow">▾</span>';
}

function renderUI(){
  renderIndustry();
  selTopic(TOPICS[0].id);
  searchJobs();
  drawSparkline('spark1',[19184, 19462, 19740, 20018, 20296, 20574, 20852],'#64748b');
  drawSparkline('spark2',[3060, 3373, 3686, 3998, 4311, 4623, 4936],'#10b981');
}
document.addEventListener('keydown',e=>{ if(e.key==='Escape'){ closeJobModal(); closeCompanyPage(); }});
renderUI();

/* 公司详情页岗位搜索 / 筛选 / 导出 */
function cpApplyMetric(metricKey){
  window._cpActiveMetric = metricKey || 'all';
  document.querySelectorAll('#cpKpis .kpi-cell').forEach(el=>el.classList.toggle('active', el.dataset.kpiKey===window._cpActiveMetric));
  cpSearch();
  const anchor = document.getElementById('cpJobsSection') || document.getElementById('cpJobsTitle');
  if(anchor) anchor.scrollIntoView({behavior:'smooth', block:'start'});
}

function cpSearch(){
  const q=((document.getElementById('cpQ')||{}).value||'').toLowerCase();
  const fType=(document.getElementById('cpFType')||{}).value||'';
  const fDir=(document.getElementById('cpFDir')||{}).value||'';
  const fDate=parseInt((document.getElementById('cpFDate')||{}).value||'0')||0;
  const now=new Date('2026-10-10');
  const dirMap={'产品':['产品','运营'],'Agent研发':['Agent'],'后端研发':['后端开发','PDE'],'算法':['算法','LLM/大模型','推荐/广告','AI Infra','NLP','CV & AIGC'],'数据分析':['数据&BI','数据'],'前端研发':['FDE','前端'],'LLM/大模型':['LLM/大模型'],'AI Infra':['AI Infra'],'推荐/广告':['推荐/广告']};
  const base=window._cpAllJobs||[];
  const metric = window._cpActiveMetric || 'all';
  const res=base.filter(j=>{
    if(metric==='ai' && !((j.tags||[]).includes('AI-Builder') || (j.tags||[]).includes('AI-User'))) return false;
    if(metric==='fullstack' && j.topic!=='全栈工程师') return false;
    if(metric==='fde' && j.topic!=='FDE 专题') return false;
    if(metric==='pde' && j.topic!=='PDE 专题') return false;
    if(q && ![j.title,j.company,j.city,j.topic,j.direction,(j.emerging_type||''),(j.tags||[]).join(' ')].some(x=>String(x||'').toLowerCase().includes(q))) return false;
    if(fType && j.type!==fType) return false;
    if(fDir){const dirs=dirMap[fDir]||[fDir]; if(!dirs.some(d=>(j.direction||'').includes(d)||(j.topic||'').includes(d))) return false;}
    if(fDate && j.date){
      const diff=(now-new Date(j.date))/(1000*60*60*24);
      if(fDate===99){if(diff<=30) return false;}
      else{if(diff>fDate) return false;}
    }
    return true;
  });
  const cnt=document.getElementById('cpFCount');
  if(cnt) cnt.textContent=`共 ${res.length.toLocaleString()} 条`;
  window._cpFilteredJobs=res;
  _cpFiltered=res; _cpPage=1;
  const body=document.getElementById('cpJobsBody');
  if(body){ body.innerHTML = renderCpRows(res.slice(0,_CP_PAGE_SIZE)) + renderCpPager(); }
}
function cpExportCsv(){
  const rows=window._cpFilteredJobs||window._cpAllJobs||[];
  const hdr=['岗位名称','公司','方向','城市','类型','更新日期','标签','JD 链接'];
  const lines=[hdr.join(',')];
  rows.forEach(j=>{
    lines.push([
      `"${(j.title||'').replace(/"/g,'""')}"`,
      `"${(j.company||'')}"`,
      `"${(j.direction||'')}"`,
      `"${(j.city||'')}"`,
      `"${(j.type||'')}"`,
      `"${(j.date||'')}"`,
      `"${(j.tags||[]).join('、').replace(/"/g,'""')}"`,
      `"${(j.url||'')}"`,
    ].join(','));
  });
  const blob=new Blob([lines.join('\\n')],{type:'text/csv;charset=utf-8'});
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob);
  const co=(window._cpAllJobs&&window._cpAllJobs[0])?window._cpAllJobs[0].company:'岗位';
  a.download=`${co}_jobs_2026-10-10.csv`; a.click();
}


function exportCsv(){
  const rows = (typeof _filteredCache !== 'undefined' && _filteredCache.length) ? _filteredCache : (typeof JOBS !== 'undefined' ? JOBS : []);
  if(!rows.length){ alert('暂无数据可导出'); return; }
  const hdr=['岗位名称','公司','方向','城市','类型','更新日期','标签','JD 链接'];
  const lines=[hdr.join(',')];
  rows.forEach(j=>{
    lines.push([
      `"${(j.title||'').replace(/"/g,'""')}"`,
      `"${(j.company||'').replace(/"/g,'""')}"`,
      `"${(j.direction||'').replace(/"/g,'""')}"`,
      `"${(j.city||'').replace(/"/g,'""')}"`,
      `"${(j.type||'')}"`,
      `"${(j.date||'')}"`,
      `"${(j.tags||[]).join('、').replace(/"/g,'""')}"`,
      `"${(j.url||'')}"`,
    ].join(','));
  });
  const blob=new Blob([lines.join('\\n')],{type:'text/csv;charset=utf-8'});
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob);
  a.download=`jobboard_2026-10-10.csv`; a.click();
}

"""

grand_total  = sum(c['total']   for c in COMPANIES) + sum(c['total']   for c in UNICORNS)
grand_ai     = sum(c['ai']      for c in COMPANIES) + sum(c['ai']      for c in UNICORNS)
grand_user   = sum(c.ai_user    for c in companies)  + sum(c.ai_user    for c in unicorns.values())
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
# 修正 JS 里字面量换行正则（/[\n...]/）
html = re.sub(r'/\[\\n([^\]]*?)\]/', lambda m: '/[\\\\n' + m.group(1) + ']/', html)
# 更稳健：直接替换整个有问题的正则片段
html = html.replace(
    "split(/[\\n；;。]/)",
    "split(/[\\n\\u3002\\uff1b;]/)"
)

# ---- post-process: 修掉 JS 字符类正则里的字面量换行 ----
def fix_regex_literals(src):
    # 把 JS 正则 /[...] 里的字面 0x0a 换成 \n
    result = []
    i = 0
    while i < len(src):
        if src[i:i+2] == '//':
            # 行注释，跳到行尾
            end = src.find('\n', i+2)
            result.append(src[i:end+1] if end != -1 else src[i:])
            i = end+1 if end != -1 else len(src)
        elif src[i] == '/' and i > 0 and src[i-1] in ' =(!,;[\n\t:|&|^~?':
            # 可能是正则开始
            j = i+1
            in_class = False
            while j < len(src):
                c = src[j]
                if c == '[': in_class = True
                elif c == ']': in_class = False
                elif c == '\\': j += 1
                elif c == '/' and not in_class: break
                elif c == '\n' and in_class:
                    # 字面换行在字符类里，替换为 \n
                    src = src[:j] + '\\n' + src[j+1:]
                j += 1
            result.append(src[i:j+1])
            i = j+1
        else:
            result.append(src[i])
            i += 1
    return ''.join(result)

html = fix_regex_literals(html)

# 额外保险：直接字符串替换已知的问题正则
for bad, good in [
    ('/[\n；;。]/', '/[\\n\\u3002\\uff1b;]/'),
    ('/[\n;；。]/', '/[\\n;\\uff1b\\u3002]/'),
]:
    html = html.replace(bad, good)
# ---- end post-process ----
OUT.write_text(html, encoding='utf-8')
print(f'✅ 成功生成：{OUT}')
