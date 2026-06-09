/* ── BG CANVAS ── */
(function(){
  const cv=document.getElementById('bg-canvas'),ctx=cv.getContext('2d');
  let W,H,p=[],g=0;
  function resize(){W=cv.width=window.innerWidth;H=cv.height=window.innerHeight;}
  function init(){p=[];const n=Math.floor(W*H/20000);
    for(let i=0;i<n;i++)p.push({x:Math.random()*W,y:Math.random()*H,
      r:Math.random()*1.5+.3,dx:(Math.random()-.5)*.22,dy:(Math.random()-.5)*.22,
      a:Math.random()*.5+.15,c:Math.random()>.5?'0,212,255':'0,255,136'});}
  function frame(){ctx.clearRect(0,0,W,H);g+=.18;
    const s=55,o=g%s;ctx.strokeStyle='rgba(0,212,255,.03)';ctx.lineWidth=1;
    for(let x=-s+o;x<W+s;x+=s){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke();}
    for(let y=-s+o;y<H+s;y+=s){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke();}
    p.forEach(q=>{q.x+=q.dx;q.y+=q.dy;
      if(q.x<0)q.x=W;if(q.x>W)q.x=0;if(q.y<0)q.y=H;if(q.y>H)q.y=0;
      ctx.beginPath();ctx.arc(q.x,q.y,q.r,0,Math.PI*2);
      ctx.fillStyle=`rgba(${q.c},${q.a})`;ctx.fill();});
    requestAnimationFrame(frame);}
  window.addEventListener('resize',()=>{resize();init();});
  resize();init();frame();
})();

/* ── GLOBAL STATE ── */
let allDrivers = [];
let allVehicles = [];
let allAlerts = [];
let telemetryLatest = {};

/* ── LOAD USER SESSION ── */
function loadUserSession(){
  fetch("/api/auth/me")
    .then(res => {
      if(!res.ok) throw new Error("Unauthorized");
      return res.json();
    })
    .then(user => {
      sessionStorage.setItem('ev_user_id', user.id);
      sessionStorage.setItem('ev_user_email', user.email);
      sessionStorage.setItem('ev_display_name', user.id);
      
      document.getElementById('sb-admin-name').textContent = user.id;
      document.getElementById('sb-admin-role').textContent = `Admin · ${user.id.toUpperCase()}`;
      const av = document.getElementById('sb-admin-avatar');
      if(av) av.textContent = user.id.charAt(0).toUpperCase();
      
      const nameEl  = document.getElementById('admin-name');
      if(nameEl)  nameEl.value  = user.id;
      const emailEl = document.getElementById('admin-email');
      if(emailEl) emailEl.value = user.email;
    })
    .catch(err => {
      console.error(err);
      window.location.href = "/#portal-card";
    });
}

/* ── CLOCK ── */
function updateClock(){
  const now=new Date();
  const days=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
  const months=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const t=`${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}`;
  document.getElementById('clock-pill').textContent=
    `📅 ${days[now.getDay()]}, ${months[now.getMonth()]} ${now.getDate()} · ${t}`;
}
setInterval(updateClock,1000); updateClock();

/* ── DONUT CHART ── */
function updateDonutChart(active, charging, idle) {
  const total = active + charging + idle;
  if (total === 0) return;
  const C = 2 * Math.PI * 40; // 251.3
  
  const activeLen = (active / total) * C;
  const chargingLen = (charging / total) * C;
  const idleLen = (idle / total) * C;
  
  const donutActive = document.getElementById('donut-active');
  const donutCharging = document.getElementById('donut-charging');
  const donutIdle = document.getElementById('donut-idle');
  const donutTotalText = document.getElementById('donut-total-text');
  
  if (donutTotalText) donutTotalText.textContent = total;
  
  if (donutActive) {
    donutActive.setAttribute('stroke-dasharray', `${activeLen.toFixed(1)} ${(C - activeLen).toFixed(1)}`);
    donutActive.setAttribute('stroke-dashoffset', C.toFixed(1));
  }
  if (donutCharging) {
    donutCharging.setAttribute('stroke-dasharray', `${chargingLen.toFixed(1)} ${(C - chargingLen).toFixed(1)}`);
    donutCharging.setAttribute('stroke-dashoffset', (C - activeLen).toFixed(1));
  }
  if (donutIdle) {
    donutIdle.setAttribute('stroke-dasharray', `${idleLen.toFixed(1)} ${(C - idleLen).toFixed(1)}`);
    donutIdle.setAttribute('stroke-dashoffset', (C - activeLen - chargingLen).toFixed(1));
  }
}

/* ── CHARTS ── */
const energyVals=[480,520,445,610,590,380,415];
function buildBarChart(id,vals,color=''){
  const chart=document.getElementById(id);
  if(!chart) return;
  chart.innerHTML = '';
  const max=Math.max(...vals);
  const days=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
  vals.forEach((v,i)=>{
    const col=document.createElement('div');col.className='bc-col';
    const bar=document.createElement('div');bar.className='bc-bar'+(color?' '+color:'');
    const pct = Math.round(v/max*100);
    bar.style.height='6px';
    bar.title=`${days[i]}: ${v} kWh`;
    if(pct>=85) bar.classList.add('green');
    else if(pct<=45) bar.classList.add('orange');
    bar.onclick=()=>showModal(`${days[i]} Energy Usage`,`Energy consumed: ${v} kWh\nVehicles active: ${24+i*2}\nAvg per vehicle: ${(v/(24+i*2)).toFixed(1)} kWh`);
    col.appendChild(bar);chart.appendChild(col);
    requestAnimationFrame(()=>{
      requestAnimationFrame(()=>{ bar.style.height = pct+'%'; });
    });
  });
}

function buildTrendLine(){
  const vals=[28,35,30,42,38,25,31];
  const W=260,H=65,pad=6;
  const max=Math.max(...vals),min=Math.min(...vals);
  const pts=vals.map((v,i)=>[pad+i*(W-pad*2)/(vals.length-1),H-pad-(v-min)/(max-min||1)*(H-pad*2)]);
  const d=pts.map((p,i)=>i===0?`M${p[0]},${p[1]}`:`L${p[0]},${p[1]}`).join(' ');
  document.getElementById('trend-line').setAttribute('d',d);
  document.getElementById('trend-area').setAttribute('d',d+` L${pts[pts.length-1][0]},${H} L${pts[0][0]},${H} Z`);
  const g=document.getElementById('trend-dots');
  if(!g) return;
  g.innerHTML = '';
  const days=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
  pts.forEach((p,i)=>{
    const c=document.createElementNS('http://www.w3.org/2000/svg','circle');
    c.setAttribute('cx',p[0]);c.setAttribute('cy',p[1]);c.setAttribute('r','3.5');
    c.setAttribute('fill','var(--blue)');c.setAttribute('stroke','var(--bg)');c.setAttribute('stroke-width','1.5');
    c.style.cursor='pointer';
    c.onclick=()=>showModal(`${days[i]} Fleet Usage`,`Active vehicles: ${vals[i]}\nPeak usage at: 09:00–11:00\nTotal distance: ${vals[i]*78} km`);
    g.appendChild(c);
  });
}

/* ── DRIVER DATA ── */
function renderDriverTable(data,tbodyId){
  const tb=document.getElementById(tbodyId);
  if(!tb) return;
  tb.innerHTML='';
  data.forEach(d=>{
    const tr=document.createElement('tr');
    tr.style.cursor='pointer';
    
    const ev = allVehicles.find(v => v.id === d.vehicle_id);
    const vehLabel = ev ? `${ev.make} ${ev.model}` : (d.vehicle || 'Unassigned');
    const latest = telemetryLatest[d.id] || {};
    const statusVal = latest.status || d.status || 'offline';
    const statusClass = statusVal.toLowerCase();
    
    if(tbodyId==='drivers-tbody'){
      tr.innerHTML=`
        <td class="td-id">${d.id}</td>
        <td>${d.name}</td>
        <td style="color:var(--muted);font-size:.76rem">${d.email}</td>
        <td>${vehLabel}</td>
        <td><span class="status-badge ${statusClass}"><span class="dot"></span>${statusVal}</span></td>
        <td>
          <button class="action-btn" onclick="event.stopPropagation();editDriver('${d.id}')">Edit</button>
          <button class="action-btn red" style="margin-left:.3rem" onclick="event.stopPropagation();removeDriver('${d.id}')">✕</button>
        </td>`;
    } else {
      tr.innerHTML=`
        <td class="td-id">${d.id}</td>
        <td>${d.name}</td>
        <td>${vehLabel}</td>
        <td><span class="status-badge ${statusClass}"><span class="dot"></span>${statusVal}</span></td>`;
    }
    
    tr.onmouseenter = () => tr.querySelectorAll('td').forEach(td => td.style.background = 'rgba(0,212,255,.04)');
    tr.onmouseleave = () => tr.querySelectorAll('td').forEach(td => td.style.background = '');
    tr.onclick = () => showModal(`Driver: ${d.name}`, `ID: ${d.id}\\nEmail: ${d.email}\\nVehicle: ${vehLabel}\\nStatus: ${statusVal.toUpperCase()}`);
    tb.appendChild(tr);
  });
}

function filterDrivers(q){
  const filtered = allDrivers.filter(d =>
    d.name.toLowerCase().includes(q.toLowerCase()) ||
    d.id.toLowerCase().includes(q.toLowerCase()) ||
    d.email.toLowerCase().includes(q.toLowerCase())
  );
  renderDriverTable(filtered, 'drivers-tbody');
}

