"""Automation Handler - Manejo de automatización.

Este handler es responsable de todas las operaciones relacionadas
con la automatización de parámetros.
"""

from typing import Optional, Callable, Any
import logging


logger = logging.getLogger(__name__)


class AutomationHandler:
    """Handler para operaciones de automatización.
    
    Maneja la creación y gestión de curvas de automatización.
    """
    
    def __init__(self):
        """Inicializar el handler de automatización."""
        self._curves: dict = {}
        self._parameters: dict = {}
        self._targets: dict = {}
        self._automation_enabled = True
        logger.info("AutomationHandler inicializado")
    
    def enable(self) -> None:
        """Habilitar automatización."""
        self._automation_enabled = True
        logger.debug("Automatización habilitada")
    
    def disable(self) -> None:
        """Deshabilitar automatización."""
        self._automation_enabled = False
        logger.debug("Automatización deshabilitada")
    
    @property
    def is_enabled(self) -> bool:
        """Verificar si la automatización está habilitada."""
        return self._automation_enabled
    
    def create_curve(
        self,
        parameter_id: str,
        points: Optional[list] = None
    ) -> dict:
        """Crear una nueva curva de automatización.
        
        Args:
            parameter_id: ID del parámetro a automatizar
            points: Lista inicial de puntos [(tick, value), ...]
            
        Returns:
            La curva creada
        """
        curve = {
            "parameter_id": parameter_id,
            "points": points or [],
            "enabled": True,
            "mode": "write"  # write, read, loop
        }
        
        self._curves[parameter_id] = curve
        logger.debug(f"Curva de automatización creada: {parameter_id}")
        return curve
    
    def add_point(
        self,
        parameter_id: str,
        tick: int,
        value: float
    ) -> bool:
        """Añadir un punto a una curva de automatización.
        
        Args:
            parameter_id: ID del parámetro
            tick: Posición en ticks
            value: Valor del punto
            
        Returns:
            True si se añadió correctamente
        """
        if parameter_id not in self._curves:
            self.create_curve(parameter_id)
        
        curve = self._curves[parameter_id]
        curve["points"].append((tick, value))
        curve["points"].sort(key=lambda p: p[0])
        
        logger.debug(f"Punto añadido: {parameter_id} @ {tick} = {value}")
        return True
    
    def remove_point(
        self,
        parameter_id: str,
        tick: int
    ) -> bool:
        """Quitar un punto de una curva.
        
        Args:
            parameter_id: ID del parámetro
            tick: Posición del punto
            
        Returns:
            True si se quitó correctamente
        """
        if parameter_id not in self._curves:
            return False
        
        curve = self._curves[parameter_id]
        
        # Buscar y quitar el punto más cercano
        for i, (t, v) in enumerate(curve["points"]):
            if abs(t - tick) < 10:  # Tolerancia
                curve["points"].pop(i)
                logger.debug(f"Punto removido: {parameter_id} @ {tick}")
                return True
        
        return False
    
    def clear_curve(self, parameter_id: str) -> bool:
        """Limpiar todos los puntos de una curva.
        
        Args:
            parameter_id: ID del parámetro
            
        Returns:
            True si se limpió correctamente
        """
        if parameter_id in self._curves:
            self._curves[parameter_id]["points"].clear()
            logger.debug(f"Curva limpiada: {parameter_id}")
            return True
        return False
    
    def get_value_at(
        self,
        parameter_id: str,
        tick: int,
        default_value: float = 0.0
    ) -> float:
        """Obtener el valor de un parámetro en una posición específica.
        
        Args:
            parameter_id: ID del parámetro
            tick: Posición en ticks
            default_value: Valor por defecto si no hay curva
            
        Returns:
            Valor interpolado
        """
        if not self._automation_enabled:
            # Devolver valor del parámetro directamente
            return self._parameters.get(parameter_id, default_value)
        
        if parameter_id not in self._curves:
            return self._parameters.get(parameter_id, default_value)
        
        curve = self._curves[parameter_id]
        points = curve["points"]
        
        if not points:
            return self._parameters.get(parameter_id, default_value)
        
        # Interpolación lineal entre puntos
        if tick <= points[0][0]:
            return points[0][1]
        if tick >= points[-1][0]:
            return points[-1][1]
        
        # Encontrar puntos adyacentes
        for i in range(len(points) - 1):
            t1, v1 = points[i]
            t2, v2 = points[i + 1]
            
            if t1 <= tick <= t2:
                # Interpolación lineal
                ratio = (tick - t1) / (t2 - t1) if t2 != t1 else 0
                return v1 + (v2 - v1) * ratio
        
        return default_value
    
    def set_parameter(self, parameter_id: str, value: float) -> None:
        """Establecer un valor de parámetro directamente.
        
        Args:
            parameter_id: ID del parámetro
            value: Valor
        """
        self._parameters[parameter_id] = value
        
        # Si hay un target, actualizarlo directamente
        if parameter_id in self._targets:
            target, attr = self._targets[parameter_id]
            setattr(target, attr, value)
    
    def get_parameter(self, parameter_id: str, default: float = 0.0) -> float:
        """Obtener un valor de parámetro.
        
        Args:
            parameter_id: ID del parámetro
            default: Valor por defecto
            
        Returns:
            Valor del parámetro
        """
        return self._parameters.get(parameter_id, default)
    
    def register_target(
        self,
        parameter_id: str,
        target: Any,
        attribute: str
    ) -> None:
        """Registrar un target para automatización.
        
        Args:
            parameter_id: ID del parámetro
            target: Objeto objetivo
            attribute: Nombre del atributo a automatizar
        """
        self._targets[parameter_id] = (target, attribute)
        logger.debug(f"Target registrado: {parameter_id} -> {target}.{attribute}")
    
    def unregister_target(self, parameter_id: str) -> None:
        """Desregistrar un target."""
        if parameter_id in self._targets:
            del self._targets[parameter_id]
            logger.debug(f"Target desregistrado: {parameter_id}")
    
    def get_curve(self, parameter_id: str) -> Optional[dict]:
        """Obtener una curva de automatización."""
        return self._curves.get(parameter_id)
    
    def get_all_curves(self) -> dict:
        """Obtener todas las curvas."""
        return self._curves.copy()
    
    def evaluate_all(self, tick: int) -> None:
        """Evaluar todas las curvas en una posición y actualizar targets.
        
        Args:
            tick: Posición en ticks
        """
        if not self._automation_enabled:
            return
        
        for parameter_id in self._targets:
            value = self.get_value_at(parameter_id, tick)
            
            # Actualizar target
            if parameter_id in self._targets:
                target, attr = self._targets[parameter_id]
                setattr(target, attr, value)
            
            # Actualizar cache de parámetros
            self._parameters[parameter_id] = value
    
    def set_curve_enabled(self, parameter_id: str, enabled: bool) -> bool:
        """Habilitar o deshabilitar una curva específica.
        
        Args:
            parameter_id: ID del parámetro
            enabled: Estado
            
        Returns:
            True si se cambió correctamente
        """
        if parameter_id in self._curves:
            self._curves[parameter_id]["enabled"] = enabled
            return True
        return False
    
    def set_curve_mode(
        self,
        parameter_id: str,
        mode: str
    ) -> bool:
        """Establecer el modo de una curva.
        
        Args:
            parameter_id: ID del parámetro
            mode: Modo (write, read, loop)
            
        Returns:
            True si se estableció correctamente
        """
        if parameter_id in self._curves:
            self._curves[parameter_id]["mode"] = mode
            return True
        return False
