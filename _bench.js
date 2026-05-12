const http = require('http');
const { gzipSync } = require('zlib');
const fs = require('fs');
const path = require('path');

const RUNS = 10;
const ttfbs = [], totals = [], sizes = [];
let done = 0;

for (let i = 0; i < RUNS; i++) {
  const t0 = process.hrtime.bigint();
  http.get({ hostname: 'localhost', port: 3000, path: '/', timeout: 5000 }, res => {
    const ttfb = Number(process.hrtime.bigint() - t0) / 1e6;
    ttfbs.push(ttfb);
    let bytes = 0;
    res.on('data', d => bytes += d.length);
    res.on('end', () => {
      totals.push(Number(process.hrtime.bigint() - t0) / 1e6);
      sizes.push(bytes);
      if (++done === RUNS) phase2();
    });
  }).on('error', e => { if (++done === RUNS) phase2(); });
}

function avg(a) { return (a.reduce((x,y)=>x+y,0)/a.length).toFixed(1); }
function mn(a)  { return Math.min(...a).toFixed(1); }
function mx(a)  { return Math.max(...a).toFixed(1); }
function p90(a) { const s=[...a].sort((x,y)=>x-y); return s[Math.floor(s.length*0.9)].toFixed(1); }

function phase2() {
  console.log('\n=== [1] Page Load Benchmark (' + RUNS + ' runs, localhost:3000) ===');
  console.log('TTFB  avg=' + avg(ttfbs) + 'ms  min=' + mn(ttfbs) + 'ms  max=' + mx(ttfbs) + 'ms  p90=' + p90(ttfbs) + 'ms');
  console.log('Total avg=' + avg(totals) + 'ms  min=' + mn(totals) + 'ms  max=' + mx(totals) + 'ms  p90=' + p90(totals) + 'ms');
  console.log('Size  ' + (sizes[0] || 0) + ' bytes (' + ((sizes[0] || 0) / 1024).toFixed(1) + ' KB)');

  const htmlPath = path.join(process.cwd(), 'apps/web/dist/index.html');
  const raw = fs.readFileSync(htmlPath);
  const gz  = gzipSync(raw, { level: 9 });

  console.log('\n=== [2] Payload Analysis ===');
  console.log('Raw HTML     : ' + (raw.length / 1024).toFixed(1) + ' KB (' + raw.length + ' bytes)');
  console.log('Gzip level-9 : ' + (gz.length / 1024).toFixed(1) + ' KB (' + gz.length + ' bytes)');
  console.log('Compression  : ' + ((1 - gz.length / raw.length) * 100).toFixed(1) + '% reduction');

  const html = raw.toString();
  const cssBytes = (html.match(/<style[\s\S]*?<\/style>/g) || []).reduce((a,b)=>a+b.length,0);
  const jsBytes  = (html.match(/<script[\s\S]*?<\/script>/g) || []).reduce((a,b)=>a+b.length,0);
  const svgCount  = (html.match(/<svg/g) || []).length;
  const fetchCalls = (html.match(/fetch\(/g) || []).length;
  const domNodes  = (html.match(/<[a-z][a-z0-9]*/gi) || []).length;
  const extUrls   = [...new Set((html.match(/https?:\/\/[^\s"'>\)]+/g) || []))];

  console.log('CSS inline   : ' + (cssBytes / 1024).toFixed(1) + ' KB');
  console.log('JS inline    : ' + (jsBytes / 1024).toFixed(1) + ' KB');
  console.log('SVG elements : ' + svgCount);
  console.log('fetch() calls: ' + fetchCalls);
  console.log('DOM nodes est: ' + domNodes);

  console.log('\n=== [3] External URLs ===');
  extUrls.forEach(u => console.log('  ' + u.slice(0, 100)));

  console.log('\n=== [4] API Health Latency ===');
  const apis = [
    { name:'mobile-gateway', port:8088 },
    { name:'rag-api',        port:8090 },
    { name:'tto-api',        port:8091 },
    { name:'rtk-bridge',     port:8092 },
    { name:'webhook-gw',     port:8093 },
    { name:'observer',       port:8094 },
    { name:'worker',         port:8095 },
  ];
  let apiDone = 0;
  apis.forEach(svc => {
    const t0 = process.hrtime.bigint();
    http.get({ hostname:'127.0.0.1', port:svc.port, path:'/health', timeout:3000 }, res => {
      const ms = (Number(process.hrtime.bigint()-t0)/1e6).toFixed(1);
      let body = ''; res.on('data',d=>body+=d);
      res.on('end', () => {
        console.log('  :' + svc.port + ' ' + svc.name.padEnd(16) + ' HTTP ' + res.statusCode + '  ' + ms + 'ms');
        if (++apiDone === apis.length) phase3();
      });
    }).on('error', e => {
      const ms = (Number(process.hrtime.bigint()-t0)/1e6).toFixed(1);
      console.log('  :' + svc.port + ' ' + svc.name.padEnd(16) + ' ERR ' + e.code + '  ' + ms + 'ms');
      if (++apiDone === apis.length) phase3();
    });
  });
}

function phase3() {
  console.log('\n=== [5] Observer /status (parallel health aggregate) ===');
  const t0 = process.hrtime.bigint();
  http.get({ hostname:'127.0.0.1', port:8094, path:'/status', timeout:10000 }, res => {
    const ms = (Number(process.hrtime.bigint()-t0)/1e6).toFixed(0);
    let body = ''; res.on('data',d=>body+=d);
    res.on('end', () => {
      try {
        const j = JSON.parse(body);
        console.log('  overall       : ' + j.overall);
        console.log('  response time : ' + ms + 'ms (parallel)');
        console.log('  degraded      : ' + (j.degraded_services && j.degraded_services.length ? j.degraded_services.join(', ') : 'none'));
        Object.entries(j.services || {}).forEach(([k,v]) => {
          console.log('  ' + k.padEnd(20) + (v.status || '').padEnd(8) + (v.latency_ms ? v.latency_ms + 'ms' : '---'));
        });
      } catch(e) { console.log('  parse error: ' + body.slice(0,200)); }
      phase4();
    });
  }).on('error', e => { console.log('  ERR: ' + e.code); phase4(); });
}

function phase4() {
  const html = fs.readFileSync(path.join(process.cwd(), 'apps/web/dist/index.html')).toString();
  console.log('\n=== [6] UX & Code Audit ===');
  console.log('  window.prompt()      : ' + (html.split('window.prompt').length - 1) + ' usage — modal replacement needed');
  console.log('  AbortSignal.timeout  : ' + (html.split('AbortSignal.timeout').length - 1) + ' usage (Chrome 103+)');
  console.log('  autoRefresh 30s      : ' + (html.split('30000').length - 1) + ' interval');
  console.log('  error states         : ' + (html.split('alert-error').length - 1) + ' boundaries');
  console.log('  loading indicators   : ' + (html.split('loading').length - 1) + ' usages');
  console.log('  empty states         : ' + (html.split('empty-state').length - 1) + ' states');
  console.log('  mobile breakpoint    : ' + (html.split('768px').length - 1) + ' responsive rules');
  console.log('  safe-area-inset      : ' + (html.split('safe-area').length - 1) + ' notch support rules');
  console.log('  Thai font (Noto)     : ' + (html.split('Noto Sans Thai').length - 1) + ' reference');
  console.log('\n=== BENCHMARK COMPLETE ===');
}
