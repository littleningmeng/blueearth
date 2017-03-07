from distutils.core import setup
import py2exe


setup( zipfile=None,
       console=[{"script":"blueearth.py", "icon_resources":[(1, "logo.ico")]}],
	   options={"py2exe":{"compressed":2, "bundle_files":1,
                          "includes":["threadpool", "PIL", "urllib", "json", "Tkinter"],
                          "dll_excludes": ["msvcm90.dll", "msvcp90.dll", "msvcr90.dll"] }})
