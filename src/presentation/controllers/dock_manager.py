"""Dock Manager - Gestor de paneles acopables.

Manejo centralizado de todos los paneles dockables
de la aplicación.
"""

from typing import Dict, Optional, Callable, List
from PySide6.QtWidgets import (
    QDockWidget, QWidget, QMainWindow
)
from PySide6.QtCore import Qt, Signal, QObject, QByteArray, QSettings
import logging


logger = logging.getLogger(__name__)


class DockConfig:
    """Configuración de un dock.
    
    Attributes:
        name: Nombre del panel
        title: Título mostrado
        area: Área por defecto
        allowed_areas: Áreas permitidas
        visible: Visible por defecto
        floating: Si puede flotar
        minimum_size: Tamaño mínimo
    """
    
    def __init__(
        self,
        name: str,
        title: str,
        area: Qt.DockWidgetArea = Qt.DockWidgetArea.LeftDockWidgetArea,
        allowed_areas: Optional[List[Qt.DockWidgetArea]] = None,
        visible: bool = True,
        floating: bool = False,
        minimum_size: tuple = (200, 150)
    ):
        self.name = name
        self.title = title
        self.area = area
        self.allowed_areas = allowed_areas or [
            Qt.DockWidgetArea.LeftDockWidgetArea,
            Qt.DockWidgetArea.RightDockWidgetArea,
            Qt.DockWidgetArea.TopDockWidgetArea,
            Qt.DockWidgetArea.BottomDockWidgetArea
        ]
        self.visible = visible
        self.floating = floating
        self.minimum_size = minimum_size




