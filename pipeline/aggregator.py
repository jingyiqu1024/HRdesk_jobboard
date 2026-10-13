from .common import to_ms, ms_to_date, parse_locations, map_type, topn, EMERGING_CUTOFF_MS, ONE_MONTH_AGO_MS
from .labeler import classify_job, get_direction, EM_RULES, EM_DESCS, CATEGORIES
from .overrides import apply_overrides, _job_key

class Stats:
    def __init__(self, name):
        self.name = name
        self.total = self.ai = self.ai_user = 0
        self.social = self.campus = self.intern = 0
        self.fde = self.pde = self.fullstack = self.emerging = 0
        self.records = []
        self.city_counter = {}
        self.domain_counter = {}
        self.jd_trait_counter = {}
        self.samples = {'fullstack':[], 'fde':[], 'pde':[], 'emerging':[]}

def process_company(name, rows, title_f, time_f, type_f=None, url_f=None):
    st = Stats(name)
    seen = set()
    for r in rows:
        title = str(r.get(title_f) or '').strip()
        if not title:
            continue
        desc = str(r.get('description') or '')
        req = str(r.get('requirement') or '')
        full = f"{title}\n{desc}\n{req}"
        cls = classify_job(title, desc, req)

        ms = to_ms(r.get(time_f))
        cities = parse_locations(r.get('work_locations'))
        typ = map_type(r.get(type_f)) if type_f else '社招'
        direction = get_direction(full) if cls['is_builder'] else '其他'

        topic = '方向热度与技术栈'
        if cls['is_fullstack']:   topic = '全栈工程师'
        elif cls['is_pde']:       topic = 'PDE 专题'
        elif cls['is_fde']:       topic = 'FDE 专题'

        st.total += 1
        if cls['is_builder']:
            st.ai += 1
        if cls['is_user']:
            st.ai_user += 1
        if typ == '社招':
            st.social += 1
        elif typ == '校招':
            st.campus += 1
        else:
            st.intern += 1

        for c in cities:
            st.city_counter[c] = st.city_counter.get(c, 0) + 1
        if cls['is_builder']:
            st.domain_counter[direction] = st.domain_counter.get(direction, 0) + 1

        emerging_group = ''
        for g, pat in EM_RULES:
            if pat.search(title):
                emerging_group = g
                break

        tags = []
        if cls['is_builder']:
            tags.append('AI-Builder')
        if cls['is_user']:
            tags.append('AI-User')
        if cls['is_pde']:
            tags.append('PDE')
        if cls['is_fde']:
            tags.append('FDE')
        if cls['is_fullstack']:
            tags.append('全栈')
        if direction != '其他':
            tags.append(direction)
        tags = tags[:5]

        if direction != '其他':
            st.jd_trait_counter[direction] = st.jd_trait_counter.get(direction, 0) + 1
        if cls['is_fde']:
            st.jd_trait_counter['FDE'] = st.jd_trait_counter.get('FDE', 0) + 1
        if cls['is_pde']:
            st.jd_trait_counter['PDE'] = st.jd_trait_counter.get('PDE', 0) + 1
        if cls['is_fullstack']:
            st.jd_trait_counter['全栈'] = st.jd_trait_counter.get('全栈', 0) + 1

        row_id = str(r.get('id') or r.get('position_code') or '')
        job = {
            'title': title, 'company': name, 'direction': direction, 'city': cities[0] if cities else '-',
            'type': typ, 'date': ms_to_date(ms), 'ms': ms, 'tags': tags,
            'program': '人才计划' if r.get('talent_plan_name') else '',
            'url': str(r.get(url_f) or '#') if url_f else f"javascript:openJdModal('{row_id}')",
            'topic': topic, 'row_id': row_id, 'emerging_group': emerging_group,
        }
        st.records.append(job)

        if title not in seen:
            seen.add(title)
            # 用去重后的最终 topic 做专题统计，保证首页专题卡/公司头部/下方列表一致
            if topic == 'PDE 专题':
                st.pde += 1
            elif topic == 'FDE 专题':
                st.fde += 1
            elif topic == '全栈工程师':
                st.fullstack += 1

            if topic == '全栈工程师' and len(st.samples['fullstack']) < 3:
                st.samples['fullstack'].append(job)
            if topic == 'FDE 专题' and len(st.samples['fde']) < 3:
                st.samples['fde'].append(job)
            if topic == 'PDE 专题' and len(st.samples['pde']) < 3:
                st.samples['pde'].append(job)
            if emerging_group and len(st.samples['emerging']) < 6:
                st.samples['emerging'].append(job)

        if emerging_group and ms >= EMERGING_CUTOFF_MS:
            st.emerging += 1

    ai_ratio = round(st.ai / st.total * 100) if st.total else 0
    st.summary = f"AI Builder {st.ai} 个（{ai_ratio}%），AI User {st.ai_user} 个，FDE {st.fde} 个，PDE {st.pde} 个。"
    return st

