import sys
import time
from PyQt5.QtWidgets import QSplashScreen
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

def show_splash(app, timeout=3000):
    """Affiche un écran de chargement"""
    # Créez une image splash.png
    splash_pixmap = QPixmap("logo.png")
    if splash_pixmap.isNull():
        # Si pas d'image, créer un écran texte
        from PyQt5.QtWidgets import QLabel
        splash = QLabel()
        splash.setText("<h2 style='color:white;background:#2d6a4f;padding:50px;'>AJEFEM<br/>Chargement...</h2>")
        splash.setStyleSheet("background:#2d6a4f; color:white;")
        splash.show()
        app.processEvents()
        return splash
    else:
        splash = QSplashScreen(splash_pixmap)
        splash.show()
        return splash