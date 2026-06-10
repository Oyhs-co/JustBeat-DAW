"""Browser Widget - Explorador de archivos y recursos.

File system tree, vistas (Samples, Projects, Presets, Exports),
preview de audio, drag & drop, búsqueda, favoritos, mini player.
"""

import logging
import os
from typing import Optional, List, Dict
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTreeView, QLineEdit, QPushButton, QFrame,
    QSplitter, QListWidget, QListWidgetItem, QFileSystemModel,
    QSlider
)
from PySide6.QtGui import QAction, QDrag, QColor
from PySide6.QtCore import Qt, Signal, QDir, QModelIndex, QMimeData, QTimer

from src.presentation.styles.pro_theme import ProTheme
from src.presentation.styles.icons import Icons

logger = logging.getLogger(__name__)

_AUDIO_EXT = {".wav", ".mp3", ".ogg", ".flac", ".aiff", ".aif"}
_PRESET_EXT = {".jbpreset", ".fxp", ".fxb"}
_PROJECT_EXT = {".jbproj"}
_MIDI_EXT = {".mid", ".midi"}

_CATEGORIES = [
    ("Samples", Icons.FILE_AUDIO, QDir.homePath() + "/Music"),
    ("Projects", Icons.FILE_PROJECT, QDir.homePath() + "/Documents/JustBeat"),
    ("Presets", Icons.SYNTH, str(Path.cwd() / "presets")),
    ("Exports", Icons.WAVEFORM, QDir.homePath() + "/Music/JustBeat Exports"),
    ("Favorites", Icons.STAR, ""),
]


