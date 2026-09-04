/**
 * SoundFx — synthesized keyboard click sounds (WebAudio, no samples needed).
 * Three voices: mechanical blue-switch, typewriter, bubble. The main window
 * plays one click per accepted physical key press (driven by keyshow-event),
 * so repeat keys and injected events never fire sounds.
 */
export type SoundVoice = "off" | "click" | "typewriter" | "bubble";

let ctx: AudioContext | null = null;
let voice: SoundVoice = "off";
let volume = 0.6;

function ensureCtx(): AudioContext | null {
  if (typeof window === "undefined") return null;
  try {
    if (!ctx) ctx = new AudioContext();
    if (ctx.state === "suspended") void ctx.resume();
    return ctx;
  } catch {
    return null;
  }
}

export function configureSound(nextVoice: SoundVoice, nextVolume: number) {
  voice = nextVoice;
  volume = Math.min(Math.max(nextVolume, 0), 1);
}

function noiseBurst(ac: AudioContext, when: number, dur: number, filterFreq: number, gainPeak: number) {
  const frames = Math.max(1, Math.floor(ac.sampleRate * dur));
  const buffer = ac.createBuffer(1, frames, ac.sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < frames; i++) data[i] = Math.random() * 2 - 1;
  const src = ac.createBufferSource();
  src.buffer = buffer;
  const filter = ac.createBiquadFilter();
  filter.type = "bandpass";
  filter.frequency.value = filterFreq;
  filter.Q.value = 1.1;
  const gain = ac.createGain();
  gain.gain.setValueAtTime(gainPeak, when);
  gain.gain.exponentialRampToValueAtTime(0.0001, when + dur);
  src.connect(filter).connect(gain).connect(ac.destination);
  src.start(when);
  src.stop(when + dur + 0.02);
}

function tone(ac: AudioContext, when: number, freq: number, dur: number, gainPeak: number, type: OscillatorType = "sine") {
  const osc = ac.createOscillator();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, when);
  const gain = ac.createGain();
  gain.gain.setValueAtTime(gainPeak, when);
  gain.gain.exponentialRampToValueAtTime(0.0001, when + dur);
  osc.connect(gain).connect(ac.destination);
  osc.start(when);
  osc.stop(when + dur + 0.02);
}

export function playKeySound(heavy: boolean) {
  if (voice === "off") return;
  const ac = ensureCtx();
  if (!ac) return;
  const now = ac.currentTime + 0.001;
  const v = volume;
  if (voice === "click") {
    // blue-switch: sharp filtered noise tick + small body thump
    noiseBurst(ac, now, heavy ? 0.014 : 0.009, heavy ? 1300 : 2100, v * (heavy ? 0.9 : 0.7));
    tone(ac, now, heavy ? 150 : 240, heavy ? 0.05 : 0.035, v * 0.25, "triangle");
    if (heavy) tone(ac, now, 60, 0.06, v * 0.4, "sine");
  } else if (voice === "typewriter") {
    // single crisp high tick
    noiseBurst(ac, now, 0.006, 3200, v * 0.8);
    tone(ac, now, 900 + (heavy ? 0 : 300), 0.02, v * 0.16, "square");
  } else if (voice === "bubble") {
    // soft upward chirp
    const osc = ac.createOscillator();
    osc.type = "sine";
    const t0 = now;
    osc.frequency.setValueAtTime(heavy ? 180 : 320, t0);
    osc.frequency.exponentialRampToValueAtTime(heavy ? 380 : 720, t0 + 0.06);
    const gain = ac.createGain();
    gain.gain.setValueAtTime(v * 0.5, t0);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.09);
    osc.connect(gain).connect(ac.destination);
    osc.start(t0);
    osc.stop(t0 + 0.11);
  }
}
