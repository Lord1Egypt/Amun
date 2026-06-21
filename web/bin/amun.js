#!/usr/bin/env node
/*
 * Amun — Breath–Computer Interface (JavaScript edition).
 *
 * A zero-dependency Node server that serves the self-contained browser game and
 * opens it. The game itself (engine, breath pipeline, renderer) runs entirely in
 * the browser, so npm users need no Python and nothing but Node's stdlib here.
 *
 *   npx amun-bci                 # serve + open the game
 *   amun --port 9000 --no-open   # custom port, don't auto-open
 *   amun --selftest              # boot, self-check, exit 0 (for CI)
 */
"use strict";

const http = require("http");
const fs = require("fs");
const path = require("path");
const { execFile } = require("child_process");

const PUBLIC = path.join(__dirname, "..", "public");
const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript",
  ".css": "text/css",
  ".png": "image/png",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
  ".json": "application/json",
  ".ico": "image/x-icon",
};

function parseArgs(argv) {
  const args = { port: 8011, open: true, selftest: false, host: "127.0.0.1" };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--port") args.port = parseInt(argv[++i], 10) || args.port;
    else if (a === "--host") args.host = argv[++i] || args.host;
    else if (a === "--no-open") args.open = false;
    else if (a === "--selftest") { args.selftest = true; args.open = false; }
    else if (a === "--help" || a === "-h") args.help = true;
  }
  return args;
}

function send(res, code, body, type) {
  res.writeHead(code, { "Content-Type": type || "text/plain", "Cache-Control": "no-store" });
  res.end(body);
}

function serveFile(res, rel) {
  // prevent path traversal
  const target = path.normalize(path.join(PUBLIC, rel));
  if (!target.startsWith(PUBLIC)) return send(res, 403, "Forbidden");
  fs.readFile(target, (err, data) => {
    if (err) return send(res, 404, "Not found");
    send(res, 200, data, MIME[path.extname(target)] || "application/octet-stream");
  });
}

function createServer() {
  return http.createServer((req, res) => {
    const url = req.url.split("?")[0];
    if (url === "/health") return send(res, 200, '{"status":"ok"}', MIME[".json"]);
    if (url === "/" || url === "/index.html") return serveFile(res, "index.html");
    return serveFile(res, url.replace(/^\/+/, ""));
  });
}

function openBrowser(url) {
  const cmd = process.platform === "darwin" ? "open"
            : process.platform === "win32" ? "cmd" : "xdg-open";
  const args = process.platform === "win32" ? ["/c", "start", "", url] : [url];
  execFile(cmd, args, () => {});
}

function banner(url) {
  return [
    "",
    "  𓅃  A M U N  —  Breath–Computer Interface  (JS edition)",
    "      pilot a falcon with your breath · no electrodes · just air",
    "",
    `  🜂  serving at ${url}`,
    "     open it, allow the microphone, and breathe.",
    "     (no mic? press & hold SPACE.  Ctrl+C to stop.)",
    "",
  ].join("\n");
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log("usage: amun [--port N] [--host H] [--no-open] [--selftest]");
    return;
  }
  const server = createServer();

  if (args.selftest) {
    // boot on an ephemeral port, hit /health and /, then exit cleanly
    server.listen(0, "127.0.0.1", () => {
      const port = server.address().port;
      const get = (p) => new Promise((resolve, reject) => {
        http.get(`http://127.0.0.1:${port}${p}`, (r) => {
          let b = ""; r.on("data", (c) => (b += c));
          r.on("end", () => resolve({ status: r.statusCode, body: b }));
        }).on("error", reject);
      });
      Promise.all([get("/health"), get("/")])
        .then(([h, idx]) => {
          const ok = h.status === 200 && idx.status === 200 &&
                     idx.body.includes("AMUN");
          console.log(ok ? "selftest: OK" : "selftest: FAILED");
          server.close(() => process.exit(ok ? 0 : 1));
        })
        .catch((e) => { console.error("selftest error:", e.message); process.exit(1); });
    });
    return;
  }

  server.listen(args.port, args.host, () => {
    const url = `http://${args.host}:${server.address().port}/`;
    console.log(banner(url));
    if (args.open) setTimeout(() => openBrowser(url), 500);
  });
  server.on("error", (e) => {
    console.error(`error: ${e.message}`);
    process.exit(1);
  });
  process.on("SIGINT", () => {
    console.log("\n  𓂀  may Ma'at weigh your flight kindly. Goodbye.");
    process.exit(0);
  });
}

main();
