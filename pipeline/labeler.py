import re

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
        if re.search(r'模型能力规划|模型演进|模型效果|模型路线图|训练策略', full, re.I): b_score += 3
        else: u_score += 3
    if re.search(r'提示词工程师|Prompt\s*Engineer|业务架构师', title, re.I): b_score += 3
    if re.search(r'前端|后端|客户端|服务端|开发工程师', title, re.I) and re.search(r'调用API|对接大模型接口|消费AI能力', full, re.I) and not re.search(r'训练|微调|推理优化|框架|底层|编译器|算力', full, re.I): u_score += 2
    if re.search(r'运营|销售|人事|行政|客服|市场', title, re.I) and not re.search(r'数据标注|模型测评|AI合规', title, re.I):
        b_score = min(b_score, 0)
        if re.search(r'AI', full, re.I): u_score += 1
    pde_dims = 0
    if weighted_score(PDE_A, title, desc, req) >= 1: pde_dims += 1
    if weighted_score(PDE_B, title, desc, req) >= 1: pde_dims += 1
    if weighted_score(PDE_C, title, desc, req) >= 1: pde_dims += 1
    # PDE：三维得分 或 标题直接命中
    # Product Engineer / 产品工程师 本身就是 PDE 特征岗，直接认定
    # PDE 排除前缀（合规/安全/法务/芯片类 Product Engineer 不算 PDE）
    _pde_exclude = bool(re.search(
        r'(?:Compliance|Security|Legal|Risk|QA|Quality)\s+Product\s+Engineer'
        r'|芯片产品工程师'  # 芯片硬件 PM，不是软件 PDE
        r'|产品工程师.*芯片|芯片.*产品工程',
        title, re.I
    ))
    is_pde = (
        not _pde_exclude
        and (
            pde_dims >= 2
            or bool(re.search(
                r'PDE(?![A-Za-z])|产品设计工程师|Product\s*Design\s*Engineer'
                r'|Product\s*Engineer'
                r'|产品工程师'
                r'|KimiCode.*产品|Kimi.*产品实习生',
                title, re.I
            ))
        )
    )
    is_builder = b_score >= 1.5
    is_user = u_score >= 1.5 and not is_builder
    is_fde = fde_score >= 1.5 and not re.search(r'销售经理|销售总监|销售代表|渠道销售', title, re.I)
    # 全栈：有全栈特征，但排除两类干扰：
    # 1. AI算力基础设施部门的非工程岗（运营/采购/商务/规划/结算）
    # 2. 已经是 PDE 的岗位（避免双标）
    _ai_infra_dept = bool(re.search(r'AI算力基础设施|算力基础设施', title, re.I))
    _non_eng_infra = bool(re.search(
        r'运营管理|商务拓展|结算专员|采购经理|资源规划|经营运营|经营分析|战略运营',
        title, re.I
    ))
    is_fullstack = fs_score >= 1.5 and not (_ai_infra_dept and _non_eng_infra)
    return {'is_builder': is_builder,'is_user': is_user,'is_pde': is_pde,'is_fde': is_fde,'is_fullstack': is_fullstack}

def get_direction(text):
    for name, pat in DIRECTION_RULES:
        if pat.search(text): return name
    return '其他AI'
