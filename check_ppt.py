import importlib.util
import sys

packages = ['pptx', 'Pillow']
for p in packages:
    print(f"{p}: {'installed' if importlib.util.find_spec(p) else 'NOT installed'}")
