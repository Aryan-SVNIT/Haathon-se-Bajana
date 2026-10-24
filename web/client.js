const $ = (id) => document.getElementById(id);
const joinBtn = $('join'), roomInput = $('room'), statusEl = $('status');
const localVideo = $('local-video'), remoteVideo = $('remote-video');
const localOverlay = $('local-overlay');
const localOverlayCtx = localOverlay.getContext('2d');
const localState = $('local-state'), remoteState = $('remote-state');
const localGesture = $('local-gesture'), remoteGesture = $('remote-gesture');
const instrumentSelect = $('instrument'), noteKeys = $('note-keys');
const soundStatus = $('sound-status'), instrumentHint = $('instrument-hint');
let ws, pc, localStream, peerId, joined = false, trackingReady = false, lastFrameSend = 0;
let selectedInstrument = instrumentSelect.value || 'piano';
let audioContext = null, masterGain = null;
const previousGestureStates = new Map();
const previousInstrumentBySource = new Map();
const lastNoteAt = new Map();
const trackingCanvas = document.createElement('canvas');
const trackingCtx = trackingCanvas.getContext('2d', { alpha: false });
const HAND_CONNECTIONS = [[0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],[5,9],[9,10],[10,11],[11,12],[9,13],[13,14],[14,15],[15,16],[13,17],[17,18],[18,19],[19,20],[0,17]];
const rtcConfig = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };
const FINGER_NAMES = ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky'];
const NOTES = {
  piano: {
    left: [
      { name: 'C3', frequency: 130.81 }, { name: 'D3', frequency: 146.83 },
      { name: 'E3', frequency: 164.81 }, { name: 'F3', frequency: 174.61 },
      { name: 'G3', frequency: 196.00 },
    ],
    right: [
      { name: 'C4', frequency: 261.63 }, { name: 'D4', frequency: 293.66 },
      { name: 'E4', frequency: 329.63 }, { name: 'F4', frequency: 349.23 },
      { name: 'G4', frequency: 392.00 },
    ],
  },
  guitar: {
    guitar: [
      { name: 'E3', frequency: 164.81 }, { name: 'A3', frequency: 220.00 },
      { name: 'D4', frequency: 293.66 }, { name: 'G4', frequency: 392.00 },
      { name: 'B4', frequency: 493.88 },
    ],
  },
};
const SLOT_LABELS = { left: 'Left hand · low notes', right: 'Right hand · high notes', guitar: 'Guitar hand · plucked notes' };
function status(text) { statusEl.textContent = text; }
function setState(el, text) { el.textContent = text; }
function send(obj) { if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj)); }

function renderInstrumentPanel() {
  const pianoMode = selectedInstrument === 'piano';
  noteKeys.classList.toggle('guitar-mode', !pianoMode);
  instrumentHint.textContent = pianoMode
    ? 'Piano: left side = C3–G3 · right side = C4–G4. Straighten, then bend a finger.'
    : 'Guitar: show one hand. Straighten, then bend a finger to pluck its note.';
  noteKeys.innerHTML = Object.entries(NOTES[selectedInstrument]).map(([slot, notes]) => `
    <div class="note-group">
      <p class="note-group-label">${SLOT_LABELS[slot]}</p>
      <div class="note-grid">${notes.map((note, i) => `
        <div class="note-key" data-note-id="${slot}:${i}">
          <strong>${note.name}</strong><span>${FINGER_NAMES[i]}</span>
        </div>`).join('')}
      </div>
    </div>`).join('');
}

async function enableAudio() {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) {
    soundStatus.textContent = 'Web Audio is not supported in this browser.';
    return;
  }
  if (!audioContext) {
    audioContext = new AudioContextClass({ latencyHint: 'interactive' });
    masterGain = audioContext.createGain();
    masterGain.gain.value = 0.34;
    masterGain.connect(audioContext.destination);
  }
  try {
    await audioContext.resume();
    soundStatus.textContent = audioContext.state === 'running'
      ? 'Sound ready · both players hear the same gesture notes.'
      : 'Sound is paused by the browser. Click Join room again after reloading.';
  } catch (error) {
    console.warn('Could not enable browser audio:', error);
    soundStatus.textContent = 'Audio could not start. Check browser sound settings.';
  }
}

function flashNoteKey(slot, fingerIndex) {
  const key = noteKeys.querySelector(`[data-note-id="${slot}:${fingerIndex}"]`);
  if (!key) return;
  key.classList.add('active');
  if (key._flashTimer) clearTimeout(key._flashTimer);
  key._flashTimer = setTimeout(() => key.classList.remove('active'), 190);
}

