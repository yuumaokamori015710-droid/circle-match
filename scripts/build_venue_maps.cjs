// Build-time only: public boundary data becomes small, server-renderable SVG paths.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const upstream = 'https://raw.githubusercontent.com/smartnews-smri/japan-topography/main/data/municipality/topojson/';
async function read(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${response.status}: ${url}`);
  return response.text();
}
(async () => {
  const context = vm.createContext({});
  vm.runInContext(await read('https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js'), context);
  vm.runInContext(await read('https://cdn.jsdelivr.net/npm/topojson-client@3.1.0/dist/topojson-client.min.js'), context);
  const {d3, topojson} = context;
  const sources = [];
  async function features(file) {
    const url = upstream + file, text = await read(url), data = JSON.parse(text);
    sources.push({url, sha256:crypto.createHash('sha256').update(text).digest('hex')});
    return topojson.feature(data, Object.values(data.objects)[0]).features;
  }
  const prefectures = await features('s0001/prefectures.json');
  const municipalities = (await features('s0010/N03-21_13_210101.json')).filter(f=>f.properties.N03_004 !== '所属未定地');
  const name = f => f.properties.N03_004 || f.properties.N03_001;
  const area = f => name(f).endsWith('区') ? '23区' : /(?:大島町|利島村|新島村|神津島村|三宅村|御蔵島村|八丈町|青ヶ島村|小笠原村)/.test(name(f)) ? '島しょ' : '多摩';
  function mainland(f) {
    const polygons = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
    const coordinates = polygons.filter(p => p[0].some(([lon, lat])=> lat>=35 && lon<146));
    return {...f, geometry:{type:'MultiPolygon', coordinates}};
  }
  function stage(features, key, filtered = false) {
    const shapes = filtered ? features.map(mainland).filter(f=>f.geometry.coordinates.length) : features;
    const projection = d3.geoMercator().fitExtent([[16,16],[624,304]], {type:'FeatureCollection',features:shapes});
    const geo = d3.geoPath(projection).digits(1);
    return shapes.map(f=>({name:name(f), key:key(f), area: f.properties.N03_004 ? area(f) : '', d:geo(f), center:geo.centroid(f).map(n=>Math.round(n*10)/10)}));
  }
  const kanto = ['東京都','神奈川県','千葉県','埼玉県','茨城県','栃木県','群馬県'];
  const regions = {'北海道':'北海道','青森県':'東北','岩手県':'東北','宮城県':'東北','秋田県':'東北','山形県':'東北','福島県':'東北'};
  for(const p of prefectures) if(kanto.includes(name(p))) regions[name(p)]='関東';
  for(const p of ['新潟県','富山県','石川県','福井県','山梨県','長野県','岐阜県','静岡県','愛知県']) regions[p]='中部';
  for(const p of ['三重県','滋賀県','京都府','大阪府','兵庫県','奈良県','和歌山県']) regions[p]='関西';
  for(const p of ['鳥取県','島根県','岡山県','広島県','山口県','徳島県','香川県','愛媛県','高知県']) regions[p]='中国・四国';
  for(const p of ['福岡県','佐賀県','長崎県','熊本県','大分県','宮崎県','鹿児島県','沖縄県']) regions[p]='九州・沖縄';
  const maps = {
    japan:stage(prefectures, f=>regions[name(f)] || '準備中'),
    kanto:stage(prefectures.filter(f=>kanto.includes(name(f))), name, true),
    tokyo:stage(municipalities.filter(f=>area(f)!=='島しょ'), area),
    wards:stage(municipalities.filter(f=>area(f)==='23区'), name),
    tama:stage(municipalities.filter(f=>area(f)==='多摩'), name),
    islands:stage(municipalities.filter(f=>area(f)==='島しょ'), name),
  };
  fs.writeFileSync(path.join(root,'outputs/venues/catalogs/region_maps.json'), JSON.stringify({sources, attribution:'国土数値情報（行政区域データ）を加工して作成。境界は2021年版。', maps}));
  console.log(JSON.stringify({bytes:fs.statSync(path.join(root,'outputs/venues/catalogs/region_maps.json')).size,shapes:Object.fromEntries(Object.entries(maps).map(([k,v])=>[k,v.length])),properties:municipalities[0].properties}));
})().catch(error=>{console.error(error);process.exitCode=1;});
