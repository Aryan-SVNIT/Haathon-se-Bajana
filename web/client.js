const $ = (id) => document.getElementById(id);
const joinBtn = $('join'), roomInput = $('room'), statusEl = $('status');
const localVideo = $('local-video'), remoteVideo = $('remote-video');
const localOverlay = $('local-overlay');
const localOverlayCtx = localOverlay.getContext('2d');
const localState = $('local-state'), remoteState = $('remote-state');
const localGesture = $('local-gesture'), remoteGesture = $('remote-gesture');
const instrumentSelect = $('instrument'), noteKeys = $('note-keys');
const soundStatus = $('sound-status'), instrumentHint = $('instrument-hint');
let ws, pc, localStream, peerId, joined = false, trackingReady = false, lastFrameSend = 0, isFrameInFlight = false;
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
const GUITAR_PLAYING_FINGERS = ['Index', 'Middle', 'Ring', 'Pinky'];
const NOTES = {
  piano: {
    left: [
      { name: 'C Major', frequency: 130.81, third: 164.81, fifth: 196.00 },
      { name: 'G Major', frequency: 196.00, third: 246.94, fifth: 293.66 },
      { name: 'A Minor', frequency: 220.00, third: 261.63, fifth: 329.63 },
      { name: 'F Major', frequency: 174.61, third: 220.00, fifth: 261.63 },
      { name: 'D Major', frequency: 146.83, third: 185.00, fifth: 220.00 },
    ],
    right: [
      { name: 'E Minor', frequency: 164.81, third: 196.00, fifth: 246.94 },
      { name: 'A Major', frequency: 220.00, third: 277.18, fifth: 329.63 },
      { name: 'B Minor', frequency: 246.94, third: 293.66, fifth: 369.99 },
      { name: 'E Major', frequency: 164.81, third: 207.65, fifth: 246.94 },
      { name: 'F# Minor', frequency: 185.00, third: 220.00, fifth: 277.18 },
    ],
  },
  guitar: {
    major: [
      { name: 'C Major', frequency: 130.81, third: 164.81, fifth: 196.00 },
      { name: 'G Major', frequency: 196.00, third: 246.94, fifth: 293.66 },
      { name: 'D Major', frequency: 146.83, third: 185.00, fifth: 220.00 },
      { name: 'A Major', frequency: 220.00, third: 277.18, fifth: 329.63 },
    ],
    minor: [
      { name: 'A Minor', frequency: 220.00, third: 261.63, fifth: 329.63 },
      { name: 'E Minor', frequency: 164.81, third: 196.00, fifth: 246.94 },
      { name: 'B Minor', frequency: 246.94, third: 293.66, fifth: 369.99 },
      { name: 'F# Minor', frequency: 185.00, third: 220.00, fifth: 277.18 },
    ],
  },
  octapad: {
    left: [
      { name: 'Cowbell', type: 'cowbell' },
      { name: 'Kick', type: 'kick' },
      { name: 'Snare', type: 'snare' },
      { name: 'Hi-Hat Closed', type: 'hihat_closed' },
      { name: 'Hi-Hat Open', type: 'hihat_open' },
    ],
    right: [
      { name: 'Ride Cymbal', type: 'ride' },
      { name: 'Low Tom', type: 'low_tom' },
      { name: 'High Tom', type: 'high_tom' },
      { name: 'Crash Cymbal', type: 'crash' },
      { name: 'Hand Clap', type: 'clap' },
    ],
  },
};
const SLOT_LABELS = { left: 'Left hand · 5 chords', right: 'Right hand · 5 chords', guitar: 'Guitar strings (Thumb UP = Major, DOWN = Minor)' };
function status(text) { statusEl.textContent = text; }
function setState(el, text) { el.textContent = text; }
function send(obj) { if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj)); }

