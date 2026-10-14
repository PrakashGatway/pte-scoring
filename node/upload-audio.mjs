import { readFile, stat } from 'node:fs/promises';
import { PteClient } from './pte-client.mjs';

// Usage: node node/upload-audio.mjs recording.wav "Text the student should read"
const [filePath, reference] = process.argv.slice(2);
if (!filePath || !reference) {
  console.error('Usage: node node/upload-audio.mjs <audio-file> "reference text"');
  process.exitCode = 1;
} else {
  try {
    if ((await stat(filePath)).size > 10_000_000) throw new Error('Audio exceeds 10 MB');
    const audio = await readFile(filePath);
    const client = new PteClient();
    const result = await client.scoreAudio(
      { id: 'audio-upload', type: 'RA', reference },
      audio,
      { allowProxyScores: true },
    );
    console.log(JSON.stringify(result, null, 2));
  } catch (error) {
    console.error(error.message);
    if (error.details) console.error(JSON.stringify(error.details, null, 2));
    process.exitCode = 1;
  }
}
