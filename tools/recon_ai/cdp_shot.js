#!/usr/bin/env node
/* CDP 截图回退：部分 Edge/Chrome 版本的 --screenshot 静默失败时使用。
   用法：node cdp_shot.js <browser> <url> <out.png> <W,H>
   退出码：0 = 已写出非空 PNG；1 = 失败（原因写 stderr）。 */
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const [exe, url, out, size] = process.argv.slice(2);
const [width, height] = (size || '1280,900').split(',').map(n => parseInt(n, 10));
const LOAD_MS = 15000;

function done(code, msg) {
  if (msg) console.error(msg);
  process.exit(code);
}
if (!exe || !url || !out) done(1, 'usage: cdp_shot.js <browser> <url> <out.png> [W,H]');

const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'recon-ai-cdp-'));
let origin = '';
try {
  const u = new URL(url);
  if (u.protocol === 'http:') origin = u.origin;
} catch (e) { /* 非 URL 目标（如 data:）无需放行 */ }
const args = ['--headless=new', '--disable-gpu', '--no-sandbox',
  '--no-first-run', '--hide-scrollbars', '--user-data-dir=' + profile,
  '--window-size=' + (width || 1280) + ',' + (height || 900),
  '--remote-debugging-port=0'];
// 部分 Chromium 版本对「公网域名解析到内网 IP 的 http 目标」按不安全来源拦截；
// 仅对本次目标 origin 放行，避免扩大浏览器的信任面。
if (origin) args.push('--unsafely-treat-insecure-origin-as-secure=' + origin);
args.push('about:blank');
const child = spawn(exe, args, { stdio: 'ignore' });

function cleanup(code, msg) {
  try { child.kill(); } catch (e) { /* 已退出 */ }
  try { fs.rmSync(profile, { recursive: true, force: true }); } catch (e) { /* 临时目录可残留 */ }
  done(code, msg);
}

const portFile = path.join(profile, 'DevToolsActivePort');
let ticks = 0;
const timer = setInterval(() => {
  ticks += 1;
  if (fs.existsSync(portFile)) {
    clearInterval(timer);
    run().catch(e => cleanup(1, 'cdp error: ' + (e && e.message ? e.message : e)));
  } else if (ticks > 80) {
    clearInterval(timer);
    cleanup(1, 'devtools port not available');
  }
}, 250);

async function run() {
  const [port] = fs.readFileSync(portFile, 'utf8').trim().split(/\r?\n/);
  const list = await fetch('http://127.0.0.1:' + port + '/json/list').then(r => r.json());
  const page = list.find(x => x.type === 'page');
  if (!page) throw new Error('no page target');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let seq = 0;
  let loaded = false;
  const send = (method, params) => ws.send(JSON.stringify({ id: ++seq, method, params }));
  const deadline = setTimeout(() => cleanup(1, 'page load timeout'), LOAD_MS);

  ws.onopen = () => {
    send('Page.enable');
    send('Page.navigate', { url });
    // 无 load 事件的页面（如 data:/file: 快照）也保底触发一次截图
    setTimeout(() => { if (!loaded) capture(); }, 3000);
  };
  ws.onmessage = ev => {
    const msg = JSON.parse(ev.data);
    if (msg.method === 'Page.loadEventFired') {
      loaded = true;
      setTimeout(capture, 500);
    }
    if (msg.id && msg.result && msg.result.data) {
      clearTimeout(deadline);
      const buf = Buffer.from(msg.result.data, 'base64');
      fs.writeFileSync(out, buf);
      ws.close();
      cleanup(buf.length > 0 ? 0 : 1, buf.length ? '' : 'empty screenshot');
    }
  };
  ws.onerror = () => cleanup(1, 'websocket error');
  function capture() { send('Page.captureScreenshot', { format: 'png' }); }
}
