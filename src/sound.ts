/**
 * SoundFx — synthesized keyboard click sounds (WebAudio, no samples needed).
 *
 * Voices:
 *  - click      mechanical blue-switch tick (noise burst + body thump)
 *  - typewriter crisp high tick
 *  - bubble     soft rising chirp
 *  - blub       underwater gurgle: a string of rising wet bubbles
 *  - bell       soft wind-chime ding (bright but gentle)
 *  - mahjong    sharp wooden tile snap
 *  - arcade     retro 8-bit "beep-doop"
 *  - laser      sci-fi pew downward sweep
 * The main window plays one click per accepted physical key press (driven by
 * keyshow-event), so repeats and injected events never fire sounds.
 */
export type SoundVoice = "off" | "click" | "typewriter" | "bubble" | "blub" | "bell" | "mahjong" | "arcade" | "laser" | "custom";

let ctx: AudioContext | null = null;
let voice: SoundVoice = "off";
let volume = 0.6;
let customBuffer: AudioBuffer | null = null;

/** Decode a user-supplied audio file (data URL from the custom sounds folder). */
export async function loadCustomSound(dataUrl: string): Promise<boolean> {
  try {
    const ac = ensureCtx();
    if (!ac) return false;
    const response = await fetch(dataUrl);
    const bytes = await response.arrayBuffer();
    customBuffer = await ac.decodeAudioData(bytes);
    return true;
  } catch {
    return false;
  }
}

// Master trim: synthesized peaks are boosted ~1.35x vs. the original design so
// the sounds read clearly on normal speakers without clipping the compressor.
const MASTER_GAIN = 1.35;

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

function noiseBurst(
  ac: AudioContext,
  when: number,
  dur: number,
  filterFreq: number,
  gainPeak: number,
  q = 1.1,
) {
  const frames = Math.max(1, Math.floor(ac.sampleRate * dur));
  const buffer = ac.createBuffer(1, frames, ac.sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < frames; i++) data[i] = Math.random() * 2 - 1;
  const src = ac.createBufferSource();
  src.buffer = buffer;
  const filter = ac.createBiquadFilter();
  filter.type = "bandpass";
  filter.frequency.value = filterFreq;
  filter.Q.value = q;
  const gain = ac.createGain();
  gain.gain.setValueAtTime(gainPeak * MASTER_GAIN, when);
  gain.gain.exponentialRampToValueAtTime(0.0001, when + dur);
  src.connect(filter).connect(gain).connect(ac.destination);
  src.start(when);
  src.stop(when + dur + 0.02);
}

function tone(
  ac: AudioContext,
  when: number,
  freq: number,
  dur: number,
  gainPeak: number,
  type: OscillatorType = "sine",
) {
  const osc = ac.createOscillator();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, when);
  const gain = ac.createGain();
  gain.gain.setValueAtTime(gainPeak * MASTER_GAIN, when);
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
  if (voice === "custom") {
    if (!customBuffer) return;
    const source = ac.createBufferSource();
    source.buffer = customBuffer;
    source.playbackRate.value = heavy ? 0.9 : 1;
    const gain = ac.createGain();
    gain.gain.value = Math.min(v * 1.2, 1);
    source.connect(gain).connect(ac.destination);
    source.start(now);
    return;
  }
  if (voice === "click") {
    // blue-switch: sharp filtered noise tick + small body thump
    noiseBurst(ac, now, heavy ? 0.014 : 0.009, heavy ? 1300 : 2100, v * (heavy ? 0.9 : 0.7));
    tone(ac, now, heavy ? 150 : 240, heavy ? 0.05 : 0.035, v * 0.3, "triangle");
    if (heavy) tone(ac, now, 60, 0.06, v * 0.45, "sine");
  } else if (voice === "typewriter") {
    // one crisp high tick
    noiseBurst(ac, now, 0.006, 3200, v * 0.85);
    tone(ac, now, 900 + (heavy ? 0 : 300), 0.02, v * 0.2, "square");
  } else if (voice === "bubble") {
    // soft upward chirp
    const osc = ac.createOscillator();
    osc.type = "sine";
    const t0 = now;
    osc.frequency.setValueAtTime(heavy ? 180 : 320, t0);
    osc.frequency.exponentialRampToValueAtTime(heavy ? 380 : 720, t0 + 0.06);
    const gain = ac.createGain();
    gain.gain.setValueAtTime(v * 0.55 * MASTER_GAIN, t0);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.09);
    osc.connect(gain).connect(ac.destination);
    osc.start(t0);
    osc.stop(t0 + 0.11);
  } else if (voice === "arcade") {
    // retro 8-bit: short square-wave "beep-doop" coin-up feel
    const steps = heavy ? 3 : 2;
    for (let i = 0; i < steps; i++) {
      const at = now + i * (heavy ? 0.11 : 0.08);
      const freq = 880 * (i % 2 === 0 ? 1 : 1.5);
      const osc = ac.createOscillator();
      osc.type = "square";
      osc.frequency.value = freq;
      const gain = ac.createGain();
      gain.gain.setValueAtTime(v * 0.24 * MASTER_GAIN, at);
      gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.09);
      osc.connect(gain).connect(ac.destination);
      osc.start(at);
      osc.stop(at + 0.11);
    }
  } else if (voice === "laser") {
    // sci-fi pew: sharp downward sweep, longer for heavy keys
    const osc = ac.createOscillator();
    osc.type = "square";
    osc.frequency.setValueAtTime(1500, now);
    osc.frequency.exponentialRampToValueAtTime(heavy ? 140 : 260, now + (heavy ? 0.22 : 0.13));
    const gain = ac.createGain();
    gain.gain.setValueAtTime(v * 0.3 * MASTER_GAIN, now);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + (heavy ? 0.24 : 0.15));
    osc.connect(gain).connect(ac.destination);
    osc.start(now);
    osc.stop(now + (heavy ? 0.26 : 0.16));
    noiseBurst(ac, now + (heavy ? 0.16 : 0.09), 0.05, 2400, v * 0.1);
  } else if (voice === "mahjong") {
    // sharp wooden tile snap: dense low-mid click + short body
    noiseBurst(ac, now, heavy ? 0.02 : 0.013, heavy ? 900 : 1300, v * (heavy ? 0.95 : 0.75), 1.6);
    tone(ac, now, heavy ? 110 : 180, heavy ? 0.09 : 0.06, v * 0.5, "triangle");
    tone(ac, now + 0.002, 2400, 0.012, v * 0.2, "sine");
  }
}

/** Metronome tick for rhythm practice (independent from key sounds). */
export function playMetronomeTick(accent: boolean) {
  const ac = ensureCtx();
  if (!ac) return;
  const now = ac.currentTime + 0.001;
  const osc = ac.createOscillator();
  osc.type = "square";
  osc.frequency.value = accent ? 1320 : 880;
  const gain = ac.createGain();
  gain.gain.setValueAtTime(accent ? 0.32 : 0.22, now);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.06);
  osc.connect(gain).connect(ac.destination);
  osc.start(now);
  osc.stop(now + 0.07);
}
