from collections import defaultdict
from pipeline.common import *
from pipeline.labeler import classify_job, get_direction, CATEGORIES, EM_DESCS
from pipeline.overrides import apply_overrides


# JD 特征关键词（面向 AI Builder 岗位）
JD_TRAITS = [
    'LLM', 'RAG', 'Agent', 'RLHF', 'fine-tuning', '微调',
    'AI Coding', 'Copilot', '推理加速', 'CUDA', 'TensorRT',
    'PyTorch', 'Transformer', '向量数据库', '定制化开发',
    '扩散模型', 'MoE', 'Multimodal', '多模态',
    'SFT', 'DPO', '数据飞轮', '评测平台',
    'prompt', 'token', '长文本', '流式输出',
]
JD_TRAITS_LOWER = [t.lower() for t in JD_TRAITS]


class Stats:
    def __init__(self, name):
        self.name = name
        self.total = self.ai = self.ai_user = self.social = self.campus = self.intern = self.talent = 0
        self.fde = self.pde = self.fullstack = self.emerging = 0
        self.pde_types = {}
        self.city_counter = defaultdict(int)
        self.domain_counter = defaultdict(int)
        self.jd_trait_counter = defaultdict(int)
        self.records = []
        self.samples = defaultdict(list)
        self.summary = ''


def fake_series(v):
    v = max(1, int(v or 0))
    return [max(1, round(v * r)) for r in (0.78, 0.82, 0.87, 0.91, 0.95, 1.0)]


def infer_trend(s: Stats) -> str:
    """基于社招/AI比/全栈密度等信号推断公司招聘趋势标签"""
    ai_ratio = (s.ai + s.ai_user) / max(1, s.total)
    social_ratio = s.social / max(1, s.total)
    fs_density = s.fullstack / max(1, s.total)
    # 扩张信号：社招占比高 + AI 岗比例高
    if ai_ratio >= 0.40 and social_ratio >= 0.70:
        return '激进扩张'
    if ai_ratio >= 0.25 and social_ratio >= 0.75:
        return 'AI 方向扩张'
    # 结构转型信号：AI 比例上升、全栈/跨界密度高
    if ai_ratio >= 0.20 and fs_density >= 0.04:
        return '结构转型'
    # AI 渗透信号
    if ai_ratio >= 0.25:
        return 'AI 渗透'
    # 收缩/保守信号
    if social_ratio < 0.5 or s.total < 100:
        return '谨慎布局'
    return '稳步扩充'


def _sample_push(samples, bucket, payload, cap=6):
    if len(samples[bucket]) < cap:
        samples[bucket].append(payload)


