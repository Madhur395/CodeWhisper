import sys
import os

# Add the codewhisper directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'codewhisper'))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'codewhisper'))

from app import create_app
app = create_app()
