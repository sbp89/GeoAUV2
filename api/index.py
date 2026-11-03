"""
Punto de entrada ASGI Serverless para Vercel — GeoAuV2
"""
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.main import app  # noqa: E402, F401