function editDriver(id){
  const d = allDrivers.find(x => x.id === id);
  if(!d) return;
  
  let vehOpts = '<option value="None">None (No EV Assigned)</option>';
  allVehicles.forEach(v => {
    const assigned = allDrivers.find(drv => drv.vehicle_id === v.id && drv.id !== d.id);
    vehOpts += `<option value="${v.id}" ${d.vehicle_id === v.id ? 'selected' : ''}>${v.id} — ${v.make} ${v.model} ${assigned ? '(Assigned to ' + assigned.name + ')' : '(Available)'}</option>`;
  });
  
  const formHtml = `
    <div style="display:flex;flex-direction:column;gap:0.8rem;text-align:left;">
      <div class="form-group">
        <label class="form-label" style="display:block;margin-bottom:0.3rem;">Driver Status</label>
        <select class="form-input form-select" id="edit-drv-status" style="width:100%;padding:0.55rem;background:rgba(255,255,255,0.05);border:1px solid var(--border);color:var(--text);border-radius:0.4rem;">
          <option value="Active" ${d.status === 'Active' ? 'selected' : ''}>Active</option>
          <option value="Idle" ${d.status === 'Idle' ? 'selected' : ''}>Idle</option>
          <option value="Offline" ${d.status === 'Offline' ? 'selected' : ''}>Offline</option>
          <option value="Charging" ${d.status === 'Charging' ? 'selected' : ''}>Charging</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label" style="display:block;margin-bottom:0.3rem;">Assign Vehicle</label>
        <select class="form-input form-select" id="edit-drv-vehicle" style="width:100%;padding:0.55rem;background:rgba(255,255,255,0.05);border:1px solid var(--border);color:var(--text);border-radius:0.4rem;">
          ${vehOpts}
        </select>
      </div>
    </div>
  `;
  
  showModal(`Edit Driver: ${d.name}`, formHtml, "Save Changes", () => {
    const status = document.getElementById('edit-drv-status').value;
    const vehicle_id = document.getElementById('edit-drv-vehicle').value;
    
    fetch(`/api/drivers/${d.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status, vehicle_id })
    })
    .then(res => {
      if(!res.ok) throw new Error("Failed to update driver");
      return res.json();
    })
    .then(() => {
      showToast(`Driver ${d.name} updated successfully!`);
      closeModalDirect();
      loadDashboardData();
    })
    .catch(err => {
      showToast(`⚠️ ${err.message}`, 'red');
    });
  });
}

function removeDriver(id){
  const d = allDrivers.find(x => x.id === id);
  if(!d) return;
  showModal(`Remove ${d.name}?`,
    `Are you sure you want to remove ${d.name} (${d.id}) from the fleet?\\nThis action cannot be undone.`,
    'Confirm Remove', () => {
      fetch(`/api/drivers/${d.id}`, { method: "DELETE" })
        .then(res => {
          if (!res.ok) throw new Error("Failed to delete driver");
          return res.json();
        })
        .then(() => {
          showToast(`🗑️ Driver ${d.name} removed`, 'red');
          closeModalDirect();
          loadDashboardData();
        })
        .catch(err => {
          showToast(`⚠️ ${err.message}`, 'red');
        });
    });
}

function openAddDriver() {
  document.getElementById('add-driver-form').style.display = 'block';
  populateVehicleSelect();
}

function closeAddDriver() {
  document.getElementById('add-driver-form').style.display = 'none';
  ['new-id', 'new-name', 'new-email'].forEach(id => document.getElementById(id).value = '');
}

function addDriver(){
  const id = document.getElementById('new-id').value.trim();
  const name = document.getElementById('new-name').value.trim();
  const email = document.getElementById('new-email').value.trim();
  const vehicle = document.getElementById('new-vehicle').value;
  if(!id || !name || !email){ showToast('⚠️ Please fill all fields', 'red'); return; }
  
  const payload = { id, name, email, vehicle_id: vehicle === 'None' ? null : vehicle };
  
  fetch("/api/drivers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  })
  .then(res => {
    if (!res.ok) return res.json().then(err => { throw new Error(err.detail || 'Failed to add driver'); });
    return res.json();
  })
  .then(newDrv => {
    showToast(`Driver ${name} added successfully!`);
    closeAddDriver();
    loadDashboardData();
  })
  .catch(err => {
    showToast(`⚠️ ${err.message}`, 'red');
  });
}

/* ── ALERTS ── */
function renderAlerts(containerId){
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';
  
  if(!allAlerts.length){
    container.innerHTML = '<div style="text-align:center;color:var(--muted);padding:2rem;font-size:.85rem;">✅ No active alerts</div>';
    return;
  }
  
  allAlerts.forEach((a) => {
    const timeStr = new Date(a.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    const div = document.createElement('div');
    div.className = `alert-item ${a.type}`;
    div.innerHTML = `
      <span class="alert-icon">${a.icon || '⚠️'}</span>
      <div style="flex:1">
        <div class="alert-title">${a.title}</div>
        <div class="alert-sub">${a.description || ''}</div>
      </div>
      <span class="alert-time">${timeStr}</span>
      <button class="alert-dismiss" onclick="event.stopPropagation();dismissAlert(${a.id})" title="Dismiss">✕</button>`;
      
    div.onclick = () => showModal(a.title, `${a.description || ''}\\nTime: ${new Date(a.timestamp).toLocaleString()}\\nPriority: ${a.type.toUpperCase()}`);
    container.appendChild(div);
  });
}

function dismissAlert(alertId){
  fetch(`/api/alerts/dismiss/${alertId}`, { method: "POST" })
    .then(res => res.json())
    .then(() => {
      allAlerts = allAlerts.filter(a => a.id !== alertId);
      updateAlertPills();
      renderAlerts('all-alerts');
      renderAlerts('dash-alerts');
      if (document.getElementById('sec-maintenance').classList.contains('active')) {
        renderMaintAlerts();
      }
      showToast(`🗑️ Alert dismissed`);
    });
}

function dismissAll(){
  fetch(`/api/alerts/dismiss-all`, { method: "POST" })
    .then(res => res.json())
    .then(() => {
      allAlerts = [];
      updateAlertPills();
      renderAlerts('all-alerts');
      renderAlerts('dash-alerts');
      if (document.getElementById('sec-maintenance').classList.contains('active')) {
        renderMaintAlerts();
      }
      showToast('✅ All alerts cleared!');
    });
}

function updateAlertPills() {
  const count = allAlerts.length;
  document.getElementById('alert-count').textContent = count;
  document.getElementById('alert-nav-badge').textContent = count;
  const countPill = document.getElementById('alerts-count-pill');
  if(countPill) countPill.textContent = count + ' Active';
}

/* ── STATIONS ── */
function initStationsDetail(){
  fetch("/api/telemetry/stations")
    .then(res => res.json())
    .then(data => {
      const grid = document.getElementById('stations-detail');
      if(!grid) return;
      grid.innerHTML = '';
      
      data.forEach(s => {
        const used = s.ports - s.free;
        const pct = Math.round(used / s.ports * 100);
        const barColor = pct >= 100 ? 'background:linear-gradient(90deg,var(--red),#ff0044)' :
          pct >= 80 ? 'background:linear-gradient(90deg,var(--orange),#ff6600)' :
          'background:linear-gradient(90deg,var(--blue),var(--green))';
        
        const statusLabel = s.free === 0 ? 'Full' : s.free <= 2 ? 'Partial Fault' : 'Online';
        const statusColor = s.free === 0 ? 'var(--red)' : s.free <= 2 ? 'var(--orange)' : 'var(--green)';
        
        const div = document.createElement('div'); div.className = 'card'; div.style.cursor = 'pointer';
        div.innerHTML = `
          <div class="st-name">${s.name}</div>
          <div class="st-meta">${s.ports} ports · ${s.type} · ${s.kw} kW</div>
          <div class="st-bar-outer"><div class="st-bar-inner" style="width:${pct}%;${barColor}"></div></div>
          <div class="st-footer">
            <span>${used}/${s.ports} in use</span>
            <span style="color:${statusColor}">${s.free === 0 ? '⚠️ ' : '● '}${statusLabel}</span>
          </div>
          <button class="action-btn" style="width:100%;margin-top:.7rem;padding:.5rem" onclick="event.stopPropagation();showToast('🔧 Maintenance request sent for ${s.name}')">Request Maintenance</button>`;
        
        div.onclick = () => showModal(s.name, `${s.name}\\nPorts: ${s.ports} total\\nAvailable: ${s.free} free\\nCost: ${s.cost}\\nCharger Type: ${s.type}\\nPower Capacity: ${s.kw} kW`);
        grid.appendChild(div);
      });
    });
}

/* ── ANALYTICS ── */
function initTopDrivers(){
  fetch("/api/analytics/driver-efficiency")
    .then(res => res.json())
    .then(data => {
      const el = document.getElementById('top-drivers');
      if(!el) return;
      el.innerHTML = '';
      const top = data.drivers.slice(0, 4);
      top.forEach((d, i) => {
        const div = document.createElement('div');
        div.style.cssText = 'display:flex;align-items:center;gap:.7rem;padding:.4rem 0;border-bottom:1px solid rgba(0,212,255,.07);cursor:pointer;';
        div.innerHTML = `
          <span style="color:var(--muted);font-size:.72rem;width:1rem">#${i+1}</span>
          <span style="font-size:1.2rem">${['🥇','🥈','🥉','🏅'][i]}</span>
          <div style="flex:1">
            <div style="font-size:.83rem;font-weight:600">${d.name}</div>
            <div style="font-size:.7rem;color:var(--muted)">${d.total_distance_km.toLocaleString()} km · ${d.avg_efficiency} km/kWh</div>
          </div>
          <span style="color:var(--green);font-weight:700;font-size:.85rem">${Math.round(d.score)}</span>`;
        
        div.onclick = () => showModal(`Top Driver: ${d.name}`, `Rank: #${i+1}\\nEfficiency: ${d.avg_efficiency} km/kWh\\nDistance: ${d.total_distance_km} km\\nHarsh Braking: ${d.total_harsh_braking}\\nHarsh Acceleration: ${d.total_harsh_acceleration}\\nOverspeeding: ${d.total_overspeed_violations}\\nDriver Behavior Score: ${d.score}/100`);
        el.appendChild(div);
      });
    });
}

