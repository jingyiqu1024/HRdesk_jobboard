const _CP_PAGE_SIZE = 50;

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
    <td style="color:#475569">${escapeHtml(j.city||'-')}</td>
    <td><span class="type-pill type-${j.type}">${escapeHtml(j.type||'')}</span></td>
    <td style="color:#475569">${escapeHtml(j.direction||'-')}</td>
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
    'ai':        'Builder + User 两类之和。Builder 负责 AI 能力建设，如训练、优化、Agent/Infra；User 负责在业务中接入和使用 AI。',
    'fullstack': '同时承担前后端的工程师。关键判定词：「全栈」「前后端」「全链路开发」，JD 中普遍要求 AI Coding 能力。',
    'fde':       'Forward Deployed Engineer，前线部署工程师。代表岗位：解决方案工程师、交付工程师。核心是把技术能力转化为客户业务结果。',
    'pde':       'Product Engineer，产品工程师。兼具产品判断、交互设计与工程实现能力，能独立完成一个功能从定义到上线的全流程。',
  };
  const topicKeyMap = {'全栈工程师':'fullstack','FDE 专题':'fde','PDE 专题':'pde'};
  window._cpActiveMetric = topicKeyMap[topicName] || 'all';
  document.getElementById('cpKpis').innerHTML=c.highlights.map(h=>{
    const tip = _kpiTips[h.key] || '';
    const tipHtml = tip ? `<span class="tip-wrap"><span class="tip-icon" tabindex="0" onmouseenter="tipShow(this)" onmouseleave="tipHide(this)" onfocus="tipShow(this)" onblur="tipHide(this)">${TIP_ICON}</span><span class="tip-box">${tip}</span></span>` : '';
    return `<div class="kpi-cell clickable ${h.key===window._cpActiveMetric?'active':''}" data-kpi-key="${h.key}" onclick="cpApplyMetric('${h.key}')"><div class="kpi-label">${h.label}${tipHtml}</div><div class="kpi-val">${h.value}</div><div class="kpi-sub">${h.sub}</div></div>`;
  }).join('');

  /* 岗位列表：保存公司全量岗位；如果是从专题卡点进来，只作为默认激活的 metric，不预先截断数据 */
  const companyJobs = JOBS.filter(j=>j.company===companyName);
  const filtered = topicName ? companyJobs.filter(j=>j.topic===topicName) : companyJobs;
  const scopeLabel = topicName ? (companyName+' · '+topicName) : companyName;

  /* 领域分布 / JD 特征 / 城市：从专题卡进入时，概览仍按当前专题预览；切换 KPI 后由 cpSearch 控制列表 */
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
  /* 存储当前公司全量岗位，供搜索/筛选/导出使用；topicName 只决定默认激活哪个 KPI，不提前截断基表 */
  window._cpAllJobs = companyJobs;
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
  const header=`<div class="list-th">岗位</div><div class="list-th">公司</div><div class="list-th">城市</div><div class="list-th">类型</div><div class="list-th">方向</div><div class="list-th">更新</div><div class="list-th">操作</div>`;
  const rows=items.map(j=>{
    const typePill=j.type?`<span class="type-pill type-${j.type}">${escapeHtml(j.type)}</span>`:'';
    const programPill=(j.program&&j.type==='校招')?'<span class="type-pill" style="background:#fef3c7;color:#b45309;margin-left:4px">人才计划</span>':'';
    return `<div class="list-row">
      <div class="list-td"><div><div class="l-tit">${escapeHtml(j.title)}</div><div class="l-sub">${(j.tags||[]).join(' · ')}</div></div></div>
      <div class="list-td" style="color:#334155;font-size:13px">${escapeHtml(j.company||'-')}</div>
      <div class="list-td l-sub">${escapeHtml(j.city||'-')}</div>
      <div class="list-td">${typePill}${programPill}</div>
      <div class="list-td l-sub">${escapeHtml(j.direction||j.topic)}</div>
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
  const tip = `近 30 天内，平台侧、模型侧与应用侧出现了更细分的 AI 原生分工，反映行业正在从「是否做 AI」转向「如何把 AI 工程化、规模化、业务化」。`;
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
    'pde':'Product Engineer，产品工程师。兼具产品判断、交互设计与工程实现能力，能独立完成一个功能从定义到上线的全流程。',
    'emerging':'近 30 天内，平台侧、模型侧与应用侧出现了更细分的 AI 原生分工，反映行业正在从「是否做 AI」转向「如何把 AI 工程化、规模化、业务化」。新兴岗位集中在工程化、评测、安全与应用落地等环节，组织分工持续加深。'
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
  const hdr=['岗位名称','公司','城市','类型','方向','更新日期','标签','JD 链接'];
  const lines=[hdr.join(',')];
  rows.forEach(j=>{
    lines.push([
      `"${(j.title||'').replace(/"/g,'""')}"`,
      `"${(j.company||'')}"`,
      `"${(j.city||'')}"`,
      `"${(j.type||'')}"`,
      `"${(j.direction||'')}"`,
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
  const hdr=['岗位名称','公司','城市','类型','方向','更新日期','标签','JD 链接'];
  const lines=[hdr.join(',')];
  rows.forEach(j=>{
    lines.push([
      `"${(j.title||'').replace(/"/g,'""')}"`,
      `"${(j.company||'').replace(/"/g,'""')}"`,
      `"${(j.city||'').replace(/"/g,'""')}"`,
      `"${(j.type||'')}"`,
      `"${(j.direction||'').replace(/"/g,'""')}"`,
      `"${(j.date||'')}"`,
      `"${(j.tags||[]).join('、').replace(/"/g,'""')}"`,
      `"${(j.url||'')}"`,
    ].join(','));
  });
  const blob=new Blob([lines.join('\\n')],{type:'text/csv;charset=utf-8'});
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob);
  a.download=`jobboard_2026-10-10.csv`; a.click();
}

