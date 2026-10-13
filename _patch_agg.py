import re
from pathlib import Path

p = Path('/Users/qujingyi/.openclaw/workspace/jobboard-demo/pipeline/aggregator.py')
src = p.read_text(encoding='utf-8')

# 1) aggregate 增加 override_map 参数
src = src.replace("def aggregate(raw):", "def aggregate(raw, override_map=None):")
src = src.replace(
    "from .labeler import classify_job, get_direction, EM_RULES, EM_DESCS, CATEGORIES",
    "from .labeler import classify_job, get_direction, EM_RULES, EM_DESCS, CATEGORIES\nfrom .overrides import apply_overrides, _job_key",
)

# 2) 找到从 "# 先得到最终展示给前端的去重 jobs" 到 "topics = [" 之前的内容，替换为 override 后反算的版本
start_marker = "    # 先得到最终展示给前端的去重 jobs"
end_marker = "    em_map = {}"
i = src.index(start_marker)
j = src.index(end_marker)

new_block = '''    # ① 先得到最终展示给前端的去重 jobs（唯一展示口径）
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

'''
src = src[:i] + new_block + src[j:]

# 4) 去掉旧的重复 heatmap/kw_counts 定义（原 em_map 之前那段已删），检查是否残留
p.write_text(src, encoding='utf-8')
print('aggregator patched:', len(src), 'bytes')
