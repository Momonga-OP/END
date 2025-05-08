import os
import sys
import sqlite3
import logging
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('migration.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('migration')

def get_sqlite_connection():
    """Get a connection to the SQLite database."""
    sqlite_path = os.path.join(os.path.dirname(__file__), "guilds.db")
    return sqlite3.connect(sqlite_path)

def get_postgres_connection():
    """Get a connection to the PostgreSQL database."""
    try:
        import psycopg2
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.error("DATABASE_URL environment variable not set")
            return None
        return psycopg2.connect(database_url)
    except ImportError:
        logger.error("psycopg2 not installed. Please install it with: pip install psycopg2-binary")
        return None
    except Exception as e:
        logger.error(f"Error connecting to PostgreSQL: {e}")
        return None

def migrate_guilds(dry_run=False):
    """Migrate guilds from SQLite to PostgreSQL."""
    # Connect to SQLite
    sqlite_conn = get_sqlite_connection()
    sqlite_cursor = sqlite_conn.cursor()
    
    # Connect to PostgreSQL
    postgres_conn = get_postgres_connection()
    if not postgres_conn:
        logger.error("Failed to connect to PostgreSQL. Migration aborted.")
        return False
    
    postgres_cursor = postgres_conn.cursor()
    
    try:
        # Get guilds from SQLite
        sqlite_cursor.execute("SELECT guild_name, emoji_id, role_id FROM guilds")
        guilds = sqlite_cursor.fetchall()
        
        if not guilds:
            logger.info("No guilds found in SQLite database.")
            return True
        
        logger.info(f"Found {len(guilds)} guilds in SQLite database.")
        
        # Migrate each guild
        for guild in guilds:
            guild_name, emoji_id, role_id = guild
            
            if dry_run:
                logger.info(f"[DRY RUN] Would migrate guild: {guild_name}")
                continue
            
            # Check if guild already exists in PostgreSQL
            postgres_cursor.execute("SELECT COUNT(*) FROM guilds WHERE guild_name = %s", (guild_name,))
            count = postgres_cursor.fetchone()[0]
            
            if count > 0:
                logger.info(f"Guild '{guild_name}' already exists in PostgreSQL. Skipping.")
                continue
            
            # Insert guild into PostgreSQL
            postgres_cursor.execute(
                "INSERT INTO guilds (guild_name, emoji_id, role_id) VALUES (%s, %s, %s)",
                (guild_name, emoji_id, role_id)
            )
            logger.info(f"Migrated guild: {guild_name}")
        
        # Commit changes
        if not dry_run:
            postgres_conn.commit()
            logger.info("Guild migration completed successfully.")
        else:
            logger.info("[DRY RUN] No changes were made to the PostgreSQL database.")
        
        return True
    except Exception as e:
        logger.error(f"Error during guild migration: {e}")
        if not dry_run:
            postgres_conn.rollback()
        return False
    finally:
        sqlite_conn.close()
        postgres_conn.close()

def migrate_ping_history(dry_run=False):
    """Migrate ping history from SQLite to PostgreSQL."""
    # Connect to SQLite
    sqlite_conn = get_sqlite_connection()
    sqlite_cursor = sqlite_conn.cursor()
    
    # Connect to PostgreSQL
    postgres_conn = get_postgres_connection()
    if not postgres_conn:
        logger.error("Failed to connect to PostgreSQL. Migration aborted.")
        return False
    
    postgres_cursor = postgres_conn.cursor()
    
    try:
        # Check if ping_history table exists in SQLite
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ping_history'")
        if not sqlite_cursor.fetchone():
            logger.info("ping_history table does not exist in SQLite database.")
            return True
        
        # Get ping history from SQLite
        sqlite_cursor.execute("SELECT guild_name, author_id, timestamp FROM ping_history")
        records = sqlite_cursor.fetchall()
        
        if not records:
            logger.info("No ping history found in SQLite database.")
            return True
        
        logger.info(f"Found {len(records)} ping history records in SQLite database.")
        
        # Migrate each record
        for record in records:
            guild_name, author_id, timestamp = record
            
            if dry_run:
                logger.info(f"[DRY RUN] Would migrate ping record: {guild_name}, {author_id}, {timestamp}")
                continue
            
            # Insert record into PostgreSQL
            postgres_cursor.execute(
                "INSERT INTO ping_history (guild_name, author_id, timestamp) VALUES (%s, %s, %s)",
                (guild_name, author_id, timestamp)
            )
            
        # Commit changes
        if not dry_run:
            postgres_conn.commit()
            logger.info("Ping history migration completed successfully.")
        else:
            logger.info("[DRY RUN] No changes were made to the PostgreSQL database.")
        
        return True
    except Exception as e:
        logger.error(f"Error during ping history migration: {e}")
        if not dry_run:
            postgres_conn.rollback()
        return False
    finally:
        sqlite_conn.close()
        postgres_conn.close()

def migrate_settings(dry_run=False):
    """Migrate settings from SQLite to PostgreSQL."""
    # Connect to SQLite
    sqlite_conn = get_sqlite_connection()
    sqlite_cursor = sqlite_conn.cursor()
    
    # Connect to PostgreSQL
    postgres_conn = get_postgres_connection()
    if not postgres_conn:
        logger.error("Failed to connect to PostgreSQL. Migration aborted.")
        return False
    
    postgres_cursor = postgres_conn.cursor()
    
    try:
        # Check if settings table exists in SQLite
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
        if not sqlite_cursor.fetchone():
            logger.info("settings table does not exist in SQLite database.")
            return True
        
        # Get settings from SQLite
        sqlite_cursor.execute("SELECT key, value FROM settings")
        settings = sqlite_cursor.fetchall()
        
        if not settings:
            logger.info("No settings found in SQLite database.")
            return True
        
        logger.info(f"Found {len(settings)} settings in SQLite database.")
        
        # Migrate each setting
        for setting in settings:
            key, value = setting
            
            if dry_run:
                logger.info(f"[DRY RUN] Would migrate setting: {key}={value}")
                continue
            
            # Check if setting already exists in PostgreSQL
            postgres_cursor.execute("SELECT COUNT(*) FROM settings WHERE key = %s", (key,))
            count = postgres_cursor.fetchone()[0]
            
            if count > 0:
                # Update existing setting
                postgres_cursor.execute(
                    "UPDATE settings SET value = %s WHERE key = %s",
                    (value, key)
                )
                logger.info(f"Updated setting: {key}")
            else:
                # Insert new setting
                postgres_cursor.execute(
                    "INSERT INTO settings (key, value) VALUES (%s, %s)",
                    (key, value)
                )
                logger.info(f"Migrated setting: {key}")
        
        # Commit changes
        if not dry_run:
            postgres_conn.commit()
            logger.info("Settings migration completed successfully.")
        else:
            logger.info("[DRY RUN] No changes were made to the PostgreSQL database.")
        
        return True
    except Exception as e:
        logger.error(f"Error during settings migration: {e}")
        if not dry_run:
            postgres_conn.rollback()
        return False
    finally:
        sqlite_conn.close()
        postgres_conn.close()

def main():
    """Main function to parse arguments and execute migration."""
    parser = argparse.ArgumentParser(description="Migrate data from SQLite to PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without making changes")
    parser.add_argument("--guilds-only", action="store_true", help="Migrate only guilds")
    parser.add_argument("--history-only", action="store_true", help="Migrate only ping history")
    parser.add_argument("--settings-only", action="store_true", help="Migrate only settings")
    
    args = parser.parse_args()
    
    # Check if PostgreSQL connection is available
    postgres_conn = get_postgres_connection()
    if not postgres_conn:
        logger.error("Failed to connect to PostgreSQL. Migration aborted.")
        return
    postgres_conn.close()
    
    # Determine what to migrate
    migrate_all = not (args.guilds_only or args.history_only or args.settings_only)
    
    if migrate_all or args.guilds_only:
        logger.info("Starting guild migration...")
        if migrate_guilds(args.dry_run):
            logger.info("Guild migration completed.")
        else:
            logger.error("Guild migration failed.")
    
    if migrate_all or args.history_only:
        logger.info("Starting ping history migration...")
        if migrate_ping_history(args.dry_run):
            logger.info("Ping history migration completed.")
        else:
            logger.error("Ping history migration failed.")
    
    if migrate_all or args.settings_only:
        logger.info("Starting settings migration...")
        if migrate_settings(args.dry_run):
            logger.info("Settings migration completed.")
        else:
            logger.error("Settings migration failed.")
    
    logger.info("Migration process finished.")

if __name__ == "__main__":
    main()
