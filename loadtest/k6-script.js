// Class 6/8: quick load test used to trigger the HPA on servicio-patron,
// model and pow. Run with:
//   k6 run loadtest/k6-script.js
//   k6 run -e TARGET=servicio-patron loadtest/k6-script.js
//   k6 run -e TARGET=model -e MODEL_URL=http://localhost:8081 loadtest/k6-script.js
//
// Env vars (all optional, sensible localhost defaults -- no hardcoded
// cluster hostnames):
//   TARGET                 "servicio-patron" (default) | "model" | "pow"
//   SERVICIO_PATRON_URL    default http://localhost:8080
//   MODEL_URL              default http://localhost:8081
//   POW_URL                default http://localhost:8090
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  scenarios: {
    ramp: {
      executor: "ramping-vus",
      startVUs: 1,
      stages: [
        { duration: "30s", target: 10 },
        { duration: "1m", target: 30 }, // enough sustained load to trip a 60-70% CPU HPA target
        { duration: "30s", target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<2000"],
  },
};

const TARGET = __ENV.TARGET || "servicio-patron";
const SERVICIO_PATRON_URL = __ENV.SERVICIO_PATRON_URL || "http://localhost:8080";
const MODEL_URL = __ENV.MODEL_URL || "http://localhost:8081";
const POW_URL = __ENV.POW_URL || "http://localhost:8090";

export default function () {
  if (TARGET === "model") {
    const payload = JSON.stringify({ features: [5.1, 3.5, 1.4, 0.2] });
    const res = http.post(`${MODEL_URL}/predict`, payload, {
      headers: { "Content-Type": "application/json" },
    });
    check(res, { "predict 200": (r) => r.status === 200 });
  } else if (TARGET === "pow") {
    const tx = JSON.stringify({ sender: "loadtest", to: "sink", amount: 1 });
    const txRes = http.post(`${POW_URL}/tx`, tx, {
      headers: { "Content-Type": "application/json" },
    });
    check(txRes, { "tx 201": (r) => r.status === 201 });

    // Mine occasionally, not on every VU iteration, to keep the mining
    // pool from growing unbounded difficulty-wise during the test.
    if (Math.random() < 0.1) {
      const mineRes = http.post(`${POW_URL}/mine`);
      check(mineRes, { "mine 200": (r) => r.status === 200 });
    }
  } else {
    const res = http.get(`${SERVICIO_PATRON_URL}/`);
    check(res, { "root 200": (r) => r.status === 200 });
  }

  sleep(1);
}
