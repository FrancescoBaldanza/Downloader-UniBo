"""
create_app_bundle.py - Crea il bundle nativo macOS 'UniBo Downloader.app'
con icona personalizzata (.icns), Info.plist con permessi TCC, launcher nativo compilato (Mach-O)
e firma ad-hoc per garantire che macOS chieda i permessi una sola volta a nome di 'UniBo Downloader'.
"""

import os
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_NAME = "UniBo Downloader.app"
APP_DIR = PROJECT_ROOT / APP_NAME
CONTENTS_DIR = APP_DIR / "Contents"
MACOS_DIR = CONTENTS_DIR / "MacOS"
RESOURCES_DIR = CONTENTS_DIR / "Resources"
ICONSET_DIR = PROJECT_ROOT / "AppIcon.iconset"


def render_app_icon(size: int = 1024) -> Image.Image:
    """
    Renderizza l'icona ufficiale UniBo Downloader ad alta risoluzione:
    - Sfondo squircle macOS bianco (#FFFFFF)
    - Due cerchi concentrici con proporzioni e colore rosso istituzionale UniBo (#BA271A)
    - Tridente di Nettuno all'ingiù centrato
    """
    try:
        from PyQt6.QtGui import QImage, QPainter, QColor, QPen, QPainterPath, QBrush
        from PyQt6.QtCore import Qt, QPointF, QRectF

        qimg = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
        qimg.fill(Qt.GlobalColor.transparent)

        painter = QPainter(qimg)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        scale = size / 1024.0

        # Sfondo squircle macOS bianco
        margin = 82.0 * scale
        squircle_size = size - 2 * margin
        squircle_rect = QRectF(margin, margin, squircle_size, squircle_size)
        radius = 195.0 * scale

        painter.setPen(QPen(QColor(220, 220, 224), max(1.0, 4.0 * scale)))
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawRoundedRect(squircle_rect, radius, radius)

        # Rosso Sigillo UniBo
        unibo_red = QColor(186, 39, 26)
        cx, cy = size / 2.0, size / 2.0

        # 1. Cerchio esterno
        r_outer = 365.0 * scale
        pen_outer = QPen(unibo_red, max(1.0, 13.0 * scale))
        pen_outer.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_outer)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), r_outer, r_outer)

        # 2. Cerchio interno (rapporto ~0.69 fedele al sigillo UniBo)
        r_inner = 252.0 * scale
        pen_inner = QPen(unibo_red, max(1.0, 9.5 * scale))
        pen_inner.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_inner)
        painter.drawEllipse(QPointF(cx, cy), r_inner, r_inner)

        # 3. Tridente classico all'ingiù
        tcy = cy - 5.0 * scale
        w_stem = 15.0 * scale
        y_top = tcy - 148.0 * scale
        y_base = tcy - 38.0 * scale

        trident_path = QPainterPath()
        trident_path.moveTo(cx - w_stem, y_top)
        trident_path.lineTo(cx + w_stem, y_top)
        trident_path.lineTo(cx + w_stem, y_base)

        # Spalla destra e rebbo esterno destro
        trident_path.cubicTo(cx + 45.0 * scale, y_base + 6.0 * scale, cx + 90.0 * scale, y_base + 22.0 * scale, cx + 106.0 * scale, tcy + 15.0 * scale)
        trident_path.cubicTo(cx + 116.0 * scale, tcy + 45.0 * scale, cx + 112.0 * scale, tcy + 95.0 * scale, cx + 98.0 * scale, tcy + 125.0 * scale)
        trident_path.lineTo(cx + 80.0 * scale, tcy + 116.0 * scale)
        trident_path.cubicTo(cx + 90.0 * scale, tcy + 90.0 * scale, cx + 88.0 * scale, tcy + 48.0 * scale, cx + 72.0 * scale, tcy + 20.0 * scale)
        trident_path.cubicTo(cx + 58.0 * scale, tcy - 4.0 * scale, cx + 38.0 * scale, tcy - 14.0 * scale, cx + 18.0 * scale, tcy - 18.0 * scale)

        # Dente centrale
        trident_path.lineTo(cx + 14.0 * scale, tcy + 138.0 * scale)
        trident_path.lineTo(cx, tcy + 168.0 * scale)
        trident_path.lineTo(cx - 14.0 * scale, tcy + 138.0 * scale)

        # Bordo interno rebbo sinistro
        trident_path.lineTo(cx - 18.0 * scale, tcy - 18.0 * scale)
        trident_path.cubicTo(cx - 38.0 * scale, tcy - 14.0 * scale, cx - 58.0 * scale, tcy - 4.0 * scale, cx - 72.0 * scale, tcy + 20.0 * scale)
        trident_path.cubicTo(cx - 88.0 * scale, tcy + 48.0 * scale, cx - 90.0 * scale, tcy + 90.0 * scale, cx - 80.0 * scale, tcy + 116.0 * scale)
        trident_path.lineTo(cx - 98.0 * scale, tcy + 125.0 * scale)
        trident_path.cubicTo(cx - 112.0 * scale, tcy + 95.0 * scale, cx - 116.0 * scale, tcy + 45.0 * scale, cx - 106.0 * scale, tcy + 15.0 * scale)
        trident_path.cubicTo(cx - 90.0 * scale, y_base + 22.0 * scale, cx - 45.0 * scale, y_base + 6.0 * scale, cx - w_stem, y_base)
        trident_path.closeSubpath()

        pen_arrow = QPen(unibo_red, max(1.0, 11.5 * scale))
        pen_arrow.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen_arrow.setCapStyle(Qt.PenCapStyle.RoundCap)

        painter.setPen(pen_arrow)
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawPath(trident_path)

        painter.end()

        ptr = qimg.bits()
        ptr.setsize(qimg.sizeInBytes())
        pil_img = Image.frombuffer("RGBA", (size, size), bytes(ptr), "raw", "BGRA", 0, 1)
        return pil_img.copy()

    except Exception:
        scale = 4
        hi = size * scale
        img = Image.new("RGBA", (hi, hi), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        margin = int(82 * scale)
        radius = int(195 * scale)
        squircle_box = [margin, margin, hi - margin, hi - margin]

        draw.rounded_rectangle(
            squircle_box,
            radius=radius,
            fill=(255, 255, 255, 255),
            outline=(220, 220, 224, 255),
            width=int(4 * scale)
        )

        unibo_red = (186, 39, 26, 255)
        cx, cy = hi / 2.0, hi / 2.0

        r_outer = 365.0 * scale
        draw.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], outline=unibo_red, width=int(13 * scale))

        r_inner = 252.0 * scale
        draw.ellipse([cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner], outline=unibo_red, width=int(9.5 * scale))

        tcy = cy - 5.0 * scale
        w_stem = 15.0 * scale
        y_top = tcy - 148.0 * scale
        y_base = tcy - 38.0 * scale

        pts = [
            (cx - w_stem, y_top),
            (cx + w_stem, y_top),
            (cx + w_stem, y_base),
            (cx + 85.0 * scale, y_base + 12.0 * scale),
            (cx + 98.0 * scale, tcy + 125.0 * scale),
            (cx + 80.0 * scale, tcy + 116.0 * scale),
            (cx + 70.0 * scale, tcy + 20.0 * scale),
            (cx + 18.0 * scale, tcy - 18.0 * scale),
            (cx + 14.0 * scale, tcy + 138.0 * scale),
            (cx, tcy + 168.0 * scale),
            (cx - 14.0 * scale, tcy + 138.0 * scale),
            (cx - 18.0 * scale, tcy - 18.0 * scale),
            (cx - 70.0 * scale, tcy + 20.0 * scale),
            (cx - 80.0 * scale, tcy + 116.0 * scale),
            (cx - 98.0 * scale, tcy + 125.0 * scale),
            (cx - 85.0 * scale, y_base + 12.0 * scale),
            (cx - w_stem, y_base),
        ]
        draw.polygon(pts, fill=(255, 255, 255, 255))
        draw.line(pts + [pts[0]], fill=unibo_red, width=int(11.5 * scale), joint="curve")

        return img.resize((size, size), Image.Resampling.LANCZOS)