function playSynthNote(instrument, slot, fingerIndex) {
  const note = NOTES[instrument]?.[slot]?.[fingerIndex];
  if (!note) return;
  flashNoteKey(slot, fingerIndex);
  if (!audioContext || audioContext.state !== 'running' || !masterGain) return;

  const now = audioContext.currentTime;
  const isPiano = instrument === 'piano';
  const duration = isPiano ? 0.95 : 0.62;
  const output = audioContext.createGain();
  output.gain.setValueAtTime(0.0001, now);
  output.gain.exponentialRampToValueAtTime(isPiano ? 0.24 : 0.20, now + (isPiano ? 0.014 : 0.004));
  output.gain.exponentialRampToValueAtTime(0.0001, now + duration);
  output.connect(masterGain);

  const partials = isPiano
    ? [{ multiplier: 1, gain: 0.82 }, { multiplier: 2, gain: 0.23 }, { multiplier: 3, gain: 0.08 }]
    : [{ multiplier: 1, gain: 0.75 }, { multiplier: 2, gain: 0.20 }, { multiplier: 3, gain: 0.07 }];
  for (const partial of partials) {
    const oscillator = audioContext.createOscillator();
    const partialGain = audioContext.createGain();
    oscillator.type = isPiano ? 'sine' : 'triangle';
    oscillator.frequency.value = note.frequency * partial.multiplier;
    partialGain.gain.value = partial.gain;
    oscillator.connect(partialGain);
    partialGain.connect(output);
    oscillator.start(now);
    oscillator.stop(now + duration + 0.03);
  }
}

function clearGestureSource(source) {
  for (const key of [...previousGestureStates.keys()]) {
    if (key.startsWith(`${source}|`)) previousGestureStates.delete(key);
  }
  previousInstrumentBySource.delete(source);
  for (const key of [...lastNoteAt.keys()]) {
    if (key.startsWith(`${source}|`)) lastNoteAt.delete(key);
  }
}

// One note triggers on the same UP -> BENT transition as the desktop instrument.
// The note maps to the same finger index (thumb, index, middle, ring, pinky).
function processGestureAudio(source, hands, slots, instrument) {
  const chosenInstrument = instrument === 'guitar' ? 'guitar' : 'piano';
  const previousInstrument = previousInstrumentBySource.get(source);
  if (previousInstrument && previousInstrument !== chosenInstrument) clearGestureSource(source);
  previousInstrumentBySource.set(source, chosenInstrument);

  const presentSlots = new Set();
  const activeHands = Array.isArray(hands) ? hands : [];
  const handSlots = Array.isArray(slots) ? slots : [];
  activeHands.forEach((fingerStates, handIndex) => {
    const slot = chosenInstrument === 'guitar' ? 'guitar' : (handSlots[handIndex] || (handIndex === 0 ? 'left' : 'right'));
    if (!NOTES[chosenInstrument][slot] || !Array.isArray(fingerStates)) return;
    presentSlots.add(slot);
    fingerStates.slice(0, 5).forEach((rawState, fingerIndex) => {
      const isUp = Boolean(rawState);
      const stateKey = `${source}|${chosenInstrument}|${slot}|${fingerIndex}`;
      const oldState = previousGestureStates.get(stateKey);
      if (oldState === true && isUp === false) {
        const lastAt = lastNoteAt.get(stateKey) || 0;
        const now = performance.now();
        if (now - lastAt > 180) {
          playSynthNote(chosenInstrument, slot, fingerIndex);
          lastNoteAt.set(stateKey, now);
        }
      }
      previousGestureStates.set(stateKey, isUp);
    });
  });

  // When a hand leaves the frame, forget its previous state so reappearing
  // hands don't generate phantom notes.
  for (const slot of Object.keys(NOTES[chosenInstrument])) {
    if (!presentSlots.has(slot)) {
      const prefix = `${source}|${chosenInstrument}|${slot}|`;
      for (const key of [...previousGestureStates.keys()]) if (key.startsWith(prefix)) previousGestureStates.delete(key);
      for (const key of [...lastNoteAt.keys()]) if (key.startsWith(prefix)) lastNoteAt.delete(key);
    }
  }
}

