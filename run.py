# run.py
import flet as ft
# Imprt main fuction
from src.mobile_app import main

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