function initAnalyticsSection(){
  buildBarChart('analytics-chart', energyVals, 'green');
  initTopDrivers();
  
  let extCard = document.getElementById("analytics-behavior-correlation-card");
  if (!extCard) {
    const parentSec = document.getElementById("sec-analytics");
    
    const fullWidthCard = document.createElement("div");
    fullWidthCard.id = "analytics-behavior-correlation-card";
    fullWidthCard.className = "card";
    fullWidthCard.style.marginTop = "1.4rem";
    
    fullWidthCard.innerHTML = `
      <div class="card-title">📈 Driver Behavior & Energy Efficiency Correlation Matrix</div>
      <div class="grid-2" style="margin-bottom: 1.2rem; margin-top: 1rem;">
        <div>
          <h4 style="color: var(--green); margin-bottom: 0.6rem; font-size: 0.9rem;">Behavioral Impact Analysis</h4>
          <div style="font-size: 0.82rem; color: var(--muted); line-height: 1.5; display: flex; flex-direction: column; gap: 0.6rem;">
            <div class="settings-row" style="display:flex;justify-content:space-between;">
              <span>Harsh Braking vs Energy Efficiency Correlation</span>
              <strong style="color: var(--orange)" id="corr-braking">-0.4215</strong>
            </div>
            <div class="settings-row" style="display:flex;justify-content:space-between;">
              <span>Overspeeding vs Energy Efficiency Correlation</span>
              <strong style="color: var(--red)" id="corr-overspeed">-0.6582</strong>
            </div>
            <div style="margin-top: 0.6rem; padding: 0.7rem 0.9rem; background: rgba(0, 212, 255, 0.05); border: 1px solid rgba(0, 212, 255, 0.15); border-radius: 0.6rem; font-size: 0.78rem;" id="corr-conclusion">
              Conclusion: Negative correlation values confirm that higher frequencies of harsh braking and overspeeding directly reduce EV battery energy efficiency (km/kWh).
            </div>
          </div>
        </div>
        <div style="display: flex; flex-direction: column;">
          <h4 style="color: var(--blue); margin-bottom: 0.6rem; font-size: 0.9rem;">Pearson Correlation Heatmap (Selected Features)</h4>
          <div style="overflow-x: auto; max-width: 100%;">
            <table id="corr-matrix-table" style="font-size: 0.72rem; text-align: center; border-collapse: collapse; width: 100%;">
            </table>
          </div>
        </div>
      </div>
    `;
    parentSec.appendChild(fullWidthCard);
    extCard = fullWidthCard;
  }
  
  fetch("/api/analytics/driver-efficiency")
    .then(res => res.json())
    .then(data => {
      document.getElementById("corr-braking").textContent = data.impact_analysis.harsh_braking_efficiency_correlation;
      document.getElementById("corr-overspeed").textContent = data.impact_analysis.overspeeding_efficiency_correlation;
      document.getElementById("corr-conclusion").textContent = data.impact_analysis.conclusion;
    });
    
  fetch("/api/analytics/correlation-matrix")
    .then(res => res.json())
    .then(data => {
      const interest = [
        'Speed', 'Acceleration', 'Harsh Braking', 'Harsh Acceleration', 
        'Overspeed Violation', 'Energy Efficiency Km Per Kwh', 
        'Battery Percentage', 'Battery Health', 'Battery Stress', 'Breakdown'
      ];
      
      const headerRow = data[0];
      const colKeysMap = {};
      Object.keys(headerRow).forEach(k => {
        if (headerRow[k]) colKeysMap[headerRow[k]] = k;
      });
      
      const table = document.getElementById("corr-matrix-table");
      if (!table) return;
      table.innerHTML = '';
      
      const thead = document.createElement("thead");
      const trHead = document.createElement("tr");
      trHead.appendChild(document.createElement("th"));
      interest.forEach(v => {
        const th = document.createElement("th");
        th.style.padding = "4px 8px";
        th.style.fontSize = "0.62rem";
        th.textContent = v.replace(" Km Per Kwh", "").replace(" Violation", "");
        trHead.appendChild(th);
      });
      thead.appendChild(trHead);
      table.appendChild(thead);
      
      const tbody = document.createElement("tbody");
      interest.forEach(rowLabel => {
        const tr = document.createElement("tr");
        
        const tdHeader = document.createElement("td");
        tdHeader.style.padding = "6px 8px";
        tdHeader.style.textAlign = "left";
        tdHeader.style.fontWeight = "600";
        tdHeader.style.color = "var(--muted)";
        tdHeader.textContent = rowLabel.replace(" Km Per Kwh", "").replace(" Violation", "");
        tr.appendChild(tdHeader);
        
        const rowRec = data.find(r => r["Correlation Matrix"] === rowLabel);
        
        interest.forEach(colLabel => {
          const td = document.createElement("td");
          td.style.padding = "6px 8px";
          td.style.border = "1px solid rgba(0, 212, 255, 0.08)";
          
          const colKey = colKeysMap[colLabel];
          let val = null;
          if (rowRec && colKey !== undefined) {
            val = rowRec[colKey];
          }
          
          if (rowLabel === colLabel) val = 1.0;
          
          if (val === null || val === undefined) {
            td.textContent = "—";
            td.style.color = "var(--muted)";
          } else {
            val = parseFloat(val);
            td.textContent = val.toFixed(2);
            
            if (val === 1.0) {
              td.style.background = "rgba(0, 212, 255, 0.18)";
              td.style.color = "var(--blue)";
              td.style.fontWeight = "bold";
            } else if (val > 0) {
              td.style.background = `rgba(0, 255, 136, ${val * 0.25})`;
              td.style.color = "var(--green)";
            } else if (val < 0) {
              td.style.background = `rgba(255, 77, 109, ${Math.abs(val) * 0.25})`;
              td.style.color = "var(--red)";
            }
          }
          tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);
    });
}

/* ── REVENUE ── */
let revDrivers = [];
function initRevenue(){
  buildRevChart('monthly');
  
  fetch("/api/analytics/driver-efficiency")
    .then(res => res.json())
    .then(data => {
      revDrivers = data.drivers.map(d => ({
        id: d.driver_id,
        name: d.name,
        vehicle: allVehicles.find(v => v.id === allDrivers.find(drv => drv.id === d.driver_id)?.vehicle_id)?.model || 'EV Fleet',
        trips: d.trips,
        income: `₹${d.income.toLocaleString()}`,
        charging: `₹${d.charging_cost.toLocaleString()}`,
        net: `₹${d.net_earnings.toLocaleString()}`,
        status: allDrivers.find(drv => drv.id === d.driver_id)?.status.toLowerCase() || 'idle'
      }));
      renderRevDrivers(revDrivers);
      renderDailyRev();
    });
}

function buildRevChart(mode){
  const chartEl = document.getElementById('rev-chart');
  if(!chartEl) return;
  chartEl.innerHTML = '';
  const labelsEl = document.getElementById('rev-chart-labels');

  let vals, labels;
  if(mode === 'monthly'){
    vals = [312000, 348000, 295000, 420000, 458000, 482600];
    labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
  } else {
    vals = [59600, 67300, 57700, 78400, 73500, 48000, 40600];
    labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  }
  if(labelsEl) labelsEl.innerHTML = labels.map(l => `<span>${l}</span>`).join('');

  const max = Math.max(...vals);
  vals.forEach((v, i) => {
    const col = document.createElement('div'); col.className = 'bc-col';
    const bar = document.createElement('div'); bar.className = 'bc-bar';
    bar.style.height = (v / max * 100) + '%';
    bar.style.background = 'linear-gradient(to top,var(--green),rgba(0,255,136,.25))';
    bar.title = `${labels[i]}: ₹${v.toLocaleString()}`;
    bar.onclick = () => showModal(`${labels[i]} Revenue`, `Total: ₹${v.toLocaleString()}\\nTrips: ~${Math.round(v * .8 / 543)}\\nCharging: ₹${Math.round(v * .2).toLocaleString()}`);
    col.appendChild(bar); chartEl.appendChild(col);
  });
}

function switchRevTab(btn, mode){
  document.querySelectorAll('#sec-revenue .rtab').forEach(b => {
    b.style.background = 'none'; b.style.color = 'var(--muted)'; b.style.borderColor = 'var(--border)';
  });
  btn.style.background = 'var(--green-dim)'; btn.style.color = 'var(--green)'; btn.style.borderColor = 'var(--green)';
  buildRevChart(mode);
}

function renderRevDrivers(data){
  const tb = document.getElementById('rev-driver-tbody');
  if(!tb) return;
  tb.innerHTML = '';
  data.forEach((d, i) => {
    const tr = document.createElement('tr'); tr.style.cursor = 'pointer';
    tr.innerHTML = `
      <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);color:var(--muted);font-weight:700">${i+1}</td>
      <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);" class="td-id">${d.id}</td>
      <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);font-weight:600">${d.name}</td>
      <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);color:var(--muted);font-size:.76rem">${d.vehicle}</td>
      <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);color:var(--blue);font-weight:600">${d.trips}</td>
      <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);color:var(--green);font-weight:700">${d.income}</td>
      <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);color:var(--red)">${d.charging}</td>
      <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);color:var(--blue);font-weight:800">${d.net}</td>
      <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);">
        <span class="status-badge ${d.status}"><span class="dot"></span>${d.status.charAt(0).toUpperCase() + d.status.slice(1)}</span>
      </td>`;
    
    tr.onmouseenter = () => tr.querySelectorAll('td').forEach(td => td.style.background = 'rgba(0,255,136,.04)');
    tr.onmouseleave = () => tr.querySelectorAll('td').forEach(td => td.style.background = '');
    tr.onclick = () => showModal(`Revenue: ${d.name}`,
      `Driver ID: ${d.id}\\nVehicle: ${d.vehicle}\\nTrips: ${d.trips}\\nGross Trip Income: ${d.income}\\nCharging Cost: ${d.charging}\\nNet Earnings: ${d.net}\\nStatus: ${d.status.toUpperCase()}`);
    tb.appendChild(tr);
  });
}

function filterRevDrivers(q){
  const f = revDrivers.filter(d =>
    d.name.toLowerCase().includes(q.toLowerCase()) ||
    d.id.toLowerCase().includes(q.toLowerCase())
  );
  renderRevDrivers(f);
}

const dailyRevData = [
  {day:'Today', trip:'₹15,480', charge:'₹3,120', total:'₹18,600', drivers:8, trips:94},
  {day:'Yesterday', trip:'₹24,800', charge:'₹5,400', total:'₹30,200', drivers:9, trips:142},
  {day:'07 Jun 2026', trip:'₹21,100', charge:'₹4,900', total:'₹26,000', drivers:9, trips:121},
  {day:'06 Jun 2026', trip:'₹18,400', charge:'₹3,800', total:'₹22,200', drivers:8, trips:105},
  {day:'05 Jun 2026', trip:'₹29,900', charge:'₹6,100', total:'₹36,000', drivers:10, trips:168},
];

function renderDailyRev(){
  const tb = document.getElementById('daily-rev-tbody');
  if(!tb || tb.children.length) return;
  dailyRevData.forEach(d => {
    const tr = document.createElement('tr'); tr.style.cursor = 'pointer';
    tr.innerHTML = `
      <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);font-weight:600">${d.day}</td>
      <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);color:var(--blue)">${d.trip}</td>
      <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);color:var(--orange)">${d.charge}</td>
      <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);color:var(--green);font-weight:800">${d.total}</td>
      <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);color:var(--muted)">${d.drivers}</td>
      <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);color:var(--muted)">${d.trips}</td>`;
    
    tr.onmouseenter = () => tr.querySelectorAll('td').forEach(td => td.style.background = 'rgba(0,255,136,.04)');
    tr.onmouseleave = () => tr.querySelectorAll('td').forEach(td => td.style.background = '');
    tr.onclick = () => showModal(`${d.day} Revenue`, `Trip Revenue: ${d.trip}\\nCharging Revenue: ${d.charge}\\nTotal: ${d.total}\\nDrivers Active: ${d.drivers}\\nTotal Trips: ${d.trips}`);
    tb.appendChild(tr);
  });
}

/* ── BATTERY MONITOR ── */
function initBatteryMonitor(){
  fetch("/api/vehicles")
    .then(res => res.json())
    .then(vehicles => {
      const tb = document.getElementById('batt-tbody');
      if(!tb) return;
      tb.innerHTML = '';
      
      let lowCount = 0;
      vehicles.forEach(v => {
        const drv = allDrivers.find(d => d.vehicle_id === v.id);
        const drvName = drv ? drv.name : 'Unassigned';
        const latest = telemetryLatest[drv ? drv.id : ''] || {};
        const battVal = latest.battery_pct !== undefined ? Math.round(latest.battery_pct) : Math.round(v.battery_health_soh * 0.8);
        const statusVal = latest.status || v.status;
        
        const low = battVal < 20;
        if(low) lowCount++;
        const color = battVal < 20 ? 'var(--red)' : battVal < 50 ? 'var(--orange)' : 'var(--green)';
        const statusClass = statusVal.toLowerCase();
        
        const tr = document.createElement('tr'); tr.style.cursor = 'pointer';
        if(low) tr.style.background = 'rgba(255,77,109,.04)';
        
        tr.innerHTML = `
          <td class="td-id">${v.id}</td>
          <td>${drvName}</td>
          <td style="color:var(--muted)">${v.make}</td>
          <td style="min-width:140px;">
            <div style="display:flex;align-items:center;gap:.5rem;">
              <div style="flex:1;background:rgba(255,255,255,.06);border-radius:2rem;height:.4rem;">
                <div style="width:${battVal}%;height:100%;border-radius:2rem;background:${color};"></div>
              </div>
              <span style="color:${color};font-weight:700;font-size:.78rem;width:2.5rem">${battVal}%</span>
            </div>
          </td>
          <td>
            <div style="display:flex;align-items:center;gap:.5rem;">
              <div style="flex:1;background:rgba(255,255,255,.06);border-radius:2rem;height:.4rem;">
                <div style="width:${v.battery_health_soh}%;height:100%;border-radius:2rem;background:var(--blue);"></div>
              </div>
              <span style="color:var(--blue);font-weight:700;font-size:.78rem;width:2.5rem">${v.battery_health_soh}%</span>
            </div>
          </td>
          <td style="color:var(--muted)">${v.battery_capacity_kwh} kWh</td>
          <td>
            <span class="status-badge ${statusClass}"><span class="dot"></span>${statusVal}</span>
          </td>
          <td>
            ${low ? '<span style="color:var(--red);font-weight:700;font-size:.75rem;">⚠️ CRITICAL</span>' :
              battVal < 50 ? '<span style="color:var(--orange);font-size:.75rem;">⚡ Low</span>' :
              '<span style="color:var(--green);font-size:.75rem;">✅ OK</span>'}
          </td>`;
          
        tr.onmouseenter = () => tr.querySelectorAll('td').forEach(td => td.style.background = 'rgba(0,212,255,.04)');
        tr.onmouseleave = () => tr.querySelectorAll('td').forEach(td => td.style.background = low ? 'rgba(255,77,109,.04)' : '');
        tr.onclick = () => showModal(`Battery: ${v.id}`, `Driver: ${drvName}\\nBrand: ${v.make} ${v.model}\\nBattery: ${battVal}%\\nHealth (SOH): ${v.battery_health_soh}%\\nCapacity: ${v.battery_capacity_kwh} kWh\\nStatus: ${statusVal.toUpperCase()}\\n${low ? '⚠️ CRITICAL — charge immediately!' : battVal < 50 ? '⚡ Low — charge soon' : '✅ Battery OK'}`);
        tb.appendChild(tr);
      });
      
      const lowBattCountEl = document.getElementById('low-batt-count');
      if (lowBattCountEl) lowBattCountEl.textContent = lowCount;
    });
}

function filterBattTable(q){
  fetch("/api/vehicles")
    .then(res => res.json())
    .then(vehicles => {
      const tb = document.getElementById('batt-tbody');
      if(!tb) return;
      tb.innerHTML = '';
      
      const filtered = vehicles.filter(v => {
        const drv = allDrivers.find(d => d.vehicle_id === v.id);
        const drvName = drv ? drv.name : 'Unassigned';
        return v.id.toLowerCase().includes(q.toLowerCase()) ||
               drvName.toLowerCase().includes(q.toLowerCase()) ||
               v.make.toLowerCase().includes(q.toLowerCase());
      });
      
      filtered.forEach(v => {
        const drv = allDrivers.find(d => d.vehicle_id === v.id);
        const drvName = drv ? drv.name : 'Unassigned';
        const latest = telemetryLatest[drv ? drv.id : ''] || {};
        const battVal = latest.battery_pct !== undefined ? Math.round(latest.battery_pct) : Math.round(v.battery_health_soh * 0.8);
        const statusVal = latest.status || v.status;
        const low = battVal < 20;
        const color = battVal < 20 ? 'var(--red)' : battVal < 50 ? 'var(--orange)' : 'var(--green)';
        const statusClass = statusVal.toLowerCase();
        
        const tr = document.createElement('tr'); tr.style.cursor = 'pointer';
        if(low) tr.style.background = 'rgba(255,77,109,.04)';
        
        tr.innerHTML = `
          <td class="td-id">${v.id}</td>
          <td>${drvName}</td>
          <td style="color:var(--muted)">${v.make}</td>
          <td style="min-width:140px;">
            <div style="display:flex;align-items:center;gap:.5rem;">
              <div style="flex:1;background:rgba(255,255,255,.06);border-radius:2rem;height:.4rem;">
                <div style="width:${battVal}%;height:100%;border-radius:2rem;background:${color};"></div>
              </div>
              <span style="color:${color};font-weight:700;font-size:.78rem;width:2.5rem">${battVal}%</span>
            </div>
          </td>
          <td>
            <div style="display:flex;align-items:center;gap:.5rem;">
              <div style="flex:1;background:rgba(255,255,255,.06);border-radius:2rem;height:.4rem;">
                <div style="width:${v.battery_health_soh}%;height:100%;border-radius:2rem;background:var(--blue);"></div>
              </div>
              <span style="color:var(--blue);font-weight:700;font-size:.78rem;width:2.5rem">${v.battery_health_soh}%</span>
            </div>
          </td>
          <td style="color:var(--muted)">${v.battery_capacity_kwh} kWh</td>
          <td>
            <span class="status-badge ${statusClass}"><span class="dot"></span>${statusVal}</span>
          </td>
          <td>
            ${low ? '<span style="color:var(--red);font-weight:700;font-size:.75rem;">⚠️ CRITICAL</span>' :
              battVal < 50 ? '<span style="color:var(--orange);font-size:.75rem;">⚡ Low</span>' :
              '<span style="color:var(--green);font-size:.75rem;">✅ OK</span>'}
          </td>`;
        tb.appendChild(tr);
      });
    });
}

/* ── VEHICLE PERFORMANCE ── */
function initVehiclePerf(){
  fetch("/api/vehicles")
    .then(res => res.json())
    .then(vehicles => {
      const tb = document.getElementById('veh-perf-tbody');
      if(!tb) return;
      tb.innerHTML = '';
      
      vehicles.forEach(v => {
        const drv = allDrivers.find(d => d.vehicle_id === v.id);
        const drvName = drv ? drv.name : 'Unassigned';
        const latest = telemetryLatest[drv ? drv.id : ''] || {};
        
        const speedVal = latest.speed !== undefined ? Math.round(latest.speed) : 0;
        const routeVal = latest.speed !== undefined ? (speedVal > 60 ? 'Highway' : 'City') : '—';
        const statusVal = latest.status || v.status;
        const overspeedVal = latest.overspeed > 0;
        
        const tr = document.createElement('tr'); tr.style.cursor = 'pointer';
        if(overspeedVal) tr.style.background = 'rgba(255,77,109,.05)';
        
        tr.innerHTML = `
          <td class="td-id">${v.id}</td>
          <td>${drvName}</td>
          <td style="color:var(--muted)">${v.make} ${v.model}</td>
          <td style="color:${overspeedVal ? 'var(--red)' : 'var(--blue)'};font-weight:700">${speedVal} km/h</td>
          <td style="color:var(--muted)">${routeVal}</td>
          <td style="font-size:.76rem">${v.vin ? '245 kW RWD' : '150 kW FWD'}</td>
          <td style="color:var(--orange)">${v.battery_capacity_kwh} kWh</td>
          <td style="color:var(--muted)">${v.year > 2023 ? '1844' : '1550'} kg</td>
          <td>
            ${overspeedVal ? '<span style="color:var(--red);font-weight:700">⚠️ YES</span>' : '<span style="color:var(--green)">✅ No</span>'}
          </td>
          <td>
            <span class="status-badge ${statusVal.toLowerCase()}"><span class="dot"></span>${statusVal}</span>
          </td>`;
          
        tr.onmouseenter = () => tr.querySelectorAll('td').forEach(td => td.style.background = 'rgba(0,212,255,.04)');
        tr.onmouseleave = () => tr.querySelectorAll('td').forEach(td => td.style.background = overspeedVal ? 'rgba(255,77,109,.05)' : '');
        tr.onclick = () => showModal(`Vehicle ${v.id}${overspeedVal ? ' ⚠️' : ''}`,
          `Driver: ${drvName}\\nModel: ${v.make} ${v.model}\\nSpeed: ${speedVal} km/h\\nRoute: ${routeVal}\\nMotor: 245 kW RWD\\nEngine: ${v.battery_capacity_kwh} kWh\\nOverspeed: ${overspeedVal ? '⚠️ YES — violation logged' : '✅ None'}\\nStatus: ${statusVal.toUpperCase()}`);
        tb.appendChild(tr);
      });
    });
}

function filterVehTable(q){
  fetch("/api/vehicles")
    .then(res => res.json())
    .then(vehicles => {
      const tb = document.getElementById('veh-perf-tbody');
      if(!tb) return;
      tb.innerHTML = '';
      
      const filtered = vehicles.filter(v => {
        const drv = allDrivers.find(d => d.vehicle_id === v.id);
        const drvName = drv ? drv.name : 'Unassigned';
        return v.id.toLowerCase().includes(q.toLowerCase()) ||
               drvName.toLowerCase().includes(q.toLowerCase()) ||
               v.make.toLowerCase().includes(q.toLowerCase());
      });
      
      filtered.forEach(v => {
        const drv = allDrivers.find(d => d.vehicle_id === v.id);
        const drvName = drv ? drv.name : 'Unassigned';
        const latest = telemetryLatest[drv ? drv.id : ''] || {};
        const speedVal = latest.speed !== undefined ? Math.round(latest.speed) : 0;
        const routeVal = latest.speed !== undefined ? (speedVal > 60 ? 'Highway' : 'City') : '—';
        const statusVal = latest.status || v.status;
        const overspeedVal = latest.overspeed > 0;
        
        const tr = document.createElement('tr'); tr.style.cursor = 'pointer';
        if(overspeedVal) tr.style.background = 'rgba(255,77,109,.05)';
        
        tr.innerHTML = `
          <td class="td-id">${v.id}</td>
          <td>${drvName}</td>
          <td style="color:var(--muted)">${v.make} ${v.model}</td>
          <td style="color:${overspeedVal ? 'var(--red)' : 'var(--blue)'};font-weight:700">${speedVal} km/h</td>
          <td style="color:var(--muted)">${routeVal}</td>
          <td style="font-size:.76rem">${v.vin ? '245 kW RWD' : '150 kW FWD'}</td>
          <td style="color:var(--orange)">${v.battery_capacity_kwh} kWh</td>
          <td style="color:var(--muted)">${v.year > 2023 ? '1844' : '1550'} kg</td>
          <td>
            ${overspeedVal ? '<span style="color:var(--red);font-weight:700">⚠️ YES</span>' : '<span style="color:var(--green)">✅ No</span>'}
          </td>
          <td>
            <span class="status-badge ${statusVal.toLowerCase()}"><span class="dot"></span>${statusVal}</span>
          </td>`;
        tb.appendChild(tr);
      });
    });
}

/* ── CHARGING ANALYTICS ── */
function initChargingAnalytics(){
  buildBarChart('charge-cost-chart',[9800,11200,8700,14400,13100,7200,6480],'orange');
  renderChargeStatus();
  
  fetch("/api/telemetry/charging")
    .then(res => res.json())
    .then(data => {
      const tb = document.getElementById('charge-log-tbody');
      if(!tb) return;
      tb.innerHTML = '';
      
      data.forEach(c => {
        const active = c.status === 'active';
        const tr = document.createElement('tr'); tr.style.cursor = 'pointer';
        if(active) tr.style.background = 'rgba(0,212,255,.04)';
        
        tr.innerHTML = `
          <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);color:var(--muted)">${c.time}</td>
          <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);" class="td-id">EV-${c.vid}</td>
          <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);">${c.driver}</td>
          <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);color:var(--muted);font-size:.76rem">${c.station}</td>
          <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);color:var(--orange);font-weight:600">${c.kwh} kWh</td>
          <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);color:var(--green);font-weight:700">${c.cost}</td>
          <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);color:var(--muted)">${c.dur}</td>
          <td style="padding:.55rem .8rem;border-bottom:1px solid rgba(0,212,255,.07);">
            <span class="status-badge ${active ? 'charging' : 'active'}"><span class="dot"></span>${active ? 'Charging' : 'Done'}</span>
          </td>`;
          
        tr.onmouseenter = () => tr.querySelectorAll('td').forEach(td => td.style.background = 'rgba(0,212,255,.04)');
        tr.onmouseleave = () => tr.querySelectorAll('td').forEach(td => td.style.background = active ? 'rgba(0,212,255,.04)' : '');
        tr.onclick = () => showModal(`Charging Session`, `Driver: ${c.driver}\\nStation: ${c.station}\\nEnergy: ${c.kwh} kWh\\nCost: ${c.cost}\\nDuration: ${c.dur}\\nStatus: ${c.status.toUpperCase()}`);
        tb.appendChild(tr);
      });
    });
}

function renderChargeStatus(){
  fetch("/api/telemetry/stations")
    .then(res => res.json())
    .then(stations => {
      const el = document.getElementById('charge-status-list');
      if(!el) return;
      el.innerHTML = '';
      stations.slice(0, 4).forEach(s => {
        const used = s.ports - s.free;
        const pct = Math.round(used / s.ports * 100);
        const color = s.free === 0 ? 'var(--red)' : s.free <= 2 ? 'var(--orange)' : 'var(--green)';
        const stLabel = s.free === 0 ? 'Full' : s.free <= 2 ? 'Partial' : 'Online';
        
        const div = document.createElement('div');
        div.innerHTML = `
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:.3rem;">
            <span style="font-size:.82rem;font-weight:600">${s.name}</span>
            <span style="font-size:.72rem;color:${color};font-weight:700">${used}/${s.ports} · ${stLabel}</span>
          </div>
          <div style="background:rgba(255,255,255,.06);border-radius:2rem;height:.4rem;">
            <div style="width:${pct}%;height:100%;border-radius:2rem;background:${color};"></div>
          </div>`;
        el.appendChild(div);
      });
    });
}

/* ── MAINTENANCE ── */
function initMaintenance(){
  renderMaintAlerts();
  renderMaintTable();
}

function renderMaintAlerts(){
  const el = document.getElementById('maint-alerts-list');
  if(!el) return;
  el.innerHTML = '';
  
  const critAlerts = allAlerts.filter(a => a.type === 'crit' || a.type === 'warn');
  if(!critAlerts.length){
    el.innerHTML = '<div style="text-align:center;color:var(--muted);padding:1.5rem;font-size:.85rem;">✅ No active alerts</div>';
    return;
  }
  
  critAlerts.forEach((a) => {
    const borderMap = {crit: 'rgba(255,77,109,.25)', warn: 'rgba(255,170,0,.25)'};
    const bgMap = {crit: 'rgba(255,77,109,.06)', warn: 'rgba(255,170,0,.06)'};
    const div = document.createElement('div');
    div.style.cssText = `display:flex;align-items:flex-start;gap:.7rem;border-radius:.65rem;padding:.65rem .85rem;
      background:${bgMap[a.type] || 'rgba(0,212,255,.05)'};border:1px solid ${borderMap[a.type] || 'rgba(0,212,255,.2)'};`;
    
    div.innerHTML = `
      <span style="font-size:1.1rem;flex-shrink:0;margin-top:1px">${a.icon || '⚠️'}</span>
      <div style="flex:1">
        <div style="font-size:.82rem;font-weight:600">${a.title}</div>
        <div style="font-size:.72rem;color:var(--muted);margin-top:.1rem">${a.description || ''}</div>
      </div>
      <button onclick="dismissAlert(${a.id})" style="background:none;border:none;cursor:pointer;color:var(--muted);font-size:.85rem;padding:0;" title="Dismiss">✕</button>`;
    el.appendChild(div);
  });
  
  const criticalCount = allAlerts.filter(a => a.type === 'crit').length;
  document.getElementById('maint-alert-count').textContent = criticalCount + ' Critical';
  document.getElementById('maint-critical').textContent = criticalCount;
  document.getElementById('maint-warn').textContent = allAlerts.filter(a => a.type === 'warn').length;
}

function renderMaintTable(){
  fetch("/api/vehicles")
    .then(res => res.json())
    .then(vehicles => {
      const tb = document.getElementById('maint-tbody');
      if(!tb) return;
      tb.innerHTML = '';
      
      const prioMap = {critical: 'var(--red)', warning: 'var(--orange)', scheduled: 'var(--blue)'};
      
      vehicles.forEach(v => {
        const drv = allDrivers.find(d => d.vehicle_id === v.id);
        const drvName = drv ? drv.name : 'Unassigned';
        const latest = telemetryLatest[drv ? drv.id : ''] || {};
        
        const breakdownVal = latest.breakdown === 1;
        const overspeedVal = latest.overspeed > 0;
        
        let priority = 'scheduled';
        let mType = 'Annual Service';
        let due = 'Jun 26';
        
        if (breakdownVal) {
          priority = 'critical';
          mType = 'Breakdown Repair';
          due = 'Urgently';
        } else if (latest.battery_pct < 20) {
          priority = 'critical';
          mType = 'Battery Charge Required';
          due = 'Immediate';
        } else if (v.odometer_km > v.next_service_km) {
          priority = 'critical';
          mType = 'Service Overdue';
          due = 'Overdue';
        } else if (overspeedVal) {
          priority = 'warning';
          mType = 'Overspeed Review';
          due = 'Soon';
        }
        
        const tr = document.createElement('tr'); tr.style.cursor = 'pointer';
        if(priority === 'critical') tr.style.background = 'rgba(255,77,109,.04)';
        
        tr.innerHTML = `
          <td class="td-id">${v.id}</td>
          <td>${drvName}</td>
          <td style="color:var(--muted);font-size:.76rem">${mType}</td>
          <td style="color:${priority === 'critical' ? 'var(--red)' : 'var(--muted)'};font-weight:600">${due}</td>
          <td>${breakdownVal ? '<span style="color:var(--red);font-weight:700">🔴 Yes</span>' : '<span style="color:var(--green)">✅ No</span>'}</td>
          <td>${overspeedVal ? '<span style="color:var(--red);font-weight:700">⚠️ Yes</span>' : '<span style="color:var(--green)">✅ No</span>'}</td>
          <td>
            <span style="color:${prioMap[priority]};font-weight:700;font-size:.75rem;text-transform:uppercase">${priority}</span>
          </td>
          <td>
            <button class="action-btn" onclick="event.stopPropagation();showToast('📋 Work order created for ${v.id}')">Assign</button>
          </td>`;
          
        tr.onmouseenter = () => tr.querySelectorAll('td').forEach(td => td.style.background = 'rgba(0,212,255,.04)');
        tr.onmouseleave = () => tr.querySelectorAll('td').forEach(td => td.style.background = priority === 'critical' ? 'rgba(255,77,109,.04)' : '');
        tr.onclick = () => showModal(`Maintenance: ${v.id}`, `Driver: ${drvName}\\nType: ${mType}\\nDue: ${due}\\nBreakdown: ${breakdownVal ? 'Yes' : 'No'}\\nOverspeed: ${overspeedVal ? 'Yes' : 'No'}\\nPriority: ${priority.toUpperCase()}`);
        tb.appendChild(tr);
      });
    });
}

function dismissAllMaint(){
  dismissAll();
}

/* ── CHARGING CINEMATIC FUNCTIONS (admin) ── */
let _cinemaCanvasAdmin, _cinemaCtxAdmin, _cinemaParticlesAdmin = [], _cinemaRAFAdmin;
function openChargingCinematicAdmin(){
  document.getElementById('cinema-overlay-admin').classList.add('open');
  _cinemaCanvasAdmin = document.getElementById('cinema-canvas-admin');
  const stage = document.querySelector('.cinema-stage-admin');
  _cinemaCanvasAdmin.width = stage.clientWidth;
  _cinemaCanvasAdmin.height = stage.clientHeight;
  _cinemaCtxAdmin = _cinemaCanvasAdmin.getContext('2d');
  _cinemaParticlesAdmin = [];
  animateChargingCinematicAdmin();
}

function closeChargingCinematicAdmin(){
  document.getElementById('cinema-overlay-admin').classList.remove('open');
  if(_cinemaRAFAdmin) cancelAnimationFrame(_cinemaRAFAdmin);
  _cinemaRAFAdmin = null; _cinemaParticlesAdmin = [];
}

function spawnParticleAdmin(stageW, stageH){
  const x = Math.random() * stageW * 0.6 + stageW * 0.2;
  const y = stageH - 20;
  const vx = (Math.random() - 0.5) * 1.2;
  const vy = - (2 + Math.random() * 3);
  const s = 2 + Math.random() * 3;
  const c = `rgba(0,255,204,${0.6 + Math.random() * .4})`;
  _cinemaParticlesAdmin.push({x, y, vx, vy, s, c, life: 80 + Math.random() * 80});
}

function animateChargingCinematicAdmin(){
  const stage = document.querySelector('.cinema-stage-admin');
  if(!_cinemaCanvasAdmin) return;
  const w = _cinemaCanvasAdmin.width = stage.clientWidth;
  const h = _cinemaCanvasAdmin.height = stage.clientHeight;
  _cinemaCtxAdmin.clearRect(0, 0, w, h);
  if(Math.random() < 0.6) spawnParticleAdmin(w, h);
  for(let i = _cinemaParticlesAdmin.length - 1; i >= 0; i--){
    const p = _cinemaParticlesAdmin[i]; p.x += p.vx; p.y += p.vy; p.vy += 0.06; p.life--;
    _cinemaCtxAdmin.beginPath(); _cinemaCtxAdmin.fillStyle = p.c; _cinemaCtxAdmin.globalCompositeOperation = 'lighter';
    _cinemaCtxAdmin.arc(p.x, p.y, p.s, 0, Math.PI * 2); _cinemaCtxAdmin.fill(); _cinemaCtxAdmin.globalCompositeOperation = 'source-over';
    if(p.life <= 0 || p.y < 30) _cinemaParticlesAdmin.splice(i, 1);
  }
  const pct = 0.78;
  const maskRect = document.getElementById('maskRectAdmin');
  if(maskRect){
    const fillH = 20 + pct * 200;
    const y = 240 - fillH;
    maskRect.setAttribute('y', y);
    maskRect.setAttribute('height', fillH);
  }
  const elv = document.getElementById('cinema-batt-val-admin'); if(elv) elv.textContent = Math.round(pct * 100) + '%';
  _cinemaRAFAdmin = requestAnimationFrame(animateChargingCinematicAdmin);
}

/* ── FLEET MANAGEMENT TABLE ── */
function initFleetTable() {
  const tb = document.getElementById('fleet-tbody');
  if(!tb) return;
  tb.innerHTML = '';
  
  allVehicles.forEach(v => {
    const drv = allDrivers.find(d => d.vehicle_id === v.id);
    const drvName = drv ? drv.name : 'Unassigned';
    const latest = telemetryLatest[drv ? drv.id : ''] || {};
    const battVal = latest.battery_pct !== undefined ? Math.round(latest.battery_pct) : Math.round(v.battery_health_soh * 0.8);
    const statusVal = latest.status || v.status;
    const odoVal = latest.odometer !== undefined ? latest.odometer : v.odometer_km;
    
    const tr = document.createElement('tr');
    tr.style.cursor = 'pointer';
    tr.innerHTML = `
      <td class="td-id">${v.id}</td>
      <td>${v.make} ${v.model}</td>
      <td>${v.plate_no}</td>
      <td>${drvName}</td>
      <td>
        <div style="display:flex;align-items:center;gap:.4rem;">
          <span style="font-weight:700;font-size:.78rem">${battVal}%</span>
        </div>
      </td>
      <td><span class="status-badge ${statusVal.toLowerCase()}"><span class="dot"></span>${statusVal}</span></td>
      <td style="color:var(--muted)">${Math.round(odoVal).toLocaleString()} km</td>
      <td>
        <button class="action-btn red" onclick="event.stopPropagation();removeVehicle('${v.id}')">✕</button>
      </td>
    `;
    
    tr.onmouseenter = () => tr.querySelectorAll('td').forEach(td => td.style.background = 'rgba(0,212,255,.04)');
    tr.onmouseleave = () => tr.querySelectorAll('td').forEach(td => td.style.background = '');
    tr.onclick = () => showModal(`Vehicle details: ${v.id}`, 
      `Make: ${v.make} ${v.model}\\nPlate: ${v.plate_no}\\nDriver: ${drvName}\\nBattery Percentage: ${battVal}%\\nStatus: ${statusVal.toUpperCase()}\\nOdometer: ${Math.round(odoVal).toLocaleString()} km\\nBattery Health SOH: ${v.battery_health_soh}%\\nVIN: ${v.vin || '—'}`);
    tb.appendChild(tr);
  });
}

function openAddVehicleModal() {
  const formHtml = `
    <div style="display:flex;flex-direction:column;gap:0.8rem;text-align:left;">
      <div class="form-group">
        <label class="form-label" style="display:block;margin-bottom:0.3rem;">Vehicle ID (e.g. EV-D011)</label>
        <input class="form-input" id="new-veh-id" style="width:100%;padding:0.55rem;background:rgba(255,255,255,0.05);border:1px solid var(--border);color:var(--text);border-radius:0.4rem;" placeholder="EV-D011">
      </div>
      <div class="form-group">
        <label class="form-label" style="display:block;margin-bottom:0.3rem;">Make / Brand</label>
        <input class="form-input" id="new-veh-make" style="width:100%;padding:0.55rem;background:rgba(255,255,255,0.05);border:1px solid var(--border);color:var(--text);border-radius:0.4rem;" placeholder="Tesla">
      </div>
      <div class="form-group">
        <label class="form-label" style="display:block;margin-bottom:0.3rem;">Model</label>
        <input class="form-input" id="new-veh-model" style="width:100%;padding:0.55rem;background:rgba(255,255,255,0.05);border:1px solid var(--border);color:var(--text);border-radius:0.4rem;" placeholder="Model Y Fleet Spec">
      </div>
      <div class="form-group">
        <label class="form-label" style="display:block;margin-bottom:0.3rem;">Plate Number</label>
        <input class="form-input" id="new-veh-plate" style="width:100%;padding:0.55rem;background:rgba(255,255,255,0.05);border:1px solid var(--border);color:var(--text);border-radius:0.4rem;" placeholder="EV-D011-TN">
      </div>
      <div class="form-group">
        <label class="form-label" style="display:block;margin-bottom:0.3rem;">Battery Capacity (kWh)</label>
        <input class="form-input" type="number" id="new-veh-capacity" style="width:100%;padding:0.55rem;background:rgba(255,255,255,0.05);border:1px solid var(--border);color:var(--text);border-radius:0.4rem;" value="60">
      </div>
      <div class="form-group">
        <label class="form-label" style="display:block;margin-bottom:0.3rem;">Year</label>
        <input class="form-input" type="number" id="new-veh-year" style="width:100%;padding:0.55rem;background:rgba(255,255,255,0.05);border:1px solid var(--border);color:var(--text);border-radius:0.4rem;" value="2024">
      </div>
    </div>
  `;
  showModal("Register New Vehicle", formHtml, "Register EV", addVehicleSubmit);
}

function addVehicleSubmit() {
  const id = document.getElementById('new-veh-id').value.trim();
  const make = document.getElementById('new-veh-make').value.trim();
  const model = document.getElementById('new-veh-model').value.trim();
  const plate_no = document.getElementById('new-veh-plate').value.trim();
  const battery_capacity_kwh = parseFloat(document.getElementById('new-veh-capacity').value);
  const year = parseInt(document.getElementById('new-veh-year').value);
  
  if (!id || !make || !model || !plate_no) {
    showToast("⚠️ All fields are required!", "red");
    return;
  }
  
  const payload = {
    id, make, model, plate_no, battery_capacity_kwh, year
  };
  
  fetch("/api/vehicles", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  })
  .then(res => {
    if (!res.ok) return res.json().then(err => { throw new Error(err.detail || "Failed to register vehicle"); });
    return res.json();
  })
  .then(newVeh => {
    showToast(`✅ Registered ${newVeh.id} successfully!`);
    closeModalDirect();
    
    fetch("/api/vehicles")
      .then(res => res.json())
      .then(data => {
        allVehicles = data;
        initFleetTable();
      });
  })
  .catch(err => {
    showToast(`⚠️ ${err.message}`, "red");
  });
}

function removeVehicle(id){
  const v = allVehicles.find(x => x.id === id);
  if(!v) return;
  showModal(`Remove ${v.id}?`,
    `Are you sure you want to remove vehicle ${v.id} (${v.make} ${v.model})?\\nThis will unlink any driver currently assigned to it.`,
    'Confirm Remove', () => {
      fetch(`/api/vehicles/${v.id}`, { method: "DELETE" })
        .then(res => {
          if (!res.ok) throw new Error("Failed to delete vehicle");
          return res.json();
        })
        .then(() => {
          showToast(`🗑️ Vehicle ${v.id} removed`, 'red');
          closeModalDirect();
          Promise.all([
            fetch("/api/drivers").then(res => res.json()),
            fetch("/api/vehicles").then(res => res.json())
          ]).then(([driversData, vehiclesData]) => {
            allDrivers = driversData;
            allVehicles = vehiclesData;
            initFleetTable();
          });
        })
        .catch(err => {
          showToast(`⚠️ ${err.message}`, 'red');
        });
    });
}

/* ── LAZY NAVIGATION ── */
function navigate(section){
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  
  const secEl = document.getElementById('sec-' + section);
  if (secEl) secEl.classList.add('active');
  const navEl = document.querySelector(`[data-section="${section}"]`);
  if (navEl) navEl.classList.add('active');
  
  if(window.innerWidth <= 680) toggleSidebar();

  if(section === 'fleet') initFleetTable();
  if(section === 'drivers') renderDriverTable(allDrivers, 'drivers-tbody');
  if(section === 'stations') initStationsDetail();
  if(section === 'analytics') initAnalyticsSection();
  if(section === 'alerts') renderAlerts('all-alerts');
  if(section === 'reports') buildBarChart('report-chart', energyVals);
  if(section === 'revenue') initRevenue();
  if(section === 'battery') initBatteryMonitor();
  if(section === 'vehicles') initVehiclePerf();
  if(section === 'charging-analytics') initChargingAnalytics();
  if(section === 'maintenance') initMaintenance();
}

function toggleSidebar(){
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('overlay').classList.toggle('open');
}

/* ── SETTINGS ── */
function saveAdminProfile(){
  const name = document.getElementById('admin-name').value.trim();
  if(name) {
    document.getElementById('sb-admin-name').textContent = name;
    sessionStorage.setItem('ev_display_name', name);
  }
  showToast('✅ Admin profile saved!');
}
function prefToggle(el, label){ showToast(`${el.checked ? '✅' : '🔕'} ${label} ${el.checked ? 'enabled' : 'disabled'}`); }

/* ── MODAL & TOAST & LOGOUT ── */
let modalActionFn = () => {};
function showModal(title, body, actionLabel, actionFn){
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = body.replace(/\n/g, '<br>');
  const btn = document.getElementById('modal-action-btn');
  if(actionLabel && actionFn){ btn.style.display = 'block'; btn.textContent = actionLabel; modalActionFn = actionFn; }
  else{ btn.style.display = 'none'; }
  document.getElementById('modal').classList.add('open');
}
function closeModal(e){ if(e.target === document.getElementById('modal')) closeModalDirect(); }
function closeModalDirect(){ document.getElementById('modal').classList.remove('open'); }

let toastTimer;
function showToast(msg, type = ''){
  const t = document.getElementById('toast');
  t.textContent = msg; t.className = 'toast' + (type ? ' ' + type : '') + ' show';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 2800);
}

function logout(){
  showToast('👋 Signing out…');
  fetch("/api/auth/logout", { method: "POST" })
    .then(() => {
      setTimeout(() => {
        document.body.style.transition = 'opacity .5s';
        document.body.style.opacity = '0';
        setTimeout(() => window.location.href = '/', 500);
      }, 700);
    });
}

/* ── PROFESSIONAL PDF EXPORT ── */
function exportProfessionalReport(sectionIds, filename = 'report.pdf'){
  if(!Array.isArray(sectionIds)) sectionIds = [sectionIds];
  showToast('Preparing professional PDF…');
  const spinner = document.getElementById('pdf-spinner'); if(spinner) spinner.style.display = 'flex';
  const wrapper = document.createElement('div');
  wrapper.style.width = '800px'; wrapper.style.margin = '0 auto'; wrapper.style.background = '#ffffff'; wrapper.style.color = '#222'; wrapper.style.padding = '28px 34px'; wrapper.style.fontFamily = 'Helvetica, Arial, sans-serif'; wrapper.style.lineHeight = '1.4';

  const topbar = document.createElement('div'); topbar.style.display = 'flex'; topbar.style.alignItems = 'center'; topbar.style.justifyContent = 'space-between'; topbar.style.marginBottom = '10px';
  const logoBox = document.createElement('div'); logoBox.innerHTML = `<div style="width:44px;height:44px;border-radius:6px;background:#e6f2ee;display:flex;align-items:center;justify-content:center;font-weight:700;color:#006a4e">T.</div>`;
  const contact = document.createElement('div'); contact.style.fontSize = '11px'; contact.style.color = '#2d6b60'; contact.textContent = 'Devon Rd, Hempstead, NY | yourinfo@emailaddress.com | WWW.TEMPLATE.NET | 222 555 7777';
  topbar.appendChild(logoBox); topbar.appendChild(contact); wrapper.appendChild(topbar);

  const title = document.createElement('div'); title.style.textAlign = 'center'; title.style.margin = '12px 0 18px 0';
  title.innerHTML = `<h1 style="margin:0;font-size:20px;color:#111">Printable Summary Report</h1><div style="font-size:12px;color:#666;margin-top:8px">Prepared by: Admin · Company: EV Fleet Analysis · Date: ${new Date().toLocaleDateString()}</div>`;
  wrapper.appendChild(title);

  const intro = document.createElement('div'); intro.style.marginTop = '12px';
  intro.innerHTML = `<h3 style="font-size:14px;margin-bottom:6px">I. Introduction</h3><div style="font-size:12px;color:#333">This report provides a concise summary of fleet performance, charging activity and revenue trends for the selected period. It is intended for operational review and decision making.</div>`;
  wrapper.appendChild(intro);

  const summaryTitle = document.createElement('h3'); summaryTitle.style.fontSize = '14px'; summaryTitle.style.marginTop = '12px'; summaryTitle.textContent = 'II. Executive Summary'; wrapper.appendChild(summaryTitle);
  const sumRow = document.createElement('div'); sumRow.style.display = 'flex'; sumRow.style.gap = '12px'; sumRow.style.marginTop = '8px';
  const keys = ['r-dist', 'r-energy', 'r-drv', 'r-sess', 'r-batt', 'r-eff'];
  keys.forEach(k => { const el = document.getElementById(k);
    const card = document.createElement('div'); card.style.flex = '1'; card.style.border = '1px solid #eef3f0'; card.style.padding = '10px'; card.style.borderRadius = '6px';
    if(el){ const label = el.previousElementSibling ? el.previousElementSibling.textContent : k; card.innerHTML = `<div style="font-size:11px;color:#666">${label}</div><div style="font-size:18px;font-weight:700;color:#0b2b24;margin-top:6px">${el.textContent}</div>`;} else { card.innerHTML = `<div style="font-size:11px;color:#666">${k}</div><div style="font-size:14px;color:#111;margin-top:6px">N/A</div>` }
    sumRow.appendChild(card);
  }); wrapper.appendChild(sumRow);

  sectionIds.forEach(sid => { const sec = document.getElementById(sid); if(!sec) return; const clone = sec.cloneNode(true);
    clone.querySelectorAll('button,input,select,textarea').forEach(n => n.remove());
    clone.style.background = 'transparent'; clone.style.color = '#111'; clone.style.marginTop = '18px';
    clone.querySelectorAll('.card-title').forEach(t => { t.style.color = '#0b2b24'; t.style.fontSize = '13px'; });
    wrapper.appendChild(clone);
  });

  const ftr = document.createElement('div'); ftr.style.marginTop = '18px'; ftr.style.fontSize = '11px'; ftr.style.color = '#666'; ftr.textContent = 'Report generated by EV Fleet Analysis · Confidential'; wrapper.appendChild(ftr);

  wrapper.style.position = 'fixed'; wrapper.style.left = '-20000px'; document.body.appendChild(wrapper);
  const opt = {scale: 2, useCORS: true, backgroundColor: '#ffffff'};
  html2canvas(wrapper, opt).then(canvas => {
    try {
      const imgData = canvas.toDataURL('image/png');
      const { jsPDF } = window.jspdf || (window.jspdf = {});
      const pdf = new jsPDF('p', 'pt', 'a4');
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = pdf.internal.pageSize.getHeight();
      const imgRatio = canvas.width / canvas.height;
      const imgW = pdfWidth - 40;
      const imgH = imgW / imgRatio;
      const totalPages = Math.ceil(imgH / (pdfHeight - 60));
      let position = 20;
      for(let i = 0; i < totalPages; i++){
        if(i > 0) pdf.addPage();
        const y = position - i * (pdfHeight - 60);
        pdf.addImage(imgData, 'PNG', 20, y, imgW, imgH);
        pdf.setDrawColor(220); pdf.setLineWidth(0.5); pdf.line(20, 18, pdfWidth - 20, 18);
        const pageNum = i + 1; pdf.setFontSize(10); pdf.setTextColor(120); pdf.text(`${pageNum} / ${totalPages}`, pdfWidth - 60, pdfHeight - 20);
      }
      pdf.save(filename);
      showToast('📥 Professional PDF exported!');
    } catch(err) {
      console.error(err);
      showToast('❌ PDF export failed','red');
    }
  }).catch(err=>{ console.error(err); showToast('❌ PDF export failed','red'); })
  .finally(()=>{ wrapper.remove(); if(spinner) spinner.style.display='none'; });
}

function exportSectionToPDF(sectionId, filename='report.pdf'){ exportProfessionalReport([sectionId], filename); }

/* ── DATA POLLING AND SYNC ── */
function loadDashboardData() {
  Promise.all([
    fetch("/api/drivers").then(res => res.json()),
    fetch("/api/vehicles").then(res => res.json()),
    fetch("/api/alerts").then(res => res.json()),
    fetch("/api/telemetry/latest").then(res => res.json()),
    fetch("/api/analytics/summary").then(res => res.json())
  ])
  .then(([driversData, vehiclesData, alertsData, telemetryData, summaryData]) => {
    allDrivers = driversData;
    allVehicles = vehiclesData;
    allAlerts = alertsData;
    telemetryLatest = telemetryData;
    
    // Update summary stats
    document.getElementById('stat-total').textContent = summaryData.total_vehicles;
    document.getElementById('stat-active').textContent = summaryData.active_vehicles;
    document.getElementById('stat-idle').textContent = summaryData.idle_vehicles;
    document.getElementById('stat-charging').textContent = summaryData.charging_vehicles;
    
    // Update donut chart
    updateDonutChart(summaryData.active_vehicles, summaryData.charging_vehicles, summaryData.idle_vehicles);
    
    // Update legends
    document.getElementById('legend-active').textContent = summaryData.active_vehicles;
    document.getElementById('legend-charging').textContent = summaryData.charging_vehicles;
    document.getElementById('legend-idle').textContent = summaryData.idle_vehicles;
    
    // Update alerts count badge
    updateAlertPills();
    
    // Populate vehicle selection for forms
    populateVehicleSelect();

    // Render dashboard components
    renderDriverTable(allDrivers.slice(0, 5), 'dash-driver-table-tbody');
    renderAlerts('dash-alerts');
  })
  .catch(err => {
    console.error("Error loading dashboard data:", err);
  });
}

function pollLatestTelemetry() {
  fetch("/api/telemetry/latest")
    .then(res => res.json())
    .then(telemetryData => {
      telemetryLatest = telemetryData;
      
      let activeCount = 0;
      let chargingCount = 0;
      let idleCount = 0;
      let totalCount = allVehicles.length;
      
      allVehicles.forEach(v => {
        const drv = allDrivers.find(d => d.vehicle_id === v.id);
        const latest = telemetryLatest[drv ? drv.id : ''] || {};
        const statusVal = latest.status || v.status || 'idle';
        
        if (statusVal.toLowerCase() === 'active') activeCount++;
        else if (statusVal.toLowerCase() === 'charging') chargingCount++;
        else idleCount++;
      });
      
      document.getElementById('stat-total').textContent = totalCount;
      document.getElementById('stat-active').textContent = activeCount;
      document.getElementById('stat-idle').textContent = idleCount;
      document.getElementById('stat-charging').textContent = chargingCount;
      
      updateDonutChart(activeCount, chargingCount, idleCount);
      document.getElementById('legend-active').textContent = activeCount;
      document.getElementById('legend-charging').textContent = chargingCount;
      document.getElementById('legend-idle').textContent = idleCount;
      
      fetch("/api/alerts")
        .then(res => res.json())
        .then(alertsData => {
          allAlerts = alertsData;
          updateAlertPills();
          
          const activeSec = document.querySelector('.section.active');
          if (activeSec) {
            const activeId = activeSec.id.replace('sec-', '');
            if (activeId === 'dashboard') {
              renderAlerts('dash-alerts');
            } else if (activeId === 'alerts') {
              renderAlerts('all-alerts');
            } else if (activeId === 'battery') {
              initBatteryMonitor();
            } else if (activeId === 'vehicles') {
              initVehiclePerf();
            } else if (activeId === 'maintenance') {
              initMaintenance();
            }
          }
        });
    })
    .catch(err => {
      console.error("Error polling telemetry:", err);
    });
}

function populateVehicleSelect() {
  const select = document.getElementById('new-vehicle');
  if(!select) return;
  
  select.innerHTML = '<option value="None">None (No EV Assigned)</option>';
  const assignedVehicleIds = allDrivers.map(d => d.vehicle_id).filter(id => id !== null);
  
  allVehicles.forEach(v => {
    const isAssigned = assignedVehicleIds.includes(v.id);
    const opt = document.createElement('option');
    opt.value = v.id;
    opt.textContent = `${v.id} — ${v.make} ${v.model} (${isAssigned ? 'Assigned' : 'Available'})`;
    select.appendChild(opt);
  });
}

/* ── START UP ── */
loadUserSession();
loadDashboardData();
setInterval(pollLatestTelemetry, 3000);

buildBarChart('energy-chart', energyVals);
buildTrendLine();