async function startCamera() {
  localStream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 640 }, height: { ideal: 400 }, frameRate: { ideal: 24, max: 30 } }, audio: false });
  localVideo.srcObject = localStream;
  await localVideo.play();
  setState(localState, 'Camera on');
}
function drawHandLandmarks(allLandmarks) {
  if (!localVideo.videoWidth || !localVideo.videoHeight) return;
  if (localOverlay.width !== localVideo.videoWidth || localOverlay.height !== localVideo.videoHeight) {
    localOverlay.width = localVideo.videoWidth;
    localOverlay.height = localVideo.videoHeight;
  }
  const ctx = localOverlayCtx;
  const w = localOverlay.width, h = localOverlay.height;
  ctx.clearRect(0, 0, w, h);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.lineWidth = Math.max(2.5, w / 240);
  const radius = Math.max(3, w / 150);
  for (const lm of allLandmarks) {
    ctx.strokeStyle = '#c8ff57';
    for (const [a, b] of HAND_CONNECTIONS) {
      ctx.beginPath(); ctx.moveTo(lm[a].x * w, lm[a].y * h); ctx.lineTo(lm[b].x * w, lm[b].y * h); ctx.stroke();
    }
    ctx.fillStyle = '#75baff';
    for (const point of lm) {
      ctx.beginPath(); ctx.arc(point.x * w, point.y * h, radius, 0, Math.PI * 2); ctx.fill();
    }
  }
}
function sendTrackingFrames(now) {
  if (joined && ws && ws.readyState === WebSocket.OPEN && localVideo.readyState >= 2 && localVideo.videoWidth > 0 && now - lastFrameSend >= 160) {
    lastFrameSend = now;
    // Keep the upload small; Python runs the existing MediaPipe tracker server-side.
    const width = 320;
    const height = Math.max(1, Math.round(width * localVideo.videoHeight / localVideo.videoWidth));
    if (trackingCanvas.width !== width || trackingCanvas.height !== height) { trackingCanvas.width = width; trackingCanvas.height = height; }
    trackingCtx.drawImage(localVideo, 0, 0, width, height);
    try {
      const frame = trackingCanvas.toDataURL('image/jpeg', 0.52);
      send({ type: 'frame', frame, instrument: selectedInstrument });
    } catch (error) { console.warn('Could not encode webcam frame for tracking:', error); }
  }
  requestAnimationFrame(sendTrackingFrames);
}
requestAnimationFrame(sendTrackingFrames);

