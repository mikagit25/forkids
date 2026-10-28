"""Image models, both run locally on CPU through onnxruntime.

depth()    - Depth Anything V2 *Small* (Apache-2.0). Only the Small model is licensed for commercial use;
             the Base/Large checkpoints are CC BY-NC and must not be used here.
             Gives a relative depth map used for 2.5D parallax: the photo's pixels are only shifted,
             nothing is painted in, so the archival image stays authentic.
colorize() - DDColor (Apache-2.0). Used only on shots marked `colorize: true`; the original is always
             shown first and the colorized version is labelled on screen.

Results are cached next to the photo (<name>.depth.png, <name>.color.jpg), so each model runs once per image.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DEPTH_MODEL = ROOT / "models" / "depth_anything_v2_vits.onnx"
COLOR_MODEL = ROOT / "models" / "ddcolor.onnx"
_sessions: dict = {}


def _session(path: Path):
    if path not in _sessions:
        import onnxruntime as ort
        so = ort.SessionOptions()
        so.log_severity_level = 3
        _sessions[path] = ort.InferenceSession(str(path), so, providers=["CPUExecutionProvider"])
    return _sessions[path]


def depth_available() -> bool:
    return DEPTH_MODEL.exists()


def color_available() -> bool:
    return COLOR_MODEL.exists()


def depth(img_path: Path) -> np.ndarray | None:
    """float32 HxW in 0..1, 1 = nearest. None if the model is not installed."""
    cache = img_path.with_suffix(".depth.png")
    if cache.exists():
        return cv2.imread(str(cache), cv2.IMREAD_UNCHANGED).astype(np.float32) / 65535
    if not depth_available():
        return None
    bgr = cv2.imread(str(img_path))
    h, w = bgr.shape[:2]
    x = cv2.resize(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), (518, 518), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255
    x = (x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    s = _session(DEPTH_MODEL)
    out = s.run(None, {s.get_inputs()[0].name: x.transpose(2, 0, 1)[None].astype(np.float32)})[0][0]
    d = cv2.resize(out, (w, h), interpolation=cv2.INTER_CUBIC)
    lo, hi = np.percentile(d, 2), np.percentile(d, 98)
    d = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)
    # edge-aware smoothing: keeps object outlines, removes model noise that would make pixels shimmer
    d = cv2.bilateralFilter(d.astype(np.float32), 9, 0.1, 9)
    cv2.imwrite(str(cache), (d * 65535).astype(np.uint16))
    return d


def is_grayscale(bgr: np.ndarray) -> bool:
    small = cv2.resize(bgr, (128, 128)).astype(np.int16)
    sat = np.abs(small[..., 0] - small[..., 1]) + np.abs(small[..., 1] - small[..., 2])
    return float(np.mean(sat)) < 18   # sepia/toned prints count as monochrome too


def colorize(img_path: Path) -> Path | None:
    """Writes <name>.color.jpg and returns its path. None if model missing."""
    out_path = img_path.with_suffix(".color.jpg")
    if out_path.exists():
        return out_path
    if not color_available():
        return None
    bgr = cv2.imread(str(img_path))
    h, w = bgr.shape[:2]
    f = bgr.astype(np.float32) / 255
    L = cv2.cvtColor(f, cv2.COLOR_BGR2LAB)[..., :1]
    small = cv2.resize(f, (512, 512))
    Ls = cv2.cvtColor(small, cv2.COLOR_BGR2LAB)[..., :1]
    gray_rgb = cv2.cvtColor(np.concatenate([Ls, np.zeros_like(Ls), np.zeros_like(Ls)], -1), cv2.COLOR_LAB2RGB)
    s = _session(COLOR_MODEL)
    ab = s.run(None, {s.get_inputs()[0].name: gray_rgb.transpose(2, 0, 1)[None].astype(np.float32)})[0][0]
    ab = cv2.resize(ab.transpose(1, 2, 0), (w, h), interpolation=cv2.INTER_CUBIC)
    ab *= 0.85  # slightly muted: reads as a careful restoration, not a modern photo
    lab = np.concatenate([L, ab], -1)
    out = np.clip(cv2.cvtColor(lab, cv2.COLOR_LAB2BGR) * 255, 0, 255).astype(np.uint8)
    cv2.imwrite(str(out_path), out, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return out_path
