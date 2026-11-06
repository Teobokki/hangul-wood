#!/bin/sh
# ONE Windows build: PyInstaller onedir -> Inno Setup installer + portable zip (same files)
set -e
export PATH=/workspace/wine-portable/current/bin:$PATH WINEPREFIX=/workspace/exwifi/.wine WINEDEBUG=-all
cd /workspace/hangul-wood
V=1.0.1
[ -f model/en_ko/model.bin ] || sh tools/get_model.sh
rm -rf build "dist/HANGUL WOOD"
wine 'C:\Python311\python.exe' -m PyInstaller --noconfirm "HANGUL WOOD.spec" > pyi.log 2>&1; echo PYI_DONE
wine 'C:\InnoSetup\ISCC.exe' installer.iss > iss.log 2>&1; echo ISS_DONE
cd dist && rm -f HANGUL-WOOD-$V-Windows-x64.zip && python3 -c "import shutil;shutil.make_archive('HANGUL-WOOD-$V-Windows-x64','zip','.','HANGUL WOOD')" && echo ZIP_DONE
ls -la; sha256sum HANGUL-WOOD-Setup-$V.exe HANGUL-WOOD-$V-Windows-x64.zip
