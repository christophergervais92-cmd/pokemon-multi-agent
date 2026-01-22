#!/usr/bin/env python3
"""
Database Connection Pooling

Provides connection pooling for SQLite databases to improve performance
and handle concurrent requests better.
"""
import os
import sqlite3
import threading
from typing import Optional, Dict
from pathlib import Path
from contextlib import contextmanager
from queue import Queue, Empty
from datetime import datetime, timedelta

from agents.utils.logger import get_logger

logger = get_logger("db_pool")

# =============================================================================
# CONFIGURATION
# =============================================================================

MAX_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "10"))
POOL_TIMEOUT = int(os.environ.get("DB_POOL_TIMEOUT", "5"))  # seconds
CONNECTION_TIMEOUT = int(os.environ.get("DB_CONNECTION_TIMEOUT", "10"))  # seconds

# =============================================================================
# CONNECTION POOL
# =============================================================================

class ConnectionPool:
    """
    Thread-safe connection pool for SQLite databases.
    
    Features:
    - Reuses connections to reduce overhead
    - Thread-safe access
    - Connection timeout handling
    - Automatic connection health checks
    """
    
    def __init__(
        self,
        db_path: Path,
        max_size: int = MAX_POOL_SIZE,
        timeout: int = POOL_TIMEOUT,
    ):
        """
        Initialize connection pool.
        
        Args:
            db_path: Path to SQLite database file
            max_size: Maximum number of connections in pool
            timeout: Timeout for getting connection from pool
        """
        self.db_path = Path(db_path)
        self.max_size = max_size
        self.timeout = timeout
        self.pool: Queue = Queue(maxsize=max_size)
        self.lock = threading.Lock()
        self.created_connections = 0
        self.active_connections = 0
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Pre-create some connections
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Pre-create some connections in the pool."""
        initial_size = min(3, self.max_size)
        for _ in range(initial_size):
            try:
                conn = self._create_connection()
                self.pool.put(conn, block=False)
                self.created_connections += 1
            except Exception as e:
                logger.warning(f"Failed to create initial connection: {e}")
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=CONNECTION_TIMEOUT,
            check_same_thread=False,  # Allow use from multiple threads
        )
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        return conn
    
    def _is_connection_alive(self, conn: sqlite3.Connection) -> bool:
        """Check if connection is still alive."""
        try:
            conn.execute("SELECT 1")
            return True
        except:
            return False
    
    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool (context manager).
        
        Usage:
            with pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM ...")
        """
        conn = None
        try:
            # Try to get connection from pool
            try:
                conn = self.pool.get(timeout=self.timeout)
            except Empty:
                # Pool is empty, create new connection if under limit
                with self.lock:
                    if self.created_connections < self.max_size:
                        conn = self._create_connection()
                        self.created_connections += 1
                        logger.debug(f"Created new connection (total: {self.created_connections})")
                    else:
                        # Wait a bit more for connection to become available
                        conn = self.pool.get(timeout=self.timeout)
            
            # Check if connection is still alive
            if not self._is_connection_alive(conn):
                logger.warning("Connection dead, creating new one")
                try:
                    conn.close()
                except:
                    pass
                conn = self._create_connection()
                with self.lock:
                    self.created_connections += 1
            
            with self.lock:
                self.active_connections += 1
            
            yield conn
            
        finally:
            if conn:
                with self.lock:
                    self.active_connections -= 1
                
                # Return connection to pool
                try:
                    self.pool.put(conn, block=False)
                except:
                    # Pool is full, close connection
                    try:
                        conn.close()
                        with self.lock:
                            self.created_connections -= 1
                    except:
                        pass
    
    def get_stats(self) -> Dict:
        """Get pool statistics."""
        with self.lock:
            return {
                "max_size": self.max_size,
                "created_connections": self.created_connections,
                "active_connections": self.active_connections,
                "available_connections": self.pool.qsize(),
                "db_path": str(self.db_path),
            }
    
    def close_all(self):
        """Close all connections in the pool."""
        with self.lock:
            while not self.pool.empty():
                try:
                    conn = self.pool.get_nowait()
                    conn.close()
                except:
                    pass
            self.created_connections = 0
            self.active_connections = 0


# Global connection pools
_pools: Dict[str, ConnectionPool] = {}

def get_pool(db_name: str, db_path: Optional[Path] = None) -> ConnectionPool:
    """
    Get or create a connection pool for a database.
    
    Args:
        db_name: Name of the database (e.g., "notifications", "pokemon_cards")
        db_path: Optional path to database file (defaults to project root)
    
    Returns:
        ConnectionPool instance
    """
    if db_name not in _pools:
        if db_path is None:
            # Default to project root
            base_dir = Path(__file__).parent.parent.parent
            db_path = base_dir / f"{db_name}.db"
        
        _pools[db_name] = ConnectionPool(db_path)
        logger.info(f"Created connection pool for {db_name}", extra={"path": str(db_path)})
    
    return _pools[db_name]


def close_all_pools():
    """Close all connection pools."""
    for pool in _pools.values():
        pool.close_all()
    _pools.clear()
