"""Dashboard RBT FX — terminal hacker hijau neon (total redesign v3.13+).

Konsep: aksen hacker/matrix (hijau neon, scanline CRT, HUD corner brackets,
boot sequence, glitch logo, matrix rain) + animasi market live ala Polymarket
(ticker tape berjalan, flash harga naik/turun, score-bar shimmer, chart pulse).
Server HTTP stdlib: GET / (dashboard), GET /api/status (JSON live),
POST /api/halt (kill switch). Semua CSS/JS inline (tanpa resource eksternal),
refresh 2 detik, globe dunia wireframe tetap berputar.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
try:
    import cc_selfupdate
except Exception:
    cc_selfupdate = None
from urllib.parse import urlparse, parse_qs

PAGE_LOGIN = r"""<!DOCTYPE html>
<html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>RBT FX :: LOGIN</title><style>
:root{--acc:#00ff9c;--amber:#ffc857}
*{margin:0;padding:0;box-sizing:border-box}
body{min-height:100vh;display:flex;align-items:center;justify-content:center;
font-family:ui-monospace,Consolas,monospace;color:#dcffee;
background:radial-gradient(700px 460px at 70% -8%,rgba(0,255,156,.08),transparent 60%),#020604}
.box{width:330px;background:rgba(5,17,11,.9);border:1px solid #155234;border-radius:10px;
padding:26px;text-align:center;position:relative}
.box:before{content:'';position:absolute;top:-1px;left:-1px;width:16px;height:16px;
border-top:2px solid var(--acc);border-left:2px solid var(--acc);border-radius:10px 0 0 0}
.box:after{content:'';position:absolute;bottom:-1px;right:-1px;width:16px;height:16px;
border-bottom:2px solid var(--acc);border-right:2px solid var(--acc);border-radius:0 0 10px 0}
h1{font-size:18px;color:var(--amber);letter-spacing:.1em;margin:8px 0 2px}
small{color:#4e8465;font-size:9px;letter-spacing:.25em}
p{font-size:10px;color:#5d9678;margin:14px 0 10px;letter-spacing:.12em}
input{width:100%;font-family:inherit;font-size:14px;color:#dcffee;text-align:center;
background:#020604;border:1px solid #155234;border-radius:6px;padding:11px;outline:none;letter-spacing:.3em}
input:focus{border-color:var(--acc);box-shadow:0 0 14px rgba(0,255,156,.25)}
button{width:100%;margin-top:12px;font-family:inherit;font-size:12px;font-weight:800;
letter-spacing:.25em;color:#02150c;background:var(--acc);border:0;border-radius:6px;
padding:12px;cursor:pointer;box-shadow:0 0 18px rgba(0,255,156,.4)}
button:hover{filter:brightness(1.15)}
#msg{font-size:10px;color:#ff2d55;min-height:14px;margin-top:10px;letter-spacing:.1em}
</style></head><body>
<div class="box">
<svg viewBox="0 0 32 24" width="42" height="30"><defs><linearGradient id="cg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffd75e"/><stop offset="1" stop-color="#d99900"/></linearGradient></defs><path d="M2 19 L2 8 L9.5 13.5 L16 2.5 L22.5 13.5 L30 8 L30 19 Z" fill="url(#cg)"/><rect x="2" y="19.5" width="28" height="3" rx="1" fill="#d99900"/></svg>
<h1>RBT FX</h1><small>COMMAND CENTER &middot; UI-2</small>
<p>MASUKKAN PASSWORD DASHBOARD</p>
<input id="pw" type="password" placeholder="*****" autofocus>
<button onclick="go()">MASUK</button>
<div id="msg"></div>
</div>
<script>
function go(){const v=document.getElementById('pw').value;
const m=document.getElementById('msg');
if(!v){m.textContent='ISI PASSWORD DULU';return}
fetch('/login',{method:'POST',
 headers:{'Content-Type':'application/x-www-form-urlencoded'},
 body:'password='+encodeURIComponent(v)}).then(r=>{
 if(r.ok){location.replace('/')}else{m.textContent='PASSWORD SALAH - COBA LAGI'}})
.catch(()=>{m.textContent='GAGAL TERHUBUNG KE SERVER'});}
document.getElementById('pw').addEventListener('keydown',e=>{if(e.key==='Enter')go()});
</script></body></html>
"""

PAGE = r"""<!DOCTYPE html>
<html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>RBT FX :: TRADING ALGO SYSTEM</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%23020604'/%3E%3Ctext x='16' y='23' font-size='18' text-anchor='middle' fill='%2300ff9c' font-family='monospace'%3E%3E%3C/text%3E%3C/svg%3E">
<style>
:root{--bg:#020604;--pan:rgba(5,17,11,.82);--pan2:#04110b;--bd:#0d2c1d;--bd2:#155234;
--acc:#00ff9c;--cy:#00e0ff;--grn:#00ff9c;--red:#ff2d55;--amber:#ffc857;--vio:#b78cff;
--tx:#dcffee;--dim:#5d9678;--dim2:#2a5440;
--f:ui-monospace,'Cascadia Code','JetBrains Mono','Fira Code',Consolas,'Courier New',monospace}
*{margin:0;padding:0;box-sizing:border-box}
html{scrollbar-color:#0f3d27 transparent}
::-webkit-scrollbar{width:8px;height:8px}
::-webkit-scrollbar-thumb{background:#0f3d27;border-radius:4px}
::-webkit-scrollbar-track{background:transparent}
::selection{background:rgba(0,255,156,.28)}
body{font-family:var(--f);font-size:12px;color:var(--tx);min-height:100vh;
background:
linear-gradient(rgba(0,255,156,.022) 1px,transparent 1px),
linear-gradient(90deg,rgba(0,255,156,.022) 1px,transparent 1px),
radial-gradient(1000px 620px at 78% -10%,rgba(0,255,156,.07),transparent 60%),
radial-gradient(820px 540px at -6% 106%,rgba(0,224,255,.05),transparent 55%),
var(--bg);
background-attachment:fixed;background-size:34px 34px,34px 34px,auto,auto,auto}
body:after{content:'';position:fixed;inset:0;pointer-events:none;z-index:9000;
background:repeating-linear-gradient(0deg,rgba(0,0,0,.20) 0 1px,transparent 1px 3px)}
body:before{content:'';position:fixed;left:0;right:0;height:110px;z-index:9001;pointer-events:none;
background:linear-gradient(180deg,transparent,rgba(0,255,156,.045),transparent);
animation:beam 8s linear infinite}
@keyframes beam{0%{top:-110px}100%{top:100%}}
#mx{position:fixed;inset:0;z-index:0;pointer-events:none}
#boot{position:fixed;inset:0;z-index:9500;background:#010402;display:flex;
align-items:center;justify-content:center;transition:opacity .6s}
#boot.hide{opacity:0;pointer-events:none}
#bootlines{color:var(--acc);font-size:13px;line-height:1.9;white-space:pre;
text-shadow:0 0 10px rgba(0,255,156,.55)}
main{position:relative;z-index:1;display:flex;flex-direction:column;
height:100vh;padding:12px;max-width:1800px;margin:0 auto}
.num{font-variant-numeric:tabular-nums}
html,body{height:100%}
.cur{animation:blink 1s steps(1) infinite;color:var(--acc)}
@keyframes blink{50%{opacity:0}}
/* ---------- topbar ---------- */
.topbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;
background:linear-gradient(180deg,rgba(10,28,18,.95),rgba(3,10,6,.92));
border:1px solid #17472e;border-radius:8px;padding:8px 12px;
box-shadow:inset 0 1px 0 rgba(255,255,255,.04)}
.logo{font-size:21px;font-weight:800;letter-spacing:.06em;color:var(--acc);
text-shadow:0 0 14px rgba(0,255,156,.55);white-space:nowrap}
.logo small{color:var(--dim);font-size:10.5px;letter-spacing:.2em;display:block;margin-top:2px}
.crown{vertical-align:-4px;margin-right:6px;filter:drop-shadow(0 0 9px rgba(255,200,87,.9))}
.brand{color:var(--amber);text-shadow:0 0 14px rgba(255,200,87,.6)}

.glitch{display:inline-block;animation:glitch 5s infinite steps(1)}
@keyframes glitch{0%,92%,100%{transform:none}93%{transform:translate(1.5px,-1px) skewX(3deg)}
95%{transform:translate(-1.5px,1px)}97%{transform:translate(1px,0) skewX(-2deg)}}
.chips{display:flex;gap:7px;flex:1;flex-wrap:wrap;min-width:300px}
.chip{display:flex;align-items:center;gap:8px;background:rgba(2,8,5,.65);
border:1px solid var(--bd2);border-radius:6px;padding:4px 10px;
color:var(--dim);white-space:nowrap}
.chip .ci{font-size:12px;color:var(--dim);filter:saturate(1.4)}
.chip .ct{display:flex;flex-direction:column;line-height:1.3}
.chip .ct small{font-size:7.5px;letter-spacing:.16em;color:#6aa88c;font-weight:700}
.chip .ct b{font-size:10.5px;font-weight:800;color:#eafff4;letter-spacing:.04em}
.chip.grn{border-color:rgba(0,255,156,.5);
box-shadow:0 0 12px rgba(0,255,156,.10),inset 0 0 10px rgba(0,255,156,.04)}
.chip.grn .ci{color:var(--grn)}
.chip.grn .ct b{color:var(--grn);text-shadow:0 0 8px rgba(0,255,156,.45)}
.chip.amber{border-color:rgba(255,200,87,.55);
box-shadow:0 0 12px rgba(255,200,87,.10)}
.chip.amber .ci,.chip.amber .ct b{color:var(--amber)}
.chip.red{border-color:rgba(255,45,85,.6);
box-shadow:0 0 14px rgba(255,45,85,.18);animation:haltPulse 2s ease-in-out infinite}
.chip.red .ci,.chip.red .ct b{color:var(--red)}
.chip.cy{border-color:rgba(0,224,255,.4)}
.chip.cy .ci,.chip.cy .ct b{color:var(--cy)}
#halt{font-family:var(--f);background:rgba(255,45,85,.07);color:var(--red);
border:1px solid rgba(255,45,85,.6);border-radius:4px;padding:7px 13px;
letter-spacing:.2em;font-weight:800;font-size:11px;cursor:pointer;
text-shadow:0 0 10px rgba(255,45,85,.55);
box-shadow:0 0 14px rgba(255,45,85,.18),inset 0 0 12px rgba(255,45,85,.06);
animation:haltPulse 2.4s ease-in-out infinite;transition:background .2s}
#halt:hover{background:rgba(255,45,85,.22)}
#halt.resume{color:var(--grn);border-color:rgba(0,255,156,.6);text-shadow:0 0 10px rgba(0,255,156,.55);
box-shadow:0 0 14px rgba(0,255,156,.2),inset 0 0 12px rgba(0,255,156,.06);animation:none}
@keyframes haltPulse{50%{box-shadow:0 0 22px rgba(255,45,85,.4),inset 0 0 14px rgba(255,45,85,.12)}}
.tclock{font-size:13px;color:var(--acc);text-shadow:0 0 10px rgba(0,255,156,.4);letter-spacing:.1em}
.tgb{font-size:10px;font-weight:800;letter-spacing:.08em;padding:6px 9px;border-radius:4px;cursor:default;margin-left:4px}
.tgb.on{color:#39d98a;background:rgba(0,255,156,.08);border:1px solid rgba(0,255,156,.4)}
.tgb.bad{color:#ff2d55;background:rgba(255,45,85,.08);border:1px solid rgba(255,45,85,.5);animation:haltPulse 1.6s ease-in-out infinite}
.tgb.off{color:#8a8fa8;background:rgba(138,143,168,.06);border:1px solid #2a2f3a}
/* ---------- ticker tape (polymarket style) ---------- */
.tape{margin-top:8px;overflow:hidden;white-space:nowrap;background:rgba(3,11,7,.85);
border:1px solid var(--bd);border-radius:4px;position:relative}
.tapein{display:inline-flex;align-items:center;padding:4px 0;
animation:tape 36s linear infinite;will-change:transform}
.tape:hover .tapein{animation-play-state:paused}
@keyframes tape{to{transform:translateX(-50%)}}
.tseg{display:inline-flex;align-items:center}
.tpit{display:inline-flex;align-items:center;gap:7px;margin:0 16px;font-size:10.5px;letter-spacing:.05em}
.tpit .tsym{color:var(--acc);font-weight:700;text-shadow:0 0 6px rgba(0,255,156,.35)}
.tpit .tpx{color:var(--tx)}
.tpit .tup{color:var(--grn)}.tpit .tdn{color:var(--red)}
/* ---------- cards ---------- */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(128px,1fr));gap:6px;margin-top:6px}
.card{position:relative;overflow:hidden;
background:linear-gradient(180deg,rgba(9,25,16,.94),rgba(4,12,8,.9));
border:1px solid #17472e;border-radius:7px;padding:5px 9px;
box-shadow:inset 0 1px 0 rgba(255,255,255,.04),0 0 14px rgba(0,0,0,.35)}
.card:before{content:'';position:absolute;top:0;left:0;right:0;height:2px;
background:linear-gradient(90deg,transparent,rgba(255,200,87,.8),transparent)}
.card .ct{display:flex;align-items:center;gap:5px;font-size:8px;
letter-spacing:.14em;color:#79b497;margin-bottom:2px;font-weight:700}
.card .ct .ci{font-size:9.5px;text-shadow:0 0 9px currentColor}
.card .v{font-size:13.5px;font-weight:800;letter-spacing:.02em;color:#eefff6;
text-shadow:0 1px 0 rgba(0,0,0,.65)}
.card .v small{font-size:8.5px;color:#7fb89a;font-weight:700;
letter-spacing:.1em;margin-left:1px}
.card .s{font-size:8px;color:#63a17e;margin-top:1px;letter-spacing:.05em}
/* v3.27: fill warna per kartu biar gampang dibedakan */
.card.a-bal{background:linear-gradient(165deg,rgba(255,200,87,.17),rgba(10,12,8,.93) 62%);border-color:rgba(255,200,87,.40)}
.card.a-bal:before{background:linear-gradient(90deg,transparent,rgba(255,200,87,.95),transparent)}
.card.a-bal .ct{color:#ffd27a}
.card.a-eq{background:linear-gradient(165deg,rgba(53,224,255,.15),rgba(6,12,16,.93) 62%);border-color:rgba(53,224,255,.38)}
.card.a-eq:before{background:linear-gradient(90deg,transparent,rgba(53,224,255,.9),transparent)}
.card.a-eq .ct{color:#7ceaff}
.card.a-dp{background:linear-gradient(165deg,rgba(0,255,156,.16),rgba(4,14,9,.93) 62%);border-color:rgba(0,255,156,.40)}
.card.a-dp:before{background:linear-gradient(90deg,transparent,rgba(0,255,156,.95),transparent)}
.card.a-dp .ct{color:#6dffb9}
.card.a-dl{background:linear-gradient(165deg,rgba(255,45,85,.16),rgba(16,5,8,.93) 62%);border-color:rgba(255,45,85,.40)}
.card.a-dl:before{background:linear-gradient(90deg,transparent,rgba(255,45,85,.95),transparent)}
.card.a-dl .ct{color:#ff7d97}
.card.a-fl{background:linear-gradient(165deg,rgba(180,139,255,.16),rgba(10,6,16,.93) 62%);border-color:rgba(180,139,255,.38)}
.card.a-fl:before{background:linear-gradient(90deg,transparent,rgba(180,139,255,.9),transparent)}
.card.a-fl .ct{color:#cdaaff}
.card.a-dd{background:linear-gradient(165deg,rgba(255,138,61,.16),rgba(15,9,4,.93) 62%);border-color:rgba(255,138,61,.38)}
.card.a-dd:before{background:linear-gradient(90deg,transparent,rgba(255,138,61,.9),transparent)}
.card.a-dd .ct{color:#ffb47d}
.card.a-kom{background:linear-gradient(165deg,rgba(143,168,184,.14),rgba(8,11,13,.93) 62%);border-color:rgba(143,168,184,.34)}
.card.a-kom:before{background:linear-gradient(90deg,transparent,rgba(143,168,184,.85),transparent)}
.card.a-kom .ct{color:#a9c4d4}
.card.a-op{background:linear-gradient(165deg,rgba(56,189,248,.15),rgba(5,11,16,.93) 62%);border-color:rgba(56,189,248,.38)}
.card.a-op:before{background:linear-gradient(90deg,transparent,rgba(56,189,248,.9),transparent)}
.card.a-op .ct{color:#7dd3fc}
.fl-up{animation:flup .9s ease-out}.fl-dn{animation:fldn .9s ease-out}
@keyframes flup{0%{filter:brightness(2.4) drop-shadow(0 0 8px var(--grn))}100%{filter:none}}
@keyframes fldn{0%{filter:brightness(2.4) drop-shadow(0 0 8px var(--red))}100%{filter:none}}
/* ---------- layout ---------- */
.cols{flex:1;min-height:0;display:grid;gap:10px;margin-top:10px;overflow-y:auto;
grid-template-columns:minmax(0,1fr) 460px;
grid-template-rows:minmax(170px,1.9fr) auto minmax(72px,1fr);
grid-template-areas:"scan chart" "conf log" "pos log"}
.cols>.pan{display:flex;flex-direction:column;min-height:0;overflow:hidden}
#sec-scan{grid-area:scan}#sec-conf{grid-area:conf}#sec-pos{grid-area:pos}
#sec-ch{grid-area:chart}#sec-log{grid-area:log;overflow:hidden}
#sec-scan .tscroll,#sec-pos .tscroll{flex:1;min-height:0;overflow-y:auto}
#sec-conf .cfl{flex:1;min-height:0}
.pan{position:relative;background:var(--pan);border:1px solid var(--bd);
border-radius:6px;padding:10px 12px}
.pan:before{content:'';position:absolute;top:-1px;left:-1px;width:15px;height:15px;
border-top:2px solid var(--acc);border-left:2px solid var(--acc);
border-radius:6px 0 0 0;filter:drop-shadow(0 0 5px rgba(0,255,156,.7))}
.pan:after{content:'';position:absolute;bottom:-1px;right:-1px;width:15px;height:15px;
border-bottom:2px solid var(--acc);border-right:2px solid var(--acc);
border-radius:0 0 6px 0;filter:drop-shadow(0 0 5px rgba(0,255,156,.7))}
.pan h3{display:flex;align-items:center;gap:8px;font-size:10.5px;font-weight:800;
letter-spacing:.16em;color:var(--acc);text-shadow:0 0 9px rgba(0,255,156,.4);
border-bottom:1px solid var(--bd);padding-bottom:6px;margin-bottom:7px}
.pan h3 .ic{color:var(--grn)}
.pan h3 .rt{margin-left:auto;display:flex;gap:8px;align-items:center;
font-size:9px;letter-spacing:.12em}
.gn{color:var(--grn);animation:livePulse 1.8s ease-in-out infinite}
@keyframes livePulse{50%{opacity:.45}}
.gearbox{width:18px;height:18px;border:1px solid var(--bd2);border-radius:3px;
display:inline-flex;align-items:center;justify-content:center;color:var(--acc);font-size:10px}
/* ---------- sidebar ---------- */
.nav{display:flex;flex-direction:column;gap:4px;background:var(--pan);
border:1px solid var(--bd);border-radius:6px;padding:8px}
.nav .it{display:flex;align-items:center;gap:9px;padding:8px 10px;border-radius:4px;
font-size:10.5px;letter-spacing:.14em;color:var(--dim);cursor:pointer;
border:1px solid transparent;transition:all .15s}
.nav .it:hover{color:var(--tx);background:rgba(0,255,156,.05)}
.nav .it.act{color:#02150c;background:var(--acc);font-weight:800;
box-shadow:0 0 16px rgba(0,255,156,.45);text-shadow:none}
.verbox{background:var(--pan);border:1px solid var(--bd);border-radius:6px;
padding:9px 11px;display:flex;justify-content:space-between;align-items:center}
.verbox .nm{font-size:9px;letter-spacing:.2em;color:var(--dim)}
.verbox .vv{color:var(--acc);font-weight:800;text-shadow:0 0 8px rgba(0,255,156,.5)}
.sysbox{background:var(--pan);border:1px solid var(--bd);border-radius:6px;padding:10px 11px}
.sysbox .hd{font-size:9px;letter-spacing:.2em;color:var(--dim);margin-bottom:8px}
.kv{display:flex;justify-content:space-between;font-size:10.5px;padding:3px 0;
border-bottom:1px dashed rgba(0,255,156,.08)}
.kv span{color:var(--dim)}.kv b{color:var(--grn);font-weight:700}
/* ---------- tabs ---------- */
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px}
.tab{font-family:var(--f);font-size:9px;letter-spacing:.12em;padding:4px 10px;
background:transparent;color:var(--dim);border:1px solid var(--bd2);
border-radius:3px;cursor:pointer;transition:all .15s}
.tab:hover{color:var(--tx);border-color:var(--acc)}
.tab.act{background:var(--acc);color:#02150c;border-color:var(--acc);font-weight:800;
box-shadow:0 0 14px rgba(0,255,156,.4)}
/* ---------- tables ---------- */
.tscroll{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:11px}
th{font-size:8.5px;letter-spacing:.16em;color:var(--dim);text-align:left;
padding:5px 6px;border-bottom:1px solid var(--bd2);white-space:nowrap}
td{padding:5px 6px;border-bottom:1px solid rgba(13,44,29,.55);white-space:nowrap}
tbody tr{transition:background .12s;cursor:pointer}
tbody tr:hover{background:rgba(0,255,156,.05)}
tr.sel{background:rgba(0,255,156,.09);box-shadow:inset 3px 0 0 var(--acc)}
.mtag{font-size:7.5px;color:var(--amber);border:1px solid rgba(255,200,87,.5);
padding:1px 4px;border-radius:2px;margin-left:5px;letter-spacing:.1em}
td.sym{color:var(--tx);font-weight:700;letter-spacing:.05em}
.reg{font-size:9px;letter-spacing:.1em;padding:2px 7px;border-radius:2px;border:1px solid}
.reg-TREND{color:var(--grn);border-color:rgba(0,255,156,.4);background:rgba(0,255,156,.07)}
.reg-RANGE{color:var(--amber);border-color:rgba(255,200,87,.4);background:rgba(255,200,87,.06)}
.reg-BREAKOUT{color:var(--cy);border-color:rgba(0,224,255,.4);background:rgba(0,224,255,.06)}
.badge{font-size:9.5px;font-weight:800;letter-spacing:.1em;padding:2px 8px;border-radius:2px}
.b-buy{background:rgba(0,255,156,.14);color:var(--grn);border:1px solid rgba(0,255,156,.5);
text-shadow:0 0 8px rgba(0,255,156,.5)}
.b-sell{background:rgba(255,45,85,.12);color:var(--red);border:1px solid rgba(255,45,85,.5);
text-shadow:0 0 8px rgba(255,45,85,.5)}
.b-dash{color:var(--dim2);border:1px dashed var(--bd2)}
.st{font-size:9px;letter-spacing:.12em;padding:2px 7px;border-radius:2px;border:1px solid var(--bd2);color:var(--dim)}
.st-READY{color:#02150c;background:var(--grn);border-color:var(--grn);font-weight:800;
box-shadow:0 0 12px rgba(0,255,156,.5);animation:livePulse 2.2s ease-in-out infinite}
.st-TRADING{color:var(--cy);border-color:rgba(0,224,255,.55);box-shadow:0 0 10px rgba(0,224,255,.25)}
.st-SNIPER_WAIT{color:var(--amber);border-color:rgba(255,200,87,.5)}
td.pu{animation:flup .8s}td.pd{animation:fldn .8s}
.sbar{display:inline-block;width:58px;height:6px;vertical-align:middle;
background:rgba(0,255,156,.07);border:1px solid var(--bd2);border-radius:3px;overflow:hidden}
.sbar i{display:block;height:100%;background:linear-gradient(90deg,#00b863,var(--acc));
box-shadow:0 0 8px rgba(0,255,156,.55)}
.sbar.hot i{position:relative}
.swbtn{font-size:9px;font-weight:700;letter-spacing:.08em;padding:2px 7px;
border-radius:4px;border:1px solid #243057;background:#0a0f1e;color:#8a92b8;
cursor:pointer;font-family:var(--mon)}
.swbtn.on{color:#04120b;background:var(--grn);border-color:var(--grn)}
.swbtn.off{color:#ff5c6c;background:rgba(255,92,108,.08);border-color:#ff5c6c}
.sbar.hot i:after{content:'';position:absolute;inset:0;transform:translateX(-100%);
background:linear-gradient(90deg,transparent,rgba(255,255,255,.55),transparent);
animation:shimmer 1.5s linear infinite}
@keyframes shimmer{to{transform:translateX(100%)}}
.scpct{margin-left:6px;font-size:10.5px;font-weight:700}
.tbar{display:inline-flex;align-items:center;gap:5px;vertical-align:middle}
.tbar .tr{width:52px;height:5px;background:rgba(255,45,85,.1);border-radius:3px;overflow:hidden}
.tbar .tr i{display:block;height:100%;background:linear-gradient(90deg,#ff2d55,#ff7a95);
box-shadow:0 0 8px rgba(255,45,85,.5)}
.tbar .sq{width:6px;height:6px;border-radius:1px}
/* ---------- confluence ---------- */
.cfl{display:grid;grid-template-columns:158px 1fr 190px;gap:8px;align-items:center}
#globe{width:100%;height:176px;display:block}
.crow{display:grid;grid-template-columns:14px 108px 68px 1fr 34px;gap:7px;
align-items:center;font-size:9.5px;padding:3px 0}
.crow .ck{width:14px;height:14px;border-radius:50%;display:inline-flex;align-items:center;
justify-content:center;font-size:8px;color:#02150c;background:var(--grn);
box-shadow:0 0 8px rgba(0,255,156,.5)}
.crow .nm{color:var(--dim);letter-spacing:.08em}
.crow .word{font-size:9px;letter-spacing:.08em}
.w-bull{color:var(--grn)}.w-bear{color:var(--red)}.w-neu{color:var(--dim2)}
.crow .barr{height:6px;background:rgba(0,255,156,.06);border:1px solid var(--bd);
border-radius:3px;overflow:hidden}
.crow .barr i{display:block;height:100%;box-shadow:0 0 8px currentColor}
.crow .pc{text-align:right;color:var(--tx);font-weight:700}
.gaugewrap{text-align:center}
.gauge{width:150px;height:150px;margin:0 auto;border-radius:50%;position:relative;
background:conic-gradient(var(--gc,#00ff9c) var(--gp,0%),rgba(0,255,156,.06) 0);
animation:breathe 3.4s ease-in-out infinite}
@keyframes breathe{50%{filter:drop-shadow(0 0 16px rgba(0,255,156,.5))}}
.gauge:before{content:'';position:absolute;inset:0;border-radius:50%;
background:repeating-conic-gradient(rgba(2,6,4,.94) 0deg 4deg,transparent 4deg 10deg);
-webkit-mask:radial-gradient(farthest-side,transparent calc(100% - 17px),#000 calc(100% - 16px));
mask:radial-gradient(farthest-side,transparent calc(100% - 17px),#000 calc(100% - 16px))}
.gauge .in{position:absolute;inset:15px;border-radius:50%;background:var(--pan2);
border:1px solid var(--bd2);display:flex;flex-direction:column;
align-items:center;justify-content:center;box-shadow:inset 0 0 18px rgba(0,255,156,.08);color:var(--gc,#00ff9c)}
.gauge .big{font-size:18px;font-weight:800;text-shadow:0 0 14px currentColor}
.gauge .lbl{font-size:7.5px;letter-spacing:.22em;color:var(--dim);margin-top:2px}
.verdict{margin:5px auto 4px;font-size:12px;font-weight:800;letter-spacing:.18em}
.v-buy{color:var(--grn);text-shadow:0 0 14px rgba(0,255,156,.6)}
.v-sell{color:var(--red);text-shadow:0 0 14px rgba(255,45,85,.6)}
.v-wait{color:var(--dim)}
.entryvalid{display:inline-block;font-size:9.5px;letter-spacing:.2em;padding:4px 12px;
border:1px solid var(--bd2);border-radius:3px;color:var(--dim)}
.entryvalid.ok{color:var(--grn);border-color:rgba(0,255,156,.6);
box-shadow:0 0 14px rgba(0,255,156,.25),inset 0 0 10px rgba(0,255,156,.06);
text-shadow:0 0 8px rgba(0,255,156,.5)}
.why{font-size:9px;color:var(--dim);margin-top:7px;min-height:12px;letter-spacing:.04em}
/* ---------- chart ---------- */
.chhead{display:flex;align-items:center;gap:10px;padding-bottom:8px;
border-bottom:1px solid var(--bd);margin-bottom:8px}
.chhead .cs{font-size:14px;font-weight:800;color:var(--acc);
text-shadow:0 0 10px rgba(0,255,156,.45);letter-spacing:.06em}
.chhead .tf{font-size:9px;color:var(--dim);border:1px solid var(--bd2);
padding:2px 7px;border-radius:2px;letter-spacing:.12em}
.chhead .px{font-size:14px;font-weight:800;color:var(--tx)}
.chhead .chg{font-size:11px;font-weight:700}
.chhead .tools{margin-left:auto;color:var(--dim2);font-size:11px;letter-spacing:.3em}
#chart{width:100%;flex:1;min-height:60px;display:block}
/* ---------- log ---------- */
#log{flex:1;min-height:0;overflow-y:auto;font-size:10.5px;line-height:1.8;
background:repeating-linear-gradient(0deg,rgba(0,255,156,.018) 0 2px,transparent 2px 4px)}
.ln .ts{color:var(--dim2)}
.ln .tg{color:var(--acc);text-shadow:0 0 6px rgba(0,255,156,.35)}
.ln .tg-WARNING,.ln .tg-CLOSE,.ln .tg-ERROR{color:var(--red);text-shadow:0 0 6px rgba(255,45,85,.4)}
.ln .tg-FILL{color:var(--cy)}
.ln .mg .symhl{color:var(--acc);font-weight:700;text-shadow:0 0 7px rgba(0,255,156,.45)}
/* ---------- positions ---------- */
#pos td.num{font-variant-numeric:tabular-nums}
/* ---------- strip ---------- */
.strip{display:grid;grid-template-columns:repeat(3,1fr) 300px;gap:9px;margin-top:9px}
.mods{display:grid;grid-template-columns:1fr 1fr;gap:8px;align-content:start}
.mod{display:flex;align-items:center;gap:7px;background:rgba(2,9,6,.55);
border:1px solid var(--bd);border-radius:4px;padding:5px 8px}
.mod .ic{width:24px;height:24px;border:1px solid rgba(0,255,156,.4);border-radius:3px;
display:flex;align-items:center;justify-content:center;font-size:12px;
background:rgba(0,255,156,.06);filter:saturate(1.6)}
.mod .tx{display:flex;flex-direction:column;font-size:8.5px;letter-spacing:.1em;color:var(--dim)}
.mod .tx b{color:var(--tx);font-size:9px;letter-spacing:.12em}
.sv{font-weight:800}
.sv.on{color:var(--grn);text-shadow:0 0 7px rgba(0,255,156,.5)}
.sv.off{color:var(--red)}
.wmapbox{background:rgba(2,9,6,.55);border:1px solid var(--bd);border-radius:4px;
padding:8px;position:relative}
.wmapbox .wtag{position:absolute;top:6px;right:9px;font-size:8px;letter-spacing:.2em;
color:var(--dim);animation:livePulse 2s infinite}
#wmap{width:100%;height:84px;display:block}
.sessbox,.msessbox{background:rgba(2,9,6,.55);border:1px solid var(--bd);
border-radius:4px;padding:9px 11px}
.sessbox h4,.msessbox h4{font-size:8.5px;letter-spacing:.2em;color:var(--dim);margin-bottom:7px}
.sess{display:flex;justify-content:space-between;font-size:10px;padding:3px 0;letter-spacing:.06em}
.sess .ok{color:var(--grn)}.sess .no{color:var(--dim2)}
.sess .tm{color:var(--tx);margin-right:7px}
.mrow{margin-bottom:7px}
.mrow .mn{display:flex;justify-content:space-between;font-size:9px;
letter-spacing:.1em;color:var(--dim);margin-bottom:3px}
.mrow .bar{height:4px;background:rgba(0,255,156,.07);border-radius:2px;overflow:hidden}
.mrow .bar i{display:block;height:100%;background:linear-gradient(90deg,#00b863,var(--acc));
box-shadow:0 0 8px rgba(0,255,156,.5)}
/* ---------- statusbar ---------- */
.statusbar{display:flex;align-items:center;gap:9px;margin-top:10px;padding:7px 12px;
background:var(--pan);border:1px solid var(--bd);border-radius:6px;
font-size:10px;letter-spacing:.16em;flex-wrap:wrap}
.sinfo{margin-left:auto;font-size:9px;letter-spacing:.1em;color:var(--dim)}
.sinfo b{color:var(--grn);font-weight:700}
.led{width:8px;height:8px;border-radius:50%;background:var(--grn);
box-shadow:0 0 10px var(--grn);animation:ledPulse 1.6s ease-in-out infinite}
@keyframes ledPulse{50%{opacity:.35}}
#statusline{color:var(--grn);text-shadow:0 0 8px rgba(0,255,156,.4)}
.credit{margin-left:16px;font-size:9.5px;letter-spacing:.22em;
color:var(--amber);font-weight:700;text-shadow:0 0 9px rgba(255,200,87,.28);
white-space:nowrap}
@media (max-width:1250px){.cols{grid-template-columns:1fr;
grid-template-rows:auto auto auto auto auto;
grid-template-areas:"scan" "chart" "conf" "log" "pos"}
#log{height:300px;flex:none}#chart{height:200px;flex:none}
.strip{grid-template-columns:1fr 1fr}.cfl{grid-template-columns:1fr;text-align:center}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
</head>
<body>
<canvas id="mx"></canvas>
<div id="boot"><pre id="bootlines"></pre></div>
<main>
<div class="topbar">
  <div class="logo"><svg class="crown" viewBox="0 0 32 24" width="38" height="28" aria-hidden="true"><defs><linearGradient id="cg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffd75e"/><stop offset="1" stop-color="#d99900"/></linearGradient></defs><path d="M2 19 L2 8 L9.5 13.5 L16 2.5 L22.5 13.5 L30 8 L30 19 Z" fill="url(#cg)" stroke="#ffe08a" stroke-width="1"/><rect x="2" y="19.5" width="28" height="3" rx="1" fill="#d99900"/></svg><span class="brand glitch">RBT FX</span><span class="cur">▊</span>
    <small>TRADING ALGO SYSTEM &middot; UI-2 <b id="uiver" style="color:#5d9678;font-weight:700"></b></small></div>
  <div class="chips">
    <div class="chip grn"><span class="ci">⬢</span><span class="ct"><small>PYTHON ENGINE</small><b id="c-engine">-ONLINE</b></span></div>
    <div id="hb-alert" style="display:none;background:#7a1f1f;color:#ffd9d9;border:1px solid #ff6b6b;border-radius:10px;padding:8px 12px;margin:8px 0;font:600 13px system-ui">
      ⚠ ENGINE BENGONG — loop utama tidak aktif sejak <b id="hb-age">-</b>. Terminal MT5/VPS macet? Tutup MT5 & jalankan ulang MULAI_SEMUA.bat.
    </div>
    <div class="chip" id="c-mt5w"><span class="ci">⌁</span><span class="ct"><small id="c-mt5s">MTS</small><b id="c-mt5">CONNECTED</b></span></div>
    <div class="chip cy"><span class="ci">▣</span><span class="ct"><small>AKUN</small><b id="c-acc">-</b></span></div>
    <div class="chip grn"><span class="ci">⛨</span><span class="ct"><small>RISK MANAGER</small><b id="c-risk">ACTIVE</b></span></div>
    <div class="chip grn" id="c-dailyw"><span class="ci">✔</span><span class="ct"><small>DAILY PROTECTION</small><b id="c-daily">ACTIVE</b></span></div>
    <div class="chip grn" id="c-wkw"><span class="ci">☾</span><span class="ct"><small>WEEKEND GUARD</small><b id="c-wk">ACTIVE</b></span></div>
  </div>
  <span class="tclock num" id="c-time">--:--:--</span>
  <button id="halt" title="TRADING AKTIF — klik untuk HALT (hentikan order baru)">⚡ ON</button>
</div>
<div class="tape"><div class="tapein" id="tape"><span class="tseg">CONNECTING TO ENGINE...</span></div></div>
<div class="cards" id="cards"></div>
<div class="cols">
<div class="pan" id="sec-scan">
      <h3><span class="ic">⌕</span> MULTI-PAIR SCANNER
        <span class="rt"><span class="gn">● AUTO SCAN</span><span class="gearbox blink">⚙</span></span></h3>
      <div class="tabs" id="tabs">
        <button class="tab act" data-c="ALL">ALL</button>
        <button class="tab" data-c="FOREX">FOREX</button>
        <button class="tab" data-c="GOLD">GOLD/SILVER</button>
        <button class="tab" data-c="CRYPTO">CRYPTO</button>
        <button class="tab" data-c="INDEX">INDEX</button>
        <button class="tab" data-c="COMMODITY">COMMODITY</button>
      </div>
      <div class="tscroll">
      <table><thead><tr><th>#</th><th>SYMBOL</th><th>PRICE</th><th>SPREAD</th>
      <th>REGIME</th><th>SIGNAL</th><th>SCORE</th><th>TREND</th><th>STATUS</th><th style="width:52px">SW</th></tr></thead>
      <tbody id="scan"></tbody></table>
      </div>
    </div>

<div class="pan" id="sec-conf">
      <h3><span class="ic">⊗</span> STRATEGY CONFLUENCE <span style="color:var(--grn)" id="cf-sym">(-)</span></h3>
      <div class="cfl">
        <div><canvas id="globe"></canvas></div>
        <div><div id="cf-bars"></div></div>
        <div class="gaugewrap">
          <div class="gauge" id="gauge"><div class="in">
            <svg class="gglobe" viewBox="0 0 64 64" width="116" height="116"
                 fill="none" stroke="currentColor" stroke-width="1.7"
                 stroke-linecap="round" aria-hidden="true"
                 style="filter:drop-shadow(0 0 8px rgba(0,255,156,.5))">
              <circle cx="32" cy="32" r="26"/>
              <ellipse cx="32" cy="32" rx="12.5" ry="26" opacity=".8"/>
              <ellipse cx="32" cy="32" rx="5" ry="26" opacity=".5"/>
              <path d="M6 32h52"/>
              <path d="M9.5 21.5C19 16.8 45 16.8 54.5 21.5" opacity=".65"/>
              <path d="M9.5 42.5C19 47.2 45 47.2 54.5 42.5" opacity=".65"/>
            </svg>
            <div id="cf-score" style="display:none"></div>
          </div></div>
          <div class="verdict v-wait" id="cf-verdict">WAIT</div>
          <div class="entryvalid" id="cf-valid">ANALYZING</div>
          <div class="why" id="cf-why"></div>
        </div>
      </div>
    </div>

<div class="pan" id="sec-pos">
      <h3><span class="ic">⇄</span> ACTIVE POSITIONS (<span id="npos">0</span>)</h3>
      <div class="tscroll">
      <table><thead><tr><th>#</th><th>SYMBOL</th><th>TYPE</th><th>LOT</th><th>ENTRY</th>
      <th>SL</th><th>TP1</th><th>TP2</th><th>PRICE</th><th>P/L</th><th>P/L (R)</th>
      <th>STATUS</th></tr></thead><tbody id="pos"></tbody></table>
      </div>
    </div>

<div class="pan" id="sec-ch">
      <div class="chhead">
        <span class="cs" id="ch-sym">XAUUSD</span><span class="tf">M15</span>
        <span class="px num" id="ch-price">-</span>
        <span class="chg" id="ch-pct">-</span>
        <span class="tools">＋ － ⤢ ⚙</span>
      </div>
      <svg id="chart" viewBox="0 0 460 230" preserveAspectRatio="none"></svg>
    </div>

<div class="pan" id="sec-log">
      <h3><span class="ic">⌨</span> EXECUTION LOG :: PYTHON ENGINE
        <span class="rt"><span class="gn">● REAL-TIME</span><span class="gearbox blink">⚙</span></span></h3>
      <div id="log"></div>
    </div>
</div>
<div class="strip" id="sec-mod">
  <div class="mods" id="mods"></div>
  <div class="wmapbox"><span class="wtag">◈ GLOBAL FLOW</span><canvas id="wmap"></canvas></div>
  <div class="sessbox"><h4>[ SESSIONS ]</h4><div id="sess"></div></div>
  <div class="msessbox"><h4>[ MARKET SESSION ]</h4><div id="msess"></div></div>
</div>
<div class="statusbar"><span class="led"></span><span id="statusline">BOOTING SYSTEM...</span>
<span class="credit">Developer Ribut Prasetyoaji &nbsp;·&nbsp; 0811 347 1112 &nbsp;·&nbsp; Jombang Jawa Timur</span>
<span class="sinfo">RBT FX CORE <b id="c-ver">v3.42</b> &nbsp;·&nbsp; UPTIME <b id="c-upt">-</b>
&nbsp;·&nbsp; PING <b id="c-ping">-</b> &nbsp;·&nbsp; PAIRS <b id="c-pairs">-</b>
&nbsp;·&nbsp; LOOP <b id="c-loop">-</b></span></div>
</main>
<script>
window.onerror=function(m,u,l,c){try{var t=document.getElementById("tape");
if(t)t.innerHTML="<span class='tseg'>JS ERROR: "+m+" (baris "+l+")</span>";
var s=document.getElementById("statusline");
if(s){s.textContent="JS ERROR: "+m+" (baris "+l+")";s.style.color="var(--red)";}}catch(x){}
return false;};
function p2(x){return ("0"+x).slice(-2);}
</script>
<script>
const $=id=>document.getElementById(id);
const fmt=(v,d=2)=>Number(v).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});
const colFor=v=>v>=0?'var(--grn)':'var(--red)';
let SEL=null,TAB='ALL';
const P0={},C0={};
const fl=(k,v)=>{const p=C0[k];C0[k]=v;return p==null||v===p?'':v>p?'fl-up':'fl-dn'};
const CAT={XAUUSD:'GOLD',XAGUSD:'GOLD',GOLD:'GOLD',SILVER:'GOLD',
 EURUSD:'FOREX',GBPUSD:'FOREX',USDJPY:'FOREX',AUDUSD:'FOREX',NZDUSD:'FOREX',USDCHF:'FOREX',USDCAD:'FOREX',
 BTCUSD:'CRYPTO',ETHUSD:'CRYPTO',BTCUSDM:'CRYPTO',ETHUSDM:'CRYPTO',
 NAS100:'INDEX',USTEC:'INDEX',USTECM:'INDEX',US30:'INDEX',GER40:'INDEX',US100:'INDEX',
 USOIL:'COMMODITY',WTI:'COMMODITY',UKOIL:'COMMODITY',XTIUSD:'COMMODITY'};
const catOf=s=>{s=String(s).toUpperCase();if(CAT[s])return CAT[s];if(/^(XAU|XAG|GOLD|SILVER|XPT)/.test(s))return 'GOLD';if(/^(BTC|ETH|SOL|XRP|LTC|DOGE|ADA|XLM|BCH|DOT|LINK)/.test(s))return 'CRYPTO';if(/(NAS|USTEC|US100|US30|US500|GER|DAX|UK100|FTSE|JP225|NIKKEI|HK50|AUS200|SPX)/.test(s))return 'INDEX';if(/(OIL|WTI|BRENT|XBR)/.test(s))return 'COMMODITY';return 'FOREX';};
/* boot sequence */
(function(){const lines=['> INIT RBT FX SYSTEM v3.42','> PYTHON ENGINE ............ [OK]',
'> MULTI-PAIR SCANNER ....... [OK]','> RISK MANAGER ............. [OK]',
'> SNIPER PULLBACK-RESUME ... [OK]','> MATRIX UPLINK ............ [OK]','> ACCESS GRANTED_'];
const el=$('bootlines'),bx=$('boot');let i=0;
const t=setInterval(()=>{if(i>=lines.length){clearInterval(t);
 setTimeout(()=>bx.classList.add('hide'),650);return}
el.textContent+=lines[i++]+'\n';},210);})();
/* matrix rain background */
(function(){const cv=$('mx'),cx=cv.getContext('2d');
const rs=()=>{cv.width=innerWidth;cv.height=innerHeight};rs();addEventListener('resize',rs);
const P=Array.from({length:90},()=>({x:Math.random(),y:Math.random(),s:Math.random()*1.6+.4,v:.00002+Math.random()*.00007}));
setInterval(()=>{cx.clearRect(0,0,cv.width,cv.height);
P.forEach(p=>{p.y-=p.v;if(p.y<0)p.y=1;
cx.globalAlpha=.14+Math.random()*.22;cx.fillStyle='#00ff9c';
cx.fillRect(p.x*cv.width,p.y*cv.height,p.s,p.s);});cx.globalAlpha=1;},120);})();
/* rotating wireframe globe (hacker green) */
(function(){const cv=$('globe');if(!cv)return;const cx=cv.getContext('2d');
let W=0,H=0;const rs=()=>{const r=cv.parentElement.getBoundingClientRect();
W=cv.width=Math.max(210,r.width);H=cv.height=176;};rs();addEventListener('resize',rs);
const gr=.017453;let rot=0;
const rnd=(function(){let s=42;return()=>{s=(s*16807)%2147483647;return s/2147483647}})();
const stars=Array.from({length:26},()=>({lo:rnd()*360*gr,la:(rnd()*.9-.45)*gr,s:rnd()*1.3+.4}));
function pt(lo,la){const x=Math.cos(la)*Math.sin(lo+rot),z=Math.cos(la)*Math.cos(lo+rot),
y=Math.sin(la);return{x:W/2+x*H*.34,y:H/2-y*H*.34,z:z}}
function seg(a,b,al,w){const pa=pt(a[0],a[1]),pb=pt(b[0],b[1]);
const z=(pa.z+pb.z)/2;cx.strokeStyle='rgba(0,255,156,'+(al*(z*.75+.35)).toFixed(3)+')';
cx.lineWidth=w;cx.beginPath();cx.moveTo(pa.x,pa.y);cx.lineTo(pb.x,pb.y);cx.stroke();}
function draw(){cx.clearRect(0,0,W,H);
const g=cx.createRadialGradient(W/2,H/2,H*.05,W/2,H/2,H*.5);
g.addColorStop(0,'rgba(0,255,156,.26)');g.addColorStop(.55,'rgba(0,255,156,.08)');
g.addColorStop(1,'rgba(0,255,156,0)');
cx.fillStyle=g;cx.beginPath();cx.arc(W/2,H/2,H*.5,0,7);cx.fill();
cx.strokeStyle='rgba(0,255,156,.5)';cx.lineWidth=1.2;
cx.beginPath();cx.arc(W/2,H/2,H*.34,0,7);cx.stroke();
[-60,-30,0,30,60].forEach(la=>{const r=gr*la;for(let lo=0;lo<360;lo+=6)
seg([lo*gr,r],[(lo+6)*gr,r],.55,1);});
for(let lo=0;lo<360;lo+=30){const l=gr*lo;for(let a=-90;a<90;a+=6)
seg([l,a*gr],[l,(a+6)*gr],.4,1);}
stars.forEach(st=>{const p=pt(st.lo,st.la);
if(p.z>0){cx.fillStyle='rgba(120,255,200,'+(p.z*.9).toFixed(2)+')';
cx.beginPath();cx.arc(p.x,p.y,st.s,0,7);cx.fill();}});}
function loop(){rot+=.0045;draw();requestAnimationFrame(loop);}
if(!(window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches))loop();else draw();})();
/* dotted world map (green) */
(function(){const cv=$('wmap');if(!cv)return;const cx=cv.getContext('2d');
const MAP=["................########################################################",
"..............##############################################...........",
".........####################################################.###......",
"......###########################################################......",
"....####...#########################.####.####..############.######....",
"...####......######################...###..##......##########..####....",
"..#####........######..###########...........#.......#######....##.....",
".######..#......####....########................#.....####..............",
".######..........##......#####.......................##..........#......",
"..######..................####.........................#...............",
"..######...................###.................##......................",
"...#####....#...............##....#............###.......#.............",
"....####...##................#...##............####......#.............",
".....##....#....................###..#.........#####....##.............",
"......#........................####...........######....##.............",
"......##.......................###.............#####.....#..##.........",
"......###.......................#...............###.........##.........",
".......####.....................##....##........##..#.......#..........",
".......######....................#...###........#...........#..........",
"........########......................##...................##..........",
".........########.....................#...................##...........",
"..........#######.......................................................",
"...........#####.................####..........####.....................",
"............####................#####........#######...................",
".............###.................####.........#####....................",
"..............##...................#............##......................"];
function draw(){const r=cv.getBoundingClientRect();cv.width=r.width||420;cv.height=84;
cx.clearRect(0,0,cv.width,cv.height);
const cols=MAP[0].length,rows=MAP.length,cw=cv.width/cols,ch=cv.height/rows;
cx.fillStyle='rgba(0,255,156,.45)';
for(let y=0;y<rows;y++)for(let x=0;x<cols;x++)
if(MAP[y][x]==='#'){cx.beginPath();cx.arc(x*cw+cw/2,y*ch+ch/2,Math.min(cw,ch)*.32,0,7);cx.fill();}}
draw();addEventListener('resize',draw);})();
const CCY=s=>((s&&s.metrics&&s.metrics.account_currency)||'USD');
function mn(v,ccy){const a=Math.abs(v)>=1000?fmt(v,0):fmt(v,2);return a+' '+ccy;}
function mns(v,ccy){const a=Math.abs(v)>=1000?fmt(v,0):fmt(v,2);
return a+' <small>'+ccy+'</small>';}
function card(ic,t,v,sub,color,cls,acc){return '<div class="card '+(acc||'')+'"><div class="ct">'+
'<span class="ci">'+ic+'</span>'+t+
'</div><div class="v num '+(cls||'')+'" style="color:'+(color||'')+'">'+v+
'</div><div class="s">'+(sub||'')+'</div></div>';}
function wordFor(key,side,v){const bull=side==='BUY';
if(key==='liquidity')return v>=55?'Sweep':'None';
if(key==='trend')return v>=55?(bull?'Uptrend':'Downtrend'):(bull?'Downtrend':'Uptrend');
if(key==='momentum')return v>=55?'Strong':'Weak';
if(key==='volume')return v>=55?'Confirmed':'Outside';
if(key==='structure')return v>=55?(bull?'Bullish':'Bearish'):(bull?'Bearish':'Bullish');
return v>=55?(bull?'Bullish':'Bearish'):(bull?'Bearish':'Bullish');}
function statusHTML(r){if(r.status==='SNIPER_WAIT')return '<span class="st st-SNIPER_WAIT">WAIT</span>';
return '<span class="st st-'+r.status+'">'+r.status+'</span>';}
function renderCF(s){const top=(SEL&&s.scanner.find(r=>r.symbol===SEL))||
(s.confluence&&s.scanner.find(r=>r.symbol===s.confluence.symbol))||s.scanner[0];
if(!top)return;
$('cf-sym').textContent='( '+top.symbol+' - '+(top.score>=70?top.signal:'-')+' )';
const nm=[['structure','MARKET STRUCTURE'],['liquidity','LIQUIDITY (SMC)'],
 ['trend','TREND FILTER'],['momentum','MOMENTUM'],['volume','VOLUME'],
 ['orderflow','ORDER FLOW']];
$('cf-bars').innerHTML=nm.map(([k,n])=>{const v=top.components[k]||0;
const w=wordFor(k,top.signal==='BUY'?'BUY':'SELL',v);
const wc=(w==='Bullish'||w==='Uptrend')?'w-bull':
 (w==='None'||w==='Outside'||w==='Weak')?'w-neu':'w-bear';
const c=(w==='Bullish'||w==='Uptrend')?'var(--grn)':
 (w==='None'||w==='Outside'||w==='Weak')?'var(--dim2)':'var(--red)';
return '<div class="crow"><span class="ck">✔</span><span class="nm">'+n+
 '</span><span class="word '+wc+'">'+w+'</span><div class="barr" style="color:'+c+'">'+
 '<i style="width:'+v+'%;background:'+c+'"></i></div>'+
 '<span class="pc">'+v.toFixed(0)+'%</span></div>';}).join('');
const sc=top.score,cc=sc>=70?(top.signal==='BUY'?'#00ff9c':'#ff2d55'):
 sc>=55?'#ffc857':'#2a5440';
$('cf-score').textContent=sc.toFixed(0)+'%';
$('cf-score').style.color=cc;
const g=$('gauge');g.style.setProperty('--gp',sc+'%');g.style.setProperty('--gc',cc);
const v=$('cf-verdict');
if(top.status==='READY'||top.status==='TRADING'){
 v.className='verdict '+(top.signal==='BUY'?'v-buy':'v-sell');
 v.textContent=(top.signal==='BUY'?'BUY ▲':'SELL ▼');}
else{v.className='verdict v-wait';v.textContent='WAIT';}
const vd=$('cf-valid');
vd.textContent=(top.status==='READY'||top.status==='TRADING')?'[ ENTRY VALID ]':
 top.status==='SNIPER_WAIT'?'[ HOLD - CARI MOMEN ]':'[ STAND BY ]';
vd.className='entryvalid'+((top.status==='READY'||top.status==='TRADING')?' ok':'');
$('cf-why').textContent=top.block_why?('>> '+top.block_why):
 (top.sniper_why?('>> sniper: '+top.sniper_why):'');
drawChart(top.ohlc,top.sl,top.tp,top);}
function drawChart(ohlc,sl,tp,top){const svg=$('chart');
$('ch-sym').textContent=top?top.symbol:'-';
if(!ohlc||!ohlc.length){svg.innerHTML='';return}
const Wp=460,H=230,P=8,VH=34;let lo=1e18,hi=-1e18;
ohlc.forEach(k=>{lo=Math.min(lo,k[3]);hi=Math.max(hi,k[2])});
[sl,tp].forEach(v=>{if(v&&v>0){lo=Math.min(lo,v);hi=Math.max(hi,v)}});
const rng=(hi-lo)||1;lo-=rng*.06;hi+=rng*.06;
const y=v=>P+(H-2*P-VH)*(1-(v-lo)/(hi-lo));
const bw=(Wp-2*P)/ohlc.length;
let out='',vmax=0.0001;
for(let g=1;g<5;g++){const gy=P+(H-2*P-VH)*g/5;
out+='<line x1="0" x2="'+Wp+'" y1="'+gy+'" y2="'+gy+
 '" stroke="rgba(0,255,156,.05)" stroke-dasharray="2 4"/>';}
ohlc.forEach(k=>{vmax=Math.max(vmax,k[2]-k[3])});
ohlc.forEach((k,i)=>{const x=P+i*bw+bw/2,up=k[4]>=k[1];
const c=up?'#00ff9c':'#ff2d55';
const hv=(k[2]-k[3])/vmax*VH;
out+='<rect x="'+(x-bw*0.3)+'" y="'+(H-P-hv)+'" width="'+(bw*0.6)+
 '" height="'+hv+'" fill="'+c+'" opacity="0.22"/>';
out+='<line x1="'+x+'" x2="'+x+'" y1="'+y(k[2])+'" y2="'+y(k[3])+
 '" stroke="'+c+'" stroke-width="1"/>';
const tp2=y(Math.max(k[1],k[4])),bt=y(Math.min(k[1],k[4]));
out+='<rect x="'+(x-bw*0.32)+'" y="'+tp2+'" width="'+(bw*0.64)+
 '" height="'+Math.max(1,bt-tp2)+'" fill="'+c+'"/>';});
[sl,tp].forEach((v,i)=>{if(v&&v>0){const c=i===0?'#ff2d55':'#00e0ff';
out+='<line x1="0" x2="'+Wp+'" y1="'+y(v)+'" y2="'+y(v)+
 '" stroke="'+c+'" stroke-width="1" stroke-dasharray="5 4" opacity=".9"/>';
out+='<text x="4" y="'+(y(v)-3)+'" fill="'+c+'" font-size="8" font-family="monospace">'+
 (i===0?'SL':'TP')+'</text>';}});
const step=Math.max(1,Math.floor(ohlc.length/6));
ohlc.forEach((k,i)=>{if(i%step)return;const d=new Date(k[0]*1000);
const lbl=p2(d.getUTCHours())+':'+p2(d.getUTCMinutes());
out+='<text x="'+(P+i*bw)+'" y="'+(H-2)+'" fill="#3f6d54" font-size="7.5" '+
 'font-family="monospace" text-anchor="middle">'+lbl+'</text>';});
if(top){const last=ohlc[ohlc.length-1],ly=y(last[4]);
out+='<line x1="0" x2="'+(Wp-58)+'" y1="'+ly+'" y2="'+ly+
 '" stroke="#00ff9c" stroke-width="0.6" stroke-dasharray="2 3" opacity=".45"/>';
out+='<circle cx="'+(Wp-60)+'" cy="'+ly+'" r="3" fill="#00ff9c">'+
 '<animate attributeName="r" values="2;5;2" dur="1.5s" repeatCount="indefinite"/>'+
 '<animate attributeName="opacity" values="1;.25;1" dur="1.5s" repeatCount="indefinite"/></circle>';
out+='<rect x="'+(Wp-56)+'" y="'+(ly-9)+'" width="52" height="16" rx="2" fill="#00ff9c"/>';
out+='<text x="'+(Wp-30)+'" y="'+(ly+3)+'" text-anchor="middle" fill="#02150c" '+
 'font-size="9" font-weight="800" font-family="monospace">'+
 Number(last[4]).toLocaleString('en-US',{maximumFractionDigits:2})+'</text>';
$('ch-price').textContent=fmt(last[4],top.digits!=null?top.digits:2);
const first=ohlc[0][4],chg=(last[4]-first)/first*100;
$('ch-pct').textContent=(chg>=0?'▲ +':'▼ ')+chg.toFixed(2)+'%';
$('ch-pct').style.color=chg>=0?'var(--grn)':'var(--red)';}
svg.innerHTML=out;}
function tapeHTML(s){const items=s.scanner.map(r=>{
const px=fmt(r.price,r.digits),pc=r.trend_pct;
const dir=pc>=0,cls=dir?'tup':'tdn',ar=dir?'▲':'▼';
return '<span class="tpit"><span class="tsym">'+r.symbol+'</span>'+
 '<span class="tpx">'+px+'</span><span class="'+cls+'">'+ar+' '+
 Math.abs(pc).toFixed(2)+'%</span></span>';}).join('');
return '<span class="tseg">'+items+'</span><span class="tseg">'+items+'</span>';}
function tick(){fetch('api/status').then(function(r){return r.json();}).then(function(s0){try{
const s=s0;
if(s.error){$('statusline').textContent=s.error==='auth'?
 'AKSES DITOLAK — LOGIN ULANG (refresh halaman, masukkan password)':'ENGINE ERROR';
$('statusline').style.color='var(--red)';return;}
$('c-engine').textContent='-ONLINE v'+s.version;
if(window.__ev===undefined){window.__ev=s.version;}
else if(window.__ev!==s.version){location.reload();return;}
var _uv=$('uiver');if(_uv){_uv.textContent=' \u00b7 UI-2 v'+s.version;}
var hb=$('hb-alert');if(hb){if(s.engine_stale){hb.style.display='block';$('hb-age').textContent=Math.round((s.hb_age||0)/60)+' menit lalu';}else{hb.style.display='none';}}
const mw=$('c-mt5w');
$('c-mt5s').textContent='MTS ('+(s.account.server||'BROKER')+')';
if(s.mode==='LIVE'){$('c-mt5').textContent='CONNECTED';mw.className='chip grn';}
else{$('c-mt5').textContent='SIMULASI';mw.className='chip amber';}
$('c-acc').textContent=s.mode+' #'+s.account.login;
$('c-time').textContent=(s.ts_wib||s.ts).substr(11)+' WIB';
const rw=$('c-risk'),dw=$('c-dailyw');
if(s.risk.trade_on){rw.className='chip grn';$('c-risk').textContent='ACTIVE';}
else if(s.risk.pause_until>0){rw.className='chip amber';$('c-risk').textContent='PAUSED';}
else{rw.className='chip red';$('c-risk').textContent='HALTED';}
if(!s.risk.halted){dw.className='chip grn';$('c-daily').textContent='ACTIVE';}
else{dw.className='chip red';$('c-daily').textContent='LOSS LIMIT';}
$('c-wk').textContent='ACTIVE';
const m=s.metrics;
const K=CCY(s);
const rp=v=>{const n=Math.abs(v);return (n>=1000?fmt(n,0):fmt(n,2))};
$('tape').innerHTML=tapeHTML(s);
$('cards').innerHTML=[
 card('◈','BALANCE',mns(m.balance,K),'SALDO AKUN','var(--amber)',
      fl('bal',m.balance),'a-bal'),
 card('◉','EQUITY',mns(m.equity,K),
      (m.equity-m.balance>=0?'+':'-')+
      fmt(m.balance>0?Math.abs(m.equity-m.balance)/m.balance*100:0,2)+'% vs saldo',
      colFor(m.equity-m.balance),fl('eq',m.equity),'a-eq'),
 card('▲','DAILY PROFIT',(m.daily_profit>=0?'+':'-')+rp(m.daily_profit)+
      ' <small>'+K+'</small>',
      'dari posisi ditutup (bot+manual)',
      colFor(m.daily_profit),fl('dp',m.daily_profit),'a-dp'),
 card('▼','DAILY LOSS','-'+rp(m.daily_loss_abs||0)+' <small>'+K+'</small> ('+
      fmt(m.daily_loss,2)+'%)',
      'realized | limit '+fmt(m.limit_used_pct,0)+'% terpakai',
      'var(--amber)','','a-dl'),
 card('≈','FLOATING TERBUKA',(m.floating_open>=0?'+':'-')+
      rp(m.floating_open)+' <small>'+K+'</small>',
      s.positions.length+' posisi jalan (bukan daily)',
      colFor(m.floating_open),fl('fl2',m.floating_open),'a-fl'),
 card('⚠','DRAWDOWN','-'+fmt(m.drawdown_pct,2)+'%',
      'Peak: '+mn(m.day_peak,K),'var(--red)','','a-dd'),
 card('¤','KOMISI/FEE ['+(m.account_model||'?')+']','-'+rp(m.commission_today||0)+' <small>'+K+'</small>',
      'Fee & Swap','','','a-kom'),
 card('▣','OPEN POSITIONS',s.positions.length+' / 5',
      (m.floating>=0?'+':'-')+rp(m.floating)+' '+K+' Float','var(--cy)',
      fl('fl',m.floating),'a-op')
].join('');
$('scan').innerHTML=s.scanner.map((r,i)=>{const sig=r.score>=70?r.signal:'-';
const tb=Math.round(r.trend_pct);
if(TAB!=='ALL'&&catOf(r.symbol)!==TAB)return '';
const p0=P0[r.symbol];P0[r.symbol]=r.price;
const pd=p0==null?'':r.price>p0?'pu':r.price<p0?'pd':'';
const hot=r.score>=70?' hot':'';
return '<tr data-sym="'+r.symbol+'" class="'+(SEL===r.symbol?'sel':'')+'">'+
 '<td style="color:var(--dim2)">'+p2(i+1)+'</td>'+
 '<td class="sym">'+r.symbol+'</td>'+
 '<td class="num '+pd+'">'+fmt(r.price,r.digits)+'</td>'+
 '<td class="num" style="color:var(--dim)">'+r.spread+'</td>'+
 '<td><span class="reg reg-'+r.regime.split(' ')[0]+'">'+r.regime.split(' ')[0]+'</span></td>'+
 '<td><span class="badge '+(sig==='BUY'?'b-buy':sig==='SELL'?'b-sell':'b-dash')+'">'+sig+'</span></td>'+
 '<td><span class="sbar'+hot+'"><i style="width:'+r.score.toFixed(0)+
 '%"></i></span><span class="scpct" style="color:'+(r.score>=70?'var(--grn)':
 r.score>=55?'var(--amber)':'var(--dim)')+'">'+r.score.toFixed(0)+'%</span></td>'+
 '<td><div class="tbar"><div class="tr"><i style="width:'+tb+'%"></i></div>'+
 '<span class="sq" style="background:'+(tb>=55?'var(--grn)':'var(--red)')+'"></span></div></td>'+
 '<td>'+statusHTML(r)+'</td>'+
 '<td><button class="swbtn'+(r.sw?' on':' off')+'" data-sw="'+r.symbol+
 '">'+(r.sw?'ON':'OFF')+'</button></td></tr>';}).join('')||
 '<tr><td colspan="10" style="text-align:center;color:var(--dim2)">[ tidak ada pair di kategori ini ]</td></tr>';
document.querySelectorAll('#scan tr').forEach(tr=>tr.onclick=()=>{
 if(tr.dataset.sym){SEL=tr.dataset.sym;renderCF(s);}});
document.querySelectorAll('#scan .swbtn').forEach(function(b){b.onclick=function(ev){
ev.preventDefault();ev.stopPropagation();
var sym=b.dataset.sw,on=b.textContent!=='ON';
fetch('api/pair_switch',{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({symbol:sym,on:on})}).then(function(){tick();})
.catch(function(){});};});
renderCF(s);
$('npos').textContent=s.positions.length;
$('pos').innerHTML=s.positions.map((p,i)=>{const pt=p.point||0;
const dir=p.type==='BUY'?1:-1;
const slPts=(p.sl&&pt)?Math.abs(p.entry-p.sl)/pt:0;
const r=slPts?((dir*(p.price-p.entry)/pt)/slPts):null;
return '<tr style="cursor:default"><td style="color:var(--dim2)">'+
 p2(i+1)+'</td><td class="sym">'+p.symbol+
 (p.manual?'<span class="mtag">MANUAL</span>':'')+
 '</td><td><span class="badge '+(p.type==='BUY'?'b-buy':'b-sell')+'">'+p.type+
 '</span></td><td class="num">'+p.lot.toFixed(2)+
 '</td><td class="num">'+fmt(p.entry,p.digits||2)+
 '</td><td class="num" style="color:var(--red)">'+(p.sl?fmt(p.sl,p.digits||2):'-')+
 '</td><td class="num" style="color:var(--cy)">'+(p.tp?fmt(p.tp,p.digits||2):'-')+
 '</td><td class="num" style="color:var(--dim)">-</td>'+
 '<td class="num">'+fmt(p.price,p.digits||2)+'</td>'+
 '<td class="num" style="color:'+colFor(p.pl)+';font-weight:700">'+
 (p.pl>=0?'+':'')+fmt(p.pl)+'</td>'+
 '<td class="num" style="color:'+(r==null?'var(--dim)':colFor(r))+'">'+
 (r==null?'-':(r>=0?'+':'')+r.toFixed(2)+'R')+'</td>'+
 '<td><span class="st '+(p.trailing?'st-TRADING':'st-SNIPER_WAIT')+'">'+
 (p.trailing?'Trailing':'Open')+'</span></td></tr>';}).join('')||
 '<tr><td colspan="12" style="text-align:center;color:var(--dim2)">[ belum ada posisi terbuka ]</td></tr>';
$('log').innerHTML=s.log.slice().reverse().map(l=>{
let mg=l.msg;
const ms=mg.match(/^([A-Z]{3,6}\d*)\s([\s\S]*)$/);
if(ms)mg='<span class="symhl">'+ms[1]+'</span> '+ms[2];
return '<div class="ln"><span class="ts">['+l.ts+']</span><span class="tg tg-'+
 l.tag+'">[ '+l.tag+' ]</span> <span class="mg">'+mg+'</span></div>';}).join('')+
 '<div class="ln"><span class="ts">root@rbt-fx:~$</span> <span class="cur">▊</span></div>';
const mods=[['📡','SCANNER',s.modules.scanner],['🧭','STRATEGY',s.modules.strategy],
 ['🛡','RISK MANAGER',s.modules.risk],['⚡','TRADE ENGINE',s.modules.trade],
 ['🎯','TRAILING SYSTEM',s.modules.trailing],['📰','NEWS FILTER',s.modules.news]];
$('mods').innerHTML=mods.map(x=>'<div class="mod"><span class="ic">'+x[0]+
 '</span><span class="tx"><b>'+x[1]+'</b><span class="sv '+
 (x[2]?'on':'off')+'">'+(x[2]?'[ON]':'[OFF]')+'</span></span></div>').join('');
const HRS={SYDNEY:[21,6],TOKYO:[0,9],LONDON:[7,16],'NEW YORK':[12,21]};
const now=new Date(s.ts.replace(' ','T')+'Z');
const hr=now.getUTCHours()+now.getUTCMinutes()/60;
$('sess').innerHTML=Object.keys(s.sessions).map(function(k){var v=s.sessions[k];return '<div class="sess">'+
 '<span><span class="'+(v.open?'ok':'no')+'">●</span> '+k+'</span>'+
 '<span><span class="tm">'+p2(now.getUTCHours())+':'+
 p2(now.getUTCMinutes())+'</span>'+
 '<span class="'+(v.open?'ok':'no')+'">'+(v.open?'(Open)':'(Closed)')+'</span></span></div>';}).join('');
$('msess').innerHTML=Object.keys(HRS).map(function(k){var a=HRS[k][0],z=HRS[k][1];
 let f=0;const len=(z>=a)?(z-a):(z+24-a);
 const cur=(hr>=a)?(hr-a):(hr+24-a);
 f=(cur>=0&&cur<len)?cur/len:0;
 return '<div class="mrow"><div class="mn"><span>'+k+'</span><span>'+
 (f>0?'Open':'Closed')+'</span></div><div class="bar"><i style="width:'+
 (f*100).toFixed(0)+'%"></i></div></div>';}).join('');
const up=s.uptime_min;
$('c-upt').textContent=(up>=1440?Math.floor(up/1440)+'D ':'')+
 p2(Math.floor(up/60)%24)+':'+p2(up%60);
$('c-ping').textContent=s.ping_ms+' ms';
$('c-pairs').textContent=s.scanner.length;
var _cnt={};s.scanner.forEach(function(r){var _c=catOf(r.symbol);_cnt[_c]=(_cnt[_c]||0)+1;});
document.querySelectorAll('.tab').forEach(function(b){var _c=b.dataset.c;
 var _n=_c==='ALL'?s.scanner.length:(_cnt[_c]||0);
 if(!b.dataset.lb){b.dataset.lb=b.textContent;}
 b.textContent=b.dataset.lb+' ('+_n+')';});
$('c-loop').textContent=s.loop_ms+' ms';
const halt=s.risk.manual_halt;
$('halt').textContent=halt?'⏸ OFF':'⚡ ON';
$('halt').className=halt?'':'resume';
$('halt').title=halt?'TRADING BERHENTI (MANUAL HALT) — klik untuk ON lagi':'TRADING AKTIF — klik untuk HALT (hentikan order baru)';
$('statusline').textContent=s.risk.halted?'TRADING HALTED — DAILY LOSS LIMIT ACTIVE':
 halt?'MANUAL HALT — NO NEW ORDERS':
 s.connected?'ALL SYSTEMS OPERATIONAL ['+s.mode+']':'LINK DOWN - RETRYING...';
$('statusline').style.color=(s.risk.halted||halt)?'var(--red)':'var(--grn)';
}catch(e){$('statusline').textContent='⚠ DATA ERROR: '+e.message;$('statusline').style.color='var(--red)';}
},function(e){$('statusline').textContent='⚠ ENGINE OFFLINE — SERVER BELUM JALAN / PREVIEW PUTUS. MUAT ULANG HALAMAN (Ctrl+Shift+R)';
$('statusline').style.color='var(--red)';
$('tape').innerHTML='<span class="tseg"><span class="tpit"><span class="tsym">OFFLINE</span>'+
 '<span class="tdn">engine tidak terjangkau — refresh browser / jalankan MULAI_SEMUA.bat</span></span></span>';});
}
$('halt').onclick=function(){fetch('api/halt',{method:'POST'}).then(function(){tick();});};
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{
 document.querySelectorAll('.tab').forEach(x=>x.classList.remove('act'));
 t.classList.add('act');TAB=t.dataset.c;tick();});
tick();setInterval(tick,2000);

</script>

</body></html>
"""


def json_default(o):
    """Pengaman terakhir: tipe numpy/aset lain -> python murni utk JSON."""
    try:
        import numpy as _np
        if isinstance(o, _np.integer):
            return int(o)
        if isinstance(o, _np.floating):
            return float(o)
        if isinstance(o, _np.ndarray):
            return o.tolist()
    except Exception:
        pass
    if isinstance(o, (set, tuple)):
        return list(o)
    return str(o)


# v4.32: mirror python dari catOf() frontend -- utk /api/selfcheck
_SC_GOLD = re.compile(r"^(XAU|XAG|GOLD|SILVER|XPT)")
_SC_CRY = re.compile(r"^(BTC|ETH|SOL|XRP|LTC|DOGE|ADA|XLM|BCH|DOT|LINK)")
_SC_IDX = re.compile(r"(NAS|USTEC|US100|US30|US500|GER|DAX|UK100|FTSE|JP225|NIKKEI|HK50|AUS200|SPX)")
_SC_COM = re.compile(r"(OIL|WTI|BRENT|XBR)")


def _selfcheck_cat(s):
    s0 = str(s or "").upper()
    if _SC_GOLD.match(s0): return "GOLD"
    if _SC_CRY.match(s0): return "CRYPTO"
    if _SC_IDX.search(s0): return "INDEX"
    if _SC_COM.search(s0): return "COMMODITY"
    return "FOREX"


def make_handler(cc, password=""):
    _token = hashlib.sha256(("rbt-fx:" + password).encode()).hexdigest()[:32] \
        if password else ""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # senyapkan access log
            pass

        def _send(self, code, body, ctype="text/html; charset=utf-8"):
            data = body.encode("utf-8")
            try:
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)
            except (ConnectionError, BrokenPipeError, socket.timeout,
                    OSError):
                pass          # klien putus (refresh/tutup tab/sinyal) --
                              #   BENIN utk trading, jangan berisik

        def _authed(self):
            if not _token:
                return True
            want = "rbt_auth=" + _token
            ck = self.headers.get("Cookie", "") or ""
            return any(c.strip() == want for c in ck.split(";"))

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                if not self._authed():
                    self._send(401, PAGE_LOGIN)
                    return
                self._send(200, PAGE)
            elif self.path == "/api/status":
                if not self._authed():
                    self._send(401, '{"error":"auth"}', "application/json")
                    return
                try:
                    st = cc.get_status()
                except Exception as e:
                    st = {"error": str(e)}
                self._send(200, json.dumps(st, default=json_default),
                           "application/json")
            elif self.path == "/api/selfcheck":
                # v4.32: bukti ground-truth tanpa JS (bisa difoto):
                # jumlah pair per kategori + daftar simbol mentah
                if not self._authed():
                    self._send(401, '{"error":"auth"}', "application/json")
                    return
                try:
                    st = cc.get_status()
                    rows = st.get("scanner") or []
                    cat = {}
                    for r in rows:
                        c = _selfcheck_cat(r.get("symbol"))
                        cat[c] = cat.get(c, 0) + 1
                    out = {"ok": True, "ui": "UI-2",
                           "version": st.get("version"),
                           "scanner": len(rows), "cat": cat,
                           "symbols": [r.get("symbol") for r in rows],
                           "gold_rows": [{"symbol": r.get("symbol"),
                                          "status": r.get("status"),
                                          "score": r.get("score")}
                                         for r in rows
                                         if _selfcheck_cat(r.get("symbol"))
                                         == "GOLD"]}
                    self._send(200, json.dumps(out, default=json_default),
                               "application/json")
                except Exception as e:
                    self._send(200, json.dumps({"ok": False,
                                                "error": str(e)}),
                               "application/json")
            else:
                self._send(404, "not found", "text/plain")

        def do_POST(self):
            if self.path == "/login":
                n = int(self.headers.get("Content-Length", 0) or 0)
                body = self.rfile.read(n).decode("utf-8", "ignore")
                pw = (parse_qs(body).get("password") or [""])[0]
                if password and pw == password:
                    data = b'{"ok":true}'
                    try:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(data)))
                        self.send_header("Set-Cookie", "rbt_auth=" + _token +
                                         "; Path=/; HttpOnly; SameSite=Lax; Max-Age=31536000")
                        self.send_header("Cache-Control", "no-store")
                        self.end_headers()
                        self.wfile.write(data)
                    except (ConnectionError, BrokenPipeError, socket.timeout,
                            OSError):
                        pass          # klien putus -> benin
                else:
                    self._send(401, '{"ok":false}', "application/json")
                return
            if self.path == "/api/update":
                if not self._authed():
                    self._send(401, '{"error":"auth"}', "application/json")
                    return
                if cc_selfupdate is None:
                    self._send(500, json.dumps({"ok": False,
                                "error": "modul cc_selfupdate tidak ada"}),
                               "application/json")
                    return
                try:
                    files, err = cc_selfupdate.run()
                except Exception as e:
                    files, err = None, str(e)
                if files is None:
                    self._send(500, json.dumps({"ok": False,
                                "error": err, "updated": 0}),
                               "application/json")
                    return
                self._send(200, json.dumps({"ok": True,
                            "updated": len(files), "files": files}),
                           "application/json")
                # restart SETELAH jawaban terkirim
                try:
                    cc.request_restart(delay=1.2)
                except Exception:
                    pass
                return
            if self.path == "/api/halt":
                if not self._authed():
                    self._send(401, '{"error":"auth"}', "application/json")
                    return
                cc.toggle_halt()
                self._send(200, json.dumps({"ok": True}), "application/json")
            elif self.path == "/api/pair_switch":
                # v4.34 (user): switch ON/OFF per pair -- OFF = pair tidak
                # dianalisa/ditradingkan. Default semua OFF.
                if not self._authed():
                    self._send(401, '{"error":"auth"}', "application/json")
                    return
                try:
                    n = int(self.headers.get("Content-Length", 0) or 0)
                    b = json.loads(self.rfile.read(n).decode("utf-8",
                                                             "ignore") or "{}")
                    sym = str(b.get("symbol") or "").upper()
                    on = bool(b.get("on"))
                    if not sym:
                        raise ValueError("symbol kosong")
                    cc.set_pair_switch(sym, on)
                    self._send(200, json.dumps(
                        {"ok": True, "symbol": sym, "sw": on}),
                        "application/json")
                except Exception as e:
                    self._send(400, json.dumps({"ok": False,
                                                "error": str(e)}),
                               "application/json")
            else:
                self._send(404, "not found", "text/plain")

    return Handler


class QuietServer(ThreadingHTTPServer):
    """HTTP server tenang: klien yang memutus koneksi sendiri (WinError
    10053/10054, broken pipe, timeout) = NORMAL utk dashboard -- cukup 1
    baris ringkas, JANGAN traceback penuh (mengganggu konsol user).
    Error lain tetap ditampilkan penuh."""

    def handle_error(self, request, client_address):
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionError, BrokenPipeError,
                            socket.timeout, TimeoutError)):
            print("[WEB] klien %s memutus koneksi (normal, aman)"
                  % (client_address[0] if client_address else "?"))
            return
        super().handle_error(request, client_address)


def make_server(cc, port=8080, password=""):
    srv = QuietServer(("0.0.0.0", int(port)), make_handler(cc, password))
    return srv