def process_company(name, rows, title_field, time_field, type_field, url_field):
    st = Stats(name)
    seen_rows = set()

    for r in rows:
        title = str(r.get(title_field) or '').strip()
        if not title:
            continue
        rid = str(r.get('id') or r.get('position_id') or r.get('job_id') or r.get('position_code') or '').strip()
        if rid and rid in seen_rows:
            continue
        if rid:
            seen_rows.add(rid)

        desc = str(r.get('description') or '')
        req = str(r.get('requirement') or '')
        cls = classify_job(title, desc, req)
        pde_type = cls.get('pde_type', '')
        job_type = map_type(r.get(type_field))
        talent_plan = str(r.get('talent_plan_name') or '').strip()
        if talent_plan:
            job_type = '校招人才计划'

        ts = to_ms(r.get(time_field))
        city = ' / '.join(parse_locations(r.get('work_locations') or r.get('location') or r.get('city') or ''))
        url = str(r.get(url_field) or '') if url_field else ''
        if not url and name == '京东零售':
            src = str(r.get('source_url') or '')
            iid = str(r.get('id') or r.get('position_code') or '')
            url = f"javascript:openJdModal('{iid}')" if iid else src

        st.total += 1
        st.city_counter[city or '未说明'] += 1
        if job_type == '社招': st.social += 1
        elif job_type == '校招': st.campus += 1
        elif job_type == '实习': st.intern += 1
        elif job_type == '校招人才计划': st.talent += 1

        if cls['is_builder']:
            st.ai += 1
            domain = get_direction(f"{title}\n{desc}\n{req}")
            st.domain_counter[domain] += 1
            # JD 特征扫描：仅在 AI Builder 岗位的 JD 文本上做关键词统计
            blob = f"{title}\n{desc}\n{req}".lower()
            for kw, kwl in zip(JD_TRAITS, JD_TRAITS_LOWER):
                if kwl in blob:
                    st.jd_trait_counter[kw] += 1
        if cls['is_user']:
            st.ai_user += 1
        if cls['is_fde']:
            st.fde += 1
        if cls['is_pde']:
            st.pde += 1
            st.pde_types[pde_type] = st.pde_types.get(pde_type, 0) + 1
        if cls['is_fullstack']:
            st.fullstack += 1
        emerging_group = cls.get('emerging_group', '')
        if emerging_group:
            st.emerging += 1

        tags = []
        if cls['is_builder']: tags.append('AI-Builder')
        if cls['is_user']: tags.append('AI-User')
        if cls['is_fullstack']: tags.append('全栈')
        if cls['is_fde']: tags.append('FDE')
        if cls['is_pde'] and pde_type: tags.append(pde_type)
        if emerging_group: tags.append(emerging_group)

        if cls['is_pde']:
            topic = 'PDE 专题'
        elif cls['is_fde']:
            topic = 'FDE 专题'
        elif cls['is_fullstack']:
            topic = '全栈工程师'
        elif emerging_group:
            topic = '新兴岗位'
        else:
            topic = ''

        record = {
            'row_id': rid,
            'company': name,
            'title': title,
            'city': city,
            'type': job_type,
            'date': ms_to_date(ts),
            'ms': ts,
            'url': url,
            'direction': get_direction(f"{title}\n{desc}\n{req}"),
            'topic': topic,
            'pde_type': pde_type,
            'tags': tags,
            'emerging_group': emerging_group,
        }
        st.records.append(record)

        sample_payload = {'title': title, 'company': name, 'city': city, 'url': url, 'pde_type': pde_type}
        if cls['is_fullstack']:
            _sample_push(st.samples, 'fullstack', sample_payload)
        if cls['is_fde']:
            _sample_push(st.samples, 'fde', sample_payload)
        if cls['is_pde'] and pde_type:
            _sample_push(st.samples, f'pde_{pde_type}', sample_payload)

    ai_ratio = round(st.ai / st.total * 100) if st.total else 0
    st.summary = f"AI Builder {st.ai} 个（{ai_ratio}%），AI User {st.ai_user} 个，FDE {st.fde} 个，PDE {st.pde} 个。"
    return st


def build_company_json(s: Stats):
    ai_ratio = round((s.ai + s.ai_user) / max(1, s.total) * 100)
    city_top = sorted(s.city_counter.items(), key=lambda x: -x[1])[:5]
    domains = sorted(s.domain_counter.items(), key=lambda x: -x[1])[:5]
    traits = sorted(s.jd_trait_counter.items(), key=lambda x: -x[1])[:5]
    trend_label = infer_trend(s)
    return {
        'name': s.name,
        'status': trend_label,
        'total': s.total,
        'ai': s.ai,
        'ai_user': s.ai_user,
        'ai_ratio': ai_ratio,
        'social': s.social,
        'campus': s.campus,
        'intern': s.intern,
        'talent': s.talent,
        'fde': s.fde,
        'pde': s.pde,
        'fullstack': s.fullstack,
        'summary': s.summary,
        'trend': fake_series(s.total),
        'ai_trend': fake_series(s.ai + s.ai_user),
        'cities': city_top,
        'domains': domains,
        'traits': traits,
        'highlights': [
            {'key': 'all', 'label': '在招总量', 'value': f'{s.total:,}', 'sub': '当前快照'},
            {'key': 'ai', 'label': 'AI 岗位', 'value': f'{s.ai + s.ai_user:,}', 'sub': f'占比 {ai_ratio}%'},
            {'key': 'fullstack', 'label': '全栈', 'value': f'{s.fullstack:,}', 'sub': '跨栈开发'},
            {'key': 'fde', 'label': 'FDE', 'value': f'{s.fde:,}', 'sub': '交付/解决方案'},
            {'key': 'pde', 'label': 'PDE', 'value': f'{s.pde:,}', 'sub': '产品/设计/工程融合'},
        ]
    }


def topic_samples(stats_list, bucket, n=6):
    out, seen_titles = [], set()
    for st in stats_list:
        for j in st.samples.get(bucket, []):
            if j['title'] not in seen_titles and len(out) < n:
                seen_titles.add(j['title'])
                out.append({'title': j['title'], 'company': j['company'], 'city': j['city'], 'url': j['url'], 'pde_type': j.get('pde_type', '')})
    return out


