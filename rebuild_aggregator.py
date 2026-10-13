import re
from pathlib import Path

path = Path('/Users/qujingyi/.openclaw/workspace/jobboard-demo/v3/pipeline/aggregator.py')
src = path.read_text(encoding='utf-8')

# 提取 Stats 类定义
stats_class = """class Stats:
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
"""

# 重新编写 process_company 函数，确保逻辑顺序正确，变量先定义再使用
process_company_code = """def process_company(name, rows, title_f, time_f, type_f=None, url_f=None):
    st = Stats(name)
    seen = set()
    for r in rows:
        title = str(r.get(title_f) or '').strip()
        if not title: continue
        desc = str(r.get('description') or '')
        req = str(r.get('requirement') or '')
        full = f"{title}\\n{desc}\\n{req}"
        cls = classify_job(title, desc, req)
        
        # 1. 基础信息解析
        ms = to_ms(r.get(time_f))
        cities = parse_locations(r.get('work_locations'))
        typ = map_type(r.get(type_f)) if type_f else '社招'
        direction = get_direction(full) if cls['is_builder'] else '其他'
        
        # 2. 专题判定 (优先级: PDE > FDE > 全栈)
        topic = '方向热度与技术栈'
        if cls['is_pde']:         topic = 'PDE 专题'
        elif cls['is_fde']:       topic = 'FDE 专题'
        elif cls['is_fullstack']: topic = '全栈工程师'
        
        # 3. 统计计数 (仅在去重前计数，或者按你的需求在去重前计数)
        st.total += 1
        if cls['is_builder']: st.ai += 1
        if cls['is_user']: st.ai_user += 1
        if typ == '社招': st.social += 1
        elif typ == '校招': st.campus += 1
        else: st.intern += 1
        
        for c in cities: st.city_counter[c] = st.city_counter.get(c, 0) + 1
        if cls['is_builder']: st.domain_counter[direction] = st.domain_counter.get(direction, 0) + 1
        
        # 统计亮点指标 (互斥)
        if topic == 'PDE 专题':    st.pde += 1
        elif topic == 'FDE 专题':  st.fde += 1
        elif topic == '全栈工程师': st.fullstack += 1
        
        # JD 标签统计 (非互斥，用于详情页卡片)
        if direction != '其他': st.jd_trait_counter[direction] = st.jd_trait_counter.get(direction, 0) + 1
        if cls['is_fde']: st.jd_trait_counter['FDE'] = st.jd_trait_counter.get('FDE', 0) + 1
        if cls['is_pde']: st.jd_trait_counter['PDE'] = st.jd_trait_counter.get('PDE', 0) + 1
        if cls['is_fullstack']: st.jd_trait_counter['全栈'] = st.jd_trait_counter.get('全栈', 0) + 1

        # 4. 新兴岗位判定
        emerging_group = ''
        for g, pat in EM_RULES:
            if pat.search(title):
                emerging_group = g
                break
        if emerging_group and ms >= EMERGING_CUTOFF_MS:
            st.emerging += 1
            
        # 5. 构造 Job 对象
        tags = []
        if cls['is_builder']: tags.append('AI-Builder')
        if cls['is_user']: tags.append('AI-User')
        if cls['is_pde']: tags.append('PDE')
        if cls['is_fde']: tags.append('FDE')
        if cls['is_fullstack']: tags.append('全栈')
        if direction != '其他': tags.append(direction)
        tags = tags[:5]
        
        row_id = str(r.get('id') or r.get('position_code') or '')
        job = {
            'title': title, 'company': name, 'direction': direction, 'city': cities[0] if cities else '-',
            'type': typ, 'date': ms_to_date(ms), 'ms': ms, 'tags': tags,
            'program': '人才计划' if r.get('talent_plan_name') else '',
            'url': str(r.get(url_f) or '#') if url_f else f"javascript:openJdModal('{row_id}')",
            'topic': topic, 'row_id': row_id, 'emerging_group': emerging_group,
        }
        
        # 6. 加入列表并去重采样
        st.records.append(job)
        if title not in seen:
            seen.add(title)
            if topic == '全栈工程师' and len(st.samples['fullstack']) < 3: st.samples['fullstack'].append(job)
            if topic == 'FDE 专题' and len(st.samples['fde']) < 3: st.samples['fde'].append(job)
            if topic == 'PDE 专题' and len(st.samples['pde']) < 3: st.samples['pde'].append(job)
            if emerging_group and len(st.samples['emerging']) < 6: st.samples['emerging'].append(job)
            
    ai_ratio = round(st.ai / st.total * 100) if st.total else 0
    st.summary = f"AI Builder {st.ai} 个（{ai_ratio}%），AI User {st.ai_user} 个，FDE {st.fde} 个，PDE {st.pde} 个。"
    return st
"""

# 使用正则替换整个 Stats 类和 process_company 函数，直到 build_company_json 之前
new_src = re.sub(r'class Stats:.*?def build_company_json', 
                 stats_class + "\n" + process_company_code + "\n" + "def build_company_json", 
                 src, flags=re.DOTALL)

path.write_text(new_src, encoding='utf-8')
print("Successfully reconstructed aggregator.py")
