"""Startup compatibility for geometry-only native children, never the API host.

The installed maintained drivers produce boxes and placed copies, with no CAD
text. Avoid build123d's eager Windows system-font scan in every transient mesh
helper. Bundled fonts, explicit font reads and every other glob are preserved.
"""
import glob
import os
from pathlib import Path
import platform
import sys


def configure():
    if os.name!='nt':return
    platform._wmi=None
    if getattr(glob.glob,'_woodwork_geometry_fonts',False):return
    original=glob.glob
    folders={os.path.normcase(os.path.normpath('C:/Windows/Fonts')),
             os.path.normcase(os.path.normpath(str(Path(os.environ.get('USERPROFILE','C:/Users/unused'))/'AppData/Local/Microsoft/Windows/Fonts')))}
    def geometry_glob(pathname,*args,**kwargs):
        path=os.fspath(pathname)
        if isinstance(path,str) and os.path.basename(path).lower() in {'*ttf','*otf','*ttc'} and os.path.normcase(os.path.normpath(os.path.dirname(path))) in folders:
            frame=sys._getframe(1)
            # cadgen may wrap glob with its malformed-font guard. Restrict the
            # optimization to build123d's known import-time registration call.
            for _ in range(3):
                if frame is None:break
                if frame.f_globals.get('__name__')=='build123d.text' and frame.f_code.co_name=='register_folder':return []
                frame=frame.f_back
        return original(pathname,*args,**kwargs)
    geometry_glob._woodwork_geometry_fonts=True
    glob.glob=geometry_glob


configure()
