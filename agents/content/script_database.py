#!/usr/bin/env python3
"""
Script Database for Video Content Management

Stores generated scripts, tracks performance, and prevents duplicates.
"""
import sqlite3
import json
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

from agents.utils.logger import get_logger

logger = get_logger("script_db")


class ScriptDatabase:
    """
    Database for managing video scripts and performance.
    
    Features:
    - Store generated topics and scripts
    - Track video performance (views, likes, shares)
    - Prevent duplicate content
    - Query by category, location, status
    """
    
    def __init__(self, db_path: str = "agents/content/scripts.db"):
        """Initialize database."""
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Create database tables if they don't exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Scripts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                script TEXT NOT NULL,
                hook TEXT,
                keywords TEXT,
                category TEXT,
                location TEXT,
                duration INTEGER,
                status TEXT DEFAULT 'pending',
                video_path TEXT,
                tiktok_url TEXT,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                generated_at TEXT,
                rendered_at TEXT,
                posted_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Performance tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                script_id INTEGER,
                views INTEGER,
                likes INTEGER,
                shares INTEGER,
                comments INTEGER,
                recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (script_id) REFERENCES scripts(id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON scripts(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON scripts(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_location ON scripts(location)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_posted_at ON scripts(posted_at)")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Database initialized at {self.db_path}")
    
    def add_script(self, topic_data: Dict) -> int:
        """
        Add a new script to the database.
        
        Args:
            topic_data: Dictionary with topic, script, keywords, etc.
        
        Returns:
            Script ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO scripts (
                topic, script, hook, keywords, category, location,
                duration, generated_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            topic_data.get('topic'),
            topic_data.get('script'),
            topic_data.get('hook'),
            json.dumps(topic_data.get('keywords', [])),
            topic_data.get('category'),
            topic_data.get('location'),
            topic_data.get('duration'),
            topic_data.get('generated_at', datetime.now().isoformat()),
            'pending'
        ))
        
        script_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Added script #{script_id}: {topic_data.get('topic')}")
        
        return script_id
    
    def get_script(self, script_id: int) -> Optional[Dict]:
        """Get script by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM scripts WHERE id = ?", (script_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            script = dict(row)
            script['keywords'] = json.loads(script['keywords']) if script['keywords'] else []
            return script
        
        return None
    
    def update_status(self, script_id: int, status: str, **kwargs):
        """
        Update script status and optional fields.
        
        Args:
            script_id: Script ID
            status: New status (pending, rendering, rendered, posted, failed)
            **kwargs: Additional fields to update (video_path, tiktok_url, etc.)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build dynamic update query
        fields = ['status = ?']
        values = [status]
        
        for key, value in kwargs.items():
            if key in ['video_path', 'tiktok_url', 'rendered_at', 'posted_at']:
                fields.append(f'{key} = ?')
                values.append(value)
        
        values.append(script_id)
        
        query = f"UPDATE scripts SET {', '.join(fields)} WHERE id = ?"
        cursor.execute(query, values)
        
        conn.commit()
        conn.close()
        
        logger.info(f"Updated script #{script_id} status: {status}")
    
    def update_performance(self, script_id: int, views: int, likes: int, shares: int = 0, comments: int = 0):
        """
        Update performance metrics for a posted video.
        
        Args:
            script_id: Script ID
            views: Total views
            likes: Total likes
            shares: Total shares
            comments: Total comments
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Update main record
        cursor.execute("""
            UPDATE scripts
            SET views = ?, likes = ?, shares = ?, comments = ?
            WHERE id = ?
        """, (views, likes, shares, comments, script_id))
        
        # Create performance snapshot
        cursor.execute("""
            INSERT INTO performance_snapshots (script_id, views, likes, shares, comments)
            VALUES (?, ?, ?, ?, ?)
        """, (script_id, views, likes, shares, comments))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Updated performance for script #{script_id}: {views} views, {likes} likes")
    
    def get_pending_scripts(self, limit: int = 10) -> List[Dict]:
        """Get scripts pending rendering."""
        return self._query_by_status('pending', limit)
    
    def get_rendered_scripts(self, limit: int = 10) -> List[Dict]:
        """Get scripts that have been rendered but not posted."""
        return self._query_by_status('rendered', limit)
    
    def _query_by_status(self, status: str, limit: int) -> List[Dict]:
        """Query scripts by status."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM scripts
            WHERE status = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (status, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        scripts = []
        for row in rows:
            script = dict(row)
            script['keywords'] = json.loads(script['keywords']) if script['keywords'] else []
            scripts.append(script)
        
        return scripts
    
    def get_top_performing(self, metric: str = 'views', limit: int = 10) -> List[Dict]:
        """
        Get top performing videos.
        
        Args:
            metric: Sort by 'views', 'likes', 'shares', or 'comments'
            limit: Number of results
        
        Returns:
            List of scripts sorted by metric
        """
        if metric not in ['views', 'likes', 'shares', 'comments']:
            metric = 'views'
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT * FROM scripts
            WHERE status = 'posted'
            ORDER BY {metric} DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        scripts = []
        for row in rows:
            script = dict(row)
            script['keywords'] = json.loads(script['keywords']) if script['keywords'] else []
            scripts.append(script)
        
        return scripts
    
    def check_duplicate(self, topic: str) -> bool:
        """
        Check if topic already exists.
        
        Args:
            topic: Topic title to check
        
        Returns:
            True if duplicate found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM scripts
            WHERE topic = ?
        """, (topic,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def get_stats(self) -> Dict:
        """Get database statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Count by status
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM scripts
            GROUP BY status
        """)
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Total performance
        cursor.execute("""
            SELECT
                SUM(views) as total_views,
                SUM(likes) as total_likes,
                SUM(shares) as total_shares,
                AVG(views) as avg_views,
                AVG(likes) as avg_likes
            FROM scripts
            WHERE status = 'posted'
        """)
        perf = cursor.fetchone()
        
        conn.close()
        
        return {
            'total_scripts': sum(status_counts.values()),
            'by_status': status_counts,
            'total_views': perf[0] or 0,
            'total_likes': perf[1] or 0,
            'total_shares': perf[2] or 0,
            'avg_views': perf[3] or 0,
            'avg_likes': perf[4] or 0
        }


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    db = ScriptDatabase()
    
    # Add test script
    topic_data = {
        'topic': 'Test Topic',
        'script': 'Test script content',
        'keywords': ['test', 'demo'],
        'category': 'culture',
        'location': 'Mongolia',
        'duration': 30
    }
    
    script_id = db.add_script(topic_data)
    print(f"Added script #{script_id}")
    
    # Get stats
    stats = db.get_stats()
    print(json.dumps(stats, indent=2))
