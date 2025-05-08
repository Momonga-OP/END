import os
import sqlite3
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('init_db')

def create_fresh_database():
    """Create a fresh SQLite database with the required tables."""
    db_path = os.path.join(os.path.dirname(__file__), "guilds.db")
    
    # Remove the existing database file if it exists
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            logger.info(f"Removed existing database file: {db_path}")
        except Exception as e:
            logger.error(f"Failed to remove existing database file: {e}")
            return False
    
    # Create a new database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create guilds table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guilds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_name TEXT NOT NULL UNIQUE,
                emoji_id TEXT NOT NULL,
                role_id TEXT NOT NULL
            )
        """)
        
        # Create ping_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ping_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_name TEXT NOT NULL,
                author_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_name) REFERENCES guilds(guild_name)
            )
        """)
        
        # Create settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        # Add default settings
        cursor.execute("""
            INSERT INTO settings (key, value) VALUES ('ALERTS_CHANNEL_ID', '1247728738326679583')
        """)
        
        # Add sample guild data
        cursor.execute("""
            INSERT INTO guilds (guild_name, emoji_id, role_id) VALUES 
            ('DEF-GTO', '<:GTO:1307418692992237668>', '1300093554080612363')
        """)
        
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully created new database at {db_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        return False

if __name__ == "__main__":
    if create_fresh_database():
        print("Database initialization successful!")
    else:
        print("Database initialization failed!")
