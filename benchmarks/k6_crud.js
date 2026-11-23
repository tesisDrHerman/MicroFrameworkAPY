import http from 'k6/http';
import { check } from 'k6';

const VUS = __ENV.VUS ? parseInt(__ENV.VUS, 10) : 100;
const WARMUP_DURATION = __ENV.WARMUP || '5s';
const WARMUP_SECS = parseInt(WARMUP_DURATION, 10) || 5;
const DURATION = __ENV.DURATION || '25s';
const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:4201';

export const options = {
  scenarios: {
    warmup: {
      executor: 'constant-vus',
      vus: Math.min(20, VUS),
      duration: `${WARMUP_SECS}s`,
      startTime: '0s',
      tags: { phase: 'warmup' },
    },
    measure: {
      executor: 'constant-vus',
      vus: VUS,
      duration: DURATION,
      startTime: `${WARMUP_SECS}s`,
      tags: { phase: 'measure' },
    },
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

export default function () {
  // 1. GET por ID con resolucion de llaves foraneas (orders -> users + categories)
  const oid = Math.floor(Math.random() * 10000) + 1;
  const rGet = http.get(`${BASE_URL}/api/orders/get?id=${oid}`);
  check(rGet, { 'CRUD GET 200': (r) => r && r.status === 200 });

  // 2. POST insercion JSON realista (cada 3 iteraciones para simular carga 75% lectura / 25% escritura)
  if (__ITER % 3 === 0) {
    const payload = JSON.stringify({
      user_id: Math.floor(Math.random() * 1000) + 1,
      category_id: Math.floor(Math.random() * 50) + 1,
      total_amount: 149.95,
      status: 'confirmed',
    });
    const rPost = http.post(`${BASE_URL}/api/orders/post`, payload, {
      headers: { 'Content-Type': 'application/json' },
    });
    check(rPost, { 'CRUD POST 200/201': (r) => r && (r.status === 200 || r.status === 201) });
  }
}
