"""Performance Monitor - Monitor de CPU y rendimiento.

Sistema de monitoreo de rendimiento del motor de audio,
incluyendo CPU, memoria y latencia.
"""

from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import time
import threading
import logging

# psutil es opcional - si no está instalado, el monitor funcionará en modo limitado
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None


logger = logging.getLogger(__name__)


class PerformanceLevel(Enum):
    """Nivel de rendimiento."""
    EXCELLENT = "excellent"      # < 30% CPU
    GOOD = "good"                  # 30-50% CPU
    WARNING = "warning"            # 50-70% CPU
    CRITICAL = "critical"          # > 70% CPU
    OVERLOAD = "overload"          # Clipping/xruns


@dataclass
class PerformanceMetrics:
    """Métricas de rendimiento.
    
    Attributes:
        cpu_percent: Porcentaje de CPU
        memory_mb: Memoria en MB
        buffer_underruns: Underruns del buffer
        xruns: Xruns detectados
        latency_ms: Latencia en ms
        dsp_load: Carga de DSP en %
        sample_rate: Sample rate actual
        buffer_size: Buffer size actual
        voices: Voces activas
        level: Nivel de rendimiento
        timestamp: Timestamp de la medición
    """
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    buffer_underruns: int = 0
    xruns: int = 0
    latency_ms: float = 0.0
    dsp_load: float = 0.0
    sample_rate: int = 44100
    buffer_size: int = 512
    voices: int = 0
    level: PerformanceLevel = PerformanceLevel.EXCELLENT
    timestamp: float = 0.0


