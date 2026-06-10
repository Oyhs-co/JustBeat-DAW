"""Main application entry point for JustBeat-DAW."""

import sys
import logging
import traceback
import os
import time
from pathlib import Path

# Force QtAwesome to use PySide6 (must be set before any qtawesome import)
os.environ.setdefault("QT_API", "pyside6")

import numpy as np
import threading

# Setup logging - console and file
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "justbeat_daw.log"

# Configure logging with file handler
# DEBUG logs visibles solo con env JUSTBEAT_DEBUG=1
_log_level = logging.DEBUG if os.getenv("JUSTBEAT_DEBUG") else logging.INFO
logging.basicConfig(
    level=_log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
if _log_level == logging.DEBUG:
    logging.getLogger().info("DEBUG logging enabled via JUSTBEAT_DEBUG=1")
logger = logging.getLogger(__name__)

# Global exception handler
def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.critical(f"Uncaught exception: {error_msg}")
    
    # Also write to a crash log file
    crash_file = log_dir / f"crash_{int(time.time() * 1000)}.log"
    with open(crash_file, 'w', encoding='utf-8') as f:
        f.write(error_msg)
    logger.critical(f"Crash log written to: {crash_file}")

# Install global exception handler
sys.excepthook = global_exception_handler

# Global application state
_app_instance = None


def main():
    """Main application entry point."""
    _t_start = time.perf_counter()
    logger.info("Starting JustBeat-DAW...")
    
    # Import here to show error if PySide6 is not installed
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        logger.error("PySide6 is not installed. Please install it with: pip install pyside6")
        print("Error: PySide6 is not installed.")
        print("Please install it with: pip install pyside6")
        sys.exit(1)
    
    # Try to import sounddevice
    try:
        import sounddevice as sd
    except ImportError:
        logger.warning("sounddevice not available, running in headless mode")
        sd = None
    
    # Create application (antes de importar widgets que usan Icons)
    app = QApplication(sys.argv)
    
    from src.presentation.gui.main_window import MainWindow
    from src.application.app_core import initialize_app, get_app_core
    from config.settings import get_settings
    app.setApplicationName("JustBeat-DAW")
    app.setOrganizationName("JustBeat")

    # Show Splash Screen
    from src.presentation.gui.splash_screen import SplashScreen
    splash_path = os.path.join(os.path.dirname(__file__), "assets", "splash.png")
    splash = SplashScreen(splash_path if os.path.exists(splash_path) else None)
    splash.show()
    # Forzar actualización inmediata del splash
    from PySide6.QtWidgets import QApplication
    QApplication.processEvents()
    splash.update_status("Loading application styles...", 10)
    time.sleep(0.4) # Simular carga de estilos pesados
    
    # Load application styles
    try:
        from src.presentation.styles import load_application_styles
        load_application_styles(app)
        logger.info("Loaded application styles")
    except Exception as e:
        logger.warning(f"Could not load styles: {e}")
    
    splash.update_status("Loading settings...", 20)
    time.sleep(0.3)
    # Load settings
    settings = get_settings()
    logger.info(f"Loaded settings: BPM={settings.project.default_bpm}")
    
    splash.update_status("Configuring Audio Buffer...", 35)
    time.sleep(0.5)
    
    splash.update_status("Initializing App Core & Audio Layers...", 50)
    # Create global application controller using AppCore
    global _app_instance
    _t0 = time.perf_counter()
    _app_instance = initialize_app(
        sample_rate=settings.audio.sample_rate,
        buffer_size=settings.audio.buffer_size
    )
    logger.debug(f"[TIMING] initialize_app() took {time.perf_counter() - _t0:.3f}s")
    time.sleep(0.4)
    
    splash.update_status("Verifying Audio Engines...", 65)
    # Verificar capas (ya se hace en initialize_app -> app.initialize())
    _app_instance.verify_audio_layers()
    time.sleep(0.5)
    
    splash.update_status("Scanning MIDI Input Devices...", 75)
    time.sleep(0.4)
    
    splash.update_status("Building Main Interface & Docks...", 85)
    # Create main window with app core
    try:
        logger.info("Creating main window...")
        _t1 = time.perf_counter()
        main_window = MainWindow(app_core=_app_instance)
        logger.debug(f"[TIMING] MainWindow() took {time.perf_counter() - _t1:.3f}s")
        logger.info("Main window created successfully")
    except Exception as e:
        logger.exception(f"Error creating main window: {e}")
        splash.close()
        return 1
    
    splash.update_status("Finalizing UI Layout...", 95)
    time.sleep(0.3)
    # Show window
    try:
        _t2 = time.perf_counter()
        main_window.show()
        logger.debug(f"[TIMING] main_window.show() took {time.perf_counter() - _t2:.3f}s")
        logger.info("Main window shown")
    except Exception as e:
        logger.exception(f"Error showing main window: {e}")
        splash.close()
        return 1
    
    splash.update_status("Ready", 100)
    time.sleep(0.8) # Pausa final para que el usuario aprecie el estado "Ready"
    splash.close()
    
    # Iniciar stream de audio de forma diferida (después de UI lista)
    _t3 = time.perf_counter()
    _app_instance.start_audio_stream()
    logger.debug(f"[TIMING] start_audio_stream() took {time.perf_counter() - _t3:.3f}s")
    logger.debug(f"[TIMING] Total startup: {time.perf_counter() - _t_start:.3f}s")
    
    logger.info("JustBeat-DAW started successfully")
    
    # Run application
    try:
        return app.exec()
    except Exception as e:
        logger.exception(f"Error during application execution: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
