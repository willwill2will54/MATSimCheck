# -*- mode: python -*-

block_cipher = None


import gooey

gooey_root = os.path.dirname(gooey.__file__)
gooey_languages = Tree(os.path.join(gooey_root, 'languages'), prefix = 'gooey/languages')
gooey_images = Tree(os.path.join(gooey_root, 'images'), prefix = 'gooey/images')


a = Analysis(['main.py'],
             pathex=['lib', '.', '/Users/willcharlton/MAT Box/u/MATSimCheck0.0.8'],
             binaries=[],
             datas=[('docs', 'docs'), ('dbs', 'dbs'), ('Core', 'Core'), ('special', 'special'), ('non_Core', 'non_Core'), ('result.csv', 'result.csv'), ('defaults.py', 'defaults.py')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='MATSimCheck',
          debug=False,
          strip=False,
          upx=True,
          console=False)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               gooey_languages,  # Add them in to collected files
               gooey_images,
               strip=False,
               upx=True,
               name='MATSimCheck')
app = BUNDLE(coll,
             name='MATSimCheck.app',
             icon=None,
             bundle_identifier='com.KCLMS.kings.MATSimCheck')
