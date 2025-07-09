# patch_distutils.py
import sys
import types
from packaging.version import Version

distutils = types.ModuleType("distutils")
distutils.version = types.ModuleType("distutils.version")
distutils.version.LooseVersion = Version

sys.modules["distutils"] = distutils
sys.modules["distutils.version"] = distutils.version
