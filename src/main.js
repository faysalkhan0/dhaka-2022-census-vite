import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import './style.css';

const TOKEN = import.meta.env.VITE_MAPBOX_TOKEN;
const DATA = `${import.meta.env.BASE_URL}data`;

const PALETTE = [
  '#087f5b', '#2ca25f', '#a6d854', '#fee08b',
  '#fdae61', '#f46d43', '#d73027', '#7b3294'
];

const DEFAULT_METRIC = 'c_01_population_including_floating_population_total';
const POPULATION = 'c_01_population_including_floating_population_total';
const MALE = 'c_01_male';
const FEMALE = 'c_01_female';
const SEX_RATIO = 'c_01_sex_ratio';

const state = {
  map: null,
  indicators: [],
  censusCache: new Map(),
  geometryCache: new Map(),
  currentParent: null,
  currentFeatures: [],
  currentLevelLabel: 'District',
  selected: null,
  metric: DEFAULT_METRIC,
  mapMode: 'choropleth',
  basemap: 'satellite',
  hover: null,
  sidebarOpen: false,
  loading: true,
  error: null,
};

const app = document.querySelector('#app');

app.innerHTML = `
  <div class="app-shell">
    <div id="map" class="map"></div>

    <header class="topbar glass">
      <div>
        <div class="eyebrow">BBS • Population & Housing Census 2022</div>
        <h1>Dhaka Census Explorer</h1>
      </div>
      <div class="top-actions">
        <button id="backBtn" class="control-btn" disabled>← Back</button>
        <button id="indicatorBtn" class="control-btn">Indicators</button>
      </div>
    </header>

    <div id="indicatorPanel" class="indicator-panel glass hidden"></div>

    <div class="map-controls glass">
      <div class="control-label">Map</div>
      <button class="seg active" data-mapmode="choropleth">Census</button>
      <button class="seg" data-mapmode="boundaries">Boundaries only</button>
      <div class="rule"></div>
      <div class="control-label">Basemap</div>
      <button class="seg active" data-base="satellite">Satellite</button>
      <button class="seg" data-base="dark">Dark</button>
    </div>

    <div id="breadcrumbs" class="breadcrumbs glass"></div>
    <div id="legend" class="legend glass"></div>
    <div id="hoverCard" class="hover-card glass hidden"></div>
    <aside id="sidebar" class="sidebar glass hidden"></aside>
    <div id="loading" class="loading glass">Loading census map…</div>
    <div id="error" class="error glass hidden"></div>
  </div>
`;

const els = {
  back: document.querySelector('#backBtn'),
  indicatorBtn: document.querySelector('#indicatorBtn'),
  indicatorPanel: document.querySelector('#indicatorPanel'),
  breadcrumbs: document.querySelector('#breadcrumbs'),
  legend: document.querySelector('#legend'),
  hoverCard: document.querySelector('#hoverCard'),
  sidebar: document.querySelector('#sidebar'),
  loading: document.querySelector('#loading'),
  error: document.querySelector('#error'),
};

