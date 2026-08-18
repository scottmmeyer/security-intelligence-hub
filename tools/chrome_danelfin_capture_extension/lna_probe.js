const OUT = document.getElementById("out");
const PROBE_URL = "http://127.0.0.1:8765/api/danelfin/browser-capture";

function write(msg) {
  OUT.textContent = msg;
}

async function runProbe() {
  write("probing localhost via OPTIONS...");
  try {
    const resp = await fetch(PROBE_URL, {
      method: "OPTIONS"
    });
    write(`probe success: status=${resp.status}`);
  } catch (err) {
    write(`probe failed: ${String(err && err.message ? err.message : err)}`);
  }
}

document.getElementById("probe").addEventListener("click", runProbe);
