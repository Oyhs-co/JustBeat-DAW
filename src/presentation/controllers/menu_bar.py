"""Menu Bar Manager - Gestor de barra de menús.

Manejo desacoplado de la barra de menús,
separado del MainWindow.
"""

from typing import Callable, Optional
from PySide6.QtWidgets import (
    QMenuBar, QMenu, QWidget, QDialog
)
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import Signal, QObject
import logging


logger = logging.getLogger(__name__)


class MenuBarManager(QObject):
    """Gestor de barra de menús.
    
    Maneja la creación y acciones de los menús
    de forma desacoplada del MainWindow.
    """
    
    # Señales
    new_project = Signal()
    open_project = Signal()
    save_project = Signal()
    save_as = Signal()
    export_wav = Signal()
    export_midi = Signal()
    preferences = Signal()
    quit = Signal()
    
    undo = Signal()
    redo = Signal()
    cut = Signal()
    copy = Signal()
    paste = Signal()
    delete = Signal()
    select_all = Signal()
    
    play = Signal()
    stop = Signal()
    record = Signal()
    loop = Signal()
    metronome = Signal()
    rewind = Signal()
    goto_start = Signal()
    goto_end = Signal()
    
    show_sequencer = Signal()
    show_synth = Signal()
    show_piano_roll = Signal()
    show_mixer = Signal()
    show_browser = Signal()
    show_keyboard = Signal()
    show_visualizer = Signal()
    show_arrange = Signal()
    show_effect_chain = Signal()
    show_automation = Signal()
    show_midi_learn = Signal()
    
    about = Signal()
    help_docs = Signal()
    shortcuts = Signal()
    
    # Nuevas señales
    project_settings = Signal()
    audio_settings = Signal()
    add_track_instrument = Signal()
    add_track_audio = Signal()
    add_track_automation = Signal()
    remove_track = Signal()
    duplicate_track = Signal()
    change_sample_rate = Signal(int)
    change_buffer_size = Signal(int)
    
    # Edit signals
    rename_track = Signal()
    color_track = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Inicializar gestor de menús.
        
        Args:
            parent: Widget padre
        """
        super().__init__(parent)
        self._parent = parent
        self._menubar: Optional[QMenuBar] = None
        self._menus: dict = {}
        self._actions: dict = {}
        
        logger.info("MenuBarManager inicializado")
    
    def create_menu_bar(self) -> QMenuBar:
        """Crear barra de menús completa.
        
        Returns:
            QMenuBar configurada
        """
        self._menubar = QMenuBar(self._parent)
        
        # Crear menús
        self._create_file_menu()
        self._create_edit_menu()
        self._create_project_menu() # Nuevo
        self._create_track_menu()   # Nuevo
        self._create_audio_menu()   # Nuevo
        self._create_transport_menu()
        self._create_view_menu()
        self._create_help_menu()
        
        return self._menubar
    
    def _create_file_menu(self) -> None:
        """Crear menú File."""
        menu = self._menubar.addMenu("&File")
        self._menus["file"] = menu
        
        # New
        action = menu.addAction("&New Project")
        action.setShortcut(QKeySequence.StandardKey.New)
        action.triggered.connect(self.new_project.emit)
        self._actions["new"] = action
        
        # Open
        action = menu.addAction("&Open Project...")
        action.setShortcut(QKeySequence.StandardKey.Open)
        action.triggered.connect(self.open_project.emit)
        self._actions["open"] = action
        
        menu.addSeparator()
        
        # Save
        action = menu.addAction("&Save")
        action.setShortcut(QKeySequence.StandardKey.Save)
        action.triggered.connect(self.save_project.emit)
        self._actions["save"] = action
        
        # Save As
        action = menu.addAction("Save &As...")
        action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        action.triggered.connect(self.save_as.emit)
        self._actions["save_as"] = action
        
        menu.addSeparator()
        
        # Export
        export_menu = menu.addMenu("&Export")
        
        action = export_menu.addAction("Export as &WAV...")
        action.triggered.connect(self.export_wav.emit)
        self._actions["export_wav"] = action
        
        action = export_menu.addAction("Export as &MIDI...")
        action.triggered.connect(self.export_midi.emit)
        self._actions["export_midi"] = action
        
        menu.addSeparator()
        
        # Preferences
        action = menu.addAction("&Preferences...")
        action.setShortcut(QKeySequence("Ctrl+,"))
        action.triggered.connect(self.preferences.emit)
        self._actions["preferences"] = action
        
        menu.addSeparator()
        
        # Quit
        action = menu.addAction("&Quit")
        action.setShortcut(QKeySequence.StandardKey.Quit)
        action.triggered.connect(self.quit.emit)
        self._actions["quit"] = action
    
    def _create_edit_menu(self) -> None:
        """Crear menú Edit."""
        menu = self._menubar.addMenu("&Edit")
        self._menus["edit"] = menu
        
        # Undo
        action = menu.addAction("&Undo")
        action.setShortcut(QKeySequence.StandardKey.Undo)
        action.triggered.connect(self.undo.emit)
        self._actions["undo"] = action
        
        # Redo
        action = menu.addAction("&Redo")
        action.setShortcut(QKeySequence.StandardKey.Redo)
        action.triggered.connect(self.redo.emit)
        self._actions["redo"] = action
        
        menu.addSeparator()
        
        # Cut
        action = menu.addAction("Cu&t")
        action.setShortcut(QKeySequence.StandardKey.Cut)
        action.triggered.connect(self.cut.emit)
        self._actions["cut"] = action
        
        # Copy
        action = menu.addAction("&Copy")
        action.setShortcut(QKeySequence.StandardKey.Copy)
        action.triggered.connect(self.copy.emit)
        self._actions["copy"] = action
        
        # Paste
        action = menu.addAction("&Paste")
        action.setShortcut(QKeySequence.StandardKey.Paste)
        action.triggered.connect(self.paste.emit)
        self._actions["paste"] = action
        
        # Delete
        action = menu.addAction("&Delete")
        action.setShortcut(QKeySequence.StandardKey.Delete)
        action.triggered.connect(self.delete.emit)
        self._actions["delete"] = action
        
        menu.addSeparator()
        
        # Select All
        action = menu.addAction("Select &All")
        action.setShortcut(QKeySequence.StandardKey.SelectAll)
        action.triggered.connect(self.select_all.emit)
        self._actions["select_all"] = action
    
    def _create_transport_menu(self) -> None:
        """Crear menú Transport."""
        menu = self._menubar.addMenu("&Transport")
        self._menus["transport"] = menu
        
        # Play/Pause
        action = menu.addAction("&Play/Pause")
        action.setShortcut(QKeySequence("Space"))
        action.triggered.connect(self.play.emit)
        self._actions["play"] = action
        
        # Stop
        action = menu.addAction("&Stop")
        action.setShortcut(QKeySequence("Ctrl+."))
        action.triggered.connect(self.stop.emit)
        self._actions["stop"] = action
        
        # Record
        action = menu.addAction("&Record")
        action.setShortcut(QKeySequence("Ctrl+R"))
        action.triggered.connect(self.record.emit)
        self._actions["record"] = action
        
        menu.addSeparator()
        
        # Go to Start
        action = menu.addAction("Go to &Start")
        action.setShortcut(QKeySequence("Home"))
        action.triggered.connect(self.goto_start.emit)
        self._actions["goto_start"] = action
        
        # Go to End
        action = menu.addAction("Go to &End")
        action.setShortcut(QKeySequence("End"))
        action.triggered.connect(self.goto_end.emit)
        self._actions["goto_end"] = action
        
        # Rewind
        action = menu.addAction("&Rewind")
        action.setShortcut(QKeySequence("Ctrl+Home"))
        action.triggered.connect(self.rewind.emit)
        self._actions["rewind"] = action
        
        menu.addSeparator()
        
        # Loop
        action = menu.addAction("&Loop")
        action.setShortcut(QKeySequence("L"))
        action.setCheckable(True)
        action.triggered.connect(self.loop.emit)
        self._actions["loop"] = action
        
        # Metronome
        action = menu.addAction("&Metronome")
        action.setShortcut(QKeySequence("M"))
        action.setCheckable(True)
        action.triggered.connect(self.metronome.emit)
        self._actions["metronome"] = action
    
    def _create_view_menu(self) -> None:
        """Crear menú View."""
        menu = self._menubar.addMenu("&View")
        self._menus["view"] = menu
        
        # Panels submenu
        panels_menu = menu.addMenu("&Panels")
        
        action = panels_menu.addAction("&Arrange View")
        action.setShortcut(QKeySequence("F2"))
        action.setCheckable(True)
        action.triggered.connect(self.show_arrange.emit)
        self._actions["show_arrange"] = action
        
        action = panels_menu.addAction("&Sequencer")
        action.setShortcut(QKeySequence("F3"))
        action.setCheckable(True)
        action.triggered.connect(self.show_sequencer.emit)
        self._actions["show_sequencer"] = action
        
        action = panels_menu.addAction("&Piano Roll")
        action.setShortcut(QKeySequence("F4"))
        action.setCheckable(True)
        action.triggered.connect(self.show_piano_roll.emit)
        self._actions["show_piano_roll"] = action
        
        action = panels_menu.addAction("&Mixer")
        action.setShortcut(QKeySequence("F5"))
        action.setCheckable(True)
        action.triggered.connect(self.show_mixer.emit)
        self._actions["show_mixer"] = action
        
        action = panels_menu.addAction("&Browser")
        action.setShortcut(QKeySequence("F6"))
        action.setCheckable(True)
        action.triggered.connect(self.show_browser.emit)
        self._actions["show_browser"] = action
        
        action = panels_menu.addAction("&Synthesizer")
        action.setShortcut(QKeySequence("F7"))
        action.setCheckable(True)
        action.triggered.connect(self.show_synth.emit)
        self._actions["show_synth"] = action
        
        action = panels_menu.addAction("&Virtual Keyboard")
        action.setShortcut(QKeySequence("F8"))
        action.setCheckable(True)
        action.triggered.connect(self.show_keyboard.emit)
        self._actions["show_keyboard"] = action
        
        action = panels_menu.addAction("&Visualizer")
        action.setShortcut(QKeySequence("F9"))
        action.setCheckable(True)
        action.triggered.connect(self.show_visualizer.emit)
        self._actions["show_visualizer"] = action
        
        menu.addSeparator()
        
        action = panels_menu.addAction("&Effect Chain")
        action.setCheckable(True)
        action.triggered.connect(self.show_effect_chain.emit)
        self._actions["show_effect_chain"] = action
        
        action = panels_menu.addAction("&Automation")
        action.setCheckable(True)
        action.triggered.connect(self.show_automation.emit)
        self._actions["show_automation"] = action
        
        action = panels_menu.addAction("&MIDI Learn")
        action.setCheckable(True)
        action.triggered.connect(self.show_midi_learn.emit)
        self._actions["show_midi_learn"] = action
        
        menu.addSeparator()
        
        # Zoom submenu
        zoom_menu = menu.addMenu("&Zoom")
        
        action = zoom_menu.addAction("&Zoom In")
        action.setShortcut(QKeySequence("Ctrl+="))
        # zoom_in.emit
        self._actions["zoom_in"] = action
        
        action = zoom_menu.addAction("Zoom &Out")
        action.setShortcut(QKeySequence("Ctrl+-"))
        # zoom_out.emit
        self._actions["zoom_out"] = action
        
        action = zoom_menu.addAction("&Fit to Window")
        action.setShortcut(QKeySequence("Ctrl+0"))
        # fit_to_window.emit
        self._actions["fit_to_window"] = action

    def _create_project_menu(self) -> None:
        """Crear menú Project."""
        menu = self._menubar.addMenu("&Project")
        self._menus["project"] = menu
        
        # Recent Files
        recent = menu.addMenu("Recent Files")
        recent.addAction("No recent projects").setEnabled(False)
        
        menu.addSeparator()
        
        action = menu.addAction("Project &Settings...")
        action.triggered.connect(self.project_settings.emit)
        self._actions["project_settings"] = action

    def _create_track_menu(self) -> None:
        """Crear menú Track."""
        menu = self._menubar.addMenu("&Track")
        self._menus["track"] = menu
        
        # Add Track submenu
        add_menu = menu.addMenu("Add &Track")
        
        action = add_menu.addAction("Add &Instrument Track")
        action.setShortcut(QKeySequence("Ctrl+T"))
        action.triggered.connect(self.add_track_instrument.emit)
        self._actions["add_track_instrument"] = action
        
        action = add_menu.addAction("Add &Audio Track")
        action.triggered.connect(self.add_track_audio.emit)
        self._actions["add_track_audio"] = action
        
        action = add_menu.addAction("Add Auto&mation Track")
        action.triggered.connect(self.add_track_automation.emit)
        self._actions["add_track_automation"] = action
        
        menu.addSeparator()
        
        # Remove Track
        action = menu.addAction("&Remove Track")
        action.setShortcut(QKeySequence("Ctrl+Shift+T"))
        action.triggered.connect(self.remove_track.emit)
        self._actions["remove_track"] = action
        
        # Duplicate Track
        action = menu.addAction("Du&plicate Track")
        action.setShortcut(QKeySequence("Ctrl+D"))
        action.triggered.connect(self.duplicate_track.emit)
        self._actions["duplicate_track"] = action
        
        menu.addSeparator()
        
        # Rename Track
        action = menu.addAction("&Rename Track")
        action.setShortcut(QKeySequence("F2"))
        action.triggered.connect(self.rename_track.emit)
        self._actions["rename_track"] = action
        
        # Color Track
        action = menu.addAction("&Color Track")
        action.triggered.connect(self.color_track.emit)
        self._actions["color_track"] = action

    def _create_audio_menu(self) -> None:
        """Crear menú Audio."""
        menu = self._menubar.addMenu("&Audio")
        self._menus["audio"] = menu
        
        # Sample Rate
        sr_menu = menu.addMenu("&Sample Rate")
        for sr in [44100, 48000, 88200, 96000]:
            action = sr_menu.addAction(f"{sr} Hz")
            action.triggered.connect(lambda checked, val=sr: self.change_sample_rate.emit(val))
            
        # Buffer Size
        buf_menu = menu.addMenu("&Buffer Size")
        for buf in [128, 256, 512, 1024]:
            action = buf_menu.addAction(f"{buf} samples")
            action.triggered.connect(lambda checked, val=buf: self.change_buffer_size.emit(val))
            
        menu.addSeparator()
        
        action = menu.addAction("&Audio Settings...")
        action.triggered.connect(self.audio_settings.emit)
        self._actions["audio_settings"] = action
    
    def _create_help_menu(self) -> None:
        """Crear menú Help."""
        menu = self._menubar.addMenu("&Help")
        self._menus["help"] = menu
        
        # Documentation
        action = menu.addAction("&Documentation")
        action.setShortcut(QKeySequence("F1"))
        action.triggered.connect(self.help_docs.emit)
        self._actions["help_docs"] = action
        
        # Keyboard Shortcuts
        action = menu.addAction("&Keyboard Shortcuts...")
        action.setShortcut(QKeySequence("Ctrl+Shift+K"))
        action.triggered.connect(self.shortcuts.emit)
        self._actions["shortcuts"] = action
        
        menu.addSeparator()
        
        # About
        action = menu.addAction("&About JustBeat-DAW")
        action.triggered.connect(self.about.emit)
        self._actions["about"] = action
    
    def get_menu(self, name: str) -> Optional[QMenu]:
        """Obtener menú por nombre.
        
        Args:
            name: Nombre del menú
            
        Returns:
            Menú o None
        """
        return self._menus.get(name)
    
    def get_action(self, name: str) -> Optional[QAction]:
        """Obtener acción por nombre.
        
        Args:
            name: Nombre de la acción
            
        Returns:
            Acción o None
        """
        return self._actions.get(name)
    
    def set_action_enabled(self, name: str, enabled: bool) -> None:
        """Habilitar/deshabilitar acción.
        
        Args:
            name: Nombre de la acción
            enabled: Estado
        """
        action = self._actions.get(name)
        if action:
            action.setEnabled(enabled)
    
    def update_undo_state(self, can_undo: bool, can_redo: bool) -> None:
        """Actualizar estado de undo/redo.
        
        Args:
            can_undo: Si puede deshacer
            can_redo: Si puede rehacer
        """
        self.set_action_enabled("undo", can_undo)
        self.set_action_enabled("redo", can_redo)
    
    def update_save_state(self, is_modified: bool) -> None:
        """Actualizar estado de guardado.
        
        Args:
            is_modified: Si hay cambios sin guardar
        """
        self.set_action_enabled("save", is_modified)

    def update_view_state(self, name: str, visible: bool) -> None:
        """Actualizar el estado de marcado de una acción de vista.
        
        Args:
            name: Nombre del panel (e.g. 'sequencer')
            visible: Si el panel está visible
        """
        # Intentar con y sin prefijo 'show_'
        action = self._actions.get(f"show_{name}") or self._actions.get(name)
        if action:
            action.setChecked(visible)