class BrowserWidget(QWidget):
    """Explorador de archivos profesional."""

    file_selected = Signal(str)
    file_dragged = Signal(str)

    def __init__(self, presentation_model=None, parent=None):
        super().__init__(parent)
        self._model = presentation_model
        self._favorites: List[str] = []
        self._current_path = QDir.homePath()

        if self._model is None:
            try:
                from src.presentation.models import get_presentation_model
                self._model = get_presentation_model()
            except ImportError:
                pass

        # Filter timer (debounce search)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(200)
        self._search_timer.timeout.connect(self._apply_filter)

        self._setup_fs_model()
        self._setup_ui()

    def _setup_fs_model(self):
        self._fs_model = QFileSystemModel()
        self._fs_model.setRootPath(QDir.rootPath())
        self._fs_model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot | QDir.Drives)
        self._fs_model.setNameFilterDisables(False)

    def _setup_ui(self):
        c = ProTheme.get()
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QFrame()
        header.setFixedHeight(32)
        header.setStyleSheet(f"background-color: {c.bg_secondary}; border-bottom: 1px solid {c.border_color};")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(8, 0, 8, 0)

        icon = QLabel()
        icon.setPixmap(Icons.FOLDER.pixmap(14, 14))
        icon.setStyleSheet("background: transparent;")
        h_lay.addWidget(icon)

        title = QLabel("Browser")
        title.setStyleSheet(f"color: {c.text_primary}; font-weight: bold; font-size: 10px; background: transparent;")
        h_lay.addWidget(title)

        h_lay.addStretch()

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search files...")
        self._search_input.setFixedWidth(160)
        self._search_input.setStyleSheet(f"""
            QLineEdit {{
                background: {c.bg_tertiary}; color: {c.text_primary};
                border: 1px solid {c.border_color}; border-radius: 3px;
                padding: 2px 6px; font-size: 9px;
            }}
            QLineEdit:focus {{ border-color: {c.border_focus}; }}
        """)
        self._search_input.textChanged.connect(self._search_timer.start)
        h_lay.addWidget(self._search_input)

        layout.addWidget(header)

        # Splitter: sidebar + tree
        splitter = QSplitter(Qt.Horizontal)

        # Sidebar
        self._sidebar = QListWidget()
        self._sidebar.setFixedWidth(90)
        self._sidebar.setStyleSheet(f"""
            QListWidget {{ background: {c.bg_secondary}; border: none; }}
            QListWidget::item {{ padding: 8px 6px; color: {c.text_secondary};
                              font-size: 9px; border-bottom: 1px solid {c.border_color}; }}
            QListWidget::item:selected {{ background: {c.bg_active}; color: {c.text_accent}; }}
            QListWidget::item:hover {{ background: {c.bg_hover}; }}
        """)
        for name, icon_char, _ in _CATEGORIES:
            item = QListWidgetItem(name)
            item.setIcon(icon_char)
            self._sidebar.addItem(item)
        self._sidebar.currentRowChanged.connect(self._on_category_changed)
        splitter.addWidget(self._sidebar)

        # Tree
        self._tree = QTreeView()
        self._tree.setModel(self._fs_model)
        self._tree.setRootIndex(self._fs_model.index(self._current_path))
        self._tree.setHeaderHidden(True)
        self._tree.setColumnHidden(1, True)
        self._tree.setColumnHidden(2, True)
        self._tree.setColumnHidden(3, True)
        self._tree.setAnimated(True)
        self._tree.setIndentation(14)
        self._tree.setDragEnabled(True)
        self._tree.setDragDropMode(QTreeView.DragDropMode.DragOnly)
        self._tree.doubleClicked.connect(self._on_tree_double_clicked)
        self._tree.setStyleSheet(f"""
            QTreeView {{ background: {c.bg_primary}; color: {c.text_primary};
                         border: none; outline: none; font-size: 9px; }}
            QTreeView::item {{ height: 24px; padding-left: 4px; }}
            QTreeView::item:selected {{ background: {c.bg_active}; color: {c.text_accent}; }}
            QTreeView::item:hover {{ background: {c.bg_hover}; }}
            QTreeView::branch {{ background: transparent; }}
        """)
        splitter.addWidget(self._tree)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)

        # Preview bar
        preview = QFrame()
        preview.setFixedHeight(28)
        preview.setStyleSheet(f"background-color: {c.bg_secondary}; border-top: 1px solid {c.border_color};")
        p_lay = QHBoxLayout(preview)
        p_lay.setContentsMargins(8, 0, 8, 0)
        p_lay.setSpacing(4)

        self._play_btn = QPushButton()
        self._play_btn.setIcon(Icons.PLAY)
        self._play_btn.setCheckable(True)
        self._play_btn.setFixedSize(20, 20)
        self._play_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.text_secondary};
                          border: none; font-size: 12px; }}
            QPushButton:hover {{ color: {c.text_accent}; }}
            QPushButton:checked {{ color: {c.accent_danger}; }}
        """)
        self._play_btn.clicked.connect(self._on_play_clicked)
        p_lay.addWidget(self._play_btn)

        self._preview_label = QLabel("No file selected")
        self._preview_label.setStyleSheet(f"color: {c.text_tertiary}; font-size: 8px; background: transparent;")
        p_lay.addWidget(self._preview_label, 1)

        self._fav_btn = QPushButton()
        self._fav_btn.setIcon(Icons.STAR_EMPTY)
        self._fav_btn.setFixedSize(20, 20)
        self._fav_btn.setStyleSheet("background: transparent; border: none; font-size: 12px;")
        self._fav_btn.clicked.connect(self._toggle_favorite)
        p_lay.addWidget(self._fav_btn)

        layout.addWidget(preview)

        self._current_selected_path: Optional[str] = None

    def _on_category_changed(self, index: int):
        if 0 <= index < len(_CATEGORIES):
            _, _, path = _CATEGORIES[index]
            if path and QDir(path).exists():
                self._current_path = path
                self._tree.setRootIndex(self._fs_model.index(path))
            elif index == 4:
                self._show_favorites()

    def _show_favorites(self):
        pass

    def _apply_filter(self):
        text = self._search_input.text().strip()
        if text:
            self._fs_model.setNameFilters([f"*{text}*"])
        else:
            self._fs_model.setNameFilters([])

    def _on_tree_double_clicked(self, index: QModelIndex):
        if not self._fs_model.isDir(index):
            path = self._fs_model.filePath(index)
            self._current_selected_path = path
            self._preview_label.setText(os.path.basename(path))
            ext = os.path.splitext(path)[1].lower()
            if ext in _AUDIO_EXT:
                self._play_btn.setChecked(True)
                self._on_play_clicked()
            self.file_selected.emit(path)
            logger.info(f"Browser selected: {path}")

    def _on_play_clicked(self):
        if self._play_btn.isChecked():
            if self._current_selected_path and self._model:
                try:
                    self._model.app_core.preview_audio_file(self._current_selected_path)
                except AttributeError:
                    pass
        else:
            try:
                import sounddevice as sd
                sd.stop()
            except ImportError:
                pass

    def _toggle_favorite(self):
        if not self._current_selected_path:
            return
        path = self._current_selected_path
        if path in self._favorites:
            self._favorites.remove(path)
            self._fav_btn.setIcon(Icons.STAR_EMPTY)
        else:
            self._favorites.append(path)
            self._fav_btn.setIcon(Icons.STAR)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        index = self._tree.currentIndex()
        if not index.isValid() or self._fs_model.isDir(index):
            return

        path = self._fs_model.filePath(index)
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(path)
        mime.setData("application/x-justbeat-file", path.encode("utf-8"))
        mime.setUrls([QDir.toNativeSeparators(path)])
        drag.setMimeData(mime)
        drag.exec(Qt.CopyAction)

    def set_root_path(self, path: str):
        if os.path.isdir(path):
            self._current_path = path
            self._tree.setRootIndex(self._fs_model.index(path))

    def get_current_path(self) -> str:
        return self._fs_model.filePath(self._tree.rootIndex())


FileBrowser = BrowserWidget
