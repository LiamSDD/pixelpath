import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from pixelpath import render_svg

SCENE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <rect x="16" y="16" width="480" height="480" rx="96" fill="#0f172a"/>
  <path d="M256 64 C362 64 448 150 448 256 S362 448 256 448 64 362 64 256 150 64 256 64 Z" fill="#38bdf8" fill-opacity="0.85"/>
  <path d="M96 352 Q176 192 256 352 T416 352" fill="none" stroke="#f59e0b" stroke-width="18"/>
  <path fill="#e11d48" fill-rule="evenodd" d="M256 120 A136 136 0 1 1 255.9 120 Z M256 168 A88 88 0 1 0 256.1 168 Z"/>
  <path d="M140 140 C200 60 312 60 372 140 C432 220 312 300 256 256 C200 212 80 220 140 140 Z" fill="#a78bfa" opacity="0.6"/>
</svg>"""


def main() -> None:
    timings = []
    for _ in range(5):
        start = time.perf_counter()
        canvas = render_svg(SCENE)
        canvas.to_png_bytes()
        timings.append(time.perf_counter() - start)
    print(f"python {sys.version.split()[0]}: 512x512 scene, render + PNG encode")
    print(f"  best {min(timings):.3f}s  median {statistics.median(timings):.3f}s  over {len(timings)} runs")


if __name__ == "__main__":
    main()
