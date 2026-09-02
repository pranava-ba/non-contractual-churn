"""Create a Desktop shortcut that launches the Paper Tracker GUI with pythonw.exe
(no console window) and a custom icon. Re-runnable and self-contained — no exe build.

    python tools/make_shortcut.py

The shortcut can then be dragged to Start / pinned. Re-run it if you move the project.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ICON = ROOT / "gui" / "assets" / "paper-tracker.ico"


def make_icon() -> None:
    """Indigo→violet rounded square with a white open-book glyph (matches the app)."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("Pillow not installed; shortcut will use the default python icon.")
        return
    ICON.parent.mkdir(parents=True, exist_ok=True)
    s = 256
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    top, bot = (94, 106, 210), (139, 92, 246)          # #5E6AD2 -> #8B5CF6
    for y in range(s):
        t = y / s
        d.line([(0, y), (s, y)],
               fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=58, fill=255)
    img.putalpha(mask)
    # open-book: two page panels + spine
    d = ImageDraw.Draw(img)
    w = (255, 255, 255, 255)
    d.rounded_rectangle([54, 84, 122, 178], radius=8, outline=w, width=11)
    d.rounded_rectangle([134, 84, 202, 178], radius=8, outline=w, width=11)
    d.line([(128, 78), (128, 184)], fill=w, width=11)
    img.save(ICON, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("Icon:", ICON)


def _psq(s: str) -> str:  # single-quote a string for PowerShell (literal, safe for backslashes)
    return "'" + str(s).replace("'", "''") + "'"


def make_shortcut() -> None:
    pyw = Path(sys.executable).with_name("pythonw.exe")
    target = pyw if pyw.exists() else Path(sys.executable)
    desktop = Path(os.path.expanduser("~")) / "Desktop"
    lnk = desktop / "Paper Tracker.lnk"
    icon = ICON if ICON.exists() else target
    ps = "; ".join([
        "$ws = New-Object -ComObject WScript.Shell",
        f"$sc = $ws.CreateShortcut({_psq(lnk)})",
        f"$sc.TargetPath = {_psq(target)}",
        '$sc.Arguments = "-m gui"',
        f"$sc.WorkingDirectory = {_psq(ROOT)}",
        f"$sc.IconLocation = {_psq(icon)}",
        '$sc.Description = "Research Paper Tracker"',
        "$sc.WindowStyle = 1",
        "$sc.Save()",
    ])
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], check=True)
    print("Shortcut:", lnk)
    print(f"  target : {target} -m gui")
    print(f"  workdir: {ROOT}")


if __name__ == "__main__":
    make_icon()
    make_shortcut()
    print("\nDone. Double-click 'Paper Tracker' on your Desktop. "
          "Drag it onto Start (or the taskbar) to pin it.")
