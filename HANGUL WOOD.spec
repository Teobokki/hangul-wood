# -*- mode: python ; coding: utf-8 -*-
# HANGUL WOOD - one onedir build; the installer and the portable zip are both made from dist\HANGUL WOOD
from PyInstaller.utils.hooks import collect_dynamic_libs
DROP = ['QtNetwork', 'QtQml', 'QtQuick', 'QtPdf', 'QtWebEngine', 'QtWebEngineCore', 'QtWebEngineWidgets', 'QtWebChannel', 'QtOpenGL',
        'QtOpenGLWidgets', 'QtSvg', 'QtSql', 'QtTest', 'QtMultimedia', 'QtCharts', 'QtDataVisualization', 'Qt3DCore', 'QtBluetooth',
        'QtPositioning', 'QtSensors', 'QtSerialPort', 'QtDBus', 'QtDesigner', 'QtHelp', 'QtUiTools', 'QtXml', 'QtConcurrent',
        'QtQuickWidgets', 'QtVirtualKeyboard', 'QtSpatialAudio', 'QtStateMachine', 'QtTextToSpeech', 'QtLocation', 'QtNfc', 'QtRemoteObjects',
        'QtScxml', 'QtWebSockets', 'QtHttpServer', 'QtGraphs', 'QtQuick3D', 'QtShaderTools']
MODEL = [('model/en_ko/model.bin', 'model/en_ko'), ('model/en_ko/shared_vocabulary.txt', 'model/en_ko'),
         ('model/en_ko/sentencepiece.model', 'model/en_ko'), ('model/en_ko/MODEL_README.md', 'model/en_ko')]
a = Analysis(['hangul_wood.py'],
             binaries=collect_dynamic_libs('ctranslate2'),
             datas=[('assets/logo.ico', 'assets'), ('assets/icon256.png', 'assets'), ('assets/wordmark512.jpg', 'assets'),
                    ('fonts/NotoSansKR-Regular.otf', 'fonts'), ('fonts/NotoSansKR-Bold.otf', 'fonts'), ('fonts/OFL.txt', 'fonts')] + MODEL,
             hiddenimports=['truststore', 'certifi', 'sentencepiece', 'hw_translate', 'hw_icons', 'hw_demo', 'ctranslate2.extensions', 'ctranslate2.logging',
                            'ctranslate2.models', 'ctranslate2.version'],
             excludes=['tkinter', 'PIL', 'cv2', 'torch', 'transformers', 'yaml', 'unittest', 'pydoc', 'numpy',
                       'ctranslate2.converters', 'ctranslate2.specs'] + ['PySide6.' + m for m in DROP],
             noarchive=False)
DROP_FILES = tuple(('qt6' + m[2:]).lower() for m in DROP)
a.binaries = [b for b in a.binaries if not any(x in b[0].lower().replace('\\', '/').split('/')[-1] for x in DROP_FILES)
              and 'opengl32sw' not in b[0].lower() and 'qtvirtualkeyboard' not in b[0].lower()]
a.datas = [d for d in a.datas if '/translations/' not in d[0].replace('\\', '/').lower()]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='HANGUL WOOD', console=False, upx=False, version='version.txt',
          icon=['assets/logo.ico'])
coll = COLLECT(exe, a.binaries, a.datas, upx=False, name='HANGUL WOOD')
