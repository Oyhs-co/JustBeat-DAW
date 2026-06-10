"""Plugin host - Manages plugin loading and lifecycle."""

import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Type, Protocol, Any
import logging


logger = logging.getLogger(__name__)


class PluginProtocol(Protocol):
    def initialize(self, config: Optional[dict] = None) -> bool: ...
    def shutdown(self) -> None: ...
    def get_plugin_type(self) -> str: ...


class PluginHost:
    """Host for managing plugins in JustBeat-DAW.
    
    This class handles plugin discovery, loading, initialization,
    and lifecycle management.
    """
    
    def __init__(self):
        """Initialize the plugin host."""
        self._plugins: Dict[str, PluginProtocol] = {}
        self._plugin_classes: Dict[str, Type[PluginProtocol]] = {}
        self._plugin_directories: List[Path] = []
    
    def add_plugin_directory(self, directory: Path) -> None:
        """Add a directory to search for plugins.
        
        Args:
            directory: Path to plugins directory
        """
        if directory.exists() and directory.is_dir():
            self._plugin_directories.append(directory)
            logger.info(f"Added plugin directory: {directory}")
    
    def discover_plugins(self) -> List[str]:
        """Discover available plugins in plugin directories.
        
        Returns:
            List of discovered plugin names
        """
        discovered = []
        
        for plugin_dir in self._plugin_directories:
            if not plugin_dir.exists():
                continue
            
            for python_file in plugin_dir.glob("*.py"):
                if python_file.name.startswith("_"):
                    continue
                
                try:
                    # Load module from file
                    module_name = python_file.stem
                    spec = importlib.util.spec_from_file_location(
                        module_name, python_file
                    )
                    
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        for name, obj in inspect.getmembers(module):
                            if (inspect.isclass(obj)
                                and hasattr(obj, 'initialize')
                                and hasattr(obj, 'shutdown')
                                and hasattr(obj, 'get_plugin_type')):
                                self._plugin_classes[name] = obj
                                discovered.append(name)
                                logger.info(f"Discovered plugin: {name}")
                
                except Exception as e:
                    logger.error(f"Error loading plugin from {python_file}: {e}")
        
        return discovered
    
    def load_plugin(self, plugin_name: str, 
                    config: Optional[Dict] = None) -> bool:
        """Load and initialize a plugin.
        
        Args:
            plugin_name: Name of the plugin to load
            config: Optional configuration for the plugin
            
        Returns:
            True if plugin loaded successfully
        """
        if plugin_name in self._plugins:
            logger.warning(f"Plugin {plugin_name} already loaded")
            return True
        
        if plugin_name not in self._plugin_classes:
            logger.error(f"Plugin class {plugin_name} not found")
            return False
        
        try:
            plugin_class = self._plugin_classes[plugin_name]
            plugin = plugin_class()
            
            if plugin.initialize(config):
                self._plugins[plugin_name] = plugin
                logger.info(f"Loaded plugin: {plugin_name}")
                return True
            else:
                logger.error(f"Failed to initialize plugin: {plugin_name}")
                return False
        
        except Exception as e:
            logger.error(f"Error loading plugin {plugin_name}: {e}")
            return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin.
        
        Args:
            plugin_name: Name of the plugin to unload
            
        Returns:
            True if plugin unloaded successfully
        """
        if plugin_name not in self._plugins:
            logger.warning(f"Plugin {plugin_name} not loaded")
            return False
        
        try:
            plugin = self._plugins[plugin_name]
            plugin.shutdown()
            del self._plugins[plugin_name]
            logger.info(f"Unloaded plugin: {plugin_name}")
            return True
        
        except Exception as e:
            logger.error(f"Error unloading plugin {plugin_name}: {e}")
            return False
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginProtocol]:
        return self._plugins.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, PluginProtocol]:
        return self._plugins.copy()
    
    def get_plugins_by_type(self, plugin_type: str) -> List[PluginProtocol]:
        return [
            plugin for plugin in self._plugins.values()
            if plugin.get_plugin_type() == plugin_type
        ]
    
    def is_loaded(self, plugin_name: str) -> bool:
        """Check if a plugin is loaded.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            True if plugin is loaded
        """
        return plugin_name in self._plugins
    
    def shutdown_all(self) -> None:
        """Shutdown all loaded plugins."""
        for plugin_name in list(self._plugins.keys()):
            self.unload_plugin(plugin_name)
        
        logger.info("All plugins shut down")
