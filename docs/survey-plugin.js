/*
 * survey-plugin.js — 北海道の公共測量 (国土地理院「公共測量実施情報」、北海道地方測量部) を
 * tabularmaps/do の 16×16 表形式地図で見せる Open MCT プラグイン。
 *
 * 構成 (dwg7/cafebabe の Open MCT 実地ノウハウに従う):
 *   - objects.addProvider + composition.addProvider + objectViews.addProvider だけを使う。Telemetry API は使わない。
 *   - ルートは独自 type 'dosurvey.root' にして概要ビューだけを紐付ける (既定の Grid View と競合させない)。
 *   - フォルダは組み込みの 'folder'。地図 (リーフ) は独自 type 'dosurvey.map' に tabular map ビューを紐付ける。
 *   - 値は件数だけ (測量が関わった市町村それぞれに 1 件。按分件数は使わない。D11)。
 *
 * ツリー:
 *   北海道の公共測量 (概要: 年度別の件数)
 *     期間を選んで見る (年度の範囲を 2 つのつまみで選ぶ)
 *     年度別 / 各年度 (新しい順)
 *
 * 描画は vendor/do/tabularmap.js (TabularMap.create) をそのまま使う。
 */
window.DoSurveyPlugin = function DoSurveyPlugin(options) {
  'use strict';
  const NS = 'dosurvey';
  const dataUrl = options.dataUrl || './data/';
  const doDataUrl = options.doDataUrl || './vendor/do/data/';

  const SOURCE_NOTE = '出典: 国土地理院ウェブサイト「公共測量実施情報」(https://psgsv4.gsi.go.jp/giaSearch/) を dwg7 が加工して作成';

  // 段階 (順序尺度)。件数の分布が強く偏るので線形ではなく区切りで塗る (D10)。
  // 区切りは選んだ年数 n で伸縮させる: 1 年度 = 0/1/2/5/10/20 を基準に、2 番目以降を n^0.8 倍して有効数字 2 桁に丸める
  // (8 年度 = 0/1/11/26/53/110、44 年度 = 0/1/41/100/210/410)。区切りの比が年数によらず揃う。同じ年数の期間どうしは同じ区切りで比べられる (D11)。
  const BASE = [2, 5, 10, 20];
  // tabularmaps/do の SEQ ランプ (tabularmap.js) から 6 段を採る
  const COLORS = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#1c5cab', '#0d366b'];

  function round2(x) {   // 有効数字 2 桁
    const e = Math.pow(10, Math.max(0, Math.floor(Math.log10(x)) - 1));
    return Math.round(x / e) * e;
  }
  function breaksFor(n) {
    const f = Math.pow(n, 0.8), br = [0, 1];
    for (const b of BASE) {
      const v = round2(b * f);
      if (v > br[br.length - 1]) br.push(v);
    }
    return br;
  }
  function classOf(v, br) {
    let k = 0;
    for (let i = 0; i < br.length; i++) if (v >= br[i]) k = i;
    return k;
  }
  function classLabels(br) {
    const labels = {};
    for (let i = 0; i < br.length; i++) {
      const lo = br[i], hi = br[i + 1];
      labels[String(i)] = hi === undefined ? `${lo} 件以上` : (hi - lo === 1 ? `${lo} 件` : `${lo}–${hi - 1} 件`);
    }
    return labels;
  }
  // 計画機関名などは登録者が自由に書く欄なので、HTML に入れる前に必ずエスケープする
  // (notes は描画コアが innerHTML で表とツールチップに入れる)。
  function esc(v) {
    return String(v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  }
  function rangeName(y0, y1) { return y0 === y1 ? `${y0} 年度` : `${y0}〜${y1} 年度`; }

  const cache = new Map();
  function getJson(url) {
    if (!cache.has(url)) cache.set(url, fetch(url).then((r) => { if (!r.ok) throw new Error(url + ' ' + r.status); return r.json(); }));
    return cache.get(url);
  }
  function loadBase() {
    return Promise.all([
      getJson(doDataUrl + 'layout-v08.json'), getJson(doDataUrl + 'municipalities.json'),
      getJson(doDataUrl + 'sapporo-wards.json'), getJson(dataUrl + 'summary.json'), getJson(dataUrl + 'matrix.json')
    ]).then(([layout, municipalities, wards, summary, matrix]) => ({ layout, municipalities, wards, summary, matrix }));
  }

  // 年度範囲 [y0, y1] の series を作る。値は段階の番号、正確な件数と主な計画機関は notes に入れる。
  function buildSeries(base, y0, y1) {
    const { matrix, summary, municipalities } = base;
    const i0 = matrix.years.indexOf(y0), i1 = matrix.years.indexOf(y1);
    const br = breaksFor(y1 - y0 + 1);
    const values = {}, notes = {}, tips = {};
    for (const m of municipalities.municipalities) {
      if (m.status !== 'active') continue;   // 根室振興局管内の 6 村は照合対象外なので無データのまま
      const row = matrix.involved[m.code] || [];
      let n = 0;
      for (let i = i0; i <= i1; i++) n += row[i] || 0;
      values[m.code] = classOf(n, br);
      const pc = new Map();
      for (const [yi, pi, c] of matrix.plannerCounts[m.code] || []) if (yi >= i0 && yi <= i1) pc.set(pi, (pc.get(pi) || 0) + c);
      const top = [...pc.entries()].sort((a, b) => b[1] - a[1] || a[0] - b[0])
        .map(([pi, c]) => [matrix.planners[pi], c]);   // 全部 (件数の多い順)
      notes[m.code] = `${n} 件` + (top.length ? ' · ' + top.map(([p, c]) => `${esc(p)} ${c}`).join('、') : '');
      tips[m.code] = { name: m.fullName, n, top };
    }
    const surveys = summary.years.filter((y) => y.year >= y0 && y.year <= y1).reduce((a, y) => a + y.surveys, 0);
    const last = summary.years[summary.years.length - 1].year;
    const partial = y1 === last ? ` (${summary.lastReceptDate} 受付分まで)` : '';
    return {
      label: `件数 · ${rangeName(y0, y1)}`,
      unit: '件',
      asOf: `測量 ${surveys.toLocaleString('ja-JP')} 件${partial}`,
      min: 0, max: br.length - 1,
      values, notes, tips,
      scale: { type: 'ordinal', labels: classLabels(br), colors: Object.fromEntries(COLORS.map((c, i) => [String(i), c])) }
    };
  }

  const ABOUT = '件数は、測量が関わった市町村それぞれに 1 件と数えます (複数の市町村にまたがる測量は各市町村に 1 件)。' +
    'セルに触れると件数と計画機関、「表で見る」で一覧。東端の列の 6 村は北方領土の村で、照合の対象外 (無データ)。';

  return function install(openmct) {
    openmct.types.addType('dosurvey.root', { name: '公共測量の概要', description: '北海道の公共測量の概要', creatable: false, cssClass: 'icon-dataset' });
    openmct.types.addType('dosurvey.map', { name: '公共測量 tabular map', description: '市町村ごとの公共測量の件数', creatable: false, cssClass: 'icon-grid-on' });

    const objects = new Map();
    const compositions = new Map();
    const id = (key) => ({ namespace: NS, key });
    function add(key, obj, parentKey) {
      objects.set(key, Object.assign({ identifier: id(key) }, obj, parentKey ? { location: `${NS}:${parentKey}` } : {}));
      if (parentKey) compositions.get(parentKey).push(id(key));
    }

    const ready = getJson(dataUrl + 'summary.json').then((summary) => {
      const last = summary.years[summary.years.length - 1].year;
      add('root', { name: '北海道の公共測量', type: 'dosurvey.root', location: 'ROOT' });
      compositions.set('root', []);
      add('map:range', { name: '期間を選んで見る', type: 'dosurvey.map', dosurvey: { range: true } }, 'root');
      compositions.set('folder:years', []);
      add('folder:years', { name: '年度別', type: 'folder' }, 'root');
      for (const y of summary.years.map((d) => d.year).reverse()) {
        add(`map:year:${y}`, { name: `${y} 年度` + (y === last ? ' (途中)' : ''), type: 'dosurvey.map', dosurvey: { year: y } }, 'folder:years');
      }
    });

    // D10 の版 (関与件数 / 按分件数 × 令和・全期間・各年度) のキーを、今の項目に読み替える (D15)。
    // 共有された URL や Open MCT の「最近見たもの」に残った古いキーでも開けるようにするため。
    function legacy(key) {
      if (key === 'folder:involved' || key === 'folder:apportioned') return { to: 'folder:years' };
      const m = /^map:(?:involved|apportioned):(reiwa|all|\d{4})$/.exec(key);
      if (!m) return null;
      if (m[1] === 'all') return { to: 'map:range' };
      if (m[1] === 'reiwa') return { to: 'map:range', name: '期間を選んで見る (2019 年度〜)', dosurvey: { range: true, from: 2019 } };
      return { to: `map:year:${m[1]}` };
    }
    function resolve(key) {
      const o = objects.get(key);
      if (o) return { obj: o, key };
      const l = legacy(key);
      const target = l && objects.get(l.to);
      if (!target) return null;
      const alias = Object.assign({}, target, { identifier: id(key) }, l.name ? { name: l.name } : {}, l.dosurvey ? { dosurvey: l.dosurvey } : {});
      return { obj: alias, key: l.to };
    }

    openmct.objects.addRoot(id('root'));
    openmct.objects.addProvider(NS, {
      get(identifier) {
        return ready.then(() => {
          const r = resolve(identifier.key);
          if (!r) throw new Error('Unknown object ' + identifier.key);
          return r.obj;
        });
      }
    });
    openmct.composition.addProvider({
      appliesTo: (o) => o.identifier.namespace === NS && (o.type === 'folder' || o.type === 'dosurvey.root'),
      load: (o) => ready.then(() => { const r = resolve(o.identifier.key); return (r && compositions.get(r.key)) || []; })
    });

    // リーフ: tabular map
    openmct.objectViews.addProvider({
      key: 'dosurvey.map.view', name: 'tabular map', cssClass: 'icon-grid-on',
      canView: (o) => o.identifier.namespace === NS && o.type === 'dosurvey.map',
      view(domainObject) {
        let map = null, host = null, disposed = false;
        return {
          show(element) {
            host = document.createElement('div');
            host.className = 'tm-openmct-host ds-host';
            element.appendChild(host);
            loadBase().then((base) => {
              if (disposed) return;
              const years = base.matrix.years;
              const opt = domainObject.dosurvey;
              let y0 = opt.range ? Math.max(years[0], opt.from || years[0]) : opt.year;
              let y1 = opt.range ? years[years.length - 1] : opt.year;
              if (opt.range) host.appendChild(rangeControl(years, y0, (a, b) => { y0 = a; y1 = b; repaint(); }));
              map = window.TabularMap.create(host, {
                layout: base.layout, municipalities: base.municipalities, wards: base.wards,
                mode: 'region', title: domainObject.name, includeNorthernTerritoriesVillages: true
              });
              // 件数は札幌市全体でしか持たない (2001 年度以降の記載は「札幌市」、それ以前の区名も札幌市に読み替える。D6) ので、
              // 10 区に展開すると全区が無データになる。展開のボタンは出さない (D15)。
              const wardsBtn = [...host.querySelectorAll('.tm-btn')].find((b) => b.textContent.includes('10区'));
              if (wardsBtn) wardsBtn.style.display = 'none';
              const svg = host.querySelector('.tm-svg');
              if (svg) {
                svg.setAttribute('aria-label', domainObject.name + ' の表形式地図');
                const title = svg.querySelector('title');
                if (title) title.remove();
              }
              let series = null;
              const repaint = () => { if (!disposed) { series = buildSeries(base, y0, y1); map.setSeries(series); } };
              repaint();
              // マウスオーバーは「件数」と「計画機関」だけにする (D11)。描画コアのツールチップの中身を差し替える。
              host.addEventListener('mousemove', (ev) => {
                const cell = ev.target.closest && ev.target.closest('.tm-cell[data-code]');
                const tip = host.querySelector('.tm-tip');
                const t = cell && series && series.tips[cell.getAttribute('data-code')];
                if (!t || !tip || tip.hidden) return;
                tip.classList.add('ds-tip');
                tip.innerHTML = `<b>${esc(t.name)}</b><span class="tm-tip-val">件数 ${t.n} 件</span>` +
                  (t.top.length ? `<span class="tm-tip-sub">計画機関 (${t.top.length})</span>` +
                    `<ol class="ds-tip-planners${t.top.length > 12 ? ' ds-tip-cols' : ''}">` +
                    t.top.map(([p, c]) => `<li><span>${esc(p)}</span><span>${c}</span></li>`).join('') + '</ol>' : '');
                // 中身を差し替えて大きさが変わったので、描画コアと同じ規則で位置を取り直す
                const r = tip.parentElement.getBoundingClientRect();
                let x = ev.clientX - r.left + 12, y = ev.clientY - r.top + 12;
                if (x + tip.offsetWidth > r.width) x = Math.max(0, ev.clientX - r.left - tip.offsetWidth - 12);
                if (y + tip.offsetHeight > r.height) y = Math.max(0, ev.clientY - r.top - tip.offsetHeight - 12);
                tip.style.left = x + 'px'; tip.style.top = y + 'px';
              });
              const note = document.createElement('div');
              note.className = 'tm-openmct-note';
              note.textContent = ABOUT + SOURCE_NOTE;
              host.appendChild(note);
            }).catch((e) => { if (host) host.textContent = 'データを読めませんでした: ' + e.message; });
          },
          destroy() {
            disposed = true;
            if (map) map.destroy();
            if (host && host.parentNode) host.parentNode.removeChild(host);
          }
        };
      }
    });

    // ルート: 概要 (年度別の件数の棒グラフ)
    openmct.objectViews.addProvider({
      key: 'dosurvey.overview', name: '概要', cssClass: 'icon-dataset',
      canView: (o) => o.identifier.namespace === NS && o.type === 'dosurvey.root',
      view() {
        let host = null;
        return {
          show(element) {
            host = document.createElement('div');
            host.className = 'ds-overview';
            element.appendChild(host);
            getJson(dataUrl + 'summary.json').then((s) => renderOverview(host, s))
              .catch((e) => { host.textContent = 'データを読めませんでした: ' + e.message; });
          },
          destroy() { if (host && host.parentNode) host.parentNode.removeChild(host); }
        };
      }
    });
  };

  // 年度範囲のスライダー (2 つのつまみ)。
  function rangeControl(years, start, onChange) {
    const lo = years[0], hi = years[years.length - 1];
    const wrap = document.createElement('div');
    wrap.className = 'ds-range';
    wrap.innerHTML = `<div class="ds-range-label"><span class="ds-range-v"></span>
        <button type="button" class="ds-range-all">全期間に戻す</button></div>
      <div class="ds-range-track"><div class="ds-range-fill"></div>
        <input type="range" class="ds-range-a" min="${lo}" max="${hi}" step="1" value="${start}" aria-label="開始年度">
        <input type="range" class="ds-range-b" min="${lo}" max="${hi}" step="1" value="${hi}" aria-label="終了年度"></div>
      <div class="ds-range-ends"><span>${lo}</span><span>${hi}</span></div>`;
    const a = wrap.querySelector('.ds-range-a'), b = wrap.querySelector('.ds-range-b');
    const v = wrap.querySelector('.ds-range-v'), fill = wrap.querySelector('.ds-range-fill');
    function update(fromA, notify = true) {
      let x = +a.value, y = +b.value;
      if (x > y) { if (fromA) { y = x; b.value = y; } else { x = y; a.value = x; } }
      v.textContent = x === y ? `${x} 年度 (1 年度)` : `${x}〜${y} 年度 (${y - x + 1} 年度)`;
      fill.style.left = ((x - lo) / (hi - lo) * 100) + '%';
      fill.style.right = ((hi - y) / (hi - lo) * 100) + '%';
      if (notify) onChange(x, y);   // 179 セルの塗り直しは十分軽いので、動かしている間も直接呼ぶ
    }
    a.addEventListener('input', () => update(true));
    b.addEventListener('input', () => update(false));
    wrap.querySelector('.ds-range-all').addEventListener('click', () => { a.value = lo; b.value = hi; update(true); });
    update(true, false);   // 初期表示は呼び出し側が描く
    return wrap;
  }

  function renderOverview(host, s) {
    const total = s.years.reduce((a, y) => a + y.surveys, 0);
    const withRegion = s.years.reduce((a, y) => a + y.withRegion, 0);
    host.innerHTML = `
      <h2 class="ds-h">北海道の公共測量 <span class="ds-sub">${s.section}</span></h2>
      <div class="ds-tiles">
        <div class="ds-tile"><div class="ds-tile-v">${total.toLocaleString('ja-JP')}</div><div class="ds-tile-k">全期間の測量件数 (${s.years[0].year}〜${s.years[s.years.length - 1].year} 年度)</div></div>
        <div class="ds-tile"><div class="ds-tile-v">${withRegion.toLocaleString('ja-JP')}</div><div class="ds-tile-k">うち実施地域図のある測量 (2004 年度〜)</div></div>
        <div class="ds-tile"><div class="ds-tile-v">${s.lastReceptDate}</div><div class="ds-tile-k">最新の受付日 (取得 ${s.fetchedAt.slice(0, 10)})</div></div>
      </div>
      <div class="ds-chart-title">受付年度ごとの測量件数</div>
      <div class="ds-chart"></div>
      <p class="ds-text">左のツリーの「期間を選んで見る」で年度の範囲を選ぶか、「年度別」から年度を選ぶと、市町村ごとの件数で 16×16 の表形式地図
        (<a href="https://github.com/tabularmaps/do" target="_blank" rel="noopener">tabularmaps/do</a>) が塗られます。
        受付年度は 4 月〜翌 3 月。合併前の旧町村名・札幌市の区名は現在の市町村に読み替えています
        (<a href="https://github.com/dwg7/do-survey/blob/main/SCHEMA.md" target="_blank" rel="noopener">読み替え表</a>)。
        実施地域図は 2004 年度以降の測量にあります。</p>
      <p class="ds-credit">出典: 国土地理院ウェブサイト「公共測量実施情報」
        (<a href="${s.sourceUrl}" target="_blank" rel="noopener">${s.sourceUrl}</a>)。
        このダッシュボードとデータ (<a href="https://github.com/dwg7/do-survey" target="_blank" rel="noopener">dwg7/do-survey</a>) は
        dwg7 がこれを編集・加工して作成したもので、国土地理院が作成したものではありません。</p>`;
    drawBars(host.querySelector('.ds-chart'), s);
  }

  // 1 系列の縦棒。
  function drawBars(el, s) {
    const W = 760, H = 240, m = { l: 40, r: 8, t: 18, b: 26 };
    const ys = s.years, n = ys.length;
    const max = Math.max(...ys.map((y) => y.surveys));
    const top = Math.ceil(max / 200) * 200;
    const bw = (W - m.l - m.r) / n;
    const x = (i) => m.l + i * bw;
    const y = (v) => m.t + (H - m.t - m.b) * (1 - v / top);
    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.setAttribute('class', 'ds-svg');
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', '受付年度ごとの測量件数');
    const mk = (tag, attrs, parent) => { const e = document.createElementNS(ns, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); (parent || svg).appendChild(e); return e; };
    for (let v = 0; v <= top; v += 200) {
      mk('line', { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), class: v === 0 ? 'ds-base' : 'ds-grid' });
      mk('text', { x: m.l - 6, y: y(v) + 4, class: 'ds-axis', 'text-anchor': 'end' }).textContent = v;
    }
    const tip = document.createElement('div');
    tip.className = 'ds-tip';
    tip.hidden = true;
    ys.forEach((d, i) => {
      const bx = x(i) + 1, w = Math.max(1, bw - 2), h = H - m.b - y(d.surveys);
      const g = mk('g', { class: 'ds-bar' });
      if (h > 0) {
        const r = Math.min(4, w / 2, h);
        mk('path', { d: `M${bx},${H - m.b}V${y(d.surveys) + r}q0,-${r} ${r},-${r}h${w - 2 * r}q${r},0 ${r},${r}V${H - m.b}Z`, class: 'ds-bar-fill' }, g);
      }
      mk('rect', { x: x(i), y: m.t, width: bw, height: H - m.t - m.b, fill: 'transparent' }, g);   // 棒より広い当たり判定
      if (d.year % 5 === 0) mk('text', { x: x(i) + bw / 2, y: H - 8, class: 'ds-axis', 'text-anchor': 'middle' }).textContent = d.year;
      g.addEventListener('mouseenter', () => {
        tip.innerHTML = `<b>${d.year} 年度</b> ${d.surveys.toLocaleString('ja-JP')} 件<br><span>実施地域図あり ${d.withRegion.toLocaleString('ja-JP')} 件</span>`;
        tip.hidden = false;
        const bb = el.getBoundingClientRect(), sc = bb.width / W;
        tip.style.left = Math.min(bb.width - 170, (x(i) + bw) * sc + 6) + 'px';
        tip.style.top = Math.max(0, y(d.surveys) * sc - 10) + 'px';
        g.classList.add('ds-hover');
      });
      g.addEventListener('mouseleave', () => { tip.hidden = true; g.classList.remove('ds-hover'); });
    });
    el.appendChild(svg);
    el.appendChild(tip);
    // 表でも見られるように (色だけに頼らない)
    const det = document.createElement('details');
    det.className = 'ds-table';
    det.innerHTML = '<summary>表で見る</summary><table><thead><tr><th>受付年度</th><th>測量件数</th><th>実施地域図あり</th></tr></thead><tbody>' +
      ys.slice().reverse().map((d) => `<tr><td>${d.year}</td><td class="tm-num">${d.surveys}</td><td class="tm-num">${d.withRegion}</td></tr>`).join('') +
      '</tbody></table>';
    el.appendChild(det);
  }
};
