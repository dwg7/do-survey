/*
 * survey-plugin.js — 北海道の公共測量 (国土地理院「公共測量実施情報」、北海道地方測量部) を
 * tabularmaps/do の 16×16 表形式地図で見せる Open MCT プラグイン。
 *
 * 構成 (dwg7/cafebabe の Open MCT 実地ノウハウに従う):
 *   - objects.addProvider + composition.addProvider + objectViews.addProvider だけを使う。Telemetry API は使わない。
 *   - ルートは独自 type 'dosurvey.root' にして概要ビューだけを紐付ける (既定の Grid View と競合させない)。
 *   - フォルダは組み込みの 'folder'。指標 (リーフ) は独自 type 'dosurvey.map' に tabular map ビューを紐付ける。
 *   - 年度は 1 リーフ = 1 年度 (切替 UI を作らず、ツリーを選択 UI として使う)。
 *
 * ツリー:
 *   北海道の公共測量 (概要: 年度別の件数)
 *     関与件数 / 按分件数
 *       令和 (2019〜) / 全期間 / 各年度 (新しい順)
 *
 * 描画は vendor/do/tabularmap.js (TabularMap.create) をそのまま使う。
 */
window.DoSurveyPlugin = function DoSurveyPlugin(options) {
  'use strict';
  const NS = 'dosurvey';
  const dataUrl = options.dataUrl || './data/';
  const doDataUrl = options.doDataUrl || './vendor/do/data/';

  const SOURCE_NOTE = '出典: 国土地理院ウェブサイト「公共測量実施情報」(https://psgsv4.gsi.go.jp/giaSearch/) を dwg7 が加工して作成';

  // 段階 (順序尺度)。件数の分布が強く偏るので線形ではなく固定の区切りで塗る (DECISIONS.md D10)。
  // 期間の長さで区切りを変えるが、同じ長さの期間どうし (年度どうし) は同じ区切りで比べられる。
  const BREAKS = {
    year: [0, 1, 2, 5, 10, 20],
    reiwa: [0, 1, 10, 25, 50, 100],
    all: [0, 1, 50, 100, 200, 400]
  };
  // tabularmaps/do の SEQ ランプ (tabularmap.js) から 6 段を採る
  const COLORS = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#1c5cab', '#0d366b'];

  const MEASURES = [
    { key: 'involved', name: '関与件数', label: '関与件数',
      about: '測量が関与した市町村それぞれに 1 件と数える (複数の市町村にまたがる測量は各市町村に 1 件)' },
    { key: 'apportioned', name: '按分件数', label: '按分件数',
      about: '1 件を関与した市町村の数で等分して数える (道全体の合計が測量件数と一致する)' }
  ];

  function breaksFor(key) { return key === 'reiwa' ? BREAKS.reiwa : key === 'all' ? BREAKS.all : BREAKS.year; }
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
  function fmtNum(v) { return Number.isInteger(v) ? String(v) : v.toFixed(1); }
  function periodName(key, meta) {
    if (key === 'reiwa') return `令和 (${meta.from}〜${meta.to} 年度)`;
    if (key === 'all') return `全期間 (${meta.from}〜${meta.to} 年度)`;
    return `${key} 年度`;
  }

  const cache = new Map();
  function getJson(url) {
    if (!cache.has(url)) cache.set(url, fetch(url).then((r) => { if (!r.ok) throw new Error(url + ' ' + r.status); return r.json(); }));
    return cache.get(url);
  }
  function loadBase() {
    return Promise.all([
      getJson(doDataUrl + 'layout-v08.json'), getJson(doDataUrl + 'municipalities.json'),
      getJson(doDataUrl + 'sapporo-wards.json'), getJson(dataUrl + 'summary.json')
    ]).then(([layout, municipalities, wards, summary]) => ({ layout, municipalities, wards, summary }));
  }

  // 1 リーフ分の series を作る。値は段階の番号、正確な件数と主な計画機関は notes に入れる。
  async function buildSeries(measure, key, summary, municipalities) {
    const d = await getJson(`${dataUrl}series/${key}.json`);
    const br = breaksFor(key);
    const values = {}, notes = {};
    const current = summary.years[summary.years.length - 1].year;
    for (const m of municipalities.municipalities) {
      if (m.status !== 'active') continue;   // 根室振興局管内の 6 村は照合対象外なので無データのまま
      const inv = d.involved[m.code] || 0, app = d.apportioned[m.code] || 0;
      const v = measure.key === 'involved' ? inv : app;
      values[m.code] = classOf(v, br);
      const top = (d.topPlanners[m.code] || []).map(([p, n]) => `${p} ${n}`).join('、');
      notes[m.code] = `関与 ${inv} 件 · 按分 ${fmtNum(app)} 件` + (top ? ` · 主な計画機関: ${top}` : '');
    }
    const partial = d.to === current ? ` (${summary.lastReceptDate} 受付分まで)` : '';
    return {
      label: `${measure.label} · ${periodName(key, d)}`,
      unit: '件',
      asOf: `測量 ${d.surveys.toLocaleString('ja-JP')} 件${partial}`,
      min: 0, max: br.length - 1,
      values, notes,
      scale: { type: 'ordinal', labels: classLabels(br), colors: Object.fromEntries(COLORS.map((c, i) => [String(i), c])) }
    };
  }

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
      add('root', { name: '北海道の公共測量', type: 'dosurvey.root', location: 'ROOT' });
      compositions.set('root', []);
      const keys = ['reiwa', 'all', ...summary.years.map((y) => String(y.year)).reverse()];
      for (const m of MEASURES) {
        const fk = 'folder:' + m.key;
        compositions.set(fk, []);
        add(fk, { name: m.name, type: 'folder' }, 'root');
        for (const k of keys) {
          const meta = summary.keys[k];
          add(`map:${m.key}:${k}`, { name: periodName(k, meta) + (k === String(summary.years[summary.years.length - 1].year) ? ' (途中)' : ''),
                                     type: 'dosurvey.map', dosurvey: { measure: m.key, key: k } }, fk);
        }
      }
    });

    openmct.objects.addRoot(id('root'));
    openmct.objects.addProvider(NS, {
      get(identifier) {
        return ready.then(() => {
          const o = objects.get(identifier.key);
          if (!o) throw new Error('Unknown object ' + identifier.key);
          return o;
        });
      }
    });
    openmct.composition.addProvider({
      appliesTo: (o) => o.identifier.namespace === NS && (o.type === 'folder' || o.type === 'dosurvey.root'),
      load: (o) => ready.then(() => compositions.get(o.identifier.key) || [])
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
            loadBase().then(async (base) => {
              if (disposed) return;
              const measure = MEASURES.find((m) => m.key === domainObject.dosurvey.measure);
              map = window.TabularMap.create(host, {
                layout: base.layout, municipalities: base.municipalities, wards: base.wards,
                mode: 'region', title: domainObject.name, includeNorthernTerritoriesVillages: true
              });
              const series = await buildSeries(measure, domainObject.dosurvey.key, base.summary, base.municipalities);
              if (disposed) return;
              map.setSeries(series);
              const note = document.createElement('div');
              note.className = 'tm-openmct-note';
              note.textContent = `${measure.about}。セルに触れると正確な件数と主な計画機関が出ます。「表で見る」で一覧。` +
                `東端の列の 6 村は北方領土の村で、照合の対象外 (無データ)。${SOURCE_NOTE}`;
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

  function renderOverview(host, s) {
    const total = s.years.reduce((a, y) => a + y.surveys, 0);
    const reiwa = s.years.filter((y) => y.year >= s.reiwaFirstYear).reduce((a, y) => a + y.surveys, 0);
    host.innerHTML = `
      <h2 class="ds-h">北海道の公共測量 <span class="ds-sub">${s.section}</span></h2>
      <div class="ds-tiles">
        <div class="ds-tile"><div class="ds-tile-v">${total.toLocaleString('ja-JP')}</div><div class="ds-tile-k">全期間の測量件数 (${s.years[0].year}〜${s.years[s.years.length - 1].year} 年度)</div></div>
        <div class="ds-tile"><div class="ds-tile-v">${reiwa.toLocaleString('ja-JP')}</div><div class="ds-tile-k">令和 (${s.reiwaFirstYear} 年度〜) の測量件数</div></div>
        <div class="ds-tile"><div class="ds-tile-v">${s.lastReceptDate}</div><div class="ds-tile-k">最新の受付日 (取得 ${s.fetchedAt.slice(0, 10)})</div></div>
      </div>
      <div class="ds-chart-title">受付年度ごとの測量件数</div>
      <div class="ds-chart"></div>
      <p class="ds-text">左のツリーの「関与件数」「按分件数」から期間を選ぶと、市町村ごとの件数で 16×16 の表形式地図
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

  // 1 系列の縦棒。令和の期間は背景の帯とラベルで示す (色で系列を分けない)。
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
    const ri = ys.findIndex((d) => d.year >= s.reiwaFirstYear);
    if (ri >= 0) {
      mk('rect', { x: x(ri), y: m.t - 14, width: W - m.r - x(ri), height: H - m.b - m.t + 14, class: 'ds-band' });
      mk('text', { x: x(ri) + 4, y: m.t - 4, class: 'ds-band-label' }).textContent = '令和';
    }
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
