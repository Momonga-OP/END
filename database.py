import os
import logging
import sqlite3
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
DEV_MODE = os.getenv("DEV_MODE", "True").lower() in ("true", "1", "t")
SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "guilds.db")

# Try to import PostgreSQL driver, but don't fail if not available (for dev mode)
try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False
    if not DEV_MODE and DATABASE_URL:
        logger.warning("psycopg2 not installed but production mode is enabled. Falling back to SQLite.")


def get_connection():
    """Get a database connection based on environment"""
    if not DEV_MODE and DATABASE_URL and HAS_PSYCOPG2:
        # Production mode with PostgreSQL
        try:
            return psycopg2.connect(DATABASE_URL)
        except Exception as e:
            logger.error(f"Error connecting to PostgreSQL: {e}")
            # Fall back to SQLite if PostgreSQL connection fails
            logger.warning("Falling back to SQLite database")
    
    # Development mode with SQLite or fallback
    try:
        # Check if the SQLite file exists and is valid
        if os.path.exists(SQLITE_DB_PATH):
            try:
                # Try to open the database to check if it's valid
                test_conn = sqlite3.connect(SQLITE_DB_PATH)
                test_conn.cursor()
                test_conn.close()
            except sqlite3.Error:
                # If the file is corrupted, remove it
                logger.warning(f"SQLite database file is corrupted, recreating it")
                os.remove(SQLITE_DB_PATH)
        
        # Create a new connection (will create the file if it doesn't exist)
        return sqlite3.connect(SQLITE_DB_PATH)
    except Exception as e:
        logger.error(f"Error with SQLite database: {e}")
        # Create a new file in a different location as last resort
        alt_path = os.path.join(os.path.dirname(__file__), "guilds_new.db")
        logger.warning(f"Creating alternative database at {alt_path}")
        return sqlite3.connect(alt_path)


def initialize_db():
    """Initialize the database and create the tables if they don't exist."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # SQLite uses INTEGER PRIMARY KEY for auto-increment
        if isinstance(conn, sqlite3.Connection):
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS guilds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_name TEXT NOT NULL UNIQUE,
                    emoji_id TEXT NOT NULL,
                    role_id TEXT NOT NULL
                )
            """)
            
            # Create ping_history table for storing ping records
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ping_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_name TEXT NOT NULL,
                    author_id TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_name) REFERENCES guilds(guild_name)
                )
            """)
            
            # Create settings table for bot configuration
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
        else:
            # PostgreSQL uses SERIAL for auto-increment
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS guilds (
                    id SERIAL PRIMARY KEY,
                    guild_name TEXT NOT NULL UNIQUE,
                    emoji_id TEXT NOT NULL,
                    role_id TEXT NOT NULL
                )
            """)
            
            # Create ping_history table for storing ping records
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ping_history (
                    id SERIAL PRIMARY KEY,
                    guild_name TEXT NOT NULL,
                    author_id TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_name) REFERENCES guilds(guild_name)
                )
            """)
            
            # Create settings table for bot configuration
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


def add_guild(guild_name: str, emoji_id: str, role_id: str):
    """Add a new guild to the database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if isinstance(conn, sqlite3.Connection):
            cursor.execute("""
                INSERT INTO guilds (guild_name, emoji_id, role_id)
                VALUES (?, ?, ?)
            """, (guild_name, emoji_id, role_id))
        else:
            cursor.execute("""
                INSERT INTO guilds (guild_name, emoji_id, role_id)
                VALUES (%s, %s, %s)
            """, (guild_name, emoji_id, role_id))
            
        conn.commit()
        conn.close()
        logger.info(f"Added guild: {guild_name}")
        return True
    except Exception as e:
        logger.error(f"Error adding guild: {e}")
        return False