class PerformanceMonitor:
    """Monitor de rendimiento.
    
    Monitorea CPU, memoria, latencia y detecta problemas.
    """
    
    def __init__(
        self,
        sample_rate: int = 44100,
        buffer_size: int = 512,
        update_interval: float = 0.5
    ):
        """Inicializar monitor.
        
        Args:
            sample_rate: Sample rate
            buffer_size: Buffer size
            update_interval: Intervalo de actualización (segundos)
        """
        self._sample_rate = sample_rate
        self._buffer_size = buffer_size
        self._update_interval = update_interval
        
        # Métricas
        self._current_metrics = PerformanceMetrics(
            sample_rate=sample_rate,
            buffer_size=buffer_size
        )
        self._metrics_history: List[PerformanceMetrics] = []
        self._max_history = 1000
        
        # Contadores
        self._buffer_underruns = 0
        self._xruns = 0
        self._peak_cpu = 0.0
        self._peak_memory = 0.0
        
        # Proceso - psutil es opcional
        if PSUTIL_AVAILABLE:
            self._process = psutil.Process()
        else:
            self._process = None
            logger.warning("psutil no disponible - monitoreo de CPU deshabilitado")
        
        # Callbacks
        self._alert_callback: Optional[Callable[[PerformanceLevel, str], None]] = None
        
        # Hilo de monitoreo
        self._monitor_thread: Optional[threading.Thread] = None
        self._is_running = False
        
        logger.info(f"PerformanceMonitor inicializado: {sample_rate}Hz, buffer {buffer_size}")
    
    @property
    def current_metrics(self) -> PerformanceMetrics:
        """Obtener métricas actuales."""
        return self._current_metrics
    
    @property
    def cpu_percent(self) -> float:
        """Obtener uso de CPU."""
        return self._current_metrics.cpu_percent
    
    @property
    def memory_mb(self) -> float:
        """Obtener uso de memoria."""
        return self._current_metrics.memory_mb
    
    @property
    def latency_ms(self) -> float:
        """Obtener latencia."""
        return self._current_metrics.latency_ms
    
    @property
    def performance_level(self) -> PerformanceLevel:
        """Obtener nivel de rendimiento."""
        return self._current_metrics.level
    
    # === Métricas ===
    
    def update_metrics(
        self,
        dsp_time: float,
        voices: int = 0
    ) -> None:
        """Actualizar métricas.
        
        Args:
            dsp_time: Tiempo de procesamiento del buffer
            voices: Voces activas
        """
        # Calcular load de DSP
        # dsp_time es el tiempo que tomó procesar el buffer
        # buffer_duration es la duración real del buffer
        buffer_duration = self._buffer_size / self._sample_rate
        dsp_load = (dsp_time / buffer_duration) * 100.0 if buffer_duration > 0 else 0.0
        
        # CPU del proceso (psutil es opcional)
        if self._process is not None:
            cpu_percent = self._process.cpu_percent()
            memory_info = self._process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
        else:
            cpu_percent = 0.0
            memory_mb = 0.0
        
        # Latencia
        latency_ms = (self._buffer_size / self._sample_rate) * 1000.0
        
        # Determinar nivel
        level = self._calculate_level(dsp_load, cpu_percent)
        
        # Crear métricas
        metrics = PerformanceMetrics(
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            buffer_underruns=self._buffer_underruns,
            xruns=self._xruns,
            latency_ms=latency_ms,
            dsp_load=min(dsp_load, 100.0),
            sample_rate=self._sample_rate,
            buffer_size=self._buffer_size,
            voices=voices,
            level=level,
            timestamp=time.time()
        )
        
        self._current_metrics = metrics
        self._add_to_history(metrics)
        
        # Actualizar picos
        if cpu_percent > self._peak_cpu:
            self._peak_cpu = cpu_percent
        if memory_mb > self._peak_memory:
            self._peak_memory = memory_mb
    
    def _calculate_level(
        self,
        dsp_load: float,
        cpu_percent: float
    ) -> PerformanceLevel:
        """Calcular nivel de rendimiento."""
        # Usar el mayor de los dos
        load = max(dsp_load, cpu_percent)
        
        if load < 30:
            return PerformanceLevel.EXCELLENT
        elif load < 50:
            return PerformanceLevel.GOOD
        elif load < 70:
            return PerformanceLevel.WARNING
        elif load < 90:
            return PerformanceLevel.CRITICAL
        else:
            return PerformanceLevel.OVERLOAD
    
    def _add_to_history(self, metrics: PerformanceMetrics) -> None:
        """Agregar métricas al historial."""
        self._metrics_history.append(metrics)
        
        if len(self._metrics_history) > self._max_history:
            self._metrics_history.pop(0)
    
    # === Monitoreo ===
    
    def start_monitoring(self) -> None:
        """Iniciar hilo de monitoreo."""
        if self._is_running:
            return
        
        self._is_running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self._monitor_thread.start()
        
        logger.info("Monitoreo iniciado")
    
    def stop_monitoring(self) -> None:
        """Detener hilo de monitoreo."""
        self._is_running = False
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
        
        logger.info("Monitoreo detenido")
    
    def _monitor_loop(self) -> None:
        """Loop de monitoreo."""
        while self._is_running:
            try:
                # Actualizar métricas del sistema (psutil es opcional)
                if self._process is not None:
                    cpu = self._process.cpu_percent()
                    memory = self._process.memory_info().rss / (1024 * 1024)
                else:
                    cpu = 0.0
                    memory = 0.0
                
                # Calcular nivel
                level = self._calculate_level(cpu, cpu)
                
                # Actualizar métricas
                self._current_metrics.cpu_percent = cpu
                self._current_metrics.memory_mb = memory
                self._current_metrics.level = level
                self._current_metrics.timestamp = time.time()
                
                # Verificar alertas
                if level in (PerformanceLevel.WARNING, 
                            PerformanceLevel.CRITICAL,
                            PerformanceLevel.OVERLOAD):
                    self._check_alerts(level)
                
            except Exception as e:
                logger.error(f"Error en monitoreo: {e}")
            
            time.sleep(self._update_interval)
    
    def _check_alerts(self, level: PerformanceLevel) -> None:
        """Verificar y enviar alertas."""
        if self._alert_callback:
            message = f"Rendimiento {level.value}: CPU {self._current_metrics.cpu_percent:.1f}%"
            self._alert_callback(level, message)
    
    def set_alert_callback(
        self,
        callback: Callable[[PerformanceLevel, str], None]
    ) -> None:
        """Establecer callback de alertas."""
        self._alert_callback = callback
    
    # === Reporte ===
    
    def get_metrics_summary(self) -> Dict:
        """Obtener resumen de métricas."""
        return {
            "current": {
                "cpu": f"{self._current_metrics.cpu_percent:.1f}%",
                "memory": f"{self._current_metrics.memory_mb:.1f} MB",
                "latency": f"{self._current_metrics.latency_ms:.2f} ms",
                "dsp_load": f"{self._current_metrics.dsp_load:.1f}%",
                "level": self._current_metrics.level.value
            },
            "peaks": {
                "cpu": f"{self._peak_cpu:.1f}%",
                "memory": f"{self._peak_memory:.1f} MB"
            },
            "xruns": self._xruns,
            "underruns": self._buffer_underruns
        }
    
    def get_history(
        self,
        limit: int = 100
    ) -> List[PerformanceMetrics]:
        """Obtener historial de métricas."""
        return self._metrics_history[-limit:]
    
    def reset_counters(self) -> None:
        """Resetear contadores."""
        self._buffer_underruns = 0
        self._xruns = 0
        self._peak_cpu = 0.0
        self._peak_memory = 0.0
        logger.info("Contadores reseteados")
    
    # === Utilidades ===
    
    def get_optimal_buffer_size(self, target_latency_ms: float = 10.0) -> int:
        """Obtener buffer size óptimo para latencia objetivo.
        
        Args:
            target_latency_ms: Latencia objetivo en ms
            
        Returns:
            Buffer size recomendado
        """
        # latency = buffer_size / sample_rate * 1000
        # buffer_size = latency * sample_rate / 1000
        buffer_size = int(target_latency_ms * self._sample_rate / 1000)
        
        # Redondear a potencia de 2
        buffer_size = 2 ** int(round(buffer_size ** 0.5))
        
        # Limitar rango
        return max(64, min(4096, buffer_size))
    
    @property
    def buffer_underruns(self) -> int:
        """Obtener contador de underruns."""
        return self._buffer_underruns
    
    def increment_underruns(self) -> None:
        """Incrementar contador de underruns."""
        self._buffer_underruns += 1
    
    @property
    def xruns(self) -> int:
        """Obtener contador de xruns."""
        return self._xruns
    
    def increment_xruns(self) -> None:
        """Incrementar contador de xruns."""
        self._xruns += 1
