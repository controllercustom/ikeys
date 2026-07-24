import { ESPLoader, Transport } from 'https://cdn.jsdelivr.net/npm/esptool-js/bundle.js';

let loader = null;
let port = null;
let transport = null;
let manifest = null;

const els = {
  board: document.getElementById('board'),
  version: document.getElementById('version'),
  eraseAll: document.getElementById('erase-all'),
  flashBtn: document.getElementById('flash-btn'),
  log: document.getElementById('log'),
  statusText: document.getElementById('status-text'),
  statusBadge: document.getElementById('status-badge'),
  progressBar: document.getElementById('progress-bar'),
  progressFill: document.getElementById('progress-fill'),
  progressText: document.getElementById('progress-text'),
  atoms3Info: document.getElementById('atoms3-info'),
  esp32s3Info: document.getElementById('esp32s3-info'),
};

const BAUD = 921600;

function log(msg, cls) {
  const line = document.createElement('div');
  line.className = cls || 'info';
  line.textContent = msg;
  els.log.appendChild(line);
  els.log.scrollTop = els.log.scrollHeight;
}

function setStatus(text, badge) {
  els.statusText.textContent = text;
  els.statusBadge.textContent = badge;
  els.statusBadge.className = 'status-badge ' + badge;
}

function setProgress(pct, text) {
  els.progressBar.classList.add('active');
  els.progressFill.style.width = Math.round(pct) + '%';
  els.progressText.textContent = text || '';
}

function clearProgress() {
  els.progressBar.classList.remove('active');
  els.progressFill.style.width = '0%';
  els.progressText.textContent = '';
}

async function loadFirmwareManifest() {
  try {
    const res = await fetch('firmware.json');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return await res.json();
  } catch (e) {
    log('Failed to load firmware manifest: ' + e.message, 'error');
    return null;
  }
}

function populateVersions(m) {
  const sel = els.version;
  sel.innerHTML = '';
  if (!m || !m.versions || m.versions.length === 0) {
    sel.innerHTML = '<option value="">No versions available</option>';
    return;
  }
  for (const v of m.versions) {
    const opt = document.createElement('option');
    opt.value = v;
    opt.textContent = v;
    sel.appendChild(opt);
  }
  if (m.latest) {
    sel.value = m.latest;
  }
}

function updateInstructions() {
  const board = els.board.value;
  els.atoms3Info.classList.toggle('hidden', board !== 'atoms3');
  els.esp32s3Info.classList.toggle('hidden', board !== 'esp32s3');
}

function flashLayout() {
  return manifest && manifest.flashLayout ? manifest.flashLayout : [
    { file: 'firmware.bin', address: 0x10000 },
  ];
}

async function flashRegion(url, address, isLast) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error('Download failed: ' + url + ' HTTP ' + resp.status);
  const data = await resp.arrayBuffer();
  log(url.split('/').pop() + ' at 0x' + address.toString(16) + ' (' + (data.byteLength / 1024).toFixed(1) + ' KB)', 'info');

  const numBlocks = await loader.flashBegin(data.byteLength, address);

  for (let seq = 0; seq < numBlocks; seq++) {
    const offset = seq * loader.FLASH_WRITE_SIZE;
    const size = Math.min(loader.FLASH_WRITE_SIZE, data.byteLength - offset);
    const chunk = new Uint8Array(data, offset, size);
    await loader.flashBlock(chunk, seq);
  }

  await loader.flashFinish(isLast);
  if (isLast) {
    log('Rebooting...', 'info');
  }
}

async function flash() {
  if (loader) {
    log('Already flashing', 'warn');
    return;
  }

  const board = els.board.value;
  const version = els.version.value;
  if (!version) {
    log('No firmware version selected', 'error');
    return;
  }

  const layout = flashLayout();
  const baseUrl = 'firmware/' + version + '/' + board + '/';

  els.flashBtn.disabled = true;
  setStatus('Connecting...', 'flashing');

  try {
    port = await navigator.serial.requestPort();
    if (!port) {
      els.flashBtn.disabled = false;
      setStatus('Ready', 'ready');
      return;
    }

    transport = new Transport(port);

    loader = new ESPLoader({
      transport,
      baudrate: BAUD,
    });

    log('Synchronizing with chip...', 'info');
    const chipDesc = await loader.main();
    log('Chip: ' + chipDesc, 'info');

    const chipName = loader.chip.CHIP_NAME || 'Unknown';
    const mac = await loader.chip.readMac(loader);
    log('Chip: ' + chipName + ' (MAC: ' + mac + ')', 'info');

    if (els.eraseAll.checked) {
      log('Erasing all flash (this takes a while)...', 'warn');
      await loader.eraseFlash();
      log('Full flash erase complete', 'info');
    }

    log('Flashing firmware...', 'info');
    setStatus('Flashing...', 'flashing');

    for (let i = 0; i < layout.length; i++) {
      const entry = layout[i];
      const isLast = i === layout.length - 1;
      await flashRegion(baseUrl + entry.file, entry.address, isLast);
    }

    log('Flashing complete!', 'success');
    setStatus('Done', 'done');

  } catch (e) {
    log('Error: ' + e.message, 'error');
    setStatus('Error', 'error');
  } finally {
    try { if (transport) await transport.disconnect(); } catch (_) {}
    loader = null;
    port = null;
    transport = null;
    els.flashBtn.disabled = false;
    clearProgress();
  }
}

els.board.addEventListener('change', updateInstructions);
els.flashBtn.addEventListener('click', flash);

(async function init() {
  log('iKeys Firmware Flasher ready', 'info');
  log('Select a board and version, then click Flash Firmware', 'info');

  manifest = await loadFirmwareManifest();
  if (manifest) {
    populateVersions(manifest);
    log('Found ' + manifest.versions.length + ' firmware version(s)', 'info');
  } else {
    log('No firmware manifest found. Push a git tag to trigger a build.', 'warn');
  }

  updateInstructions();
})();
