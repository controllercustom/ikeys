/*
 * MIT License
 *
 * Copyright (c) 2026 controllercustom@myyahoo.com
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

#ifndef WEBPAGE_H
#define WEBPAGE_H

#include <Arduino.h>

const char index_html[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="mobile-web-app-capable" content="yes">
    <title>iKeys v0.4 Keyboard</title>
    <style>
        :root {
            --bg-chassis: #e0e0d1;
            --pale-yellow: #fdf6be;
            --deep-navy: #1a2b4c;
            --border-color: #dcd3a0;
            --key-shadow-inset: inset -2px -2px 4px rgba(0,0,0,0.1), 2px 2px 5px rgba(0,0,0,0.2);
        }
        html, body {
            margin: 0; padding: 0;
            width: 100%; height: 100%;
            overflow: hidden;
            font-family: Helvetica, Arial, sans-serif;
            background-color: var(--bg-chassis);
            display: flex;
            flex-direction: column;
            -webkit-touch-callout: none;
            -webkit-user-select: none;
            user-select: none;
            touch-action: none;
        }

        #debug {
            background: #333; color: #0f0;
            font-family: monospace; font-size: 12px;
            padding: 2px 8px;
            white-space: nowrap; overflow: hidden;
            display: flex; align-items: center; gap: 8px;
            flex-shrink: 0; height: 24px; box-sizing: border-box;
        }

        #grid, #numpad {
            flex: 1;
            display: grid;
            gap: 4px;
            padding: 4px;
            box-sizing: border-box;
            min-height: 0;
        }
        #grid {
            grid-template-columns: repeat(12, 1fr);
            grid-template-rows: repeat(8, 1fr);
        }
        #numpad {
            display: none;
            grid-template-columns: repeat(12, 1fr);
            grid-template-rows: repeat(8, 1fr);
        }

        .key {
            background-color: var(--pale-yellow);
            border: 2px solid var(--border-color);
            box-shadow: var(--key-shadow-inset);
            display: flex; align-items: center; justify-content: center;
            font-weight: bold; cursor: pointer;
            transition: all 0.05s ease-in-out;
            user-select: none; -webkit-user-select: none; -webkit-touch-callout: none;
            border-radius: 6px;
            color: #111; font-size: 3.8vmin;
            line-height: 1; text-align: center;
            box-sizing: border-box; padding: 0;
            touch-action: none;
            overflow: hidden;
            min-width: 0;
            min-height: 0;
        }
        .key:active {
            transform: translateY(1px);
            box-shadow: inset 2px 2px 4px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.2);
        }

        .f-key { flex-grow: 0; }

        .nav-key {
            background-color: var(--deep-navy) !important;
            border: none !important;
            box-shadow: none !important;
            color: #fff; font-size: 3.5vmin;
            border-radius: 20px;
        }

        .oval {
            border-radius: 20px;
            background-color: var(--deep-navy) !important;
            border: none !important;
            box-shadow: none !important;
            color: #fff; font-size: 2.8vmin;
        }

        .key-dual {
            position: relative;
            overflow: hidden;
        }
        .key-top {
            position: absolute;
            top: 2px;
            right: 4px;
            font-size: 4.8vmin;
            line-height: 1;
        }
        .key-bot {
            position: absolute;
            bottom: 2px;
            left: 4px;
            font-size: 4.8vmin;
            line-height: 1;
        }
        #numpad .key-dual.mac-dim .key-bot { opacity: 0.25; }
        .key-stack {
            flex-direction: column;
            line-height: 1.2;
            font-size: 3.6vmin;
        }

        .led { margin-right: 6px; font-size: 11px; font-weight: bold; }
        .led.on  { color: #0f0; }
        .led.off { color: #888; }

        .mod-active, .drag-active, .smt-active, .np-active, .mac-active {
            box-shadow: inset 2px 2px 10px rgba(0,0,0,0.5) !important;
            transform: translateY(1px);
        }
        .mod-active { background-color: #b89c4c !important; }
        .drag-active { background-color: #3a6aaa !important; }
        .smt-active { background-color: #5a9a3a !important; }
        .np-active { background-color: #4a7acc !important; }
        .mac-active { background-color: #4a7acc !important; }
        .mac-disabled { opacity: 0.3; pointer-events: none; }

        .rotate-overlay {
            display: none;
            position: fixed;
            inset: 0;
            z-index: 9999;
            background: var(--deep-navy);
            color: #fff;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            font-size: 5vmin;
            text-align: center;
        }
        .rotate-overlay .icon {
            font-size: 12vmin;
            margin-bottom: 4vmin;
        }
        .key-mcfg {
            background-color: #4a7acc !important;
            color: #fff;
            font-size: 3.2vmin;
        }
        #numpad .key-dual .key-top,
        #numpad .key-dual .key-bot {
            font-size: 3.8vmin;
        }
        .key-display {
            background-color: #3a5a8a !important;
            color: #dde;
            font-size: 2.8vmin;
            pointer-events: none;
        }
        .key-exit {
            background-color: #8a3a3a !important;
            border-color: #6a2a2a !important;
            color: #fff;
        }
        .key-media {
            background-color: #7a4acc !important;
            color: #fff;
            font-size: 3.2vmin;
        }
    </style>
</head>
<body>
    <div id="rotate-overlay" class="rotate-overlay">
        <div class="icon">↻</div>
        <div>Rotate device to landscape</div>
    </div>
    <div id="debug">
        <span id="dbg-ws">WS: ---</span>
        <span id="dbg-key">Key: ---</span>
        <span id="dbg-leds"><span class="led off" id="led-nl">NL</span><span class="led off" id="led-cl">CL</span><span class="led off" id="led-sl">SL</span></span>

    </div>
    <div id="grid"></div>
    <div id="numpad"></div>

<script>
let ws;
const st = { 0:'CONNECTING', 1:'OPEN', 2:'CLOSING', 3:'CLOSED' };
const modKeys = {'*Shft':'shift','*Ctrl':'ctrl','*Alt':'alt','*Cmd':'meta'};
let modState = {};
let mouseSpeed = 5;
let mouseAccel = 0;
let numpadMode = false;
let smartTypingEnabled = false;
let macOSMode = false;

function checkOrientation() {
    const el = document.getElementById('rotate-overlay');
    if (!el) return;
    const portrait = window.matchMedia('(orientation: portrait)').matches;
    el.style.display = portrait ? 'flex' : 'none';
}

function updateDbg() {
    document.getElementById('dbg-ws').textContent = 'WS: ' + (ws ? st[ws.readyState] : 'null');
}

function connectWS() {
    updateDbg();
    ws = new WebSocket('ws://' + location.hostname + ':81/');
    ws.onopen  = () =>  { updateDbg(); document.getElementById('dbg-ws').style.color='#0f0'; };
    ws.onmessage = (e) => {
        const d = e.data;
        if (d.startsWith('#LED:')) {
            const s = parseInt(d.substring(5), 16);
            document.getElementById('led-nl').className = 'led' + (s & 1 ? ' on' : ' off');
            document.getElementById('led-cl').className = 'led' + (s & 2 ? ' on' : ' off');
            document.getElementById('led-sl').className = 'led' + (s & 4 ? ' on' : ' off');
            document.querySelectorAll('[data-k="*CaLk"]').forEach(function(b) {
                b.classList.toggle('mod-active', !!(s & 2));
            });
            document.querySelectorAll('[data-k="*NL"]').forEach(function(b) {
                b.classList.toggle('mod-active', !!(s & 1));
            });
        } else if (d.startsWith('#DRAG:')) {
            const ok = document.querySelector('[data-k="*RClk"]');
            if (ok) ok.classList.toggle('drag-active', d.charAt(6) === '1');
        } else if (d.startsWith('#SMT:')) {
            smartTypingEnabled = d.charAt(5) === '1';
            const sk = document.querySelector('[data-k="*SmT"]');
            if (sk) sk.classList.toggle('smt-active', smartTypingEnabled);
        } else if (d.startsWith('#MSPEED:')) {
            mouseSpeed = parseInt(d.substring(8));
            const sv = document.querySelector('[data-k="*SpdVal"]');
            if (sv) sv.innerHTML = 'Speed: ' + mouseSpeed;
        } else if (d.startsWith('#MACCEL:')) {
            mouseAccel = parseInt(d.substring(8));
            const av = document.querySelector('[data-k="*AclVal"]');
            if (av) av.innerHTML = 'Accel: ' + mouseAccel;
        } else if (d.startsWith('#NP:')) {
            numpadMode = d.charAt(4) === '1';
            toggleNumpad();
        } else if (d.startsWith('#MAC:')) {
            macOSMode = d.charAt(5) === '1';
            applyMacMode();
        }
    };
    ws.onclose   = () => { updateDbg(); setTimeout(connectWS, 2000); };
    ws.onerror   = () => { updateDbg(); document.getElementById('dbg-ws').style.color='#f00'; };
}
connectWS();

window.matchMedia('(orientation: portrait)').addListener(checkOrientation);
checkOrientation();

function reconcileDisplay() {
    const g = document.getElementById('grid');
    const n = document.getElementById('numpad');
    const dbg = document.getElementById('debug');
    if (numpadMode) {
        g.style.display = 'none';
        n.style.display = 'grid';
        dbg.style.display = '';
    } else {
        g.style.display = 'grid';
        n.style.display = 'none';
        dbg.style.display = '';
    }
}

function toggleNumpad() {
    const npk = document.querySelector('[data-k="*NP"]');
    if (numpadMode) { if (npk) npk.classList.add('np-active'); }
    else            { if (npk) npk.classList.remove('np-active'); }
    reconcileDisplay();
}

function applyMacMode() {
    document.querySelectorAll('[data-k="*Mac"]').forEach(function(b) {
        b.classList.toggle('mac-active', macOSMode);
    });
    document.querySelectorAll('[data-k="*Ins"]').forEach(function(b) {
        b.classList.toggle('mac-disabled', macOSMode);
    });
    document.querySelectorAll('[data-k="*NL"]').forEach(function(b) {
        b.innerHTML = macOSMode ? 'Clear' : 'NL';
    });
    document.querySelectorAll('#numpad .key-dual').forEach(function(b) {
        b.classList.toggle('mac-dim', macOSMode);
    });
}

function applyConfig() {
    const sv = document.querySelector('[data-k="*SpdVal"]');
    if (sv) sv.innerHTML = 'Speed: ' + mouseSpeed;
    const av = document.querySelector('[data-k="*AclVal"]');
    if (av) av.innerHTML = 'Accel: ' + mouseAccel;
    if (ws && ws.readyState === 1) {
        ws.send('#MSPEED:' + mouseSpeed);
        ws.send('#MACCEL:' + mouseAccel);
    }
}

function sendDown(k, btn) {
    if (k === '*SpdD') { mouseSpeed = Math.max(1, mouseSpeed - 1); applyConfig(); return; }
    if (k === '*SpdU') { mouseSpeed = Math.min(20, mouseSpeed + 1); applyConfig(); return; }
    if (k === '*AclD') { mouseAccel = Math.max(0, mouseAccel - 1); applyConfig(); return; }
    if (k === '*AclU') { mouseAccel = Math.min(10, mouseAccel + 1); applyConfig(); return; }
    if (k === '*SpdVal' || k === '*AclVal') { return; }

    if (!(ws && ws.readyState === 1)) return;
    ws.send(k);
    if (smartTypingEnabled) {
        if (k === ',' || k === ';') { ws.send(' '); ws.send('~ '); }
        else if (k === ':') { ws.send(' '); ws.send('~ '); ws.send(' '); ws.send('~ '); }
    }
    const mk = modKeys[k]; if (mk) { modState[mk] = true; btn.classList.add('mod-active'); }

    const d = document.getElementById('dbg-key');
    let disp = k;
    if (k === ' ')       disp = '[SPACE]';
    else if (k === '\r') disp = '[ENTER]';
    else if (k === '\t') disp = '[TAB]';
    else if (k === '\b') disp = '[BS]';
    d.textContent = 'Key: ' + disp;
}

function sendUp(k, btn) {
    if (!(ws && ws.readyState === 1)) return;
    ws.send('~' + k);
    const mk = modKeys[k]; if (mk) { modState[mk] = false; btn.classList.remove('mod-active'); }
}



const gridData = [
  // Row 1 — System Utilities
  {l:'Esc',     k:'\x1b'},        {l:'Tab', k:'\t', s:'*SHT'},   {l:'~<br>`', k:'`', s:'~'},
  {l:'Mac Mode', k:'*Mac'},      {l:'Num Pad', k:'*NP'},  {l:'Insert', k:'*Ins'},
  {l:'Home',    k:'*Home'},      {l:'End',     k:'*End'}, {l:'Smart Typing', k:'*SmT'},
  {l:'PgUp',    k:'*PgUp'},     {l:'PgDn',    k:'*PgDn'},{l:'Del', k:'*Del'},

  // Row 2 — Function keys (circular)
  {l:'F1' , c:'f-key', k:'*F1'},  {l:'F2' , c:'f-key', k:'*F2'},
  {l:'F3' , c:'f-key', k:'*F3'},  {l:'F4' , c:'f-key', k:'*F4'},
  {l:'F5' , c:'f-key', k:'*F5'},  {l:'F6' , c:'f-key', k:'*F6'},
  {l:'F7' , c:'f-key', k:'*F7'},  {l:'F8' , c:'f-key', k:'*F8'},
  {l:'F9' , c:'f-key', k:'*F9'},  {l:'F10', c:'f-key', k:'*F10'},
  {l:'F11', c:'f-key', k:'*F11'}, {l:'F12', c:'f-key', k:'*F12'},

  // Row 3 — Numbers / Symbols (double-stack)
  {l:'!<br>1', k:'1', s:'!'},{l:'@<br>2', k:'2', s:'@'},{l:'#<br>3', k:'3', s:'#'},{l:'$<br>4', k:'4', s:'$'},{l:'%<br>5', k:'5', s:'%'},{l:'^<br>6', k:'6', s:'^'},
  {l:'&<br>7', k:'7', s:'&'},{l:'*<br>8', k:'8', s:'*'},{l:'(<br>9', k:'9', s:'('},{l:')<br>0', k:'0', s:')'},{l:'_<br>-', k:'-', s:'_'},{l:'+<br>=', k:'=', s:'+'},

  // Row 4 — QWERTY top
  {l:'Q', k:'q'},{l:'W', k:'w'},{l:'E', k:'e'},{l:'R', k:'r'},{l:'T', k:'t'},
  {l:'Y', k:'y'},{l:'U', k:'u'},{l:'I', k:'i'},{l:'O', k:'o'},{l:'P', k:'p'},
  {l:'Backspace<br>Delete', span:2, stack:true, k:'\b'},

  // Row 5 — Home row + Blue zone top
  {l:'A', k:'a'},{l:'S', k:'s'},{l:'D', k:'d'},{l:'F', k:'f'},{l:'G', k:'g'},
  {l:'H', k:'h'},{l:'J', k:'j'},{l:'K', k:'k'},{l:'L', k:'l'},
  {l:'↖', c:'nav-key', k:'*MUL'}, {l:'↑', c:'nav-key', k:'*MUp'},
  {l:'↗', c:'nav-key', k:'*MUR'},

  // Row 6 — Bottom alpha + Blue zone middle
  {l:'Z', k:'z'},{l:'X', k:'x'},{l:'C', k:'c'},{l:'V', k:'v'},{l:'B', k:'b'},
  {l:'N', k:'n'},{l:'M', k:'m'},   {l:':<br>;', k:';', s:':'}, {l:'"<br>\'', k:'\'', s:'"'},
  {l:'←', c:'nav-key', k:'*MLt'}, {l:'※', c:'nav-key', k:'*Cn'},
  {l:'→', c:'nav-key', k:'*MRt'},

  // Row 7 — Modifiers + Space + Blue zone bottom
  {l:'Caps<br>Lock', stack:true, k:'*CaLk'},
  {l:'Shift ↑', span:2, k:'*Shft'},
  {l:'SPACE',     span:3, k:' '},
  {l:'<<br>,', k:',', s:'<'}, {l:'><br>.', k:'.', s:'>'}, {l:'?<br>/', k:'/', s:'?'},
  {l:'↙', c:'nav-key', k:'*MDL'}, {l:'↓', c:'nav-key', k:'*MDn'},
  {l:'↘', c:'nav-key', k:'*MDR'},

  // Row 8 — Bottom control + Blue zone footer
  {l:'Ctrl', k:'*Ctrl'}, {l:'Alt Option', k:'*Alt'},
  {l:'⌘' ,      k:'*Cmd'},  {l:'←',       k:'*Lft'},
  {l:'→' ,      k:'*Rgt'},  {l:'↑' ,      k:'*Up2'},
  {l:'↓' ,      k:'*Dn2'},  {l:'Enter ↵', span:2, k:'\r'},
  {l:'※※', c:'nav-key',    k:'*Spkl'},
  {l:'⬗ R',          c:'oval',       k:'*LClk'},
  {l:'⬖ Drag', c:'oval',       k:'*RClk'}
];

const grid = document.getElementById('grid');

for (let cell of gridData) {
    const btn = document.createElement('button');
    const isDual = cell.l && cell.l.indexOf('<br>') !== -1;
    if (cell.stack) {
        let parts = cell.l.split('<br>');
        btn.innerHTML = '<span>' + parts[0] + '</span><span>' + parts[1] + '</span>';
    } else if (isDual) {
        let parts = cell.l.split('<br>');
        btn.innerHTML = '<span class="key-top">' + parts[0] + '</span><span class="key-bot">' + parts[1] + '</span>';
    } else {
        btn.innerHTML = cell.l || (cell.k === ' ' ? 'SPACE' : cell.k);
    }
    btn.className = 'key' + (cell.stack ? ' key-stack' : isDual ? ' key-dual' : '') + ((cell.c) ? (' ' + cell.c) : '');

    btn.dataset.k = cell.k;
    if (cell.s) btn.dataset.s = cell.s;

    if (cell.span) {
        btn.style.gridColumn = 'span ' + cell.span;
    }

    grid.appendChild(btn);
}

// Build numpad overlay (8x12 grid)
const numpadData = [
    // Row 1 — Speed / Accel controls
    [1, 3, 1, 1, 'Spd\u2212', '*SpdD'],
    [1, 4, 1, 2, 'Speed: 5', '*SpdVal'],
    [1, 6, 1, 1, 'Spd+', '*SpdU'],
    [1, 7, 1, 1, 'Acl\u2212', '*AclD'],
    [1, 8, 1, 2, 'Accel: 0', '*AclVal'],
    [1, 10, 1, 1, 'Acl+', '*AclU'],
    // Row 2 — Exit
        [2, 5, 1, 4, '\u2715 Exit', '*NP'],
        // Row 3 — Media keys
        [3, 5, 1, 1, 'Mute', '*MEDmute'],   [3, 6, 1, 1, 'Vol\u2212', '*MEDvoldn'],
        [3, 7, 1, 1, 'Vol+', '*MEDvolup'],  [3, 8, 1, 1, 'Play', '*MEDplay'],
        // Row 4 — Media keys
        [4, 5, 1, 1, 'Prev', '*MEDprev'],   [4, 6, 1, 1, 'RW', '*MEDrw'],
        [4, 7, 1, 1, 'FF', '*MEDff'],   [4, 8, 1, 1, 'Next', '*MEDnext'],
        // Row 4 — Left keypad
    [4, 1, 1, 1, 'NL', '*NL'],   [4, 2, 1, 1, '/', '*NP/'],
    [4, 3, 1, 1, '*', '*NP*'],   [4, 4, 1, 1, '\u2212', '*NP-'],
    // Row 5 — Left
    [5, 1, 1, 1, '7<br>Home', '*NP7'],   [5, 2, 1, 1, '8<br>\u2191', '*NP8'],
    [5, 3, 1, 1, '9<br>PgUp', '*NP9'],   [5, 4, 2, 1, '+', '*NP+'],
    // Row 6 — Left
    [6, 1, 1, 1, '4<br>\u2190', '*NP4'],  [6, 2, 1, 1, '5', '*NP5'],
    [6, 3, 1, 1, '6<br>\u2192', '*NP6'],
    // Row 7 — Left
    [7, 1, 1, 1, '1<br>End', '*NP1'],    [7, 2, 1, 1, '2<br>\u2193', '*NP2'],
    [7, 3, 1, 1, '3<br>PgDn', '*NP3'],   [7, 4, 2, 1, 'Enter', '*NPEn'],
    // Row 8 — Left
    [8, 1, 1, 2, '0<br>Ins', '*NP0'],    [8, 3, 1, 1, '.<br>Del', '*NPD'],
    // Row 4 — Right keypad (mirror)
    [4, 9, 1, 1, 'NL', '*NL'],   [4, 10, 1, 1, '/', '*NP/'],
    [4, 11, 1, 1, '*', '*NP*'],  [4, 12, 1, 1, '\u2212', '*NP-'],
    // Row 5 — Right
    [5, 9, 1, 1, '7<br>Home', '*NP7'],   [5, 10, 1, 1, '8<br>\u2191', '*NP8'],
    [5, 11, 1, 1, '9<br>PgUp', '*NP9'],  [5, 12, 2, 1, '+', '*NP+'],
    // Row 6 — Right
    [6, 9, 1, 1, '4<br>\u2190', '*NP4'],  [6, 10, 1, 1, '5', '*NP5'],
    [6, 11, 1, 1, '6<br>\u2192', '*NP6'],
    // Row 7 — Right
    [7, 9, 1, 1, '1<br>End', '*NP1'],    [7, 10, 1, 1, '2<br>\u2193', '*NP2'],
    [7, 11, 1, 1, '3<br>PgDn', '*NP3'],  [7, 12, 2, 1, 'Enter', '*NPEn'],
    // Row 8 — Right
    [8, 9, 1, 2, '0<br>Ins', '*NP0'],    [8, 11, 1, 1, '.<br>Del', '*NPD'],
];
const npad = document.getElementById('numpad');
numpadData.forEach(function(item) {
    const btn = document.createElement('button');
    const label = item[4];
    const isDual = label.indexOf('<br>') !== -1;
    if (isDual) {
        const parts = label.split('<br>');
        btn.innerHTML = '<span class="key-top">' + parts[0] + '</span><span class="key-bot">' + parts[1] + '</span>';
    } else {
        btn.innerHTML = label;
    }
    let cls = 'key';
    if (isDual) cls += ' key-dual';
    if (item[5] === '*NP')                  cls += ' key-exit';
    else if (item[5] === '*SpdVal' || item[5] === '*AclVal') cls += ' key-display';
    else if (item[5].startsWith('*Spd') || item[5].startsWith('*Acl')) cls += ' key-mcfg';
    else if (item[5].startsWith('*MED'))    cls += ' key-media';
    btn.className = cls;
    btn.dataset.k = item[5];
    btn.style.gridRow = item[0] + ' / span ' + item[2];
    btn.style.gridColumn = item[1] + ' / span ' + item[3];
    npad.appendChild(btn);
});

document.addEventListener('contextmenu', function(e) {
    const btn = e.target.closest('.key');
    if (btn) e.preventDefault();
});

let pressedBtns = new Map();

function ptrKey(btn) {
    return (btn.dataset.s && modState.shift) ? btn.dataset.s : btn.dataset.k;
}

document.addEventListener('pointerdown', function(e) {
    const btn = e.target.closest('.key');
    if (!btn) return;
    e.preventDefault();
    btn.setPointerCapture(e.pointerId);
    const k = ptrKey(btn);
    btn._k = k;
    pressedBtns.set(e.pointerId, {btn: btn, k: k});
    sendDown(k, btn);
});

document.addEventListener('pointermove', function(e) {
    const entry = pressedBtns.get(e.pointerId);
    if (!entry) return;
    const el = document.elementFromPoint(e.clientX, e.clientY);
    if (!el) return;
    const newBtn = el.closest('.key');
    if (newBtn === entry.btn) return;
    // Release old key
    sendUp(entry.k, entry.btn);
    if (newBtn) {
        const k = ptrKey(newBtn);
        newBtn._k = k;
        entry.btn = newBtn;
        entry.k = k;
        sendDown(k, newBtn);
    }
});

function pointerEnd(e) {
    const entry = pressedBtns.get(e.pointerId);
    if (!entry) return;
    pressedBtns.delete(e.pointerId);
    sendUp(entry.k, entry.btn);
}
document.addEventListener('pointerup', pointerEnd);
document.addEventListener('pointercancel', pointerEnd);
</script>
</body>
</html>
)rawliteral";

#endif