def generate_icon():
    print("[1/4] Creazione grafica icona ad alta risoluzione 1024x1024...")
    master_img = render_app_icon(1024)

    gui_dir = PROJECT_ROOT / "gui"
    gui_dir.mkdir(parents=True, exist_ok=True)
    master_img.save(gui_dir / "icon.png", "PNG")
    master_img.save(RESOURCES_DIR / "icon.png", "PNG")

    if ICONSET_DIR.exists():
        shutil.rmtree(ICONSET_DIR)
    ICONSET_DIR.mkdir(parents=True, exist_ok=True)

    icon_sizes = [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"),
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png"),
    ]

    for s, name in icon_sizes:
        resized = master_img.resize((s, s), Image.Resampling.LANCZOS)
        resized.save(ICONSET_DIR / name, "PNG")

    print("[2/4] Compilazione icona nativa macOS AppIcon.icns...")
    icns_path = RESOURCES_DIR / "AppIcon.icns"
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(["iconutil", "-c", "icns", str(ICONSET_DIR), "-o", str(icns_path)], check=True)
    shutil.rmtree(ICONSET_DIR, ignore_errors=True)


def build_app():
    print(f"Costruzione bundle applicazione: {APP_DIR}...")
    MACOS_DIR.mkdir(parents=True, exist_ok=True)
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Info.plist con descrizioni esplicite dei permessi macOS TCC
    # Questo garantisce che macOS mostri il nome 'UniBo Downloader' con l'icona ufficiale
    # e ricordi i permessi una sola volta senza allarmi ripetuti su python3.11.
    info_plist_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>UniBo Downloader</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>it.unibo.downloader</string>
    <key>CFBundleName</key>
    <string>UniBo Downloader</string>
    <key>CFBundleDisplayName</key>
    <string>UniBo Downloader</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
    <key>NSSupportsAutomaticGraphicsSwitching</key>
    <true/>
    <key>NSDesktopFolderUsageDescription</key>
    <string>UniBo Downloader necessita dell'accesso alla cartella Scrivania per creare e sincronizzare le cartelle dei tuoi corsi universitari.</string>
    <key>NSDocumentsFolderUsageDescription</key>
    <string>UniBo Downloader necessita dell'accesso alla cartella Documenti per salvare e organizzare i materiali didattici dei tuoi insegnamenti.</string>
    <key>NSDownloadsFolderUsageDescription</key>
    <string>UniBo Downloader necessita dell'accesso alla cartella Download per scaricare i file e le dispense da Virtuale UniBo.</string>
    <key>NSRemovableVolumesUsageDescription</key>
    <string>UniBo Downloader necessita dell'accesso ai volumi esterni per salvare i materiali dei corsi.</string>
    <key>NSAppleEventsUsageDescription</key>
    <string>UniBo Downloader invia notifiche di sistema al completamento delle sincronizzazioni.</string>
