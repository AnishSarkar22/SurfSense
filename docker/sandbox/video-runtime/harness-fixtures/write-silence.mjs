import {writeFile} from "node:fs/promises";
import path from "node:path";

const output = process.argv[2];
const seconds = Number(process.argv[3]);
if (!output || !Number.isFinite(seconds) || seconds <= 0 || seconds > 180) {
  throw new Error("Usage: node write-silence.mjs OUTPUT.wav SECONDS");
}
const target = path.resolve(output);

const sampleRate = 48_000;
const channels = 1;
const bytesPerSample = 2;
const dataBytes = Math.ceil(seconds * sampleRate) * channels * bytesPerSample;
const wav = Buffer.alloc(44 + dataBytes);
wav.write("RIFF", 0);
wav.writeUInt32LE(36 + dataBytes, 4);
wav.write("WAVEfmt ", 8);
wav.writeUInt32LE(16, 16);
wav.writeUInt16LE(1, 20);
wav.writeUInt16LE(channels, 22);
wav.writeUInt32LE(sampleRate, 24);
wav.writeUInt32LE(sampleRate * channels * bytesPerSample, 28);
wav.writeUInt16LE(channels * bytesPerSample, 32);
wav.writeUInt16LE(bytesPerSample * 8, 34);
wav.write("data", 36);
wav.writeUInt32LE(dataBytes, 40);
await writeFile(target, wav);