function renderInstrumentPanel() {
  const pianoMode = selectedInstrument === 'piano';
  const guitarMode = selectedInstrument === 'guitar';
  noteKeys.classList.toggle('guitar-mode', guitarMode);
  noteKeys.classList.toggle('octapad-mode', selectedInstrument === 'octapad');

  if (pianoMode) {
    instrumentHint.textContent = 'Piano: Left = C/G/Am/F/D Chords · Right = Em/A/Bm/E/F#m Chords. Bend a finger to play.';
    noteKeys.innerHTML = Object.entries(NOTES.piano).map(([slot, notes]) => `
      <div class="note-group">
        <p class="note-group-label">${SLOT_LABELS[slot]}</p>
        <div class="note-grid">${notes.map((note, i) => `
          <div class="note-key" data-note-id="${slot}:${i}">
            <strong>${note.name}</strong><span>${FINGER_NAMES[i]}</span>
          </div>`).join('')}
        </div>
      </div>`).join('');
  } else if (guitarMode) {
    instrumentHint.textContent = 'Guitar: Thumb UP = Major mode · Thumb DOWN = Minor mode. Bend Index, Middle, Ring, or Pinky to play.';
    const notes = NOTES.guitar.major;
    noteKeys.innerHTML = `
      <div class="note-group" style="grid-column: 1/-1;">
        <p class="note-group-label" id="guitar-mode-header">🎸 Guitar Strings · [MAJOR MODE active (Thumb UP)]</p>
        <div class="note-grid" style="grid-template-columns: repeat(4, minmax(0, 1fr)); max-width: 760px;">
          ${notes.map((note, i) => `
            <div class="note-key" data-note-id="guitar:${i}">
              <strong id="guitar-note-name-${i}">${note.name}</strong><span>${GUITAR_PLAYING_FINGERS[i]}</span>
            </div>`).join('')}
        </div>
      </div>`;
  } else {
    instrumentHint.textContent = 'Octapad: Left Hand = Kick/Snare/HiHat (Pads 1-4) · Right Hand = Toms/Crash/Clap (Pads 5-8). 1 Hand: Thumb switches Bank A/B.';
    const pads = [
      { id: 'left:1', name: 'Kick', num: 'PAD 1', hand: 'L-Index', icon: '🥁' },
      { id: 'left:2', name: 'Snare', num: 'PAD 2', hand: 'L-Middle', icon: '🎯' },
      { id: 'right:1', name: 'Low Tom', num: 'PAD 5', hand: 'R-Index', icon: '🪘' },
      { id: 'right:2', name: 'High Tom', num: 'PAD 6', hand: 'R-Middle', icon: '🪘' },
      { id: 'left:3', name: 'Hi-Hat Closed', num: 'PAD 3', hand: 'L-Ring', icon: '🔘' },
      { id: 'left:4', name: 'Hi-Hat Open', num: 'PAD 4', hand: 'L-Pinky', icon: '💿' },
      { id: 'right:3', name: 'Crash Cymbal', num: 'PAD 7', hand: 'R-Ring', icon: '💥' },
      { id: 'right:4', name: 'Hand Clap', num: 'PAD 8', hand: 'R-Pinky', icon: '👏' },
    ];
    noteKeys.innerHTML = `
      <div class="note-group" style="grid-column: 1/-1;">
        <p class="note-group-label" id="octapad-header" style="color: #d18eff;">🥁 Roland Octapad SPD-30 · [8 Backlit Electronic Drum Pads]</p>
        <div class="note-grid" style="grid-template-columns: repeat(4, minmax(0, 1fr)); max-width: 820px; gap: 10px;">
          ${pads.map(pad => `
            <div class="note-key" data-note-id="${pad.id}" style="min-height: 80px; border-color: rgba(180, 120, 255, 0.35);">
              <small style="opacity: 0.68; font-size: 11px;">${pad.num}</small>
              <strong style="font-size: 15px; margin: 3px 0;">${pad.icon} ${pad.name}</strong>
              <span style="font-size: 11px; color: #b892ff;">${pad.hand}</span>
            </div>`).join('')}
        </div>
      </div>`;
  }
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

function flashNoteKey(slotOrKey, fingerIndex) {
  const noteId = slotOrKey === 'major' || slotOrKey === 'minor' ? `guitar:${fingerIndex}` : `${slotOrKey}:${fingerIndex}`;
  const key = noteKeys.querySelector(`[data-note-id="${noteId}"]`);
  if (!key) return;
  key.classList.add('active');
  if (key._flashTimer) clearTimeout(key._flashTimer);
  key._flashTimer = setTimeout(() => key.classList.remove('active'), 320);
}

let noiseBuffer = null;
function getNoiseBuffer() {
  if (!audioContext) return null;
  if (!noiseBuffer) {
    const bufferSize = audioContext.sampleRate * 2;
    noiseBuffer = audioContext.createBuffer(1, bufferSize, audioContext.sampleRate);
    const output = noiseBuffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      output[i] = Math.random() * 2 - 1;
    }
  }
  return noiseBuffer;
}