</dict>
</plist>
"""
    with open(CONTENTS_DIR / "Info.plist", "w", encoding="utf-8") as f:
        f.write(info_plist_content)

    # 2. Genera Icona
    generate_icon()

    # 3. Compila launcher nativo Mach-O in C per assegnare la responsabilità a 'it.unibo.downloader'
    print("[3/4] Compilazione launcher binario nativo macOS (Mach-O)...")
    c_source = f"""
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#include <libgen.h>
#include <mach-o/dyld.h>

int main(int argc, char *argv[]) {{
    char exePath[PATH_MAX];
    uint32_t size = sizeof(exePath);
    if (_NSGetExecutablePath(exePath, &size) != 0) {{
        return 1;
    }}

    // Percorso reale del bundle
    char *dir1 = dirname(exePath);       // Contents/MacOS
    char *dir2 = dirname(dir1);          // Contents
    char *appDir = dirname(dir2);        // UniBo Downloader.app
    char *projectRoot = dirname(appDir); // Project root

    chdir(projectRoot);

    char pythonPathEnv[PATH_MAX * 2];
    const char *existingPPath = getenv("PYTHONPATH");
    if (existingPPath && strlen(existingPPath) > 0) {{
        snprintf(pythonPathEnv, sizeof(pythonPathEnv), "%s:%s", projectRoot, existingPPath);
    }} else {{
        snprintf(pythonPathEnv, sizeof(pythonPathEnv), "%s", projectRoot);
    }}
    setenv("PYTHONPATH", pythonPathEnv, 1);

    // Eseguibile Python
    const char *pythonBin = "/Users/francescobaldanza/Workspace/miniconda3/bin/python3";
    if (access(pythonBin, X_OK) != 0) {{
        pythonBin = "python3";
    }}

    char mainScript[PATH_MAX];
    snprintf(mainScript, sizeof(mainScript), "%s/main.py", projectRoot);

    char *args[] = {{
        (char *)pythonBin,
        mainScript,
        NULL
    }};

    execv(pythonBin, args);
    return 1;
}}
"""
    c_source_path = PROJECT_ROOT / "scripts" / "launcher.c"
    with open(c_source_path, "w", encoding="utf-8") as f:
        f.write(c_source)

    exec_path = MACOS_DIR / "UniBo Downloader"
    try:
        subprocess.run(["clang", "-O2", str(c_source_path), "-o", str(exec_path)], check=True)
        print("   Launcher nativo compilato con successo.")
    except Exception as e:
        print(f"   Fallback su script di avvio: {e}")
        launcher_script = f"""#!/bin/bash
