"""PanelController - Controller for dock panel management.

This controller manages:
- Panel visibility toggles
- Panel docking/undocking
- Panel state persistence
- Panel layout management
"""

import logging
from typing import Dict, Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QDockWidget


logger = logging.getLogger(__name__)


class PanelController(QObject):
    """
    Controller for managing dock panels.
    
    Signals:
        panel_visibility_changed: Emitido cuando cambia visibilidad (panel_id, visible)
        panel_layout_changed: Emitido cuando cambia layout
    """
    
    # Signals
    panel_visibility_changed = Signal(str, bool)
    panel_layout_changed = Signal()
    
    def __init__(self) -> None:
        """Initialize the panel controller."""
        super().__init__()
        self._panels: Dict[str, QDockWidget] = {}
        self._panel_order: list[str] = []
        
        logger.info("PanelController initialized")
    
    def register_panel(self, panel_id: str, dock_widget: QDockWidget) -> None:
        """Register a panel with the controller.
        
        Args:
            panel_id: Unique identifier for the panel
            dock_widget: The QDockWidget instance
        """
        self._panels[panel_id] = dock_widget
        self._panel_order.append(panel_id)
        logger.debug(f"Panel registered: {panel_id}")
    
    def show_panel(self, panel_id: str) -> bool:
        """Show a panel.
        
        Args:
            panel_id: Panel identifier
            
        Returns:
            True if successful
        """
        if panel_id not in self._panels:
            logger.warning(f"Panel not found: {panel_id}")
            return False
        
        panel = self._panels[panel_id]
        panel.show()
        self.panel_visibility_changed.emit(panel_id, True)
        logger.info(f"Panel shown: {panel_id}")
        return True
    
    def hide_panel(self, panel_id: str) -> bool:
        """Hide a panel.
        
        Args:
            panel_id: Panel identifier
            
        Returns:
            True if successful
        """
        if panel_id not in self._panels:
            logger.warning(f"Panel not found: {panel_id}")
            return False
        
        panel = self._panels[panel_id]
        panel.hide()
        self.panel_visibility_changed.emit(panel_id, False)
        logger.info(f"Panel hidden: {panel_id}")
        return True
    
    def toggle_panel(self, panel_id: str) -> bool:
        """Toggle panel visibility.
        
        Args:
            panel_id: Panel identifier
            
        Returns:
            New visibility state
        """
        if panel_id not in self._panels:
            logger.warning(f"Panel not found: {panel_id}")
            return False
        
        panel = self._panels[panel_id]
        is_visible = panel.isVisible()
        
        if is_visible:
            self.hide_panel(panel_id)
        else:
            self.show_panel(panel_id)
        
        return not is_visible
    
    def is_panel_visible(self, panel_id: str) -> bool:
        """Check if a panel is visible.
        
        Args:
            panel_id: Panel identifier
            
        Returns:
            True if visible
        """
        if panel_id not in self._panels:
            return False
        return self._panels[panel_id].isVisible()
    
    def show_all_panels(self) -> None:
        """Show all registered panels."""
        for panel_id in self._panels:
            self.show_panel(panel_id)
    
    def hide_all_panels(self) -> None:
        """Hide all panels."""
        for panel_id in self._panels:
            self.hide_panel(panel_id)
    
    def get_panel(self, panel_id: str) -> Optional[QDockWidget]:
        """Get a panel by ID.
        
        Args:
            panel_id: Panel identifier
            
        Returns:
            The QDockWidget or None
        """
        return self._panels.get(panel_id)
    
    @property
    def registered_panels(self) -> list[str]:
        """Get list of registered panel IDs."""
        return self._panel_order.copy()
