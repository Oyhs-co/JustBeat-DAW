"""Shortcuts Dialog - Editor visual de atajos de teclado.

Permite visualizar, reasignar y resetear atajos de teclado
organizados por categorías con detección de conflictos.
"""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTreeWidget, QTreeWidgetItem,
    QDialogButtonBox, QMessageBox, QWidget
)
from PySide6.QtGui import QKeySequence, QColor

from src.presentation.styles.pro_theme import ProTheme
from src.presentation.controllers.keyboard_shortcuts import ShortcutsManager


class ShortcutsDialog(QDialog):
    """Diálogo para editar atajos de teclado."""

    def __init__(self, manager: ShortcutsManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._manager = manager
        self._current_edit_item: Optional[QTreeWidgetItem] = None

        self.setWindowTitle("Keyboard Shortcuts")
        self.setMinimumSize(600, 450)
        self.setModal(True)

        self._setup_ui()
        self._populate_tree()
        self._apply_theme()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel("Click on a shortcut to reassign it. Press the desired key combination.")
        header.setStyleSheet("color: #a0a0b0; font-size: 9pt; padding: 4px 0;")
        layout.addWidget(header)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Action", "Shortcut", "Description"])
        self._tree.setAlternatingRowColors(False)
        self._tree.setRootIsDecorated(True)
        self._tree.setAnimated(True)
        self._tree.setIndentation(20)
        self._tree.setColumnWidth(0, 200)
        self._tree.setColumnWidth(1, 160)
        self._tree.header().setStretchLastSection(True)
        self._tree.setSelectionMode(QTreeWidget.SelectionMode.NoSelection)
        self._tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._tree)

        btn_layout = QHBoxLayout()
        self._reset_btn = QPushButton("Reset to Defaults")
        self._reset_btn.clicked.connect(self._on_reset_defaults)
        btn_layout.addWidget(self._reset_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)

    def _apply_theme(self):
        c = ProTheme.get()
        self._tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {c.bg_secondary};
                color: {c.text_primary};
                border: 1px solid {c.border_color};
                border-radius: 4px;
                font-size: 10pt;
            }}
            QTreeWidget::item {{
                padding: 4px 8px;
                border-bottom: 1px solid {c.border_color};
            }}
            QTreeWidget::item:hover {{
                background-color: {c.bg_hover};
            }}
            QHeaderView::section {{
                background-color: {c.dock_title_bg};
                color: {c.dock_title_text};
                padding: 6px 8px;
                border: none;
                border-bottom: 1px solid {c.border_color};
                font-weight: bold;
                font-size: 9pt;
            }}
        """)

    def _populate_tree(self):
        self._tree.clear()
        for category in self._manager.get_categories():
            cat_item = QTreeWidgetItem(self._tree, [category])
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            font = cat_item.font(0)
            font.setBold(True)
            cat_item.setFont(0, font)
            c = ProTheme.get()
            cat_item.setForeground(0, QColor(c.text_accent))

            for entry in self._manager.get_by_category(category):
                item = QTreeWidgetItem(cat_item)
                item.setText(0, entry.name)
                item.setText(1, entry.current_key)
                item.setText(2, entry.description)
                item.setData(1, Qt.ItemDataRole.UserRole, entry.name)
                cat_item.addChild(item)

            cat_item.setExpanded(True)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        if column != 1:
            return
        action_name = item.data(1, Qt.ItemDataRole.UserRole)
        if action_name is None:
            return

        self._current_edit_item = item
        item.setText(1, "Press new shortcut...")

    def keyPressEvent(self, event):
        if hasattr(self, '_current_edit_item') and self._current_edit_item is not None:
            item = self._current_edit_item
            action_name = item.data(1, Qt.ItemDataRole.UserRole)
            if action_name is not None:
                key = QKeySequence(event.keyCombination())
                if event.modifiers() != Qt.KeyboardModifier.NoModifier:
                    key = QKeySequence(event.modifiers() | event.key())
                key_str = key.toString()

                if key_str and key_str != "Press new shortcut...":
                    conflict = self._manager.find_conflict(action_name, key_str)
                    if conflict:
                        reply = QMessageBox.question(
                            self, "Shortcut Conflict",
                            f"'{key_str}' is already assigned to '{conflict}'.\n"
                            f"Do you want to reassign it anyway?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        if reply == QMessageBox.StandardButton.Yes:
                            self._manager.set_shortcut(conflict, "")
                    self._manager.set_shortcut(action_name, key_str)
                    item.setText(1, key_str)
                else:
                    entry = self._manager._entries.get(action_name)
                    item.setText(1, entry.current_key if entry else "")

                self._current_edit_item = None
                return

        super().keyPressEvent(event)

    def _on_reset_defaults(self):
        reply = QMessageBox.question(
            self, "Reset Shortcuts",
            "Reset all shortcuts to their default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._manager.reset_defaults()
            self._populate_tree()