def update_guild(guild_name: str, emoji_id: str = None, role_id: str = None):
    """Update an existing guild in the database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Build the update query based on provided parameters
        update_parts = []
        params = []
        
        if emoji_id is not None:
            update_parts.append("emoji_id = ?" if isinstance(conn, sqlite3.Connection) else "emoji_id = %s")
            params.append(emoji_id)
            
        if role_id is not None:
            update_parts.append("role_id = ?" if isinstance(conn, sqlite3.Connection) else "role_id = %s")
            params.append(role_id)
            
        if not update_parts:
            logger.warning("No fields to update for guild")
            return False
            
        update_query = f"UPDATE guilds SET {', '.join(update_parts)} WHERE guild_name = ?"
        if not isinstance(conn, sqlite3.Connection):
            update_query = update_query.replace("?", "%s")
            
        params.append(guild_name)
        
        cursor.execute(update_query, params)
        conn.commit()
        conn.close()
        logger.info(f"Updated guild: {guild_name}")
        return True
    except Exception as e:
        logger.error(f"Error updating guild: {e}")
        return False


def delete_guild(guild_name: str):
    """Delete a guild from the database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if isinstance(conn, sqlite3.Connection):
            cursor.execute("DELETE FROM guilds WHERE guild_name = ?", (guild_name,))
        else:
            cursor.execute("DELETE FROM guilds WHERE guild_name = %s", (guild_name,))
            
        conn.commit()
        conn.close()
        logger.info(f"Deleted guild: {guild_name}")
        return True
    except Exception as e:
        logger.error(f"Error deleting guild: {e}")
        return False


def get_all_guilds():
    """Fetch all guilds from the database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM guilds")
        guilds = cursor.fetchall()
        conn.close()
        return guilds
    except Exception as e:
        logger.error(f"Error fetching guilds: {e}")
        return []


def get_guild_by_name(guild_name: str):
    """Fetch a specific guild by name."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if isinstance(conn, sqlite3.Connection):
            cursor.execute("SELECT * FROM guilds WHERE guild_name = ?", (guild_name,))
        else:
            cursor.execute("SELECT * FROM guilds WHERE guild_name = %s", (guild_name,))
            
        guild = cursor.fetchone()
        conn.close()
        return guild
    except Exception as e:
        logger.error(f"Error fetching guild: {e}")
        return None


def add_ping_record(guild_name: str, author_id: str):
    """Add a ping record to the database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if isinstance(conn, sqlite3.Connection):
            cursor.execute("""
                INSERT INTO ping_history (guild_name, author_id)
                VALUES (?, ?)
            """, (guild_name, author_id))
        else:
            cursor.execute("""
                INSERT INTO ping_history (guild_name, author_id)
                VALUES (%s, %s)
            """, (guild_name, author_id))
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error adding ping record: {e}")
        return False


def get_ping_history(guild_name: str, days: int = 7):
    """Get ping history for a guild for the specified number of days."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if isinstance(conn, sqlite3.Connection):
            cursor.execute("""
                SELECT * FROM ping_history 
                WHERE guild_name = ? AND timestamp > datetime('now', '-' || ? || ' days')
                ORDER BY timestamp DESC
            """, (guild_name, days))
        else:
            cursor.execute("""
                SELECT * FROM ping_history 
                WHERE guild_name = %s AND timestamp > NOW() - INTERVAL '%s days'
                ORDER BY timestamp DESC
            """, (guild_name, days))
            
        records = cursor.fetchall()
        conn.close()
        return records
    except Exception as e:
        logger.error(f"Error fetching ping history: {e}")
        return []


def get_setting(key: str, default=None):
    """Get a setting from the database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if isinstance(conn, sqlite3.Connection):
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        else:
            cursor.execute("SELECT value FROM settings WHERE key = %s", (key,))
            
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else default
    except Exception as e:
        logger.error(f"Error fetching setting: {e}")
        return default


def set_setting(key: str, value: str):
    """Set a setting in the database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Try to update first
        if isinstance(conn, sqlite3.Connection):
            cursor.execute("""
                UPDATE settings SET value = ? WHERE key = ?
            """, (value, key))
            
            # If no rows were updated, insert a new row
            if cursor.rowcount == 0:
                cursor.execute("""
                    INSERT INTO settings (key, value) VALUES (?, ?)
                """, (key, value))
        else:
            cursor.execute("""
                INSERT INTO settings (key, value) VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (key, value))
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error setting setting: {e}")
        return False


# Initialize the database when the module is imported
try:
    initialize_db()
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
    # Don't re-raise, allow the application to continue
