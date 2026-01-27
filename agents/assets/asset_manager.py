#!/usr/bin/env python3
"""
Asset Manager for Tribal Footage Library

Manages video assets with metadata, indexing, and search capabilities.
"""
import os
import json
import sqlite3
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

from agents.utils.logger import get_logger

logger = get_logger("asset_manager")


class AssetManager:
    """
    Manages video asset library with metadata and indexing.
    
    Features:
    - Index video files with metadata
    - Tag assets with locations and keywords
    - Search and filter assets
    - Track asset usage
    """
    
    SUPPORTED_FORMATS = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
    
    def __init__(
        self,
        assets_dir: str = "remotion/public/assets/footage",
        db_path: str = "agents/assets/assets.db"
    ):
        """
        Initialize asset manager.
        
        Args:
            assets_dir: Root directory for video assets
            db_path: Database file path
        """
        self.assets_dir = Path(assets_dir)
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()
        
        logger.info(f"Asset manager initialized: {self.assets_dir}")
    
    def _init_db(self):
        """Create database tables."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Assets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE,
                filepath TEXT NOT NULL,
                location TEXT,
                duration REAL,
                resolution TEXT,
                filesize INTEGER,
                tags TEXT,
                description TEXT,
                usage_count INTEGER DEFAULT 0,
                last_used TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                indexed_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Usage tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS asset_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_id INTEGER,
                video_id INTEGER,
                used_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (asset_id) REFERENCES assets(id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_location ON assets(location)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags ON assets(tags)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_filename ON assets(filename)")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Database initialized at {self.db_path}")
    
    def scan_directory(self, rescan: bool = False) -> int:
        """
        Scan assets directory and index all video files.
        
        Args:
            rescan: If True, re-index existing assets
        
        Returns:
            Number of assets indexed
        """
        logger.info(f"Scanning directory: {self.assets_dir}")
        
        indexed_count = 0
        
        for root, dirs, files in os.walk(self.assets_dir):
            for filename in files:
                if any(filename.lower().endswith(ext) for ext in self.SUPPORTED_FORMATS):
                    filepath = Path(root) / filename
                    
                    # Check if already indexed
                    if not rescan and self.get_asset_by_filename(filename):
                        continue
                    
                    # Add to database
                    self.add_asset(filepath)
                    indexed_count += 1
        
        logger.info(f"Indexed {indexed_count} assets")
        return indexed_count
    
    def add_asset(
        self,
        filepath: Path,
        location: Optional[str] = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None
    ) -> int:
        """
        Add asset to database with metadata.
        
        Args:
            filepath: Path to video file
            location: Geographic location (Mongolia, Nepal, PNG)
            tags: List of descriptive tags
            description: Asset description
        
        Returns:
            Asset ID
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            logger.error(f"File not found: {filepath}")
            return -1
        
        # Extract metadata
        filename = filepath.name
        filesize = filepath.stat().st_size
        
        # Infer location from path if not provided
        if not location:
            location = self._infer_location(filepath)
        
        # Auto-tag if not provided
        if tags is None:
            tags = self._auto_tag(filepath)
        
        # Get video metadata (duration, resolution)
        duration, resolution = self._get_video_metadata(filepath)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if already exists
        cursor.execute("SELECT id FROM assets WHERE filename = ?", (filename,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing
            asset_id = existing[0]
            cursor.execute("""
                UPDATE assets
                SET filepath = ?, location = ?, duration = ?, resolution = ?,
                    filesize = ?, tags = ?, description = ?, indexed_at = ?
                WHERE id = ?
            """, (
                str(filepath), location, duration, resolution,
                filesize, json.dumps(tags), description,
                datetime.now().isoformat(), asset_id
            ))
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO assets (
                    filename, filepath, location, duration, resolution,
                    filesize, tags, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                filename, str(filepath), location, duration, resolution,
                filesize, json.dumps(tags), description
            ))
            asset_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        logger.info(f"Added asset #{asset_id}: {filename} ({location})")
        
        return asset_id
    
    def _infer_location(self, filepath: Path) -> str:
        """Infer location from file path."""
        path_str = str(filepath).lower()
        
        if 'mongolia' in path_str:
            return 'Mongolia'
        elif 'nepal' in path_str:
            return 'Nepal'
        elif 'papua' in path_str or 'png' in path_str:
            return 'Papua New Guinea'
        
        return 'Unknown'
    
    def _auto_tag(self, filepath: Path) -> List[str]:
        """Auto-generate tags from filename and path."""
        tags = []
        
        # Extract from filename
        filename = filepath.stem.lower()
        
        # Common keywords
        keywords = [
            'hunting', 'festival', 'cooking', 'dance', 'ceremony',
            'traditional', 'village', 'mountain', 'river', 'forest',
            'craft', 'clothing', 'music', 'family', 'elder',
            'children', 'fire', 'food', 'ritual', 'celebration'
        ]
        
        for keyword in keywords:
            if keyword in filename:
                tags.append(keyword)
        
        # Add location as tag
        location = self._infer_location(filepath)
        if location != 'Unknown':
            tags.append(location.lower())
        
        return tags
    
    def _get_video_metadata(self, filepath: Path) -> Tuple[Optional[float], Optional[str]]:
        """
        Extract video metadata (duration, resolution).
        
        Returns:
            (duration_seconds, resolution_string)
        """
        try:
            # Try with ffprobe if available
            import subprocess
            
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries',
                 'format=duration:stream=width,height', '-of', 'json',
                 str(filepath)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                duration = None
                if 'format' in data and 'duration' in data['format']:
                    duration = float(data['format']['duration'])
                
                resolution = None
                if 'streams' in data and len(data['streams']) > 0:
                    stream = data['streams'][0]
                    if 'width' in stream and 'height' in stream:
                        resolution = f"{stream['width']}x{stream['height']}"
                
                return duration, resolution
        
        except Exception as e:
            logger.debug(f"Could not extract metadata for {filepath}: {e}")
        
        return None, None
    
    def get_asset_by_filename(self, filename: str) -> Optional[Dict]:
        """Get asset by filename."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM assets WHERE filename = ?", (filename,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            asset = dict(row)
            asset['tags'] = json.loads(asset['tags']) if asset['tags'] else []
            return asset
        
        return None
    
    def get_asset(self, asset_id: int) -> Optional[Dict]:
        """Get asset by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM assets WHERE id = ?", (asset_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            asset = dict(row)
            asset['tags'] = json.loads(asset['tags']) if asset['tags'] else []
            return asset
        
        return None
    
    def search_assets(
        self,
        location: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_duration: Optional[float] = None,
        max_duration: Optional[float] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Search assets by criteria.
        
        Args:
            location: Filter by location
            tags: Filter by tags (any match)
            min_duration: Minimum duration in seconds
            max_duration: Maximum duration in seconds
            limit: Maximum results
        
        Returns:
            List of matching assets
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM assets WHERE 1=1"
        params = []
        
        if location:
            query += " AND location = ?"
            params.append(location)
        
        if min_duration:
            query += " AND duration >= ?"
            params.append(min_duration)
        
        if max_duration:
            query += " AND duration <= ?"
            params.append(max_duration)
        
        query += " ORDER BY usage_count ASC, RANDOM() LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        assets = []
        for row in rows:
            asset = dict(row)
            asset['tags'] = json.loads(asset['tags']) if asset['tags'] else []
            
            # Filter by tags if specified
            if tags:
                asset_tags = set(asset['tags'])
                if not any(tag.lower() in asset_tags for tag in tags):
                    continue
            
            assets.append(asset)
        
        return assets
    
    def track_usage(self, asset_id: int, video_id: Optional[int] = None):
        """Track asset usage."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Update usage count
        cursor.execute("""
            UPDATE assets
            SET usage_count = usage_count + 1,
                last_used = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), asset_id))
        
        # Log usage
        cursor.execute("""
            INSERT INTO asset_usage (asset_id, video_id)
            VALUES (?, ?)
        """, (asset_id, video_id))
        
        conn.commit()
        conn.close()
    
    def get_stats(self) -> Dict:
        """Get asset library statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total assets
        cursor.execute("SELECT COUNT(*) FROM assets")
        total = cursor.fetchone()[0]
        
        # By location
        cursor.execute("""
            SELECT location, COUNT(*) as count
            FROM assets
            GROUP BY location
        """)
        by_location = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Total duration
        cursor.execute("SELECT SUM(duration) FROM assets WHERE duration IS NOT NULL")
        total_duration = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_assets': total,
            'by_location': by_location,
            'total_duration_seconds': total_duration,
            'total_duration_minutes': total_duration / 60
        }


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    manager = AssetManager()
    
    # Scan directory
    count = manager.scan_directory(rescan=True)
    print(f"Indexed {count} assets")
    
    # Get stats
    stats = manager.get_stats()
    print(json.dumps(stats, indent=2))
    
    # Search
    assets = manager.search_assets(location="Mongolia", limit=5)
    print(f"\nFound {len(assets)} Mongolia assets")
