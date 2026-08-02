"""
Rate Limiter & Retry Logic
==========================

Exponential backoff, jitter, circuit breaker pattern
1.5GB RAM friendly - no external dependencies
Thread-safe for parallel scanning
"""

import time
import random
import threading
from typing import Callable, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class RateLimitConfig:
    """Rate limit yapılandırması"""
    max_retries: int = 5
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    circuit_breaker_threshold: int = 10  # Bu kadar hata sonrası circuit break


class CircuitBreaker:
    """Circuit breaker pattern - çok hata olunca servisi geçici devre dışı bırak (thread-safe)"""
    
    def __init__(self, threshold: int = 10, timeout: int = 300):
        self.threshold = threshold  # Kaç hata sonra açılsın
        self.timeout = timeout  # Kaç saniye kapalı kalsın
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()  # Thread safety için
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Fonksiyonu circuit breaker ile çağır (thread-safe)"""
        
        with self._lock:
            # OPEN state: Circuit açık, çağrıya izin verme
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise Exception(f"Circuit breaker OPEN - {self.timeout}s timeout")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Timeout geçti mi, deneme yapılabilir mi?"""
        if self.last_failure_time is None:
            return True
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.timeout
    
    def _on_success(self):
        """Başarılı çağrı - circuit'i sıfırla (thread-safe)"""
        with self._lock:
            self.failure_count = 0
            self.state = "CLOSED"
    
    def _on_failure(self):
        """Başarısız çağrı - counter artır (thread-safe)"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= self.threshold:
                self.state = "OPEN"
    
    def reset(self):
        """Manuel reset (thread-safe)"""
        with self._lock:
            self.failure_count = 0
            self.state = "CLOSED"
            self.last_failure_time = None


class RateLimiter:
    """Rate limiter - exponential backoff + jitter + circuit breaker (thread-safe)"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.circuit_breakers = {}  # Per-service circuit breakers
        self._lock = threading.Lock()  # Thread safety için
    
    def _get_circuit_breaker(self, service: str) -> CircuitBreaker:
        """Service için circuit breaker al (lazy init, thread-safe)"""
        with self._lock:
            if service not in self.circuit_breakers:
                self.circuit_breakers[service] = CircuitBreaker(
                    threshold=self.config.circuit_breaker_threshold,
                    timeout=300  # 5 dakika
                )
            return self.circuit_breakers[service]
    
    def _calculate_delay(self, attempt: int) -> float:
        """Exponential backoff + jitter"""
        # Exponential: 1s, 2s, 4s, 8s, 16s, 32s, 60s (max)
        delay = min(
            self.config.base_delay * (self.config.exponential_base ** attempt),
            self.config.max_delay
        )
        
        # Jitter: ±25% random
        if self.config.jitter:
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0.1, delay)  # Minimum 0.1s
    
    def call_with_retry(
        self, 
        func: Callable, 
        *args, 
        service: str = "default",
        **kwargs
    ) -> Any:
        """
        Fonksiyonu retry logic ile çağır
        
        Args:
            func: Çağrılacak fonksiyon
            service: Servis adı (circuit breaker için)
            *args, **kwargs: Fonksiyon parametreleri
        
        Returns:
            Fonksiyon sonucu
        
        Raises:
            Exception: Max retry sonrası
        """
        circuit_breaker = self._get_circuit_breaker(service)
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                # Circuit breaker ile çağır
                result = circuit_breaker.call(func, *args, **kwargs)
                
                # Başarılı - sonucu döndür
                if attempt > 0:
                    print(f"  ✓ {service}: Başarılı (attempt {attempt + 1}/{self.config.max_retries})")
                return result
                
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()
                
                # Rate limit check
                is_rate_limit = any(kw in error_str for kw in [
                    '429', 'rate limit', 'too many requests', 
                    'quota exceeded', 'throttle'
                ])
                
                # Connection error check
                is_connection_error = any(kw in error_str for kw in [
                    'connection', 'timeout', 'network', 'unreachable'
                ])
                
                # Retry yapılacak mı?
                should_retry = is_rate_limit or is_connection_error
                
                if not should_retry:
                    # Fatal error - retry yok
                    raise e
                
                if attempt < self.config.max_retries - 1:
                    delay = self._calculate_delay(attempt)
                    
                    if is_rate_limit:
                        # Rate limit özel mesaj
                        print(f"  ⏳ {service}: Rate limit (attempt {attempt + 1}/{self.config.max_retries}) → {delay:.1f}s bekleniyor...")
                    else:
                        # Connection error
                        print(f"  🔄 {service}: Bağlantı hatası (attempt {attempt + 1}/{self.config.max_retries}) → {delay:.1f}s bekleniyor...")
                    
                    time.sleep(delay)
                else:
                    # Son deneme de başarısız
                    print(f"  ❌ {service}: Max retry aşıldı ({self.config.max_retries} deneme)")
                    raise e
        
        # Buraya gelmemeli ama güvenlik için
        if last_exception:
            raise last_exception
    
    def reset_circuit_breaker(self, service: str):
        """Service için circuit breaker'ı sıfırla"""
        if service in self.circuit_breakers:
            self.circuit_breakers[service].reset()
    
    def get_circuit_state(self, service: str) -> str:
        """Circuit breaker durumu"""
        if service in self.circuit_breakers:
            return self.circuit_breakers[service].state
        return "CLOSED"


# === SERVICE-SPECIFIC RATE LIMITERS ===

class GitHubRateLimiter(RateLimiter):
    """GitHub Models API için özel rate limiter (15 req/min)"""
    
    def __init__(self):
        super().__init__(RateLimitConfig(
            max_retries=5,
            base_delay=4.0,  # GitHub: 4s base delay (15/min = 4s/req)
            max_delay=120.0,
            circuit_breaker_threshold=5
        ))


class GeminiRateLimiter(RateLimiter):
    """Google Gemini API için özel rate limiter (1500 req/day)"""
    
    def __init__(self):
        super().__init__(RateLimitConfig(
            max_retries=5,
            base_delay=1.0,  # Gemini: Generous limit
            max_delay=60.0,
            circuit_breaker_threshold=10
        ))


class WordPressRateLimiter(RateLimiter):
    """WordPress.org API için özel rate limiter"""
    
    def __init__(self):
        super().__init__(RateLimitConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=30.0,
            circuit_breaker_threshold=8
        ))


# === GLOBAL INSTANCES (singleton - hafif) ===

_rate_limiters = {
    "github": GitHubRateLimiter(),
    "gemini": GeminiRateLimiter(),
    "wordpress": WordPressRateLimiter(),
    "default": RateLimiter()
}


def get_rate_limiter(service: str = "default") -> RateLimiter:
    """Service için rate limiter al"""
    return _rate_limiters.get(service, _rate_limiters["default"])


def call_with_retry(func: Callable, service: str = "default", *args, **kwargs) -> Any:
    """Convenience function - retry logic ile fonksiyon çağır"""
    limiter = get_rate_limiter(service)
    return limiter.call_with_retry(func, *args, service=service, **kwargs)
