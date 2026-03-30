import sys
import os
import json
import configparser
import webbrowser
from datetime import datetime
from PyQt5.QtCore import QUrl, Qt, QTimer, QSize
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, 
    QProgressBar, QMessageBox, QToolBar, QAction, 
    QLineEdit, QDialog, QPushButton, QFileDialog, QLabel,
    QStatusBar, QMenu, QSystemTrayIcon
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
from PyQt5.QtGui import QIcon, QFont, QPixmap

class AJEFEMApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Charger la configuration
        self.config = self.load_config()
        
        # Configuration de la fenêtre
        self.setWindowTitle("AJEFEM - Application Bureau")
        self.setGeometry(100, 100, 1280, 800)
        
        # Définir l'icône si disponible
        if os.path.exists("icon.ico"):
            self.setWindowIcon(QIcon("icon.ico"))
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Créer la barre d'outils
        self.create_toolbar()
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(3)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #2d6a4f;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Barre de statut
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Prêt")
        
        # WebView
        self.webview = QWebEngineView()
        
        # Configurer le profil pour le cache
        profile = self.webview.page().profile()
        profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)
        
        # Intercepter les demandes de téléchargement/ouverture
        profile.downloadRequested.connect(self.on_download_requested)
        
        # Intercepter les nouvelles fenêtres - méthode alternative
        self.webview.page().createWindow = self.handle_new_window
        
        # URL de votre site
        self.url = self.get_url()
        
        # Connecter les signaux de chargement
        self.webview.loadStarted.connect(self.on_load_started)
        self.webview.loadFinished.connect(self.on_load_finished)
        self.webview.loadProgress.connect(self.on_load_progress)
        
        layout.addWidget(self.webview)
        
        # Vérifier les mises à jour au démarrage
        if self.config and self.config.getboolean('Update', 'AutoCheck', fallback=True):
            self.check_for_updates()
        
        # Charger la page
        self.load_page()
        
        # Système de tray (optionnel)
        self.setup_tray_icon()
    
    def load_config(self):
        """Charge la configuration depuis config.ini"""
        config = configparser.ConfigParser()
        
        # Déterminer le chemin du fichier de config
        if getattr(sys, 'frozen', False):
            # L'application est empaquetée (exe)
            base_path = os.path.dirname(sys.executable)
        else:
            # Mode développement
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        config_path = os.path.join(base_path, 'config.ini')
        
        if os.path.exists(config_path):
            try:
                config.read(config_path, encoding='utf-8')
                return config
            except Exception as e:
                print(f"Erreur lecture config: {e}")
        
        # Configuration par défaut
        config['Application'] = {
            'Version': '1.0.0',
            'InstallPath': base_path
        }
        config['Update'] = {
            'AutoCheck': 'true',
            'LastCheck': '',
            'UpdateURL': 'https://ajefem.org/update/check'
        }
        config['Offline'] = {
            'Enabled': 'false',
            'CacheSize': '100',
            'CachePath': os.path.join(base_path, 'cache')
        }
        config['PDF'] = {
            'OpenInExternal': 'true',
            'PrintDialog': 'true'
        }
        
        return config
    
    def get_url(self):
        """Détermine l'URL à charger en fonction du mode"""
        # Vérifier si mode hors ligne activé
        if self.config and self.config.getboolean('Offline', 'Enabled', fallback=False):
            # Mode hors ligne - vérifier si cache existe
            cache_path = self.config.get('Offline', 'CachePath', fallback='cache')
            index_path = os.path.join(cache_path, 'index.html')
            if os.path.exists(index_path):
                return QUrl.fromLocalFile(index_path)
        
        # Mode normal - URL en ligne
        return "https://ajefem.org/login.php"
    
    def load_page(self):
        """Charge la page principale"""
        url = self.get_url()
        if isinstance(url, QUrl):
            self.webview.setUrl(url)
        else:
            self.webview.setUrl(QUrl(url))
    
    def create_toolbar(self):
        """Crée une barre d'outils complète"""
        toolbar = QToolBar("Navigation")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # Style pour la barre d'outils
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #f5f5f5;
                border-bottom: 1px solid #ddd;
                padding: 5px;
                spacing: 5px;
            }
            QToolButton {
                background-color: transparent;
                border: none;
                padding: 5px;
                border-radius: 4px;
            }
            QToolButton:hover {
                background-color: #e0e0e0;
            }
        """)
        
        # Bouton Retour
        back_btn = QAction("←", self)
        back_btn.setToolTip("Retour")
        back_btn.setStatusTip("Retour à la page précédente")
        back_btn.triggered.connect(lambda: self.webview.back())
        toolbar.addAction(back_btn)
        
        # Bouton Avancer
        forward_btn = QAction("→", self)
        forward_btn.setToolTip("Avancer")
        forward_btn.setStatusTip("Aller à la page suivante")
        forward_btn.triggered.connect(lambda: self.webview.forward())
        toolbar.addAction(forward_btn)
        
        # Bouton Rafraîchir
        refresh_btn = QAction("⟳", self)
        refresh_btn.setToolTip("Rafraîchir")
        refresh_btn.setStatusTip("Recharger la page")
        refresh_btn.triggered.connect(lambda: self.webview.reload())
        toolbar.addAction(refresh_btn)
        
        # Bouton Accueil
        home_btn = QAction("🏠", self)
        home_btn.setToolTip("Accueil")
        home_btn.setStatusTip("Retour à l'accueil")
        home_btn.triggered.connect(self.go_home)
        toolbar.addAction(home_btn)
        
        toolbar.addSeparator()
        
        # Barre d'adresse
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Entrez une URL...")
        self.url_bar.setMinimumWidth(400)
        self.url_bar.setStyleSheet("""
            QLineEdit {
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
            }
        """)
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        toolbar.addWidget(self.url_bar)
        
        toolbar.addSeparator()
        
        # Bouton PDF
        pdf_btn = QAction("📄 PDF", self)
        pdf_btn.setToolTip("Ouvrir un PDF")
        pdf_btn.setStatusTip("Ouvrir un fichier PDF")
        pdf_btn.triggered.connect(self.open_pdf_dialog)
        toolbar.addAction(pdf_btn)
        
        # Bouton Menu
        menu_btn = QAction("☰", self)
        menu_btn.setToolTip("Menu")
        menu_btn.triggered.connect(self.show_menu)
        toolbar.addAction(menu_btn)
    
    def go_home(self):
        """Retour à l'accueil"""
        self.load_page()
    
    def navigate_to_url(self):
        """Navigation depuis la barre d'adresse"""
        url = self.url_bar.text().strip()
        if not url:
            return
        
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        
        self.webview.setUrl(QUrl(url))
    
    def show_menu(self):
        """Affiche le menu contextuel"""
        menu = QMenu(self)
        
        # Actions du menu
        offline_action = QAction("Mode hors ligne", self)
        offline_action.setCheckable(True)
        if self.config:
            offline_action.setChecked(self.config.getboolean('Offline', 'Enabled', fallback=False))
        offline_action.triggered.connect(self.toggle_offline_mode)
        menu.addAction(offline_action)
        
        menu.addSeparator()
        
        check_update_action = QAction("Vérifier les mises à jour", self)
        check_update_action.triggered.connect(self.check_for_updates)
        menu.addAction(check_update_action)
        
        menu.addSeparator()
        
        about_action = QAction("À propos", self)
        about_action.triggered.connect(self.show_about)
        menu.addAction(about_action)
        
        # Positionner le menu
        menu.exec_(self.mapToGlobal(self.url_bar.pos()))
    
    def toggle_offline_mode(self):
        """Active/désactive le mode hors ligne"""
        if self.config:
            current = self.config.getboolean('Offline', 'Enabled', fallback=False)
            self.config.set('Offline', 'Enabled', str(not current).lower())
            
            # Sauvegarder la configuration
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            config_path = os.path.join(base_path, 'config.ini')
            with open(config_path, 'w', encoding='utf-8') as f:
                self.config.write(f)
            
            QMessageBox.information(
                self,
                "Mode hors ligne",
                f"Mode hors ligne {'activé' if not current else 'désactivé'}.\n"
                "Redémarrez l'application pour appliquer les changements."
            )
    
    def check_for_updates(self):
        """Vérifie les mises à jour"""
        update_url = self.config.get('Update', 'UpdateURL', fallback='https://ajefem.org/update/check')
        
        # Fonction pour mettre à jour l'interface
        def show_no_update():
            QMessageBox.information(
                self,
                "Mise à jour",
                "Vous utilisez déjà la dernière version d'AJEFEM."
            )
        
        def show_update_available(version, changelog):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Mise à jour disponible")
            msg.setText(f"Une nouvelle version ({version}) est disponible !")
            msg.setInformativeText(f"Changements :\n{changelog}\n\nVoulez-vous télécharger la mise à jour ?")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            
            if msg.exec_() == QMessageBox.Yes:
                webbrowser.open("https://ajefem.org/download")
        
        # Simuler une vérification (à remplacer par une vraie requête)
        # Dans une vraie application, vous feriez une requête HTTP ici
        self.status_bar.showMessage("Vérification des mises à jour...", 2000)
        QTimer.singleShot(2000, show_no_update)
    
    def show_about(self):
        """Affiche la fenêtre À propos"""
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("À propos d'AJEFEM")
        about_dialog.setFixedSize(400, 300)
        
        layout = QVBoxLayout(about_dialog)
        
        # Logo
        if os.path.exists("icon.ico"):
            logo_label = QLabel()
            logo_pixmap = QPixmap("icon.ico").scaled(64, 64, Qt.KeepAspectRatio)
            logo_label.setPixmap(logo_pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(logo_label)
        
        # Texte
        title_label = QLabel("<h2>AJEFEM Desktop</h2>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        version = self.config.get('Application', 'Version', fallback='1.0.0') if self.config else '1.0.0'
        version_label = QLabel(f"Version {version}")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        desc_label = QLabel(
            "Application officielle de l'AJEFEM\n"
            "Action de Jeunes et Femmes pour l'Entraide Mutuelle\n\n"
            "© 2026 AJEFEM - Tous droits réservés"
        )
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Bouton fermer
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(about_dialog.accept)
        layout.addWidget(close_btn)
        
        about_dialog.exec_()
    
    def on_download_requested(self, download_item):
        """Gère les téléchargements"""
        url = download_item.url().toString().lower()
        
        # Vérifier si c'est un PDF
        if url.endswith('.pdf') or '.pdf?' in url:
            # Ouvrir dans le navigateur externe
            webbrowser.open(download_item.url().toString())
            download_item.cancel()
            self.status_bar.showMessage("PDF ouvert dans le navigateur", 2000)
        else:
            # Proposer l'enregistrement
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Enregistrer sous",
                os.path.basename(download_item.url().fileName())
            )
            if save_path:
                download_item.setPath(save_path)
                download_item.accept()
                self.status_bar.showMessage(f"Téléchargement : {os.path.basename(save_path)}", 3000)
            else:
                download_item.cancel()
    
    def handle_new_window(self, url):
        """Gère l'ouverture des nouvelles fenêtres"""
        url_str = url.toString().lower()
        
        # Si c'est un PDF, l'ouvrir dans une nouvelle fenêtre
        if url_str.endswith('.pdf') or '.pdf?' in url_str:
            self.open_pdf_in_window(url.toString())
            return self.webview
        
        # Sinon, charger dans la fenêtre principale
        self.webview.setUrl(url)
        return self.webview
    
    def open_pdf_dialog(self):
        """Ouvre une boîte de dialogue pour sélectionner un PDF"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Ouvrir un document PDF",
            "",
            "PDF Files (*.pdf)"
        )
        if file_path:
            self.open_pdf_in_window(QUrl.fromLocalFile(file_path).toString())
    
    def open_pdf_in_window(self, pdf_url):
        """Ouvre un PDF dans une nouvelle fenêtre"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Document PDF")
        dialog.resize(900, 700)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowMinMaxButtonsHint)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # WebView pour le PDF
        pdf_view = QWebEngineView()
        pdf_view.setUrl(QUrl(pdf_url))
        layout.addWidget(pdf_view)
        
        # Barre d'outils pour la fenêtre PDF
        pdf_toolbar = QToolBar()
        pdf_toolbar.setIconSize(QSize(20, 20))
        
        # Bouton imprimer
        print_btn = QAction("🖨️ Imprimer", self)
        print_btn.setToolTip("Imprimer ce document")
        print_btn.triggered.connect(lambda: self.print_pdf(pdf_view))
        pdf_toolbar.addAction(print_btn)
        
        # Bouton télécharger
        download_btn = QAction("💾 Télécharger", self)
        download_btn.setToolTip("Télécharger ce document")
        download_btn.triggered.connect(lambda: webbrowser.open(pdf_url))
        pdf_toolbar.addAction(download_btn)
        
        # Bouton fermer
        close_btn = QAction("✖ Fermer", self)
        close_btn.triggered.connect(dialog.accept)
        pdf_toolbar.addAction(close_btn)
        
        layout.insertWidget(0, pdf_toolbar)
        
        dialog.exec_()
    
    def print_pdf(self, webview):
        """Imprime un PDF"""
        webview.page().printToPdf(lambda x: self.save_pdf_and_print(x))
    
    def save_pdf_and_print(self, pdf_data):
        """Sauvegarde le PDF temporairement et imprime"""
        import tempfile
        temp_path = os.path.join(tempfile.gettempdir(), "ajefem_temp.pdf")
        with open(temp_path, 'wb') as f:
            f.write(pdf_data)
        webbrowser.open(temp_path)
    
    def setup_tray_icon(self):
        """Configure l'icône dans la barre des tâches"""
        try:
            if os.path.exists("icon.ico"):
                tray_icon = QSystemTrayIcon(QIcon("icon.ico"), self)
                tray_icon.setToolTip("AJEFEM Desktop")
                
                # Menu du tray
                tray_menu = QMenu()
                show_action = QAction("Afficher", self)
                show_action.triggered.connect(self.show)
                quit_action = QAction("Quitter", self)
                quit_action.triggered.connect(QApplication.quit)
                
                tray_menu.addAction(show_action)
                tray_menu.addSeparator()
                tray_menu.addAction(quit_action)
                
                tray_icon.setContextMenu(tray_menu)
                tray_icon.show()
        except Exception as e:
            print(f"Erreur tray icon: {e}")
    
    def on_load_started(self):
        """Début du chargement"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("Chargement...", 1000)
    
    def on_load_progress(self, progress):
        """Mise à jour de la progression"""
        self.progress_bar.setValue(progress)
    
    def on_load_finished(self, ok):
        """Fin du chargement"""
        self.progress_bar.setVisible(False)
        
        # Mettre à jour la barre d'adresse
        current_url = self.webview.url().toString()
        self.url_bar.setText(current_url)
        
        if not ok:
            self.show_error_page()
            self.status_bar.showMessage("Erreur de connexion", 3000)
        else:
            title = self.webview.page().title()
            if title:
                self.setWindowTitle(f"AJEFEM - {title}")
            self.status_bar.showMessage("Page chargée", 2000)
    
    def show_error_page(self):
        """Affiche une page d'erreur personnalisée avec options de secours"""
        html_error = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: 'Segoe UI', Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }
                .error-container {
                    max-width: 500px;
                    margin: 20px;
                    background: white;
                    padding: 40px;
                    border-radius: 20px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    text-align: center;
                }
                h1 { 
                    color: #d32f2f; 
                    font-size: 48px;
                    margin-bottom: 20px;
                }
                .icon { font-size: 80px; margin-bottom: 20px; }
                p { 
                    margin: 15px 0; 
                    line-height: 1.6; 
                    color: #666;
                }
                .btn {
                    display: inline-block;
                    background: #2d6a4f;
                    color: white;
                    border: none;
                    padding: 12px 30px;
                    font-size: 16px;
                    border-radius: 8px;
                    cursor: pointer;
                    margin: 10px 5px;
                    text-decoration: none;
                    transition: all 0.3s;
                }
                .btn:hover {
                    background: #1b4d3e;
                    transform: translateY(-2px);
                }
                .btn-secondary {
                    background: #6c757d;
                }
                .btn-secondary:hover {
                    background: #5a6268;
                }
                .offline-note {
                    margin-top: 20px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    font-size: 12px;
                    color: #999;
                }
            </style>
        </head>
        <body>
            <div class="error-container">
                <div class="icon">🔌</div>
                <h1>Erreur de connexion</h1>
                <p>Impossible de se connecter au serveur AJEFEM.</p>
                <p>Veuillez vérifier votre connexion Internet et réessayer.</p>
                <button class="btn" onclick="window.location.reload()">
                    🔄 Réessayer
                </button>
                <div class="offline-note">
                    💡 Astuce : Vous pouvez activer le mode hors ligne<br>
                    dans le menu ☰ en haut à droite
                </div>
            </div>
        </body>
        </html>
        """
        self.webview.setHtml(html_error)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Style global de l'application
    app.setStyle("Fusion")
    
    window = AJEFEMApp()
    window.show()
    
    sys.exit(app.exec_())