function fmt(value, type='number') {
  if (value === null || value === undefined || value === '' || value === '-') return 'N/A';
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  if (type === 'percent') return `${n.toLocaleString(undefined, { maximumFractionDigits: 2 })}%`;
  if (type === 'decimal') return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function flattenIndicators() {
  return state.indicators.flatMap(table => table.groups.flatMap(group => group.fields.map(field => ({
    ...field, tableCode: table.code, tableTitle: table.title, groupTitle: group.title
  }))));
}

function indicatorByField(field) {
  return flattenIndicators().find(x => x.field === field);
}

function tableForField(field) {
  return state.indicators.find(table => table.groups.some(group => group.fields.some(f => f.field === field)));
}

async function fetchJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Could not load ${path} (${res.status})`);
  return res.json();
}

async function loadIndicators() {
  state.indicators = await fetchJSON(`${DATA}/indicators.json`);
}

async function loadGeometry(type) {
  if (!state.geometryCache.has(type)) {
    state.geometryCache.set(type, fetchJSON(`${DATA}/geojson/${type}.geojson`));
  }
  return state.geometryCache.get(type);
}

async function loadCensus(type) {
  if (!state.censusCache.has(type)) {
    const p = fetchJSON(`${DATA}/census/${type}.json`).then(rows => {
      const m = new Map();
      rows.forEach(row => m.set(row.id, row.values));
      return m;
    });
    state.censusCache.set(type, p);
  }
  return state.censusCache.get(type);
}

function childrenTypes(parent) {
  if (!parent) return ['district'];
  switch (parent.properties.admin_type) {
    case 'district': return ['city_corporation', 'upazila'];
    case 'city_corporation': return ['city_ward'];
    case 'upazila': return ['paurashava', 'union'];
    case 'paurashava': return ['paurashava_ward'];
    case 'city_ward': return ['mauza', 'village'];
    case 'union': return ['mauza', 'village'];
    case 'paurashava_ward': return ['mauza', 'village'];
    default: return [];
  }
}

function typeLabel(type) {
  return ({
    district: 'District', city_corporation: 'City Corporation', city_ward: 'City Ward',
    upazila: 'Upazila', paurashava: 'Paurashava', paurashava_ward: 'Paurashava Ward',
    union: 'Union', mauza: 'Mauza', village: 'Village'
  })[type] || type;
}

function displayName(feature) {
  const p = feature.properties || {};
  const census = state.censusCache.get(p.admin_type);
  return p.location_label || p.admin_label || p.matched_key;
}

async function buildFeatures(parent) {
  const types = childrenTypes(parent);
  const sets = await Promise.all(types.map(async type => {
    const [geo, census] = await Promise.all([loadGeometry(type), loadCensus(type)]);
    return geo.features.filter(f => {
      if (!f.geometry) return false;
      if (!parent) return true;
      return f.properties.navigation_parent_key === parent.properties.matched_key;
    }).map(f => ({ ...f, properties: { ...f.properties, ...(census.get(f.properties.matched_key) || {}) } }));
  }));
  return sets.flat();
}

function metricValue(feature) {
  const v = feature.properties?.[state.metric];
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function colorFor(value, values) {
  if (state.mapMode === 'boundaries') return 'rgba(0,0,0,0)';
  if (value === null || !values.length) return 'rgba(130,130,130,.35)';
  const sorted = [...values].sort((a,b)=>a-b);
  let rank = sorted.findIndex(v => v >= value);
  if (rank < 0) rank = sorted.length - 1;
  const q = sorted.length <= 1 ? 0 : rank / (sorted.length - 1);
  const idx = Math.min(PALETTE.length - 1, Math.floor(q * PALETTE.length));
  return PALETTE[idx];
}

function renderIndicatorPanel() {
  els.indicatorPanel.innerHTML = `
    <div class="panel-head"><strong>Indicators</strong><button id="closeIndicators">×</button></div>
    <div class="indicator-note">Select a census measure to color the map. Labels follow the original Dhaka 2022 census tables.</div>
    ${state.indicators.map(table => `
      <section class="indicator-table">
        <button class="table-title" data-table="${table.code}">${table.title}</button>
        <div class="table-groups">
          ${table.groups.map(group => `
            <div class="indicator-group">
              <div class="group-title">${group.title}</div>
              ${group.fields.map(field => `
                <button class="indicator-item ${field.field === state.metric ? 'selected' : ''}" data-field="${field.field}">
                  <span>${field.label}</span><span class="radio">${field.field === state.metric ? '●' : '○'}</span>
                </button>
              `).join('')}
            </div>
          `).join('')}
        </div>
      </section>
    `).join('')}
  `;
  document.querySelector('#closeIndicators').onclick = () => els.indicatorPanel.classList.add('hidden');
  document.querySelectorAll('.indicator-item').forEach(btn => btn.onclick = async () => {
    state.metric = btn.dataset.field;
    els.indicatorPanel.classList.add('hidden');
    state.selected = state.selected ? { ...state.selected, properties: { ...state.selected.properties } } : null;
    renderAll();
    updateMapPaint();
  });
}

function renderLegend() {
  const ind = indicatorByField(state.metric);
  els.legend.innerHTML = `
    <div class="legend-title">${ind?.label || 'Indicator'}</div>
    <div class="legend-gradient"></div>
    <div class="legend-range"><span>Lower</span><span>Higher</span></div>
  `;
  els.legend.classList.toggle('hidden', state.mapMode === 'boundaries');
}

function renderBreadcrumbs() {
  const chain = [];
  let p = state.currentParent;
  while (p) { chain.unshift(p); p = p.__parent; }
  els.breadcrumbs.innerHTML = chain.length
    ? chain.map((f, i) => `<button data-crumb="${i}">${displayName(f)}</button>`).join('<span>›</span>')
    : '<span>Dhaka</span>';
  els.breadcrumbs.querySelectorAll('[data-crumb]').forEach(btn => btn.onclick = () => {
    const i = Number(btn.dataset.crumb);
    const target = chain[i];
    navigateTo(target);
  });
}

function renderSidebar() {
  if (!state.sidebarOpen || !state.selected) {
    els.sidebar.classList.add('hidden');
    return;
  }
  const p = state.selected.properties || {};
  const ind = indicatorByField(state.metric);
  const table = state.indicators;
  els.sidebar.classList.remove('hidden');
  els.sidebar.innerHTML = `
    <div class="sidebar-head">
      <div>
        <div class="eyebrow">${typeLabel(p.admin_type)}</div>
        <h2>${displayName(state.selected)}</h2>
      </div>
      <button id="closeSidebar">×</button>
    </div>
    <div class="selected-highlight">
      <span>${ind?.label || 'Selected indicator'}</span>
      <strong>${fmt(p[state.metric], ind?.type)}</strong>
    </div>
    ${childrenTypes(state.selected).length ? '<button id="exploreBtn" class="explore-btn">Explore this area →</button>' : ''}
    <div class="sidebar-scroll">
      ${table.map(t => `
        <section class="data-table-section">
          <h3>${t.title}</h3>
          ${t.groups.map(g => `
            <div class="data-group">
              <div class="data-group-title">${g.title}</div>
              ${g.fields.map(f => `
                <div class="info-row"><span>${f.label}</span><strong>${fmt(p[f.field], f.type)}</strong></div>
              `).join('')}
            </div>
          `).join('')}
        </section>
      `).join('')}
    </div>
  `;
  document.querySelector('#closeSidebar').onclick = () => { state.sidebarOpen = false; state.selected = null; renderAll(); };
  const explore = document.querySelector('#exploreBtn');
  if (explore) explore.onclick = () => navigateTo(state.selected);
}

function renderHover() {
  if (!state.hover) { els.hoverCard.classList.add('hidden'); return; }
  const p = state.hover.properties || {};
  const ind = indicatorByField(state.metric);
  const rows = [
    [ind?.label || 'Indicator', fmt(p[state.metric], ind?.type)],
    ['Population', fmt(p[POPULATION], 'number')],
    ['Sex ratio', fmt(p[SEX_RATIO], 'decimal')],
  ];
  els.hoverCard.innerHTML = `<div class="hover-title">${displayName(state.hover)}</div>${rows.map(r => `<div class="hover-row"><span>${r[0]}</span><strong>${r[1]}</strong></div>`).join('')}`;
  els.hoverCard.style.left = `${Math.min(window.innerWidth - 290, state.hoverX + 16)}px`;
  els.hoverCard.style.top = `${Math.min(window.innerHeight - 150, state.hoverY + 16)}px`;
  els.hoverCard.classList.remove('hidden');
}

function renderAll() {
  renderIndicatorPanel();
  renderLegend();
  renderBreadcrumbs();
  renderSidebar();
  renderHover();
  els.back.disabled = !state.currentParent;
}

function updateMapPaint() {
  if (!state.map || !state.map.getLayer('census-fill')) return;
  const values = state.currentFeatures.map(metricValue).filter(v => v !== null);
  const expr = ['case'];
  state.currentFeatures.forEach(f => {
    const v = metricValue(f);
    expr.push(['==', ['get','matched_key'], f.properties.matched_key], colorFor(v, values));
  });
  expr.push('rgba(130,130,130,.35)');
  state.map.setPaintProperty('census-fill', 'fill-color', expr);
  state.map.setPaintProperty('census-fill', 'fill-opacity', state.mapMode === 'boundaries' ? 0 : 0.82);
  state.map.setPaintProperty('census-outline', 'line-color', state.mapMode === 'boundaries' ? '#ffffff' : 'rgba(255,255,255,.72)');
  state.map.setPaintProperty('census-outline', 'line-width', state.mapMode === 'boundaries' ? 1.4 : 1.0);
}

function installLayers() {
  if (!state.map.getSource('census')) {
    state.map.addSource('census', { type: 'geojson', promoteId: 'matched_key', data: { type:'FeatureCollection', features:[] } });
  }
  if (!state.map.getLayer('census-fill')) {
    state.map.addLayer({ id:'census-fill', type:'fill', source:'census', paint:{ 'fill-color': '#2ca25f', 'fill-opacity': .82 } });
    state.map.addLayer({ id:'census-outline', type:'line', source:'census', paint:{ 'line-color':'rgba(255,255,255,.72)', 'line-width':1 } });
    state.map.addLayer({ id:'census-hover', type:'line', source:'census', paint:{ 'line-color':'#ffffff', 'line-width':2.4, 'line-opacity':['case',['boolean',['feature-state','hover'],false],1,0] } });
    state.map.on('mousemove','census-fill', e => {
      state.map.getCanvas().style.cursor = 'pointer';
      const f = e.features?.[0];
      if (!f) return;
      if (state.hover?.properties?.matched_key !== f.properties.matched_key) {
        if (state.hover) state.map.setFeatureState({source:'census',id:state.hover.properties.matched_key}, {hover:false});
        state.hover = f;
        state.hoverX = e.point.x;
        state.hoverY = e.point.y;
        state.map.setFeatureState({source:'census',id:f.properties.matched_key}, {hover:true});
        renderHover();
      } else { state.hoverX=e.point.x; state.hoverY=e.point.y; renderHover(); }
    });
    state.map.on('mouseleave','census-fill', () => {
      state.map.getCanvas().style.cursor = '';
      if (state.hover) state.map.setFeatureState({source:'census',id:state.hover.properties.matched_key}, {hover:false});
      state.hover = null; renderHover();
    });
    state.map.on('click','census-fill', e => {
      const f=e.features?.[0]; if (!f) return;
      state.selected = state.currentFeatures.find(x=>x.properties.matched_key===f.properties.matched_key) || f;
      state.sidebarOpen = true;
      renderSidebar();
    });
  }
}

async function showFeatures(parent) {
  state.loading = true;
  els.loading.classList.remove('hidden');
  try {
    const features = await buildFeatures(parent);
    features.forEach(f => { f.__parent = parent || null; });
    state.currentFeatures = features;
    state.currentParent = parent;
    state.selected = null;
    state.sidebarOpen = false;
    state.hover = null;
    state.map.getSource('census').setData({ type:'FeatureCollection', features });
    updateMapPaint();
    renderAll();
    if (parent) fitFeature(parent);
  } catch (err) {
    showError(err);
  } finally {
    state.loading = false;
    els.loading.classList.add('hidden');
  }
}

function fitFeature(feature) {
  if (!feature?.geometry) return;
  const coords=[];
  const walk=x=>Array.isArray(x[0]) ? x.forEach(walk) : coords.push(x);
  walk(feature.geometry.coordinates);
  if (!coords.length) return;
  const b=new mapboxgl.LngLatBounds(coords[0],coords[0]);
  coords.forEach(c=>b.extend(c));
  state.map.fitBounds(b,{padding:{top:110,bottom:60,left:60,right:state.sidebarOpen?420:60},duration:650,maxZoom:12.5});
}

async function navigateTo(parent) {
  if (!parent) { await showFeatures(null); return; }
  await showFeatures(parent);
}

function setupMap() {
  if (!TOKEN || !TOKEN.startsWith('pk.')) {
    showError(new Error('Mapbox token missing. Create .env.local and set VITE_MAPBOX_TOKEN=your_public_token.'));
    return;
  }
  mapboxgl.accessToken = TOKEN;
  state.map = new mapboxgl.Map({
    container:'map',
    style:'mapbox://styles/mapbox/satellite-streets-v12',
    center:[90.4125,23.685], zoom:8.7, pitch:0, bearing:0,
    attributionControl:true, preserveDrawingBuffer:false
  });
  state.map.addControl(new mapboxgl.NavigationControl({showCompass:false}), 'bottom-right');
  state.map.addControl(new mapboxgl.ScaleControl({maxWidth:120,unit:'metric'}), 'bottom-left');
  state.map.on('load', async () => {
    installLayers();
    await showFeatures(null);
  });
}

function setBasemap(name) {
  state.basemap=name;
  const style = name==='satellite' ? 'mapbox://styles/mapbox/satellite-streets-v12' : 'mapbox://styles/mapbox/dark-v11';
  state.map.setStyle(style);
  state.map.once('style.load', () => { installLayers(); state.map.getSource('census').setData({type:'FeatureCollection',features:state.currentFeatures}); updateMapPaint(); });
  document.querySelectorAll('[data-base]').forEach(b=>b.classList.toggle('active',b.dataset.base===name));
}

function showError(err) {
  console.error(err);
  els.error.textContent=err.message || String(err);
  els.error.classList.remove('hidden');
}

els.indicatorBtn.onclick=()=>els.indicatorPanel.classList.toggle('hidden');
els.back.onclick=()=>{
  if (!state.currentParent) return;
  const parent = state.currentParent.__parent;
  navigateTo(parent || null);
};
document.querySelectorAll('[data-mapmode]').forEach(b=>b.onclick=()=>{
  state.mapMode=b.dataset.mapmode;
  document.querySelectorAll('[data-mapmode]').forEach(x=>x.classList.toggle('active',x.dataset.mapmode===state.mapMode));
  renderLegend(); updateMapPaint();
});
document.querySelectorAll('[data-base]').forEach(b=>b.onclick=()=>setBasemap(b.dataset.base));

(async function init(){
  try {
    await loadIndicators();
    renderAll();
    setupMap();
  } catch(err) { showError(err); els.loading.classList.add('hidden'); }
})();
