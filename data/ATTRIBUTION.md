# Natural audio attribution

These audio files are engineering fixtures, not a representative speech-quality corpus.
The exact source URLs, revisions, hashes and conversions are in `NATURAL_FIXTURES.json`.

## LibriSpeech

- Source dataset: [LibriSpeech, OpenSLR SLR12](https://www.openslr.org/12).
- Dataset creators: Vassil Panayotov, Guoguo Chen, Daniel Povey, Sanjeev Khudanpur. The original audiobook recordings are from LibriVox volunteers.
- License: [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/).
- Download mirror: [langtern/librispeech-test-en](https://github.com/langtern/librispeech-test-en/tree/aa69814de02d7d9eca5e61456c8fee8a0e85dd92), which identifies its data as LibriSpeech test audio and provides a CC BY 4.0 notice.
- Files: `librispeech_5142-36586.wav`, `librispeech_7021-79759.wav`.
- Changes: source FLAC decoded to signed 16-bit PCM WAV with FFmpeg. Sample rate, channels, level and full duration retained. Further benchmark crops must record their exact sample intervals and attribution in the benchmark manifest.
- The mirror provides chapter-level files. Corresponding transcript files list 5 and 6 utterance IDs. A benchmark window should not be mislabeled as an original utterance.

## unfa

- Author: unfa.
- Original: [Clean male shout: “Are you readyyy?!”](https://freesound.org/people/unfa/sounds/258342/), December 20, 2014.
- License shown by the original page: [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
- Download mirror: [Sleepwalking/libllsm2/test/are-you-ready.wav](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/test/are-you-ready.wav). The libllsm2 README identifies the original Freesound URL.
- File: `unfa_are-you-ready.wav`.
- Changes: no changes to the downloaded mirror WAV. The mirror is 44.1 kHz mono PCM while the original is described as 96 kHz stereo FLAC; the mirror's conversion settings are unknown.
- The original page now states that the author does not consent to generative ML training. This project uses the file for non-ML analysis/synthesis evaluation, not generative ML training.

All source/license pages were checked on 2026-10-11. Code licenses of the mirror repositories are not being used as the audio license.

## 初回の使用範囲

今回の比較レポートで使用したのはLibriSpeechの2ファイルの先頭各6秒です。unfaの音声は調査時の取得候補で、初回レポートにも取得スクリプトのmanifestにも含めていません。録音本体はGit管理していません。
