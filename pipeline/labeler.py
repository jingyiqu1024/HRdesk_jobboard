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
    r'AI架构|模型能力规划',
]
USER_PATS = [
    r'使用AI工具|AI辅助|AI提效|AI赋能|Copilot|AI写文案|AI分析|生成代码',
    r'智能客服|AI运营|AIGC运营|智能营销|AI写JD|AI辅助招聘',
    r'调用API做业务功能|消费AI能力|接入AI能力|对接大模型接口',
]

# FDE：Forward Deployed Engineer，前线部署工程师
# "业务架构师" 移除 —— 字节内部的业务架构师是 IT/内部系统岗，不是 ToB FDE
FDE_PATS = [
    r'FDE(?![A-Za-z])|Forward\s*Deployed|前线部署',
    r'解决方案工程师|解决方案架构师|交付工程师',
    r'深入客户业务现场|技术能力转化为业务结果|经验反哺|驻场交付',
]
# FDE 仅在 title 中生效的弱信号
FDE_TITLE_ONLY_PATS = [
    r'方案落地',
]

# 全栈：优先级全栈 > PDE > FDE
FS_TITLE_PATS = [
    r'全栈|Full[\s_-]?Stack|前后端|跨栈',
    r'AI全栈|端到端开发|全链路开发|AI Native.*Full',
    r'同时负责前端和后端|客户端与服务端|前后端一体化',
]
FS_BODY_PATS = [
    # desc/req 里只认「全栈开发/全栈工程师/全栈产品/AI全栈开发」等明确工程语境
    # 避免部门介绍模板「负责字节跳动的全栈算力基础设施」误触发
    r'全栈(?:开发|工程师|产品|研发)|AI全栈(?:开发|工程师)?|Full[\s_-]?Stack\s*(?:Dev|Engineer|开发)',
    r'端到端开发|全链路开发|前后端一体化|同时负责前端和后端|客户端与服务端',
]

def fs_score_calc(title, desc, req):
    """全栈得分：title 按原权重；desc/req 只认明确工程语境。"""
    score = 0.0
    for pat in FS_TITLE_PATS:
        if re.search(pat, title, re.I): score += 2.0
    for pat in FS_BODY_PATS:
        if re.search(pat, desc, re.I): score += 1.5
        if re.search(pat, req, re.I):  score += 1.0
    return score

PDE_A = [r'需求洞察|概念构思|产品规划|产品定义']
PDE_B = [r'体验感知|交互设计|原型验证|设计语言|\bUI\b|\bUX\b|\bUI/UX\b']
PDE_C = [r'代码实现|工程实现|全链路交付|独立负责.*上线|端到端交付|写代码']

# PDE 四类组合标签
# P=产品思维 D=设计感知 E=工程实现
# 只展示双维及以上：PD / PE / DE / PDE
_PDE_TYPE_MAP = {
    (True,  True,  True):  'PDE',
    (True,  True,  False): 'PD',
    (True,  False, True):  'PE',
    (False, True,  True):  'DE',
}  # 单维命中不展示，返回 ''

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

# ── 非产研岗位黑名单 ──────────────────────────────────────────────
# 产研 = 产品（含产品经理/PM）、研发、测试、设计、算法。
# 以下类型一律排除出所有专题/AI标注（title 命中即排除）。
# 注意：产品经理/PM 绝对不排除。
_NON_PROD_TECH_PAT = re.compile(
    # 人力/行政/培训
    r'HR(?!\s*BP技术|产品|系统)|人力资源|招聘(?!系统|平台|工具|算法|Agent)|猎头|HRBP|人事(?!系统)|培训师|员工关系|薪酬|绩效专员|管培生|轮岗'
    # 销售/BD/商务/渠道
    r'|销售(?!策略算法|预测算法|系统|平台)|商务(?:拓展|开发|合作)|渠道(?:经理|专员|销售)|大客户(?:经理|总监)|客户成功(?:经理)?|KA(?:经理|专员)'
    # 市场/品牌/PR
    r'|市场(?:营销|专员|经理|总监|推广)|品牌(?:经理|专员)|公关|媒介(?:投放|规划)|投放优化师'
    # 运营（排除纯非技术运营）
    r'|(?:品类|内容|社区|活动|直播|商家|达人|账号)运营'
    r'|运营(?:专员|助理|实习生)'
    # 财务/法务/合规/风控
    r'|财务(?:分析师|经理|专员|总监|BP)|法务(?:专员|经理|顾问)|合规(?:专员|经理)|风控(?:专员|经理)(?!模型|算法|系统)'
    # 采购/供应链/物流
    r'|采购(?:经理|专员|总监)|供应链(?:经理|专员)(?!系统|平台|算法)|物流(?:规划|专员)|仓储(?:管理|专员)'
    # 客服/售后
    r'|客服(?:专员|经理|主管)|售后(?:服务|专员)(?!工程师)'
    # 芯片/硬件（不算软件产研）
    r'|芯片(?:研发|验证|设计|工程)|固件(?:验证|开发|工程)|FPGA|RTL|EDA|IC设计'
    r'|硬件(?:工程师|研发|设计)(?!.*软件)'
    # 行政/后勤
    r'|行政(?:专员|经理|助理)|安保|后勤|保洁|司机',
    re.I
)