DIR="$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" && pwd )"
PROJECT_ROOT="$( cd "$DIR/../../.." && pwd )"
PYTHON_EXEC="/Users/francescobaldanza/Workspace/miniconda3/bin/python3"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
cd "$PROJECT_ROOT"
exec "$PYTHON_EXEC" main.py
"""
        with open(exec_path, "w", encoding="utf-8") as f:
            f.write(launcher_script)

    os.chmod(exec_path, 0o755)
    c_source_path.unlink(missing_ok=True)

    # 4. Firma ad-hoc del bundle e rimozione attributi di quarantena
    print("[4/4] Firma ad-hoc del bundle e registrazione autorizzazioni TCC...")
    try:
        # Pulisci attributi estesi residui (detritus) per consentire la firma
        subprocess.run(["xattr", "-cr", str(APP_DIR)], check=False)
        subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(APP_DIR)], check=True)
    except Exception as e:
        print(f"   Avviso durante codesign: {e}")

    # Touch e aggiornamento database LaunchServices macOS per refresh immediato icona Finder
    subprocess.run(["touch", str(APP_DIR)], check=False)
    subprocess.run(["touch", str(CONTENTS_DIR / "Info.plist")], check=False)
    subprocess.run(["touch", str(RESOURCES_DIR / "AppIcon.icns")], check=False)
    
    lsregister_candidates = [
        "/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister",
        "/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
    ]
    for lspath in lsregister_candidates:
        if os.path.exists(lspath):
            subprocess.run([lspath, "-f", "-R", "-u", str(APP_DIR)], check=False)
            break

    # Svuota cache icone QuickLook/Finder
    subprocess.run(["qlmanage", "-r", "cache"], check=False)

    # Aggiorna anche link su Desktop
    desktop_link = Path.home() / "Desktop" / APP_NAME
    if desktop_link.exists() or desktop_link.is_symlink():
        desktop_link.unlink(missing_ok=True)
    subprocess.run(["ln", "-sf", str(APP_DIR), str(desktop_link)], check=False)

    print(f"\nApplicazione macOS creata e firmata con successo in:")
    print(f"   {APP_DIR}")


if __name__ == "__main__":
    build_app()
