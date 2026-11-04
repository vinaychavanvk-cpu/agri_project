import os
import sys

# Ensure the root project directory is on the Python module path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Import the Flask application instance
from app import app