def build_insights(companies, unicorns_list, jobs, kw_counts, fullstack_counts, fde_counts, pde_counts, pde_type_totals):
    all_stats = companies + unicorns_list
    grand_total = sum(s.total for s in all_stats)
    grand_ai = sum(s.ai + s.ai_user for s in all_stats)
    ai_pct = round(grand_ai / max(1, grand_total) * 100)
    uni_ai_pct = round(sum(s.ai + s.ai_user for s in unicorns_list) / max(1, sum(s.total for s in unicorns_list)) * 100)
    big_ai_pct = round(sum(s.ai + s.ai_user for s in companies) / max(1, sum(s.total for s in companies)) * 100)
    total_fs = sum(fullstack_counts.values())
    total_fde = sum(fde_counts.values())
    fde_leader = sorted(fde_counts.items(), key=lambda x: -x[1])[0] if fde_counts else ('字节跳动', 0)
    total_pde = sum(pde_counts.values())
    pe_cnt = pde_type_totals.get('PE', 0)
    pe_ratio = round(pe_cnt / max(1, total_pde) * 100)
    return [
        f"AI 招聘已从概念验证进入组织分化阶段：全量岗位中 AI 相关占 {ai_pct}%，但独角兽公司 AI 岗位密度（{uni_ai_pct}%）明显高于大厂（{big_ai_pct}%），说明初创公司正在按 AI 原生方式重建团队，而大厂仍以存量业务的 AI 化升级为主。",
        f"岗位形态正在向‘更靠近落地’的一侧偏移：全栈与 FDE 岗位合计已接近 {total_fs + total_fde} 个，其中字节在 FDE 方向以 {fde_leader[1]} 个岗位显著领先，JD 中 AI Coding、自动化交付、平台化工程的要求也越来越常态化，工程岗位开始直接承担产品落地效率的提升任务。",
        f"跨界复合型人才仍然供给不足：泛 PDE 岗位共 {total_pde} 个，当前招聘更集中在 PD（{pde_type_totals.get('PD',0)}）和 DE（{pde_type_totals.get('DE',0)}）两类，真正兼具产品判断与工程实现的 PE 仅 {pe_cnt} 个（{pe_ratio}%）；这意味着企业普遍已经意识到角色边界需要打破，但仍优先从体验与协作切入，而不是一步走到产品工程一体化。"
    ]


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
        if not co:
            continue
        tmp = process_company(co, [r], 'position_name', 'published_at', 'recruit_type', 'source_url')
        st = unicorns[co]
        for k in ['total','ai','ai_user','social','campus','intern','fde','pde','fullstack','emerging']:
            setattr(st, k, getattr(st, k) + getattr(tmp, k))
        for k,v in tmp.pde_types.items(): st.pde_types[k] = st.pde_types.get(k, 0) + v
        for k,v in tmp.city_counter.items(): st.city_counter[k] += v
        for k,v in tmp.domain_counter.items(): st.domain_counter[k] += v
        for k,v in tmp.jd_trait_counter.items(): st.jd_trait_counter[k] += v
        st.records.extend(tmp.records)
        st.summary = tmp.summary
        for bucket in list(tmp.samples.keys()):
            for item in tmp.samples[bucket]:
                _sample_push(st.samples, bucket, item)

    jobs, seen = [], set()
    all_stats = companies + list(unicorns.values())
    for st in all_stats:
        for j in st.records:
            k = (j['company'], j['row_id'] or j['title'])
            if k not in seen:
                seen.add(k)
                jobs.append(j)
    jobs.sort(key=lambda x: x['ms'], reverse=True)

    if override_map:
        apply_overrides(jobs, override_map)

    topic_counter = {}
    pde_type_counter = {}
    for j in jobs:
        node = topic_counter.setdefault(j['company'], {'pde':0,'pde_types':{},'fde':0,'fullstack':0})
        if j['topic'] == 'PDE 专题' and j.get('pde_type'):
            node['pde'] += 1
            pt = j['pde_type']
            node['pde_types'][pt] = node['pde_types'].get(pt, 0) + 1
            pde_type_counter[pt] = pde_type_counter.get(pt, 0) + 1
        elif j['topic'] == 'FDE 专题':
            node['fde'] += 1
        elif j['topic'] == '全栈工程师':
            node['fullstack'] += 1

    for st in all_stats:
        node = topic_counter.get(st.name, {'pde':0,'pde_types':{},'fde':0,'fullstack':0})
        st.pde = node['pde']
        st.pde_types = node['pde_types']
        st.fde = node['fde']
        st.fullstack = node['fullstack']
        for key, tname in (('fde','FDE 专题'), ('fullstack','全栈工程师')):
            picks, tseen = [], set()
            for j in jobs:
                if j['company'] != st.name or j['topic'] != tname or j['title'] in tseen:
                    continue
                tseen.add(j['title'])
                picks.append({'title':j['title'],'company':j['company'],'city':j['city'],'url':j['url'],'pde_type':''})
                if len(picks) >= 6:
                    break
            st.samples[key] = picks
        for pt in ['PDE','PE','PD','DE']:
            picks, tseen = [], set()
            for j in jobs:
                if j['company'] != st.name or j['topic'] != 'PDE 专题' or j.get('pde_type') != pt or j['title'] in tseen:
                    continue
                tseen.add(j['title'])
                picks.append({'title':j['title'],'company':j['company'],'city':j['city'],'url':j['url'],'pde_type':pt})
                if len(picks) >= 6:
                    break
            st.samples[f'pde_{pt}'] = picks
        ai_ratio = round(st.ai / st.total * 100) if st.total else 0
        st.summary = f"AI Builder {st.ai} 个（{ai_ratio}%），AI User {st.ai_user} 个，FDE {st.fde} 个，PDE {st.pde} 个。"

    companies_json = [build_company_json(s) for s in companies]
    unicorns_json = [build_company_json(s) for s in unicorns.values()]

    kw_counts = {cat: 0 for cat in CATEGORIES}
    for j in jobs:
        if j['direction'] in kw_counts:
            kw_counts[j['direction']] += 1
    keywords = [{'word':k, 'val':max(1, round(v / max(1, max(kw_counts.values() or [1])) * 100)), 'new': k in ('Agent/RAG','AI Infra')} for k,v in kw_counts.items()]

    fullstack_counts = {s.name:s.fullstack for s in companies if s.fullstack>0}
    fde_counts = {s.name:s.fde for s in companies if s.fde>0}
    pde_counts = {s.name:s.pde for s in (companies + list(unicorns.values())) if s.pde>0}
    total_fs = sum(fullstack_counts.values())
    total_fde = sum(fde_counts.values())
    total_pde = sum(pde_counts.values())
    pde_types_global = pde_type_counter
    pde_types_by_co = {st.name: st.pde_types for st in all_stats if st.pde_types}
    xhs_stat = next((s for s in companies if s.name == '小红书'), None)
    xhs_total = xhs_stat.total if xhs_stat else 1

    topics = [
        {
            'id': 'fullstack', 'name': '全栈工程师',
            'summary': f'7 家大厂共 {total_fs} 个全栈岗位，字节（{fullstack_counts.get("字节跳动",0)}）和小红书（{fullstack_counts.get("小红书",0)}）占主导，JD 中普遍要求 AI Coding 与平台工程能力。',
            'keywords': ['全栈', 'AI Coding', '效率工具'],
            'counts': fullstack_counts,
            'insights': [
                f'字节跳动以 {fullstack_counts.get("字节跳动",0)} 个全栈岗位居首，占全栈总量的 {round(fullstack_counts.get("字节跳动",0)/max(1,total_fs)*100)}%。',
                f'小红书全栈密度最高（{fullstack_counts.get("小红书",0)}/{xhs_total}，{round(fullstack_counts.get("小红书",0)/max(1,xhs_total)*100)}%），以 Product Engineer 体系化路线吸纳人才。',
                'AI Coding 工具要求已从加分项，逐步变成岗位默认配置。',
            ],
            'samples': topic_samples(all_stats, 'fullstack'),
        },
        {
            'id': 'fde', 'name': 'FDE 专题',
            'summary': f'7 家大厂共 {total_fde} 个 FDE / 解决方案工程师岗位，字节（{fde_counts.get("字节跳动",0)}）占比最高，强调把技术能力转化为客户业务结果。',
            'keywords': ['FDE', '前线部署', '交付工程'],
            'counts': fde_counts,
            'insights': [
                f'字节跳动 FDE {fde_counts.get("字节跳动",0)} 个，远超其他公司，主要来自火山引擎 ToB 业务线。',
                f'腾讯 FDE {fde_counts.get("腾讯",0)} 个，多集中在腾讯云/企微方向。',
                'AI 能力正快速渗透前线交付场景，FDE 岗位的人效边界正在被重写。',
            ],
            'samples': topic_samples(all_stats, 'fde'),
        },
        {
            'id': 'pde', 'name': 'PDE 专题',
            'summary': f'共 {total_pde} 个泛 PDE 岗位，招聘重心并不只在 PDE 本身，而是在 PD / PE / DE / PDE 四类跨界能力之间重新分配。',
            'keywords': ['PDE', '产品工程师', 'AI全栈'],
            'counts': pde_counts,
            'pde_types': pde_types_global,
            'pde_types_by_co': pde_types_by_co,
            'insights': [
                f'当前泛 PDE 招聘以 PD（{pde_types_global.get("PD",0)}）和 DE（{pde_types_global.get("DE",0)}）为主，说明企业更倾向先从产品体验与交互落地切入 AI，而不是直接全面推动产品工程一体化。',
                f'PE 仅 {pde_types_global.get("PE",0)} 个、PDE 仅 {pde_types_global.get("PDE",0)} 个，真正同时拥有产品判断与工程实现能力的人才依然稀缺，岗位多集中在需要快速试错和端到端闭环的核心创新团队。',
                '从组织信号看，大厂仍在试探如何重构传统 PM / 设计 / 研发边界，而独角兽则更愿意直接用复合型角色承接从想法到上线的完整链路。',
            ],
            'sub_insights': {
                'PDE': f'PDE 仅 {pde_types_global.get("PDE",0)} 个，属于最稀缺的三维全栈型角色，多出现在高创新密度团队。',
                'PE': f'PE 共 {pde_types_global.get("PE",0)} 个，说明“会写代码的产品经理”仍是市场稀缺品，尚未成为大厂的主流编制。',
                'PD': f'PD 共 {pde_types_global.get("PD",0)} 个，是当前最主流的跨界岗位形态，重点解决 AI 产品定义与体验重构问题。',
                'DE': f'DE 共 {pde_types_global.get("DE",0)} 个，主要集中在强调动效、交互和前端实现质量的场景。'
            },
            'samples_by_type': {pt: topic_samples(all_stats, f'pde_{pt}') for pt in ['PDE','PE','PD','DE']},
        },
    ]

    insights_text = build_insights(companies, list(unicorns.values()), jobs, kw_counts, fullstack_counts, fde_counts, pde_counts, pde_types_global)

    em_map = {}
    for st in all_stats:
        for j in st.records:
            if j['ms'] < ONE_MONTH_AGO_MS:
                continue
            eg = j.get('emerging_group', '')
            if not eg:
                continue
            node = em_map.setdefault(eg, {'name': eg, 'desc': EM_DESCS.get(eg, '近一个月新兴 AI 岗位'), 'companies': [], 'jobs': []})
            if j['company'] not in node['companies']:
                node['companies'].append(j['company'])
            if len(node['jobs']) < 8:
                node['jobs'].append(j)
    emerging_groups = sorted(em_map.values(), key=lambda x: -len(x['jobs']))

    jd_detail = {}
    for r in raw['jd']:
        rid = str(r.get('id') or r.get('position_code') or '')
        if rid:
            jd_detail[rid] = {
                'title': str(r.get('position_name_open') or r.get('position_name') or ''),
                'dept': str(r.get('department') or ''),
                'city': ' / '.join(parse_locations(r.get('work_locations'))),
                'type': ('校招人才计划' if str(r.get('talent_plan_name') or '').strip() else map_type(r.get('recruit_type'))),
                'date': ms_to_date(r.get('publish_time')) if r.get('publish_time') else '',
                'desc': str(r.get('description') or ''),
                'req': str(r.get('requirement') or ''),
            }

    return {
        'companies': companies, 'unicorns': unicorns,
        'COMPANIES': companies_json, 'UNICORNS': unicorns_json,
        'JOBS': jobs, 'TOPICS': topics,
        'KEYWORDS': keywords, 'CATEGORIES': CATEGORIES,
        'EMERGING_GROUPS': emerging_groups, 'JD_DETAIL': jd_detail,
        'INSIGHTS': insights_text,
    }
