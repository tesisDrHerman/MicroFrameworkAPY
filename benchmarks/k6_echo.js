import http from 'k6/http';
import { check } from 'k6';

const VUS = __ENV.VUS ? parseInt(__ENV.VUS, 10) : 100;
const DURATION = __ENV.DURATION || '150s';
const METHOD = (__ENV.METHOD || 'GET').toUpperCase();
const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:4201';

export const options = {
  scenarios: {
    warmup: {
      executor: 'constant-vus',
      vus: Math.min(20, VUS),
      duration: '30s',
      startTime: '0s',
      tags: { phase: 'warmup' },
    },
    measure: {
      executor: 'constant-vus',
      vus: VUS,
      duration: DURATION,
      startTime: '30s',
      tags: { phase: 'measure' },
    },
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

export default function () {
  let res;
  if (METHOD === 'GET') {
    res = http.get(`${BASE_URL}/echo/get?value=benchmark_payload`);
  } else if (METHOD === 'POST') {
    res = http.post(
      `${BASE_URL}/echo/post`,
      JSON.stringify({ key: 'benchmark_payload', id: 42, active: true }),
      { headers: { 'Content-Type': 'application/json' } }
    );
  } else if (METHOD === 'PUT') {
    res = http.put(`${BASE_URL}/echo/put?value=benchmark_updated`, null);
  } else if (METHOD === 'DELETE') {
    res = http.del(`${BASE_URL}/echo/delete?value=benchmark_deleted`, null);
  } else if (METHOD === 'PATCH') {
    res = http.patch(`${BASE_URL}/echo/patch?value=benchmark_patched`, null);
  }
  check(res, { 'status is 200': (r) => r && r.status === 200 });
}
