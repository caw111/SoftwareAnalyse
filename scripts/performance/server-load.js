// Server-only acceptance script. Never invoked by build, test, Docker or CI.
import http from 'k6/http';
import { check, fail } from 'k6';
import { Trend, Rate, Counter, Gauge } from 'k6/metrics';

const base = (__ENV.BASE_URL || '').replace(/\/$/, '');
const dataset = __ENV.DATASET || 'demo';
const concurrency = Number(__ENV.CONCURRENCY || 20);
const seconds = Number(__ENV.DURATION_SECONDS || 300);
if (__ENV.CONFIRM_SERVER_TEST !== 'yes' || !/^https?:\/\//.test(base)) {
  throw new Error('Only run intentionally on the server: set BASE_URL and CONFIRM_SERVER_TEST=yes. No local load test is authorized.');
}
if (!Number.isInteger(concurrency) || concurrency < 1 || concurrency > 100 || !Number.isInteger(seconds) || seconds < 30 || seconds > 3600) {
  throw new Error('CONCURRENCY must be 1..100, DURATION_SECONDS must be 30..3600. Acceptance baseline: 20 / 300.');
}
const searches = new Trend('search_latency_ms', true);
const details = new Trend('detail_latency_ms', true);
const stats = new Trend('statistics_latency_ms', true);
const errors = new Rate('measured_error_rate');
const requests = new Counter('measured_requests');
const catalogRevision = new Gauge('catalog_revision');
const catalogCount = new Gauge('catalog_canonical_works');
const initialProbe = new Trend('initial_probe_ms', true);
const querySet = Array.from({ length: 50 }, (_, i) => ({
  type: ['', 'PAPER', 'PATENT', 'PROJECT', 'AWARD'][i % 5],
  from: 2019 + (Math.floor(i / 5) % 8), to: 2026,
  sort: ['year', 'citations'][Math.floor(i / 25)],
  q: i < 40 ? '' : ['知识', '并发', '数据', '学术', '不存在的固定查询'][i % 5],
  page: 0, size: 20,
}));
function query(values) {
  return Object.entries(values).map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join('&');
}
export const options = {
  scenarios: {
    warmup: { executor: 'constant-vus', vus: concurrency, duration: '30s', gracefulStop: '5s', exec: 'warmup' },
    measured: { executor: 'constant-vus', vus: concurrency, duration: `${seconds}s`, startTime: '35s', gracefulStop: '10s', exec: 'measured' },
  },
  thresholds: {
    search_latency_ms: ['p(95)<2000'],
    detail_latency_ms: ['p(95)<1000'],
    statistics_latency_ms: ['p(95)<3000'],
    measured_error_rate: ['rate<0.01'],
  },
  summaryTrendStats: ['count', 'min', 'med', 'p(95)', 'p(99)', 'max'],
  userAgent: 'AcademicPlatform-ServerAcceptance/0.1',
};
export function setup() {
  const probe = http.get(`${base}/api/works?dataset=${dataset}&size=50`, { timeout: '10s', tags: { phase: 'setup', name: 'setup_catalog' } });
  if (probe.status !== 200) fail(`Catalog probe failed: HTTP ${probe.status}`);
  const body = probe.json();
  if (body.total < 10000) fail(`At least 10,000 canonical works required; got ${body.total}. Use an isolated server acceptance database.`);
  if (body.items.length === 0) fail('No detail samples available.');
  catalogRevision.add(body.revision); catalogCount.add(body.total); initialProbe.add(probe.timings.duration);
  return { revision: body.revision, total: body.total, ids: body.items.map(w => w.id), firstProbeMs: probe.timings.duration };
}
function execute(data, measuredPhase) {
  const slot = (__VU + __ITER) % 20;
  const entry = querySet[(__ITER + __VU * 7) % querySet.length];
  let path, metric, name;
  if (slot < 12) {
    path = '/api/works?' + query({ ...entry, dataset, revision: data.revision }); metric = searches; name = 'search';
  } else if (slot < 17) {
    path = `/api/works/${data.ids[(__ITER + __VU) % data.ids.length]}?revision=${data.revision}`; metric = details; name = 'detail';
  } else {
    path = '/api/statistics?' + query({ type: entry.type, from: entry.from, to: entry.to, dataset, revision: data.revision }); metric = stats; name = 'statistics';
  }
  const response = http.get(base + path, { timeout: '5s', tags: { name, phase: measuredPhase ? 'measured' : 'warmup' } });
  let valid = response.status === 200;
  if (valid) {
    try {
      const body = response.json();
      valid = body.revision === data.revision && (name === 'search' ? Array.isArray(body.items) && typeof body.total === 'number' : name === 'detail' ? !!body.id : !!body.metrics);
    } catch (_) { valid = false; }
  }
  check(valid, { 'HTTP 200 with expected payload and fixed revision': v => v }, { phase: measuredPhase ? 'measured' : 'warmup' });
  if (measuredPhase) {
    // Record failures as well; never improve p95 by discarding slow errors.
    metric.add(response.timings.duration); errors.add(!valid); requests.add(1);
  }
}
export function warmup(data) { execute(data, false); }
export function measured(data) { execute(data, true); }
export function handleSummary(data) {
  const report = {
    generatedAt: new Date().toISOString(), baseUrl: base, dataset, concurrency, measuredSeconds: seconds,
    warmupSeconds: 30, requestMix: '60% search / 25% detail / 15% statistics',
    environment: __ENV.ENVIRONMENT || 'NOT RECORDED: supply CPU/RAM/OS/DB/JVM/revision/replicas/client location',
    revision: data.metrics.catalog_revision?.values.value,
    canonicalWorks: data.metrics.catalog_canonical_works?.values.value,
    querySet, note: 'Warm-cache fixed-query closed-loop test. Not a cold-start, open-arrival, unbounded-query or scalability result.',
    summary: data,
  };
  return { 'server-load-results.json': JSON.stringify(report, null, 2), stdout: 'Server test finished. Inspect server-load-results.json, error rate, per-endpoint p95/p99 and resource monitoring.\n' };
}