function renderGestureText(element, hands, slots, instrument) {
  if (!hands || !hands.length) { element.textContent = 'No hand detected — show an open palm'; return; }
  const handSlots = Array.isArray(slots) ? slots : [];
  element.textContent = hands.map((f, i) => {
    const name = instrument === 'guitar' ? 'Guitar hand' : ((handSlots[i] || (i === 0 ? 'left' : 'right')) === 'right' ? 'Right hand' : 'Left hand');
    return `${name}: ${f.map(v => v ? 'UP' : 'BENT').join(' · ')}`;
  }).join(' | ');
}
async function createPeer() {
  if (pc) pc.close();
  pc = new RTCPeerConnection(rtcConfig);
  pc.onicecandidate = (event) => { if (event.candidate) send({type:'ice', candidate:event.candidate}); };
  pc.ontrack = (event) => {
    remoteVideo.srcObject = event.streams[0]; remoteVideo.play().catch(()=>{});
    setState(remoteState, 'Video connected');
    status(trackingReady ? 'Video connected · Python hand tracking active' : 'Video connected · waiting for Python hand tracker');
  };
  pc.onconnectionstatechange = () => {
    if (pc) setState(remoteState, pc.connectionState);
    if (pc && ['failed','disconnected','closed'].includes(pc.connectionState)) status(`WebRTC ${pc.connectionState}. Check network or TURN configuration.`);
  };
  if (localStream) localStream.getTracks().forEach(track => pc.addTrack(track, localStream));
}
async function handleSignal(data) {
  if (data.type === 'joined') {
    peerId = data.peer_id; joined = true;
    setState(localState, 'In room ' + data.room);
    status(`Joined room ${data.room}. ${data.players}/2 players connected.`);
  } else if (data.type === 'peer-available') {
    if (!pc) await createPeer();
    if (data.initiator) {
      const offer = await pc.createOffer(); await pc.setLocalDescription(offer);
      send({type:'offer', description:pc.localDescription}); status('Calling opponent…');
    } else status('Opponent found. Waiting for offer…');
  } else if (data.type === 'offer') {
    if (!pc) await createPeer();
    await pc.setRemoteDescription(data.description);
    const answer = await pc.createAnswer(); await pc.setLocalDescription(answer);
    send({type:'answer', description:pc.localDescription});
  } else if (data.type === 'answer') {
    if (pc) await pc.setRemoteDescription(data.description);
  } else if (data.type === 'ice') {
    if (pc && data.candidate) { try { await pc.addIceCandidate(data.candidate); } catch (e) { console.warn('ICE candidate rejected', e); } }
  } else if (data.type === 'tracked-result') {
    trackingReady = true;
    drawHandLandmarks(data.landmarks || []);
    const hands = data.hands || [], slots = data.slots || [];
    const instrument = data.instrument || selectedInstrument;
    renderGestureText(localGesture, hands, slots, instrument);
    processGestureAudio('local', hands, slots, instrument);
    setState(localState, `${instrument === 'guitar' ? 'Guitar' : 'Piano'} · ${hands.length ? `Tracking · ${hands.length} hand${hands.length === 1 ? '' : 's'}` : 'Tracking · no hand'}`);
    if (pc && pc.connectionState === 'connected') status('Video connected · Python hand tracking active · gesture instruments ready');
    else status('Python hand tracking active · waiting for opponent video');
  } else if (data.type === 'tracker-error') {
    trackingReady = false;
    localGesture.textContent = `TRACKER ERROR: ${data.message || 'unknown Python tracking error'}`;
    setState(localState, 'Tracker failed');
    status('Python hand tracking failed. See the message under “Your hand”.');
  } else if (data.type === 'gesture') {
    const instrument = data.instrument === 'guitar' ? 'guitar' : 'piano';
    const hands = data.hands || [], slots = data.slots || [];
    renderGestureText(remoteGesture, hands, slots, instrument);
    processGestureAudio('remote', hands, slots, instrument);
    setState(remoteState, `${instrument === 'guitar' ? 'Guitar' : 'Piano'} · ${hands.length ? `Tracking · ${hands.length} hand${hands.length === 1 ? '' : 's'}` : 'Connected · no hand'}`);
  } else if (data.type === 'peer-left') {
    remoteVideo.srcObject = null; setState(remoteState, 'Opponent left'); remoteGesture.textContent = 'Waiting for player';
    clearGestureSource('remote');
    if (pc) { pc.close(); pc = null; }
    status('Opponent disconnected. They can rejoin the room.');
  } else if (data.type === 'error') {
    status(data.message); joinBtn.disabled = false;
  }
}
function friendlyCameraError(error) {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return 'Camera API unavailable. Open this page at http://localhost:8080 or use HTTPS.';
  if (error && error.name === 'NotAllowedError') return 'Camera permission blocked. Click the site icon beside the address, allow Camera, then reload.';
  if (error && error.name === 'NotFoundError') return 'No webcam found. Connect a camera and try again.';
  if (error && error.name === 'NotReadableError') return 'Webcam is busy. Close Camera/Zoom/Teams and try again.';
  return 'Could not start camera: ' + (error?.message || error?.name || 'unknown error');
}
async function joinRoom() {
  if (joined) return;
  const room = roomInput.value.trim().toUpperCase();
  if (room.length < 3) { status('Enter a room code with at least 3 characters.'); return; }
  joinBtn.disabled = true;
  status('Enabling sound and requesting webcam permission…');
  try {
    // Create/resume Web Audio synchronously from the Join click before camera awaits.
    await enableAudio();
    await startCamera();
    status('Camera ready. Joining room; Python will run hand tracking on the server…');
    localGesture.textContent = 'Waiting for Python hand tracker…';
    setState(localState, 'Camera on · joining room');
    const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${scheme}://${location.host}/ws`);
    ws.onopen = () => send({type:'join', room});
    ws.onmessage = async (event) => { try { await handleSignal(JSON.parse(event.data)); } catch (e) { console.error(e); status('Connection negotiation error: ' + e.message); } };
    ws.onerror = () => status('WebSocket connection failed. Check that the server is running.');
    ws.onclose = () => { joined = false; joinBtn.disabled = false; if (pc) {pc.close(); pc=null;} };
  } catch (e) {
    console.error(e); status(friendlyCameraError(e)); joinBtn.disabled = false;
    if (localStream) { localStream.getTracks().forEach(t=>t.stop()); localStream = null; }
    localVideo.srcObject = null; setState(localState, 'Camera unavailable');
  }
}
instrumentSelect.addEventListener('change', () => {
  selectedInstrument = instrumentSelect.value === 'guitar' ? 'guitar' : 'piano';
  clearGestureSource('local');
  renderInstrumentPanel();
  soundStatus.textContent = audioContext?.state === 'running'
    ? 'Sound ready · both players hear the same gesture notes.'
    : 'Sound will be enabled when you join the room.';
});
renderInstrumentPanel();
joinBtn.addEventListener('click', joinRoom);
roomInput.addEventListener('keydown', e => { if (e.key === 'Enter') joinRoom(); });
window.addEventListener('beforeunload', () => { if(ws) ws.close(); if(pc) pc.close(); if(localStream) localStream.getTracks().forEach(t=>t.stop()); if(audioContext) audioContext.close(); });
