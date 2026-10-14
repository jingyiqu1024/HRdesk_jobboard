const _CP_PAGE_SIZE = 50;
const _PAGE_SIZE = 50;
let _curPage = 1;
let _filteredCache = [];
let _cpFiltered = [];
let _cpPage = 1;
let _pdeActiveType = 'PDE';

const TIP_ICON = `<svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="6.25" stroke="currentColor" stroke-width="1.5"/><path d="M6.9 6.1a1.35 1.35 0 1 1 2.1 1.12c-.72.48-1 .82-1 1.53v.2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="8" cy="11.5" r=".8" fill="currentColor"/></svg>`;
function tipShow(el){ const box = el && el.parentElement && el.parentElement.querySelector('.tip-box'); if(box) box.classList.add('show'); }
function tipHide(el){ const box = el && el.parentElement && el.parentElement.querySelector('.tip-box'); if(box) box.classList.remove('show'); }

function escapeHtml(s){return String(s||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');}

/* ─── Industry Grid ─── */
function changeText(v){ if(!v) return '持平'; return v>0 ? `<span class="up">↑ ${v}%</span>` : `<span class="dn">↓ ${Math.abs(v)}%</span>`; }

function renderIndustry(){
  const bigGrid = document.getElementById('coGrid');
  const uniGrid = document.getElementById('uniGrid');
  if(!bigGrid || !uniGrid) return;

  const renderCard = (c) => `
    <div class="co-card" onclick="openCompanyPage('${c.name}')">
      <div class="co-head">
        <span class="co-nm">${c.name}</span>
        <span class="co-status" data-trend="${c.status}">${c.status}</span>
      </div>
      <div class="co-metrics">
        <div class="cm-item"><div class="cm-label">总计</div><div class="cm-val">${c.total.toLocaleString()}</div></div>
        <div class="cm-item"><div class="cm-label">AI岗</div><div class="cm-val">${(c.ai + (c.ai_user||0)).toLocaleString()}</div></div>
        <div class="cm-item"><div class="cm-label">全栈</div><div class="cm-val">${(c.fullstack||0)}</div></div>
        <div class="cm-item"><div class="cm-label">PDE</div><div class="cm-val">${(c.pde||0)}</div></div>
      </div>
      <div class="co-jump">查看详情 →</div>
    </div>`;

  bigGrid.innerHTML = COMPANIES.map(renderCard).join('');
  uniGrid.innerHTML = UNICORNS.map(renderCard).join('');
}

function drawMiniLine(canvas, vals, color){
  const dpr=window.devicePixelRatio||1;
  canvas.width=64*dpr; canvas.height=32*dpr;
  const ctx=canvas.getContext('2d'); ctx.scale(dpr,dpr);
  const w=64, h=32, pad=3;
  const min=Math.min(...vals), max=Math.max(...vals), range=(max-min)||1;
  const xs=vals.map((_,i)=>pad+i*(w-pad*2)/(vals.length-1));
  const ys=vals.map(v=>h-pad-((v-min)/range)*(h-pad*2));
  ctx.beginPath(); ctx.moveTo(xs[0],ys[0]);
  xs.forEach((x,i)=>i?ctx.lineTo(x,ys[i]):null);
  ctx.strokeStyle=color; ctx.lineWidth=1.8; ctx.lineJoin='round'; ctx.stroke();
  ctx.beginPath(); ctx.arc(xs[xs.length-1],ys[ys.length-1],2,0,Math.PI*2); ctx.fillStyle=color; ctx.fill();
}

/* ─── Topic Tabs ─── */
function renderTopicTabs(){
  const el = document.getElementById('topicTabs');
  if(!el) return;
  el.innerHTML = TOPICS.map(t => `<div class="topic-tab${t.id==='fullstack'?' active':''}" data-id="${t.id}" onclick="selTopic('${t.id}')">${t.name}</div>`).join('');
}

function selTopic(id){
  document.querySelectorAll('.topic-tab').forEach(el => el.classList.toggle('active', el.dataset.id===id));
  const t = TOPICS.find(x => x.id===id);
  const panel = document.getElementById('topicPanel');
  if(!t || !panel) return;

  let content = `
    <div class="panel-hd">
      <div><h3>${t.name}</h3><div class="ph-sum">${t.summary}</div></div>
    </div>
    <div class="insight-box insight-box-topic"><ul>${t.insights.map(x=>'<li>'+x+'</li>').join('')}</ul></div>`;

  if(id === 'pde'){
    content += `
      <div class="pde-tabs">
        ${['PDE','PE','PD','DE'].map(type => `<div class="pde-tab${type===_pdeActiveType?' active':''}" onclick="selPdeType('${type}')">${type}</div>`).join('')}
      </div>
      <div class="pde-type-desc" id="pdeTypeDesc"></div>
      <div class="sample-list" id="pdeSampleList"></div>`;
    panel.innerHTML = content;
    selPdeType(_pdeActiveType);
  } else {
    content += `
      <div class="sample-list">
        ${(t.samples||[]).map(s => renderSampleRow(s)).join('')}
      </div>
      <div class="sample-more" onclick="jumpToJobList('${t.name}')">查看全部 ${t.name} 岗位 →</div>`;
    panel.innerHTML = content;
  }
}

function selPdeType(type){
  _pdeActiveType = type;
  document.querySelectorAll('.pde-tab').forEach(el => el.classList.toggle('active', el.textContent===type));
  const t = TOPICS.find(x => x.id==='pde');
  const samples = t.samples_by_type[type] || [];
  const descMap = {
    'PDE': '三维全中：兼具产品思维(P)、设计感知(D)与工程实现(E)能力的全能型人才。',
    'PE': '产品思维(P) + 工程实现(E)：从产品视角直接推动工程实现。',
    'PD': '产品思维(P) + 设计感知(D)：更偏产品定义与体验设计融合。',
    'DE': '设计感知(D) + 工程实现(E)：更偏高还原交互与前端工程落地。'
  };
  const subInsight = (t.sub_insights && t.sub_insights[type]) || '';
  document.getElementById('pdeTypeDesc').innerHTML = `<div>${descMap[type]}</div>${subInsight?`<div class="pde-type-note">${subInsight}</div>`:''}`;
  document.getElementById('pdeSampleList').innerHTML = samples.map(s => renderSampleRow(s)).join('') || '<div class="empty-tip">暂无匹配样本</div>';
  const moreBtn = document.querySelector('.sample-more-pde');
  if(moreBtn) moreBtn.remove();
  const listEl = document.getElementById('pdeSampleList');
  const btn = document.createElement('div');
  btn.className = 'sample-more sample-more-pde';
  btn.onclick = () => jumpToJobList('PDE 专题', type);
  btn.textContent = `查看全部 ${type} 岗位 →`;
  listEl.after(btn);
}

function renderSampleRow(s){
  const url = s.url || '#';
  const isJd = url.startsWith('javascript:');
  const click = isJd ? url.replace('javascript:','') : `window.open('${url}','_blank')`;
  return `
    <div class="sample-row" onclick="${click}">
      <div class="s-title">${escapeHtml(s.title)}</div>
      <div class="s-meta">${escapeHtml(s.company)} · ${escapeHtml(s.city)}</div>
    </div>`;
}

function jumpToJobList(topicName, pdeType=''){
  const fTopic = document.getElementById('fTopic');
  const fCo = document.getElementById('fCo');
  const fType = document.getElementById('fType');
  const fDir = document.getElementById('fDir');
  const fDate = document.getElementById('fDate');
  const jQ = document.getElementById('jQ');
  if(fCo) fCo.value = '';
  if(fType) fType.value = '';
  if(fDir) fDir.value = '';
  if(fDate) fDate.value = '';
  if(fTopic) fTopic.value = topicName;
  if(jQ) jQ.value = pdeType;
  searchJobs();
  const sec = document.getElementById('jobListSection');
  sec.classList.add('section-flash');
  sec.scrollIntoView({behavior:'smooth', block:'start'});
  setTimeout(()=>sec.classList.remove('section-flash'), 1200);
}

/* ─── Job List Search ─── */
function searchJobs(){
  const q = (document.getElementById('jQ').value||'').toLowerCase();
  const fTopic = (document.getElementById('fTopic')||{}).value||'';
  const fCo = (document.getElementById('fCo')||{}).value||'';
  const fType = (document.getElementById('fType')||{}).value||'';
  const fDir = (document.getElementById('fDir')||{}).value||'';
  const fDate = parseInt((document.getElementById('fDate')||{}).value||'0')||0;
  const now = new Date('2026-10-10');

  _filteredCache = JOBS.filter(j => {
    if(fTopic && j.topic !== fTopic) return false;
    if(fCo && j.company !== fCo) return false;
    if(fType && j.type !== fType) return false;
    if(fDir && j.direction !== fDir) return false;
    if(q && ![j.title, j.company, j.city, j.topic, j.direction, (j.pde_type||''), (j.tags||[]).join(' ')].some(x => String(x||'').toLowerCase().includes(q))) return false;
    if(fDate && j.date){
      const diff = (now - new Date(j.date))/(1000*60*60*24);
      if(fDate===99){ if(diff<=30) return false; }
      else { if(diff>fDate) return false; }
    }
    return true;
  });

  const cnt = document.getElementById('filterCount');
  if(cnt) cnt.textContent = `共 ${_filteredCache.length.toLocaleString()} 条`;
  _curPage = 1;
  gotoPage(1);
}

function gotoPage(page){
  const pages = Math.ceil(_filteredCache.length / _PAGE_SIZE);
  _curPage = Math.max(1, Math.min(page, pages||1));
  const el = document.getElementById('jobList');
  if(!el) return;
  const slice = _filteredCache.slice((_curPage-1)*_PAGE_SIZE, _curPage*_PAGE_SIZE);
  el.innerHTML = renderJobList(slice) + renderPager(_filteredCache.length, _curPage, _PAGE_SIZE);
}

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
    d.dept ? {text: d.dept, cls: ''}     : null,
    d.city ? {text: d.city, cls: 'blue'} : null,
    d.type ? {text: d.type, cls: 'green'}: null,
    d.date ? {text: '📅 ' + d.date, cls: ''}  : null,
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
function renderJobAction(j, className='', text='查看 ↗'){
  const cls = className ? ` class="${className}"` : '';
  const baseStyle = className ? '' : ' style="text-decoration:none;font-size:12px;color:#94a3b8;transition:.15s;background:none;border:none;padding:0;cursor:pointer"';
  if((j.company||'')==='京东零售' || String(j.url||'').startsWith('javascript:openJdModal(')){
    const rid = String(j.row_id||'').replace(/'/g,"\\'");
    return `<button type="button"${cls}${baseStyle} onmouseover="this.style.color='#2563eb'" onmouseout="this.style.color='#94a3b8'" onclick="openJdModal('${rid}')">${text}</button>`;
  }
  return `<a href="${escapeHtml(j.url||'#')}" target="_blank" rel="noopener"${cls}${baseStyle} onmouseover="this.style.color='#2563eb'" onmouseout="this.style.color='#94a3b8'">${text}</a>`;
}

/* 城市单元格：超出用省略号，hover 用全局 fixed tooltip 展示全称 */
function cityCell(city){
  const full = String(city||'-');
  if(!full.includes(' / ')) return escapeHtml(full);
  return `<span class="city-wrap" data-city="${escapeHtml(full)}">${escapeHtml(full)}</span>`;
}
function ensureCityTooltip(){
  let t = document.getElementById('cityTooltip');
  if(!t){ t = document.createElement('div'); t.id = 'cityTooltip'; document.body.appendChild(t); }
  return t;
}
document.addEventListener('mouseover', e => {
  const el = e.target && e.target.closest ? e.target.closest('.city-wrap') : null;
  if(!el) return;
  const t = ensureCityTooltip();
  t.textContent = (el.dataset.city || el.textContent.trim()).replace(/ \/ /g, '\n');
  t.style.display = 'block';
  const r = el.getBoundingClientRect();
  const tw = t.offsetWidth;
  let left = Math.min(r.left, window.innerWidth - tw - 10);
  t.style.left = Math.max(8, left) + 'px';
  t.style.top = (r.bottom + 6) + 'px';
});
document.addEventListener('mouseout', e => {
  const el = e.target && e.target.closest ? e.target.closest('.city-wrap') : null;
  if(!el) return;
  const t = document.getElementById('cityTooltip');
  if(t) t.style.display = 'none';
});

function renderJobList(items){
  if(!items.length) return '<div class="empty-tip">暂无匹配岗位</div>';
  const header = `<div class="list-table"><div class="list-th">岗位</div><div class="list-th">公司</div><div class="list-th">城市</div><div class="list-th">类型</div><div class="list-th">方向</div><div class="list-th">更新</div><div class="list-th"></div>`;
  const rows = items.map(j => {
    const typePill = j.type ? `<span class="type-pill type-${j.type}">${escapeHtml(j.type)}</span>` : '';
    const tags = (j.tags||[]).slice(0,2).map(t=>`<span class="l-tag">${escapeHtml(t)}</span>`).join('');
    return `
      <div class="list-row">
        <div class="list-td"><div style="min-width:0"><div class="l-tit" title="${escapeHtml(j.title)}">${escapeHtml(j.title)}</div><div class="l-sub">${tags}</div></div></div>
        <div class="list-td"><span class="l-co">${escapeHtml(j.company)}</span></div>
        <div class="list-td l-city">${cityCell(j.city)}</div>
        <div class="list-td">${typePill}</div>
        <div class="list-td"><span class="l-dir">${escapeHtml(j.direction||j.topic)}</span></div>
        <div class="list-td"><span class="l-date">${escapeHtml(j.date)}</span></div>
        <div class="list-td">${renderJobAction(j,'','查看 ↗')}</div>
      </div>`;
  }).join('');
  return header + rows + '</div>';
}

function renderPager(total, cur, pageSize){
  const pages = Math.ceil(total / pageSize);
  if(pages <= 1) return '';
  const btn = (p, txt, cls='', dis=false) => `<button class="pager-btn ${cls}" onclick="gotoPage(${p})" ${dis?'disabled':''}>${txt}</button>`;
  let h = `<div class="pager"><span class="pager-info">共 ${total.toLocaleString()} 条</span>`;
  h += btn(1, '首页', '', cur===1) + btn(cur-1, '上一页', '', cur===1);
  const lo=Math.max(1,cur-2), hi=Math.min(pages,cur+2);
  if(lo>1) h += `<span class="pager-dots">…</span>`;
  for(let p=lo;p<=hi;p++) h += btn(p, p, p===cur?'cur':'');
  if(hi<pages) h += `<span class="pager-dots">…</span>`;
  h += btn(cur+1, '下一页', '', cur===pages) + btn(pages, '末页', '', cur===pages);
  return h + '</div>';
}

/* ─── Init & Data Injection ─── */
function renderHeroInsights(){
  const el = document.getElementById('insightBanner');
  if(!el || !INSIGHTS) return;
  el.innerHTML = `
    <div class="hero-insight">
      <div class="hi-head"><span class="hi-badge">双周洞察</span><span class="hi-date">本期情报关键信号汇总</span></div>
      <div class="hi-list">${INSIGHTS.map(txt => `<div class="hi-item"><span class="hi-dot"></span>${txt}</div>`).join('')}</div>
    </div>`;
}

function updateGlobalStats(){
  const all = COMPANIES.concat(UNICORNS);
  const total = all.reduce((sum,c)=>sum+c.total, 0);
  const ai = all.reduce((sum,c)=>sum+(c.ai||0)+(c.ai_user||0), 0);
  const social = all.reduce((sum,c)=>sum+c.social, 0);
  const campus = all.reduce((sum,c)=>sum+c.campus, 0);
  const talent = all.reduce((sum,c)=>sum+(c.talent||0), 0);
  const builder = all.reduce((sum,c)=>sum+c.ai, 0);
  const user = all.reduce((sum,c)=>sum+c.ai_user, 0);
  const fullstack = all.reduce((sum,c)=>sum+(c.fullstack||0), 0);
  const pde = all.reduce((sum,c)=>sum+(c.pde||0), 0);

  document.getElementById('ovTotal').textContent = total.toLocaleString();
  document.getElementById('ovTotalSub').textContent = `社招 ${social.toLocaleString()} / 校招 ${(campus + talent).toLocaleString()}（人才计划 ${talent.toLocaleString()}）`;
  document.getElementById('ovAi').textContent = ai.toLocaleString();
  document.getElementById('ovAiSub').textContent = `占比 ${round(ai/total*100)}% · Builder ${builder.toLocaleString()} / User ${user.toLocaleString()}`;
  const ovFullstack = document.getElementById('ovFullstack');
  const ovFullstackSub = document.getElementById('ovFullstackSub');
  const ovPde = document.getElementById('ovPde');
  const ovPdeSub = document.getElementById('ovPdeSub');
  if(ovFullstack) ovFullstack.textContent = fullstack.toLocaleString();
  if(ovFullstackSub) ovFullstackSub.textContent = `占总岗位 ${round(fullstack/Math.max(1,total)*100)}%`;
  if(ovPde) ovPde.textContent = pde.toLocaleString();
  if(ovPdeSub) ovPdeSub.textContent = `占总岗位 ${round(pde/Math.max(1,total)*100)}%`;
  document.getElementById('bigCount').textContent = `${COMPANIES.length} 家`;
  document.getElementById('uniCount').textContent = `${UNICORNS.length} 家`;
  
  const fCo = document.getElementById('fCo');
  if(fCo) {
    const cos = COMPANIES.concat(UNICORNS).map(c=>c.name).sort();
    fCo.innerHTML = '<option value="">全部</option>' + cos.map(c=>`<option>${c}</option>`).join('');
  }

  const fDir = document.getElementById('fDir');
  if(fDir) {
    const dirs = [...new Set(JOBS.map(j=>j.direction).filter(Boolean))].sort();
    fDir.innerHTML = '<option value="">全部方向</option>' + dirs.map(d=>`<option>${d}</option>`).join('');
  }
}
function round(n){ return Math.round(n); }

/* 公司卡展开/收起：默认只显示一行 */
function toggleCoGrid(which){
  const grid = document.getElementById(which==='big' ? 'coGrid' : 'uniGrid');
  const btn = document.getElementById(which==='big' ? 'bigToggle' : 'uniToggle');
  if(!grid || !btn) return;
  const collapsed = grid.classList.toggle('co-grid-collapsed');
  btn.textContent = collapsed ? '+ 展开' : '− 收起';
}

function renderUI(){
  updateGlobalStats();
  renderHeroInsights();
  renderIndustry();
  renderTopicTabs();
  selTopic(TOPICS[0].id);
  searchJobs();
  drawSparkline('spark1',[19184, 19462, 19740, 20018, 20296, 20574, 20852],'#64748b');
  drawSparkline('spark2',[3060, 3373, 3686, 3998, 4311, 4623, 4936],'#10b981');
  drawSparkline('spark3',[214, 246, 281, 308, 336, 360, 384],'#7c3aed');
  drawSparkline('spark4',[28, 33, 37, 41, 44, 47, 50],'#2563eb');
}

/* ─── Company Page ─── */
function openCompanyPage(name, topicName){
  topicName = topicName || '';
  const c = COMPANIES.find(x=>x.name===name) || UNICORNS.find(x=>x.name===name);
  if(!c) return;
  document.getElementById('cpName').textContent = c.name;
  document.getElementById('cpStatus').textContent = c.status;
  document.getElementById('cpDesc').textContent = c.summary;
  document.getElementById('cpDesc').style.display = '';

  const _kpiTips = {
    'all':'',
    'ai':'Builder + User 两类之和。Builder 负责 AI 能力建设，如训练、优化、Agent/Infra；User 负责在业务中接入和使用 AI。',
    'fullstack':'同时承担前后端的工程师。关键判定词：「全栈」「前后端」「全链路开发」，JD 中普遍要求 AI Coding 能力。',
    'fde':'Forward Deployed Engineer，前线部署工程师。代表岗位：解决方案工程师、交付工程师。核心是把技术能力转化为客户业务结果。',
    'pde':'Product Engineer，产品工程师。兼具产品判断、交互设计与工程实现能力。',
  };
  const topicKeyMap = {'全栈工程师':'fullstack','FDE 专题':'fde','PDE 专题':'pde'};
  window._cpActiveMetric = topicKeyMap[topicName] || 'all';

  const hls = c.highlights || [];
  document.getElementById('cpKpis').innerHTML = hls.map(h => {
    const tip = _kpiTips[h.key] || '';
    const tipHtml = tip ? `<span class="tip-wrap"><span class="tip-icon" tabindex="0" onmouseenter="tipShow(this)" onmouseleave="tipHide(this)" onfocus="tipShow(this)" onblur="tipHide(this)">${TIP_ICON}</span><span class="tip-box">${tip}</span></span>` : '';
    return `<div class="kpi-cell clickable ${h.key===window._cpActiveMetric?'active':''}" data-kpi-key="${h.key}" onclick="cpApplyMetric('${h.key}')"><div class="kpi-label">${h.label}${tipHtml}</div><div class="kpi-val">${h.value}</div><div class="kpi-sub">${h.sub}</div></div>`;
  }).join('');

  const companyJobs = JOBS.filter(j => j.company === name);
  const filtered = topicName ? companyJobs.filter(j => j.topic === topicName) : companyJobs;
  const scopeLabel = topicName ? (name + ' · ' + topicName) : name;

  let domains = c.domains || [], traits = c.traits || [], cities = c.cities || [];
  if(topicName && filtered.length){
    const tally = (key, topN) => {
      const m = {}; filtered.forEach(j => { const k = j[key]; if(k) m[k] = (m[k]||0)+1; });
      const arr = Object.entries(m).sort((a,b) => b[1]-a[1]);
      return arr.length ? arr.slice(0, topN) : null;
    };
    domains = tally('direction', 5) || domains;
    const tagMap = {};
    filtered.forEach(j => (j.tags||[]).forEach(t => { tagMap[t] = (tagMap[t]||0)+1; }));
    const tagArr = Object.entries(tagMap).sort((a,b) => b[1]-a[1]).slice(0,5);
    if(tagArr.length){
      const maxT = tagArr[0][1];
      traits = tagArr.map(([t,n]) => [t, Math.round(n/filtered.length*100)]);
    }
    cities = tally('city', 4) || cities;
  }

  document.getElementById('cpDomainSub').textContent = topicName ? (scopeLabel + ' 专业子方向岗位数') : 'Top 5 专业子方向的岗位数量';
  document.getElementById('cpTraitSub').textContent = topicName ? (scopeLabel + ' JD 命中岗位数') : 'AI Builder JD 中各关键词命中岗位数';
  renderBars('cpDomains', domains.map(d => [d[0], d[1]]));
  renderBars('cpTraits', traits.map(d => [d[0], d[1]]));
  renderBars('cpCities', cities.map(d => [d[0], d[1]]));

  document.getElementById('cpJobsTitle').textContent = topicName ? (scopeLabel + ' 在招岗位') : (name + ' 全部在招岗位');
  document.getElementById('cpJobsSub').textContent = '岗位、城市、类型、发布时间' + (topicName ? '（已按专题筛选）' : '');

  document.querySelectorAll('.cp-overview-only').forEach(el => { el.style.display = topicName ? 'none' : ''; });

  window._cpAllJobs = companyJobs;
  // 初始化方向下拉（当前公司的岗位方向集合）
  const cpFDir = document.getElementById('cpFDir');
  if(cpFDir){
    const dirs = [...new Set(companyJobs.map(j=>j.direction).filter(Boolean))].sort();
    cpFDir.innerHTML = '<option value="">全部方向</option>' + dirs.map(d=>`<option>${d}</option>`).join('');
  }
  ['cpQ','cpFType','cpFTopic','cpFDir','cpFDate'].forEach(id => { const el = document.getElementById(id); if(el) el.value = ''; });
  window._cpFilteredByMetric = null;
  cpSearch();

  document.getElementById('companyPage').classList.add('show');
  document.body.style.overflow = 'hidden';
  setTimeout(() => drawTrend('cpTrend', c.trend, c.ai_trend), 50);
}

function cpApplyMetric(metricKey){
  window._cpActiveMetric = metricKey;
  document.querySelectorAll('#cpKpis .kpi-cell').forEach(el => el.classList.toggle('active', el.dataset.kpiKey === metricKey));
  const topicMap = {fullstack:'全栈工程师', fde:'FDE 专题', pde:'PDE 专题'};
  const topicFilter = topicMap[metricKey] || '';
  // 写入专题筛选下拉
  const cpFTopic = document.getElementById('cpFTopic');
  if(cpFTopic) cpFTopic.value = topicFilter;
  // 清空其他筛选
  ['cpFType','cpFDir','cpFDate'].forEach(id => { const el = document.getElementById(id); if(el) el.value = ''; });
  // 不再用 _cpFilteredByMetric，由 cpSearch 直接读 cpFTopic 过滤
  window._cpFilteredByMetric = null;
  cpSearch();
  // 平滑滚动到岗位列表
  const sec = document.getElementById('cpJobsSection');
  if(sec) sec.scrollIntoView({behavior: 'smooth', block: 'start'});
}

function closeCompanyPage(){ document.getElementById('companyPage').classList.remove('show'); document.body.style.overflow = ''; }

function cpSearch(){
  const q = (document.getElementById('cpQ').value||'').toLowerCase();
  const fType = (document.getElementById('cpFType')||{}).value||'';
  const fTopic = (document.getElementById('cpFTopic')||{}).value||'';
  const fDir = (document.getElementById('cpFDir')||{}).value||'';
  const fDate = parseInt((document.getElementById('cpFDate')||{}).value||'0');
  const now = new Date('2026-10-10');
  const base = window._cpAllJobs || [];

  _cpFiltered = base.filter(j => {
    if(fType && j.type !== fType) return false;
    if(fTopic && j.topic !== fTopic) return false;
    if(fDir && j.direction !== fDir) return false;
    if(q && ![j.title, j.direction, j.city, j.topic].some(x => String(x||'').toLowerCase().includes(q))) return false;
    if(fDate && j.date){
      const diff = (now - new Date(j.date))/(1000*60*60*24);
      if(fDate===99){ if(diff<=30) return false; }
      else { if(diff>fDate) return false; }
    }
    return true;
  });
  document.getElementById('cpFCount').textContent = `共 ${_cpFiltered.length.toLocaleString()} 条`;
  _cpPage = 1;
  cpGotoPage(1);
}

function cpGotoPage(p){
  const pages = Math.ceil(_cpFiltered.length / _CP_PAGE_SIZE);
  _cpPage = Math.max(1, Math.min(p, pages||1));
  const body = document.getElementById('cpJobsBody');
  if(!body) return;
  const slice = _cpFiltered.slice((_cpPage-1)*_CP_PAGE_SIZE, _cpPage*_CP_PAGE_SIZE);
  body.innerHTML = slice.map(j => {
    const cityStr = escapeHtml(j.city||'-');
    return `<tr>
      <td><div class="job-name" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(j.title)}</div></td>
      <td style="color:var(--muted);overflow:hidden">${cityCell(j.city)}</td>
      <td><span class="type-pill type-${j.type}">${escapeHtml(j.type)}</span></td>
      <td style="color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(j.direction||'-')}</td>
      <td style="color:var(--muted2)">${escapeHtml(j.date)}</td>
      <td>${renderJobAction(j,'btn-ghost','查看')}</td>
    </tr>`;
  }).join('') + `<tr><td colspan="6">${renderPagerCp(_cpFiltered.length, _cpPage, _CP_PAGE_SIZE)}</td></tr>`;
}

function renderPagerCp(total, cur, pageSize){
  const pages = Math.ceil(total / pageSize);
  if(pages <= 1) return '';
  const btn = (p, txt, cls='', dis=false) => `<button class="pager-btn ${cls}" onclick="cpGotoPage(${p})" ${dis?'disabled':''}>${txt}</button>`;
  let h = `<div class="pager"><span class="pager-info">共 ${total.toLocaleString()} 条</span>`;
  h += btn(1, '首页', '', cur===1) + btn(cur-1, '上一页', '', cur===1);
  const lo=Math.max(1,cur-1), hi=Math.min(pages,cur+1);
  for(let p=lo;p<=hi;p++) h += btn(p, p, p===cur?'cur':'');
  h += btn(cur+1, '下一页', '', cur===pages) + btn(pages, '末页', '', cur===pages);
  return h + '</div>';
}

function exportCsv(){
  const rows = _filteredCache.length ? _filteredCache : JOBS;
  const hdr = ['岗位','公司','城市','类型','方向','更新'];
  const lines = [hdr.join(',')];
  rows.forEach(j => lines.push([`"${j.title}"`,`"${j.company}"`,`"${j.city}"`,`"${j.type}"`,`"${j.direction}"`,`"${j.date}"`].join(',')));
  const blob = new Blob([lines.join('\n')], {type:'text/csv;charset=utf-8'});
  const a = document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='jobs_export.csv'; a.click();
}

document.addEventListener('keydown',e=>{ if(e.key==='Escape'){ closeJobModal(); closeCompanyPage(); }});
window.onload = renderUI;