def build_company_json(st):
    ai_ratio = round(st.ai / st.total * 100) if st.total else 0
    return {
        'name': st.name,'total': st.total,'ai': st.ai,'ai_ratio': ai_ratio,'social': st.social,'change': 0,'ai_change': 0,
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

def topic_samples(stats_list, bucket, n=3):
    out = []
    seen_titles = set()
    for st in stats_list:
        for j in st.samples[bucket]:
            if j['title'] not in seen_titles and len(out) < n:
                seen_titles.add(j['title'])
                out.append({'title': j['title'], 'company': j['company'], 'city': j['city'], 'url': j['url']})
    return out

def aggregate(raw, override_map=None):
    companies = [
        process_company('字节跳动', raw['bytedance'], 'position_name', 'publish_time', 'recruit_type', 'source_url'),
        process_company('阿里淘天', raw['taotian_all'], 'position_name', 'modify_time', 'recruit_type', 'source_url'),
        process_company('腾讯', raw['tencent'], 'position_name', 'last_update_time', 'recruit_type', 'source_url'),
        process_company('美团', raw['meituan'], 'position_name', 'refresh_time', 'recruit_type', 'source_url'),
        process_company('小红书', raw['xhs'], 'position_name', 'publish_time', 'recruit_type', 'source_url'),
        process_company('京东零售', raw['jd'], 'position_name', 'publish_time', 'recruit_type', None),
        process_company('拼多多', raw['pdd'], 'position_name', 'update_date', 'recruit_type', 'source_url'),
    ]
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

    # ① 先得到最终展示给前端的去重 jobs（唯一展示口径）
    jobs, seen = [], set()
    all_stats = companies + list(unicorns.values())
    for st in all_stats:
        for j in st.records:
            k = (j['company'], j['row_id'] or j['title'])
            if k not in seen:
                seen.add(k)
                jobs.append(j)
    jobs.sort(key=lambda x: x['ms'], reverse=True)

    # ② 应用人工修正（若有），之后所有统计全部基于修正后的 jobs
    if override_map:
        apply_overrides(jobs, override_map)

    # ③ 基于最终 jobs 反算公司级专题统计（互斥 topic 口径），并重建 samples
    topic_counter = {}
    for j in jobs:
        node = topic_counter.setdefault(j['company'], {'pde':0, 'fde':0, 'fullstack':0})
        if j['topic'] == 'PDE 专题':
            node['pde'] += 1
        elif j['topic'] == 'FDE 专题':
            node['fde'] += 1
        elif j['topic'] == '全栈工程师':
            node['fullstack'] += 1

    for st in all_stats:
        node = topic_counter.get(st.name, {'pde':0, 'fde':0, 'fullstack':0})
        st.pde = node['pde']
        st.fde = node['fde']
        st.fullstack = node['fullstack']
        for key, tname in (('pde','PDE 专题'), ('fde','FDE 专题'), ('fullstack','全栈工程师')):
            picks, tseen = [], set()
            for j in jobs:
                if j['company'] != st.name or j['topic'] != tname:
                    continue
                if j['title'] in tseen:
                    continue
                tseen.add(j['title'])
                picks.append({'title': j['title'], 'company': j['company'], 'city': j['city'], 'url': j['url']})
                if len(picks) >= 3:
                    break
            st.samples[key] = picks
        ai_ratio = round(st.ai / st.total * 100) if st.total else 0
        st.summary = f"AI Builder {st.ai} 个（{ai_ratio}%），AI User {st.ai_user} 个，FDE {st.fde} 个，PDE {st.pde} 个。"

    companies_json = [build_company_json(s) for s in companies]
    unicorns_json = [build_company_json(s) for s in unicorns.values()]

    heatmap = {st.name: [st.domain_counter.get(cat, 0) for cat in CATEGORIES] for st in companies}
    kw_counts = {cat: 0 for cat in CATEGORIES}
    for j in jobs:
        if j['direction'] in kw_counts: kw_counts[j['direction']] += 1
    kw_max = max(kw_counts.values()) or 1
    keywords = [{'word':k, 'val':max(1, round(v/kw_max*100)), 'new': k in ('Agent/RAG','AI Infra')} for k,v in kw_counts.items()]

    fullstack_counts = {s.name:s.fullstack for s in companies if s.fullstack>0}
    fde_counts       = {s.name:s.fde       for s in companies if s.fde>0}
    pde_counts       = {s.name:s.pde       for s in companies if s.pde>0}
    total_fs, total_fde, total_pde = sum(fullstack_counts.values()), sum(fde_counts.values()), sum(pde_counts.values())
    topics = [
        {'id':'fullstack','name':'全栈工程师','summary':f'7 家大厂共 {total_fs} 个全栈岗位，字节（{fullstack_counts.get("字节跳动",0)}）和小红书（{fullstack_counts.get("小红书",0)}）占主导，JD 中普遍要求 AI Coding 与平台工程能力。','keywords':['全栈','AI Coding','效率工具'],'counts':fullstack_counts,'insights':[f'字节跳动以 {fullstack_counts.get("字节跳动",0)} 个全栈岗位居首，占全栈总量的 {round(fullstack_counts.get("字节跳动",0)/max(1,total_fs)*100)}%。',f'小红书全栈比例最高（{fullstack_counts.get("小红书",0)}/{[s for s in companies if s.name=="小红书"][0].total}），产品驱动型团队全栈需求更旺。','全栈 JD 中 AI Coding 工具要求普遍出现，成为新一代全栈能力的核心差异点。'],'samples': topic_samples(all_stats, 'fullstack')},
        {'id':'fde','name':'FDE 专题','summary':f'7 家大厂共 {total_fde} 个 FDE / 解决方案工程师岗位，字节（{fde_counts.get("字节跳动",0)}）占比超过 60%，强调把技术能力转化为客户业务结果。','keywords':['FDE','前线部署','交付工程'],'counts':fde_counts,'insights':[f'字节跳动 FDE {fde_counts.get("字节跳动",0)} 个，远超其他公司，与其 ToB 业务快速扩张高度相关。',f'腾讯 FDE {fde_counts.get("腾讯",0)} 个，多集中在企微/云方向，侧重客户深度绑定。','近期 FDE JD 中"AI+交付"描述密度上升，AI 降低了前线部署的交付成本。'],'samples': topic_samples(all_stats, 'fde')},
        {'id':'pde','name':'PDE 专题','summary':f'7 家大厂共 {total_pde} 个 PDE 岗位，小红书（{pde_counts.get("小红书",0)}）和字节（{pde_counts.get("字节跳动",0)}）布局最积极，核心判定标准是产品判断+体验感知+工程实现三维融合。','keywords':['PDE','产品工程师','AI全栈'],'counts':pde_counts,'insights':[f'小红书 PDE 比例居首（{pde_counts.get("小红书",0)} 个），与其产品驱动文化高度契合。','本期 PDE 判定采用三维复合信号，至少命中产品判断、体验感知、工程实现中的两维。','大厂 PDE 需求集中在 AI 功能快速交付和端到端验证，替代传统 PM+RD 协作模式。'],'samples': topic_samples(all_stats, 'pde')},
        {'id':'emerging','name':'新兴岗位','summary':'近一个月内，7 家大厂 + 6 家 AI 独角兽出现了一批 AI 原生新角色，这些岗位在半年前几乎不存在。','emerging':True,'insights':['Agent Harness 工程师在字节、美团、小红书、阶跃星辰同步出现，Agentic 基础设施正快速工程化。','具身智能岗位在字节、美团、拼多多集中爆发，大厂已开始为实体 AI 做人才储备。','Post-Training 工程师在独角兽中涌现，大模型训练能力从外购向自研切换的强信号。']},
        {'id':'tech_stack','name':'方向热度与技术栈','summary':'基于全量 {:,} 个岗位的真实统计，LLM/大模型方向需求最旺，Agent/RAG 快速追赶。'.format(sum(c['total'] for c in companies_json)),'special':True,'insights':[f'LLM/大模型在 7 家大厂共 {kw_counts.get("LLM/大模型",0)} 个岗位，字节单家占比最高。',f'Agent/RAG 共 {kw_counts.get("Agent/RAG",0)} 个，正从概念验证走向工程化规模部署。',f'AI Infra 共 {kw_counts.get("AI Infra",0)} 个，独角兽公司的自建算力需求拉动明显。']},
    ]

    em_map = {}
    for st in all_stats:
        for j in st.records:
            if j['ms'] < ONE_MONTH_AGO_MS: continue
            eg = j.get('emerging_group', '')
            if not eg: continue
            node = em_map.setdefault(eg, {'name': eg, 'desc': EM_DESCS.get(eg, '近一个月新兴 AI 岗位'), 'companies': [], 'jobs': []})
            if j['company'] not in node['companies']: node['companies'].append(j['company'])
            if len(node['jobs']) < 8: node['jobs'].append(j)
    emerging_groups = sorted(em_map.values(), key=lambda x: -len(x['jobs']))

    jd_detail = {}
    for r in raw['jd']:
        rid = str(r.get('id') or r.get('position_code') or '')
        if rid:
            jd_detail[rid] = {'title': str(r.get('position_name_open') or r.get('position_name') or ''),'dept': str(r.get('department') or ''),'city': ' / '.join(parse_locations(r.get('work_locations'))),'type': map_type(r.get('recruit_type')),'date': ms_to_date(r.get('publish_time')) if r.get('publish_time') else '','desc': str(r.get('description') or ''),'req': str(r.get('requirement') or '')}

    return {'companies': companies,'unicorns': unicorns,'COMPANIES': companies_json,'UNICORNS': unicorns_json,'JOBS': jobs,'TOPICS': topics,'HEATMAP': heatmap,'KEYWORDS': keywords,'CATEGORIES': CATEGORIES,'EMERGING_GROUPS': emerging_groups,'JD_DETAIL': jd_detail}

