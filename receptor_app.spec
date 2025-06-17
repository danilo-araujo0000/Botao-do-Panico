# -*- mode: python ; coding: utf-8 -*-

import os

# Definir caminhos
block_cipher = None
app_name = 'botaoPanico_Receptor'
main_script = 'src/receptor.py'
icon_path = 'data/icons/client.png'

# Dados adicionais para incluir no executável
added_files = [
    ('data/icons/client.png', 'data/icons'),
]

# Verificar se existe diretório de sons
sounds_dir = 'data/sounds'
if os.path.exists(sounds_dir):
    added_files.append((sounds_dir, 'sounds'))

# Módulos ocultos necessários
hiddenimports = [
    'flask',
    'tkinter',
    'tkinter.ttk',
    'tkinter.font',
    'threading',
    'queue',
    'subprocess',
    'datetime',
    'tempfile',
    'requests',
    'pygame',
    'pygame.mixer',
]

# Análise do script principal
a = Analysis(
    [main_script],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
        'tensorflow',
        'torch',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remover duplicatas
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Configuração do executável
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Sem console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path if os.path.exists(icon_path) else None,
    version_info={
        'version': (1, 0, 0, 0),
        'description': 'Receptor do Sistema de Botão de Pânico',
        'product_name': 'Botão de Pânico - Receptor',
        'product_version': '1.0.0',
        'company_name': 'Sistema de Segurança',
        'file_description': 'Aplicação receptora de alertas de emergência',
        'internal_name': 'BotaoPanico_Receptor',
        'copyright': '© 2025 Sistema de Segurança',
        'original_filename': f'{app_name}.exe',
    }
) 