function playPercussionSynth(kind) {
  if (!audioContext || audioContext.state !== 'running' || !masterGain) return;
  const now = audioContext.currentTime;

  if (kind === 'kick') {
    const osc = audioContext.createOscillator();
    const gain = audioContext.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(155, now);
    osc.frequency.exponentialRampToValueAtTime(42, now + 0.05);
    gain.gain.setValueAtTime(0.88, now);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.32);
    osc.connect(gain);
    gain.connect(masterGain);
    osc.start(now);
    osc.stop(now + 0.33);
  } else if (kind === 'snare') {
    const osc = audioContext.createOscillator();
    const oscGain = audioContext.createGain();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(185, now);
    oscGain.gain.setValueAtTime(0.42, now);
    oscGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.08);
    osc.connect(oscGain);
    oscGain.connect(masterGain);
    osc.start(now);
    osc.stop(now + 0.09);

    const nBuf = getNoiseBuffer();
    if (nBuf) {
      const src = audioContext.createBufferSource();
      src.buffer = nBuf;
      const filter = audioContext.createBiquadFilter();
      filter.type = 'highpass';
      filter.frequency.setValueAtTime(800, now);
      const nGain = audioContext.createGain();
      nGain.gain.setValueAtTime(0.68, now);
      nGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.18);
      src.connect(filter);
      filter.connect(nGain);
      nGain.connect(masterGain);
      src.start(now);
      src.stop(now + 0.19);
    }
  } else if (kind === 'hihat_closed' || kind === 'hihat_open') {
    const isClosed = kind === 'hihat_closed';
    const dur = isClosed ? 0.055 : 0.42;
    const nBuf = getNoiseBuffer();
    if (nBuf) {
      const src = audioContext.createBufferSource();
      src.buffer = nBuf;
      const filter = audioContext.createBiquadFilter();
      filter.type = 'bandpass';
      filter.frequency.setValueAtTime(7000, now);
      filter.Q.setValueAtTime(isClosed ? 2.5 : 1.5, now);
      const gain = audioContext.createGain();
      gain.gain.setValueAtTime(0.48, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + dur);
      src.connect(filter);
      filter.connect(gain);
      gain.connect(masterGain);
      src.start(now);
      src.stop(now + dur + 0.01);
    }
  } else if (kind === 'low_tom' || kind === 'high_tom') {
    const fStart = kind === 'low_tom' ? 135 : 220;
    const fEnd = kind === 'low_tom' ? 82 : 145;
    const osc = audioContext.createOscillator();
    const gain = audioContext.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(fStart, now);
    osc.frequency.exponentialRampToValueAtTime(fEnd, now + 0.05);
    gain.gain.setValueAtTime(0.72, now);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.38);
    osc.connect(gain);
    gain.connect(masterGain);
    osc.start(now);
    osc.stop(now + 0.39);
  } else if (kind === 'crash') {
    [440, 630, 890].forEach(f => {
      const osc = audioContext.createOscillator();
      const gain = audioContext.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(f, now);
      gain.gain.setValueAtTime(0.12, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 1.25);
      osc.connect(gain);
      gain.connect(masterGain);
      osc.start(now);
      osc.stop(now + 1.26);
    });
    const nBuf = getNoiseBuffer();
    if (nBuf) {
      const src = audioContext.createBufferSource();
      src.buffer = nBuf;
      const filter = audioContext.createBiquadFilter();
      filter.type = 'bandpass';
      filter.frequency.setValueAtTime(5500, now);
      filter.Q.setValueAtTime(1.2, now);
      const gain = audioContext.createGain();
      gain.gain.setValueAtTime(0.45, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 1.25);
      src.connect(filter);
      filter.connect(gain);
      gain.connect(masterGain);
      src.start(now);
      src.stop(now + 1.26);
    }
  } else if (kind === 'clap') {
    const nBuf = getNoiseBuffer();
    if (nBuf) {
      [0, 0.011, 0.022, 0.033].forEach((offset, idx) => {
        const src = audioContext.createBufferSource();
        src.buffer = nBuf;
        const filter = audioContext.createBiquadFilter();
        filter.type = 'bandpass';
        filter.frequency.setValueAtTime(1200, now + offset);
        filter.Q.setValueAtTime(2.0, now + offset);
        const gain = audioContext.createGain();
        const dur = idx === 3 ? 0.22 : 0.015;
        gain.gain.setValueAtTime(0.0001, now);
        gain.gain.setValueAtTime(0.45, now + offset);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + offset + dur);
        src.connect(filter);
        filter.connect(gain);
        gain.connect(masterGain);
        src.start(now + offset);
        src.stop(now + offset + dur + 0.01);
      });
    }
  } else if (kind === 'cowbell') {
    [540, 800].forEach(f => {
      const osc = audioContext.createOscillator();
      const gain = audioContext.createGain();
      osc.type = 'square';
      osc.frequency.setValueAtTime(f, now);
      gain.gain.setValueAtTime(0.20, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.32);
      osc.connect(gain);
      gain.connect(masterGain);
      osc.start(now);
      osc.stop(now + 0.33);
    });
  } else if (kind === 'ride') {
    const osc = audioContext.createOscillator();
    const gain = audioContext.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(2100, now);
    gain.gain.setValueAtTime(0.28, now);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 1.1);
    osc.connect(gain);
    gain.connect(masterGain);
    osc.start(now);
    osc.stop(now + 1.11);
  }
}