class DockManager(QObject):
    """Gestor de paneles dock.
    
    Maneja la creación, visibilidad y orden de los
    paneles dockables de la aplicación.
    """
    
    # Señales
    dock_visibility_changed = Signal(str, bool)  # name, visible
    
    def __init__(self, parent: Optional[QMainWindow] = None):
        """Inicializar gestor de docks.
        
        Args:
            parent: Ventana principal
        """
        super().__init__(parent)
        self._parent = parent
        self._docks: Dict[str, QDockWidget] = {}
        self._configs: Dict[str, DockConfig] = {}
        self._widgets: Dict[str, QWidget] = {}
        
        logger.info("DockManager inicializado")
    
    def register_dock(
        self,
        name: str,
        widget: QWidget,
        config: Optional[DockConfig] = None
    ) -> QDockWidget:
        """Registrar un dock.
        
        Args:
            name: Nombre único del dock
            widget: Widget contenido
            config: Configuración
            
        Returns:
            QDockWidget creado
        """
        # Usar configuración por defecto
        if config is None:
            config = DockConfig(name=name, title=name)
        
        # Crear dock con título minimalista
        dock = QDockWidget(config.title, self._parent)
        dock.setObjectName(f"{name}Dock")
        dock.setWidget(widget)
        dock.setFloating(config.floating)
        
        # Título minimalista (solo mostrar cuando no está dockeado)
        if config.floating:
            dock.setTitleBarWidget(None)
        
        if config.minimum_size:
            dock.setMinimumSize(config.minimum_size[0], config.minimum_size[1])
        
        # Configurar áreas (Combinar con OR bitwise)
        areas = Qt.DockWidgetArea(0)
        for area in config.allowed_areas:
            areas |= area
        dock.setAllowedAreas(areas)
        
        # Conectar señal
        dock.visibilityChanged.connect(
            lambda v: self._on_visibility_changed(name, v)
        )
        
        # Guardar referencias
        self._docks[name] = dock
        self._configs[name] = config
        self._widgets[name] = widget
        
        logger.debug(f"Dock registrado: {name}")
        return dock
    
    def add_dock(
        self,
        name: str,
        area: Qt.DockWidgetArea,
        relative_to: Optional[str] = None
    ) -> None:
        """Añadir dock a la ventana principal.
        
        Args:
            name: Nombre del dock
            area: Área donde posicionar
            relative_to: Dock relativo (para split)
        """
        dock = self._docks.get(name)
        if not dock:
            logger.warning(f"Dock no encontrado: {name}")
            return
        
        config = self._configs.get(name)
        
        if relative_to:
            relative_dock = self._docks.get(relative_to)
            if relative_dock:
                self._parent.addDockWidget(area, dock)
                self._parent.splitDockWidget(relative_dock, dock, Qt.Orientation.Horizontal)
        else:
            self._parent.addDockWidget(area, dock)
        
        # Mostrar/ocultar según config
        dock.setVisible(config.visible if config else True)
    
    def tabify_docks(self, names: list) -> None:
        """Agrupar docks en tabs.
        
        Args:
            names: Lista de nombres de docks a tabificar
        """
        if not self._parent or len(names) < 2:
            return
        first = self._docks.get(names[0])
        if not first:
            return
        for name in names[1:]:
            dock = self._docks.get(name)
            if dock:
                self._parent.tabifyDockWidget(first, dock)

    def _on_visibility_changed(self, name: str, visible: bool) -> None:
        """Callback de cambio de visibilidad."""
        self.dock_visibility_changed.emit(name, visible)
    
    def show_dock(self, name: str) -> None:
        """Mostrar dock.
        
        Args:
            name: Nombre del dock
        """
        dock = self._docks.get(name)
        if dock:
            dock.show()
            dock.setVisible(True)
    
    def hide_dock(self, name: str) -> None:
        """Ocultar dock.
        
        Args:
            name: Nombre del dock
        """
        dock = self._docks.get(name)
        if dock:
            dock.hide()
            dock.setVisible(False)
    
    def toggle_dock(self, name: str) -> bool:
        """Alternar visibilidad.
        
        Args:
            name: Nombre del dock
            
        Returns:
            Nueva visibilidad
        """
        dock = self._docks.get(name)
        if dock:
            new_state = not dock.isVisible()
            dock.setVisible(new_state)
            return new_state
        return False
    
    def get_dock(self, name: str) -> Optional[QDockWidget]:
        """Obtener dock por nombre.
        
        Args:
            name: Nombre del dock
            
        Returns:
            Dock o None
        """
        return self._docks.get(name)
    
    def get_widget(self, name: str) -> Optional[QWidget]:
        """Obtener widget de un dock.
        
        Args:
            name: Nombre del dock
            
        Returns:
            Widget o None
        """
        return self._widgets.get(name)
    
    def is_visible(self, name: str) -> bool:
        """Verificar si un dock es visible.
        
        Args:
            name: Nombre del dock
            
        Returns:
            Visibilidad
        """
        dock = self._docks.get(name)
        return dock.isVisible() if dock else False
    
    def get_visible_docks(self) -> List[str]:
        """Obtener lista de docks visibles.
        
        Returns:
            Nombres de docks visibles
        """
        return [name for name, dock in self._docks.items() if dock.isVisible()]
    
    def get_all_docks(self) -> List[str]:
        """Obtener todos los docks registrados.
        
        Returns:
            Nombres de todos los docks
        """
        return list(self._docks.keys())
    
    def save_layout(self) -> dict:
        """Guardar estado de layout.
        
        Returns:
            Diccionario con estado
        """
        return {
            name: {
                "visible": dock.isVisible(),
                "area": self._parent.dockWidgetArea(dock),
                "floating": dock.isFloating()
            }
            for name, dock in self._docks.items()
        }
    
    def restore_layout(self, state: dict) -> None:
        """Restaurar estado de layout.
        
        Args:
            state: Diccionario con estado
        """
        for name, dock_state in state.items():
            dock = self._docks.get(name)
            if dock:
                if "visible" in dock_state:
                    dock.setVisible(dock_state["visible"])
                if "floating" in dock_state:
                    dock.setFloating(dock_state["floating"])

    def get_registered_widgets(self) -> Dict[str, QWidget]:
        """Obtener todos los widgets registrados (público).

        Returns:
            Dict con {name: widget}
        """
        return dict(self._widgets)

    def get_registered_docks(self) -> Dict[str, QDockWidget]:
        """Obtener todos los docks registrados (público).

        Returns:
            Dict con {name: dock}
        """
        return dict(self._docks)

    # === Persistencia de layout ===

    LAYOUT_SETTINGS_KEY = "dock_layout"
    VISIBILITY_SETTINGS_KEY = "dock_visibility"

    def save_state(self) -> QByteArray:
        """Guardar estado de docks via QMainWindow.saveState()."""
        if self._parent:
            return self._parent.saveState()
        return QByteArray()

    def restore_state(self, state: QByteArray) -> bool:
        """Restaurar estado de docks via QMainWindow.restoreState()."""
        if self._parent:
            return self._parent.restoreState(state)
        return False

    def save_settings(self) -> None:
        """Persistir layout y visibilidad en QSettings."""
        settings = QSettings("JustBeat", "JustBeat-DAW")
        settings.setValue(self.LAYOUT_SETTINGS_KEY, self.save_state())
        visibility = {
            name: dock.isVisible()
            for name, dock in self._docks.items()
        }
        settings.setValue(self.VISIBILITY_SETTINGS_KEY, visibility)
        settings.sync()

    def restore_settings(self) -> bool:
        """Restaurar layout desde QSettings.

        Returns:
            True si se restauró un layout previo
        """
        settings = QSettings("JustBeat", "JustBeat-DAW")
        state = settings.value(self.LAYOUT_SETTINGS_KEY)
        if state is None:
            return False

        restored = self.restore_state(state)
        if restored:
            visibility = settings.value(self.VISIBILITY_SETTINGS_KEY, {})
            if isinstance(visibility, dict):
                for name, visible in visibility.items():
                    dock = self._docks.get(name)
                    if dock:
                        dock.setVisible(visible)
        return restored

    def setup_standard_layout(self, widgets: Dict[str, QWidget]) -> None:
        """Configurar layout estándar profesional estilo DAW clásica.
        
        Layout:
          - Arriba: Arrange View (área principal, 60% altura)
          - Izquierda: Browser (angosto)
          - Abajo (tabs): Sequencer + Piano Roll + Automation
          - Derecha (tabs): Mixer + Synth + Effects
        
        Args:
            widgets: Diccionario {name: widget}
        """
        if not self._parent:
            return

        # 1. Registrar todos los docks con su configuración
        logger.info("DockManager: Registering docks...")
        for name, widget in widgets.items():
            config = DEFAULT_DOCK_CONFIGS.get(name)
            logger.info(f"  Registering: {name}")
            self.register_dock(name, widget, config)
        logger.info("DockManager: All docks registered.")

        # 2. Añadir a áreas iniciales
        logger.info("DockManager: Setting up areas...")
        
        # Top: Arrange (área de trabajo principal)
        if "arrange" in self._docks:
            self.add_dock("arrange", Qt.DockWidgetArea.TopDockWidgetArea)
        
        # Left: Browser (explorador de recursos)
        if "browser" in self._docks:
            self.add_dock("browser", Qt.DockWidgetArea.LeftDockWidgetArea)
        
        # Bottom area: Mixer
        if "mixer" in self._docks:
            self.add_dock("mixer", Qt.DockWidgetArea.BottomDockWidgetArea)
        
        # Right area: empty initially, will be filled with tabs
        
        logger.info("DockManager: Initial areas set. Configuring tabs...")
        
        # 3. Tabificar grupos
        # Grupo bottom: Sequencer + Piano Roll + Automation
        bottom_tab_group = [n for n in ["sequencer", "piano_roll", "automation"] if n in self._docks]
        if bottom_tab_group:
            for name in bottom_tab_group:
                self.add_dock(name, Qt.DockWidgetArea.BottomDockWidgetArea)
            self.tabify_docks(bottom_tab_group)
        
        # Grupo right: Synth + Effects
        right_tab_group = [n for n in ["synth", "effect_chain"] if n in self._docks]
        if right_tab_group:
            for name in right_tab_group:
                self.add_dock(name, Qt.DockWidgetArea.RightDockWidgetArea)
            self.tabify_docks(right_tab_group)
        
        # Keyboard y visualizer al fondo
        for name in ["keyboard", "visualizer"]:
            if name in self._docks:
                self.add_dock(name, Qt.DockWidgetArea.BottomDockWidgetArea)
        
        # MIDI Learn oculto por defecto
        if "midi_learn" in self._docks:
            self.add_dock("midi_learn", Qt.DockWidgetArea.RightDockWidgetArea)
        
        logger.info("DockManager: Configuring initial visibility...")
        
        # 4. Visibilidad inicial
        visible_docks = ["arrange", "browser", "mixer", "piano_roll", "sequencer"]
        for name, dock in self._docks.items():
            dock.setVisible(name in visible_docks)
                
        logger.info("DockManager: standard layout setup complete.")


