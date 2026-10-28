#!/bin/bash
# One-time setup on a Linux server (Ubuntu/Debian). Run from this folder:  bash setup_linux.sh
set -e
cd "$(dirname "$0")"
command -v ffmpeg >/dev/null || { echo "installing ffmpeg"; sudo apt-get update -y && sudo apt-get install -y ffmpeg; }
python3 -c 'import venv' 2>/dev/null || sudo apt-get install -y python3-venv
[ -d .venv ] || python3 -m venv .venv
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