function playSynthNote(instrument, slotOrMode, noteIndex) {
  const note = NOTES[instrument]?.[slotOrMode]?.[noteIndex];
  if (!note) return;
  flashNoteKey(slotOrMode, noteIndex);
  if (!audioContext || audioContext.state !== 'running' || !masterGain) return;

  if (instrument === 'octapad') {
    playPercussionSynth(note.type);
    return;
  }

  const now = audioContext.currentTime;
  const isPiano = instrument === 'piano';
  const duration = isPiano ? 2.30 : 2.10;
  const output = audioContext.createGain();

  output.gain.setValueAtTime(0.0001, now);
  if (isPiano) {
    output.gain.linearRampToValueAtTime(0.28, now + 0.012);
    output.gain.exponentialRampToValueAtTime(0.12, now + 0.35);
    output.gain.exponentialRampToValueAtTime(0.0001, now + duration);
  } else {
    output.gain.linearRampToValueAtTime(0.26, now + 0.004);
    output.gain.exponentialRampToValueAtTime(0.10, now + 0.25);
    output.gain.exponentialRampToValueAtTime(0.0001, now + duration);
  }
  output.connect(masterGain);

  if (isPiano) {
    const chordFreqs = [note.frequency, note.third || (note.frequency * 1.25), note.fifth || (note.frequency * 1.5)];
    const chordGains = [0.44, 0.32, 0.28];
    chordFreqs.forEach((freq, fIndex) => {
      const baseGain = chordGains[fIndex];
      const partials = [
        { mult: 1.0, gain: baseGain * 0.70, decay: duration },
        { mult: 2.0, gain: baseGain * 0.22, decay: duration * 0.85 },
        { mult: 1.002, gain: baseGain * 0.12, decay: duration * 0.90 },
      ];
      for (const p of partials) {
        const osc = audioContext.createOscillator();
        const pGain = audioContext.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq * p.mult, now);
        pGain.gain.setValueAtTime(p.gain, now);
        pGain.gain.exponentialRampToValueAtTime(0.0001, now + p.decay);
        osc.connect(pGain);
        pGain.connect(output);
        osc.start(now);
        osc.stop(now + p.decay + 0.05);
      }
    });
  } else {
    // Guitar: Synthesize root string + defining 3rd string
    const rootFreq = note.frequency;
    const thirdFreq = note.third || (rootFreq * 1.25);
    const dtStrum = 0.0025;

    const rootPartials = [
      { mult: 1.0, gain: 0.50, type: 'triangle', offset: 0, decay: duration },
      { mult: 2.0, gain: 0.20, type: 'sine', offset: 0, decay: duration * 0.8 },
      { mult: 3.0, gain: 0.08, type: 'sine', offset: 0, decay: duration * 0.5 },
    ];
    const thirdPartials = [
      { mult: 1.0, gain: 0.44, type: 'triangle', offset: dtStrum, decay: duration },
      { mult: 2.0, gain: 0.17, type: 'sine', offset: dtStrum, decay: duration * 0.75 },
      { mult: 3.0, gain: 0.06, type: 'sine', offset: dtStrum, decay: duration * 0.45 },
    ];

    for (const p of [...rootPartials, ...thirdPartials]) {
      const osc = audioContext.createOscillator();
      const pGain = audioContext.createGain();
      const tStart = now + p.offset;
      osc.type = p.type;
      osc.frequency.setValueAtTime((p.offset === 0 ? rootFreq : thirdFreq) * p.mult, tStart);
      pGain.gain.setValueAtTime(0.0001, now);
      pGain.gain.setValueAtTime(p.gain, tStart);
      pGain.gain.exponentialRampToValueAtTime(0.0001, tStart + p.decay);
      osc.connect(pGain);
      pGain.connect(output);
      osc.start(tStart);
      osc.stop(tStart + p.decay + 0.05);
    }
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
function processGestureAudio(source, hands, slots, instrument) {
  const chosenInstrument = instrument === 'octapad' ? 'octapad' : (instrument === 'guitar' ? 'guitar' : 'piano');
  const previousInstrument = previousInstrumentBySource.get(source);
  if (previousInstrument && previousInstrument !== chosenInstrument) clearGestureSource(source);
  previousInstrumentBySource.set(source, chosenInstrument);

  const presentSlots = new Set();
  const activeHands = Array.isArray(hands) ? hands : [];
  const handSlots = Array.isArray(slots) ? slots : [];

  if (chosenInstrument === 'guitar') {
    if (activeHands.length && Array.isArray(activeHands[0])) {
      presentSlots.add('guitar');
      const fingerStates = activeHands[0];
      const thumbIsUp = Boolean(fingerStates[0]);
      const guitarMode = thumbIsUp ? 'major' : 'minor';

      // Update UI guitar mode label and chord names in real time
      if (source === 'local') {
        const header = $('guitar-mode-header');
        if (header) {
          header.textContent = thumbIsUp
            ? '🎸 Guitar Strings · [MAJOR MODE active (Thumb UP)]'
            : '🎸 Guitar Strings · [MINOR MODE active (Thumb DOWN)]';
          header.style.color = thumbIsUp ? 'var(--lime)' : '#ff9f43';
        }
        const activeNotes = NOTES.guitar[guitarMode];
        activeNotes.forEach((n, i) => {
          const el = $(`guitar-note-name-${i}`);
          if (el && el.textContent !== n.name) el.textContent = n.name;
        });
      }

      // 4 playable fingers: Index (1), Middle (2), Ring (3), Pinky (4)
      for (let fingerIndex = 1; fingerIndex <= 4; fingerIndex++) {
        const noteIndex = fingerIndex - 1;
        const isUp = Boolean(fingerStates[fingerIndex]);
        const stateKey = `${source}|guitar|${fingerIndex}`;
        const oldState = previousGestureStates.get(stateKey);
        if (oldState === true && isUp === false) {
          const lastAt = lastNoteAt.get(stateKey) || 0;
          const now = performance.now();
          if (now - lastAt > 140) {
            playSynthNote('guitar', guitarMode, noteIndex);
            lastNoteAt.set(stateKey, now);
          }
        }
        previousGestureStates.set(stateKey, isUp);
      }
    } else {
      clearGestureSource(source);
    }
  } else if (chosenInstrument === 'octapad') {
    const isSingleHand = activeHands.length === 1;

    if (isSingleHand && Array.isArray(activeHands[0])) {
      const fingerStates = activeHands[0];
      const thumbIsUp = Boolean(fingerStates[0]);
      const targetBank = thumbIsUp ? 'left' : 'right';
      presentSlots.add(targetBank);

      if (source === 'local') {
        const header = $('octapad-header');
        if (header) {
          header.textContent = thumbIsUp
            ? '🥁 Roland Octapad · [BANK A active (Pads 1-4, Thumb UP)]'
            : '🥁 Roland Octapad · [BANK B active (Pads 5-8, Thumb DOWN)]';
          header.style.color = thumbIsUp ? '#d18eff' : '#ff9f43';
        }
      }

      for (let fingerIndex = 1; fingerIndex <= 4; fingerIndex++) {
        const isUp = Boolean(fingerStates[fingerIndex]);
        const stateKey = `${source}|octapad|single|${fingerIndex}`;
        const oldState = previousGestureStates.get(stateKey);
        if (oldState === true && isUp === false) {
          const lastAt = lastNoteAt.get(stateKey) || 0;
          const now = performance.now();
          if (now - lastAt > 130) {
            playSynthNote('octapad', targetBank, fingerIndex);
            lastNoteAt.set(stateKey, now);
          }
        }
        previousGestureStates.set(stateKey, isUp);
      }
    } else {
      // 2 Hands: Left (Pads 1-4) & Right (Pads 5-8)
      activeHands.forEach((fingerStates, handIndex) => {
        const slot = handSlots[handIndex] || (handIndex === 0 ? 'left' : 'right');
        if (!NOTES.octapad[slot] || !Array.isArray(fingerStates)) return;
        presentSlots.add(slot);

        fingerStates.slice(0, 5).forEach((rawState, fingerIndex) => {
          const isUp = Boolean(rawState);
          const stateKey = `${source}|octapad|${slot}|${fingerIndex}`;
          const oldState = previousGestureStates.get(stateKey);
          if (oldState === true && isUp === false) {
            const lastAt = lastNoteAt.get(stateKey) || 0;
            const now = performance.now();
            if (now - lastAt > 130) {
              playSynthNote('octapad', slot, fingerIndex);
              lastNoteAt.set(stateKey, now);
            }
          }
          previousGestureStates.set(stateKey, isUp);
        });
      });
    }

    for (const slot of ['left', 'right']) {
      if (!presentSlots.has(slot)) {
        const prefix = `${source}|octapad|${slot}|`;
        for (const key of [...previousGestureStates.keys()]) if (key.startsWith(prefix)) previousGestureStates.delete(key);
        for (const key of [...lastNoteAt.keys()]) if (key.startsWith(prefix)) lastNoteAt.delete(key);
      }
    }
  } else {
    // Piano mode
    activeHands.forEach((fingerStates, handIndex) => {
      const slot = handSlots[handIndex] || (handIndex === 0 ? 'left' : 'right');
      if (!NOTES.piano[slot] || !Array.isArray(fingerStates)) return;
      presentSlots.add(slot);
      fingerStates.slice(0, 5).forEach((rawState, fingerIndex) => {
        const isUp = Boolean(rawState);
        const stateKey = `${source}|piano|${slot}|${fingerIndex}`;
        const oldState = previousGestureStates.get(stateKey);
        if (oldState === true && isUp === false) {
          const lastAt = lastNoteAt.get(stateKey) || 0;
          const now = performance.now();
          if (now - lastAt > 140) {
            playSynthNote('piano', slot, fingerIndex);
            lastNoteAt.set(stateKey, now);
          }
        }
        previousGestureStates.set(stateKey, isUp);
      });
    });

    for (const slot of Object.keys(NOTES.piano)) {
      if (!presentSlots.has(slot)) {
        const prefix = `${source}|piano|${slot}|`;
        for (const key of [...previousGestureStates.keys()]) if (key.startsWith(prefix)) previousGestureStates.delete(key);
        for (const key of [...lastNoteAt.keys()]) if (key.startsWith(prefix)) lastNoteAt.delete(key);
      }
    }
  }
}

async function startCamera() {
  localStream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 640 }, height: { ideal: 400 }, frameRate: { ideal: 24, max: 30 } }, audio: false });
  localVideo.srcObject = localStream;
  await localVideo.play();
  setState(localState, 'Camera on');
}
function drawHandLandmarks(allLandmarks, hands) {
  if (!localVideo.videoWidth || !localVideo.videoHeight) return;
  if (localOverlay.width !== localVideo.videoWidth || localOverlay.height !== localVideo.videoHeight) {
    localOverlay.width = localVideo.videoWidth;
    localOverlay.height = localVideo.videoHeight;
  }
  const ctx = localOverlayCtx;
  const w = localOverlay.width, h = localOverlay.height;
  ctx.clearRect(0, 0, w, h);
  if (!allLandmarks || !allLandmarks.length) return;

  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.lineWidth = Math.max(2.5, w / 220);
  const radius = Math.max(4, w / 140);
  const tipIndices = [4, 8, 12, 16, 20];
  const tipLabels = ['T', 'I', 'M', 'R', 'P'];

  allLandmarks.forEach((lm, handIdx) => {
    const handStates = hands && hands[handIdx] ? hands[handIdx] : [true, true, true, true, true];
    // Draw skeleton bone connections
    ctx.strokeStyle = '#c8ff57cc';
    for (const [a, b] of HAND_CONNECTIONS) {
      if (lm[a] && lm[b]) {
        ctx.beginPath();
        ctx.moveTo(lm[a].x * w, lm[a].y * h);
        ctx.lineTo(lm[b].x * w, lm[b].y * h);
        ctx.stroke();
      }
    }
    // Draw joints
    ctx.fillStyle = '#75baffaa';
    for (let i = 0; i < lm.length; i++) {
      if (!tipIndices.includes(i) && lm[i]) {
        ctx.beginPath();
        ctx.arc(lm[i].x * w, lm[i].y * h, radius * 0.7, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    // Draw fingertips with dynamic state color: green if UP, orange if BENT/plucked
    tipIndices.forEach((tipId, fIdx) => {
      const isUp = Boolean(handStates[fIdx]);
      const pt = lm[tipId];
      if (!pt) return;
      const px = pt.x * w, py = pt.y * h;
      ctx.fillStyle = isUp ? '#c8ff57' : '#ff9f43';
      ctx.beginPath();
      ctx.arc(px, py, radius * 1.35, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#0a0c10';
      ctx.lineWidth = 2;
      ctx.stroke();
      // Tip letter badge (T, I, M, R, P)
      ctx.font = `bold ${Math.max(10, Math.round(w / 45))}px 'DM Mono', monospace`;
      ctx.fillStyle = isUp ? '#c8ff57' : '#ff9f43';
      ctx.fillText(tipLabels[fIdx], px + 7, py - 6);
    });
  });
}

function sendTrackingFrames(now) {
  // Reset inflight flag if server took unusually long (> 800ms)
  if (isFrameInFlight && now - lastFrameSend > 800) {
    isFrameInFlight = false;
  }
  // Low-latency flow control: send next frame only after previous frame is handled, with 55ms minimum interval (~18 FPS)
  if (joined && ws && ws.readyState === WebSocket.OPEN && localVideo.readyState >= 2 && localVideo.videoWidth > 0 && !isFrameInFlight && (now - lastFrameSend >= 55)) {
    isFrameInFlight = true;
    lastFrameSend = now;
    const width = 320;
    const height = Math.max(1, Math.round(width * localVideo.videoHeight / localVideo.videoWidth));
    if (trackingCanvas.width !== width || trackingCanvas.height !== height) {
      trackingCanvas.width = width;
      trackingCanvas.height = height;
    }
    trackingCtx.drawImage(localVideo, 0, 0, width, height);
    try {
      const frame = trackingCanvas.toDataURL('image/jpeg', 0.46);
      send({ type: 'frame', frame, instrument: selectedInstrument });
    } catch (error) {
      isFrameInFlight = false;
      console.warn('Could not encode webcam frame for tracking:', error);
    }
  }
  requestAnimationFrame(sendTrackingFrames);
}
requestAnimationFrame(sendTrackingFrames);

function formatInstrumentName(inst) {
  if (inst === 'guitar') return 'Guitar';
  if (inst === 'octapad') return 'Octapad';
  return 'Piano';
}

function renderGestureText(element, hands, slots, instrument) {
  if (!hands || !hands.length) { element.textContent = 'No hand detected — show an open palm'; return; }
  const handSlots = Array.isArray(slots) ? slots : [];
  element.textContent = hands.map((f, i) => {
    if (instrument === 'guitar') {
      const mode = f[0] ? 'MAJOR (Thumb UP)' : 'MINOR (Thumb DOWN)';
      const fingers = f.slice(1).map((v, idx) => `${GUITAR_PLAYING_FINGERS[idx]}:${v ? 'UP' : 'PLUCK'}`).join(' · ');
      return `Guitar [${mode}] · ${fingers}`;
    }
    if (instrument === 'octapad') {
      if (hands.length === 1) {
        const mode = f[0] ? 'BANK A (Thumb UP)' : 'BANK B (Thumb DOWN)';
        const fingers = ['IDX', 'MID', 'RNG', 'PNK'].map((label, idx) => `${label}:${f[idx + 1] ? 'UP' : 'HIT'}`).join(' · ');
        return `Octapad [${mode}] · ${fingers}`;
      }
      const bank = (handSlots[i] || (i === 0 ? 'left' : 'right')) === 'left' ? 'Bank A (Rhythm)' : 'Bank B (Fills)';
      const fingers = f.map((v, idx) => `${idx === 0 ? 'THUMB' : (idx === 1 ? 'IDX' : (idx === 2 ? 'MID' : (idx === 3 ? 'RNG' : 'PNK')))}:${v ? 'UP' : 'HIT'}`).join(' · ');
      return `Octapad [${bank}] · ${fingers}`;
    }
    const name = ((handSlots[i] || (i === 0 ? 'left' : 'right')) === 'right' ? 'Right hand' : 'Left hand');
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
    isFrameInFlight = false;
    trackingReady = true;
    drawHandLandmarks(data.landmarks || [], data.hands || []);
    const hands = data.hands || [], slots = data.slots || [];
    const instrument = data.instrument || selectedInstrument;
    renderGestureText(localGesture, hands, slots, instrument);
    processGestureAudio('local', hands, slots, instrument);
    const instName = formatInstrumentName(instrument);
    setState(localState, `${instName} · ${hands.length ? `Tracking · ${hands.length} hand${hands.length === 1 ? '' : 's'}` : 'Tracking · no hand'}`);
    if (pc && pc.connectionState === 'connected') status('Video connected · Python hand tracking active · gesture instruments ready');
    else status('Python hand tracking active · waiting for opponent video');
  } else if (data.type === 'tracker-error') {
    isFrameInFlight = false;
    trackingReady = false;
    localGesture.textContent = `TRACKER ERROR: ${data.message || 'unknown Python tracking error'}`;
    setState(localState, 'Tracker failed');
    status('Python hand tracking failed. See the message under “Your hand”.');
  } else if (data.type === 'gesture') {
    const instrument = data.instrument || selectedInstrument;
    const hands = data.hands || [], slots = data.slots || [];
    renderGestureText(remoteGesture, hands, slots, instrument);
    processGestureAudio('remote', hands, slots, instrument);
    const instName = formatInstrumentName(instrument);
    setState(remoteState, `${instName} · ${hands.length ? `Tracking · ${hands.length} hand${hands.length === 1 ? '' : 's'}` : 'Connected · no hand'}`);
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
  selectedInstrument = instrumentSelect.value;
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
