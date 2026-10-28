#!/bin/bash
# One-time setup on macOS 13+ (Intel or Apple Silicon). Run from this folder:  bash setup_mac.sh
set -e
cd "$(dirname "$0")"

if ! command -v brew >/dev/null; then
  echo "Homebrew is required: https://brew.sh"; exit 1
fi
brew list python@3.12 >/dev/null 2>&1 || brew install python@3.12
command -v ffmpeg >/dev/null || brew install ffmpeg

PY="$(brew --prefix python@3.12)/bin/python3.12"
[ -d .venv ] || "$PY" -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

mkdir -p models fonts
[ -f models/kokoro-v1.0.onnx ] || curl -L -o models/kokoro-v1.0.onnx \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
[ -f models/voices-v1.0.bin ] || curl -L -o models/voices-v1.0.bin \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin

G=https://raw.githubusercontent.com/google/fonts/main/ofl
[ -f fonts/PlayfairDisplay.ttf ]   || curl -sL -o fonts/PlayfairDisplay.ttf   "$G/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf"
[ -f fonts/Oswald.ttf ]            || curl -sL -o fonts/Oswald.ttf            "$G/oswald/Oswald%5Bwght%5D.ttf"
[ -f fonts/SourceSans3.ttf ]       || curl -sL -o fonts/SourceSans3.ttf       "$G/sourcesans3/SourceSans3%5Bwght%5D.ttf"
[ -f fonts/EBGaramond.ttf ]        || curl -sL -o fonts/EBGaramond.ttf        "$G/ebgaramond/EBGaramond%5Bwght%5D.ttf"
[ -f fonts/EBGaramond-Italic.ttf ] || curl -sL -o fonts/EBGaramond-Italic.ttf "$G/ebgaramond/EBGaramond-Italic%5Bwght%5D.ttf"

echo
echo "Ready. Next:"
echo "  source .venv/bin/activate"
echo "  python run.py episodes/1918-flu all"