_CHIP_DEPT_PAT = re.compile(r'芯片研发|固件|存算与AI|VLSI|硬件平台', re.I)

def is_non_prod_tech(title):
    if _NON_PROD_TECH_PAT.search(title): return True
    if _CHIP_DEPT_PAT.search(title): return True
    return False

def classify_job(title, desc, req):
    title = title or ""
    desc  = desc  or ""
    req   = req   or ""
    full  = f"{title}\n{desc}\n{req}"

    if is_non_prod_tech(title):
        return {'is_builder': False, 'is_user': False,
                'is_pde': False, 'is_fde': False, 'is_fullstack': False}

    b_score = weighted_score(BUILDER_PATS, title, desc, req)
    u_score = weighted_score(USER_PATS, title, desc, req)

    # FDE score
    fde_score = weighted_score(FDE_PATS, title, desc, req)
    for pat in FDE_TITLE_ONLY_PATS:
        if re.search(pat, title, re.I): fde_score += 2.0

    # 全栈 score
    fs_s = fs_score_calc(title, desc, req)

    if re.search(r'AI产品经理|模型产品经理|AIGC产品经理', title, re.I):
        if re.search(r'模型能力规划|模型演进|模型效果|模型路线图|训练策略', full, re.I):
            b_score += 3
        else:
            u_score += 3
    if re.search(r'提示词工程师|Prompt\s*Engineer', title, re.I): b_score += 3
    if re.search(r'前端|后端|客户端|服务端|开发工程师', title, re.I) \
       and re.search(r'调用API|对接大模型接口|消费AI能力', full, re.I) \
       and not re.search(r'训练|微调|推理优化|框架|底层|编译器|算力', full, re.I):
        u_score += 2
    if re.search(r'运营|销售|人事|行政|客服|市场', title, re.I) \
       and not re.search(r'数据标注|模型测评|AI合规', title, re.I):
        b_score = min(b_score, 0)
        if re.search(r'AI', full, re.I): u_score += 1

    # PDE 三维
    pde_dims = 0
    if weighted_score(PDE_A, title, desc, req) >= 1: pde_dims += 1
    if weighted_score(PDE_B, title, desc, req) >= 1: pde_dims += 1
    if weighted_score(PDE_C, title, desc, req) >= 1: pde_dims += 1

    _pde_exclude = bool(re.search(
        r'(?:Compliance|Security|Legal|Risk|QA|Quality)\s+Product\s+Engineer'
        r'|芯片产品工程师|产品工程师.*芯片|芯片.*产品工程'
        r'|算法工程师|评测算法|数据工程师|网络传输工程师|通信网络|车云通信'
        r'|(?:Agent\s+)?Infra\s+工程师',
        title, re.I
    ))
    # PDE 四类判定：基于三维是否命中，输出组合标签
    # 直接命中规则已删除，完全依赖维度组合
    _hit_a = weighted_score(PDE_A, title, desc, req) >= 1
    _hit_b = weighted_score(PDE_B, title, desc, req) >= 1
    _hit_c = weighted_score(PDE_C, title, desc, req) >= 1
    _pde_type = '' if _pde_exclude else _PDE_TYPE_MAP.get((_hit_a, _hit_b, _hit_c), '')
    is_pde = _pde_type != ''

    is_builder   = b_score >= 1.5
    is_user      = u_score >= 1.5 and not is_builder
    is_fde       = fde_score >= 1.5 and not re.search(
        r'销售经理|销售总监|销售代表|渠道销售', title, re.I)
    is_fullstack = fs_s >= 1.5

    return {'is_builder': is_builder, 'is_user': is_user,
            'is_pde': is_pde, 'pde_type': _pde_type,
            'is_fde': is_fde, 'is_fullstack': is_fullstack}

def get_direction(text):
    for name, pat in DIRECTION_RULES:
        if pat.search(text): return name
    return '其他AI'