# Configuraciones predefinidas para JustBeat-DAW
DEFAULT_DOCK_CONFIGS = {
    "sequencer": DockConfig(
        name="sequencer",
        title="Sequencer",
        area=Qt.DockWidgetArea.TopDockWidgetArea,
        minimum_size=(800, 200)
    ),
    "synth": DockConfig(
        name="synth",
        title="Synthesizer",
        area=Qt.DockWidgetArea.LeftDockWidgetArea,
        minimum_size=(350, 180)
    ),
    "piano_roll": DockConfig(
        name="piano_roll",
        title="Piano Roll",
        area=Qt.DockWidgetArea.RightDockWidgetArea,
        minimum_size=(600, 450)
    ),
    "mixer": DockConfig(
        name="mixer",
        title="Mixer",
        area=Qt.DockWidgetArea.BottomDockWidgetArea,
        minimum_size=(400, 180)
    ),
    "browser": DockConfig(
        name="browser",
        title="Browser",
        area=Qt.DockWidgetArea.LeftDockWidgetArea,
        minimum_size=(280, 150)
    ),
    "keyboard": DockConfig(
        name="keyboard",
        title="Virtual Keyboard",
        area=Qt.DockWidgetArea.BottomDockWidgetArea,
        minimum_size=(500, 150)
    ),
    "visualizer": DockConfig(
        name="visualizer",
        title="Visualizer",
        area=Qt.DockWidgetArea.BottomDockWidgetArea,
        minimum_size=(500, 140)
    ),
    "arrange": DockConfig(
        name="arrange",
        title="Arrange",
        area=Qt.DockWidgetArea.TopDockWidgetArea,
        minimum_size=(800, 150)
    ),
    "effect_chain": DockConfig(
        name="effect_chain",
        title="Effect Chain",
        area=Qt.DockWidgetArea.RightDockWidgetArea,
        minimum_size=(300, 200)
    ),
    "automation": DockConfig(
        name="automation",
        title="Automation",
        area=Qt.DockWidgetArea.BottomDockWidgetArea,
        minimum_size=(400, 150)
    ),
    "midi_learn": DockConfig(
        name="midi_learn",
        title="MIDI Learn",
        area=Qt.DockWidgetArea.RightDockWidgetArea,
        visible=False,
        floating=True,
        minimum_size=(300, 200)
    ),
}
