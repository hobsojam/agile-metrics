// Run `npm audit`, failing on any advisory that is not explicitly allowlisted.
//
// npm has no built-in way to accept a specific advisory, so CI used to run a
// bare `npm audit`, which leaves no option when an advisory has no patched
// version. Each allowlist entry must say why the risk is accepted; remove it
// as soon as a fix ships (this script reports entries that no longer match).
import { execFileSync } from "node:child_process";
import console from "node:console";
import process from "node:process";

const ALLOWLIST = {
  // picomatch <= 4.0.7 ReDoS via repeated extglobs; no patched release exists
  // (4.0.7 is the latest). Only reached through build/test tooling (vite,
  // vitest, typescript-eslint) matching our own fixed glob patterns, never
  // untrusted input, and absent from the production bundle
  // (`npm audit --omit=dev` is clean).
  "GHSA-fc5q-39xc-vjpf": "picomatch ReDoS, dev tooling only, no fix available",
};

let raw;
try {
  raw = execFileSync("npm", ["audit", "--json"], { encoding: "utf8" });
} catch (err) {
  // npm audit exits non-zero when it finds anything; the JSON is still on stdout.
  raw = err.stdout;
  if (!raw) throw err;
}

const report = JSON.parse(raw);
if (report.error) {
  console.error("npm audit failed:", report.error);
  process.exit(1);
}

const found = new Map(); // GHSA id -> advisory
for (const vuln of Object.values(report.vulnerabilities ?? {})) {
  for (const via of vuln.via) {
    // String entries point at another vulnerable package; objects are the advisories.
    if (typeof via === "object") {
      found.set(via.url.split("/").pop(), via);
    }
  }
}

const blocking = [...found].filter(([id]) => !(id in ALLOWLIST));
const allowed = [...found].filter(([id]) => id in ALLOWLIST);
const stale = Object.keys(ALLOWLIST).filter((id) => !found.has(id));

for (const [id, adv] of allowed) {
  console.log(`allowlisted: ${id} (${adv.name}, ${adv.severity}) - ${ALLOWLIST[id]}`);
}
for (const id of stale) {
  console.log(`note: allowlisted ${id} no longer reported; remove it from scripts/audit.mjs`);
}
if (blocking.length > 0) {
  for (const [id, adv] of blocking) {
    console.error(`VULNERABLE: ${id} ${adv.name} ${adv.range} (${adv.severity}): ${adv.title} ${adv.url}`);
  }
  process.exit(1);
}
console.log("npm audit: no unaccepted vulnerabilities");
