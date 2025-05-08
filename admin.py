import argparse
import os
import sys
import logging
from dotenv import load_dotenv
from tabulate import tabulate
from database import (
    get_connection, 
    get_all_guilds, 
    add_guild, 
    update_guild, 
    delete_guild,
    get_setting,
    set_setting,
    get_ping_history
)

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('admin')

def list_guilds():
    """List all guilds in the database."""
    guilds = get_all_guilds()
    
    if not guilds:
        print("No guilds found in the database.")
        return
    
    # Format the data for tabulate
    headers = ["ID", "Guild Name", "Emoji", "Role ID"]
    table_data = [[guild[0], guild[1], guild[2], guild[3]] for guild in guilds]
    
    # Print the table
    print("\n=== Guilds ===")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print(f"Total: {len(guilds)} guilds")

def add_new_guild(guild_name, emoji_id, role_id):
    """Add a new guild to the database."""
    if add_guild(guild_name, emoji_id, role_id):
        print(f"Guild '{guild_name}' added successfully.")
    else:
        print(f"Failed to add guild '{guild_name}'.")

def modify_guild(guild_name, emoji_id=None, role_id=None):
    """Update an existing guild in the database."""
    if update_guild(guild_name, emoji_id, role_id):
        print(f"Guild '{guild_name}' updated successfully.")
    else:
        print(f"Failed to update guild '{guild_name}'.")

def remove_guild(guild_name):
    """Remove a guild from the database."""
    if delete_guild(guild_name):
        print(f"Guild '{guild_name}' deleted successfully.")
    else:
        print(f"Failed to delete guild '{guild_name}'.")

def list_settings():
    """List all settings in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM settings")
        settings = cursor.fetchall()
        
        if not settings:
            print("No settings found in the database.")
            return
        
        # Format the data for tabulate
        headers = ["Key", "Value"]
        table_data = [[setting[0], setting[1]] for setting in settings]
        
        # Print the table
        print("\n=== Settings ===")
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        print(f"Total: {len(settings)} settings")
    except Exception as e:
        print(f"Error listing settings: {e}")
    finally:
        conn.close()

def update_setting(key, value):
    """Update a setting in the database."""
    if set_setting(key, value):
        print(f"Setting '{key}' updated to '{value}'.")
    else:
        print(f"Failed to update setting '{key}'.")

def list_ping_history(guild_name=None, days=7):
    """List ping history for a guild."""
    if guild_name:
        records = get_ping_history(guild_name, days)
        
        if not records:
            print(f"No ping history found for guild '{guild_name}' in the last {days} days.")
            return
        
        # Format the data for tabulate
        headers = ["ID", "Guild Name", "Author ID", "Timestamp"]
        table_data = [[record[0], record[1], record[2], record[3]] for record in records]
        
        # Print the table
        print(f"\n=== Ping History for {guild_name} (Last {days} days) ===")
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        print(f"Total: {len(records)} pings")
    else:
        # Get all guild names
        guilds = get_all_guilds()
        if not guilds:
            print("No guilds found in the database.")
            return
            
        for guild in guilds:
            guild_name = guild[1]  # Guild name is at index 1
            records = get_ping_history(guild_name, days)
            
            if not records:
                print(f"No ping history found for guild '{guild_name}' in the last {days} days.")
                continue
            
            # Format the data for tabulate
            headers = ["ID", "Guild Name", "Author ID", "Timestamp"]
            table_data = [[record[0], record[1], record[2], record[3]] for record in records]
            
            # Print the table
            print(f"\n=== Ping History for {guild_name} (Last {days} days) ===")
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
            print(f"Total: {len(records)} pings")

def test_connection():
    """Test the database connection."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0] == 1:
            print("Database connection successful!")
            
            # Show connection details
            if os.getenv("DEV_MODE", "True").lower() in ("true", "1", "t"):
                print("Mode: Development (SQLite)")
                print(f"Database path: {os.path.join(os.path.dirname(__file__), 'guilds.db')}")
            else:
                print("Mode: Production (PostgreSQL)")
                db_url = os.getenv("DATABASE_URL", "")
                if db_url:
                    # Hide password in output
                    masked_url = db_url.replace("://", "://***:***@")
                    print(f"Database URL: {masked_url}")
                else:
                    print("Database URL not set in environment variables.")
        else:
            print("Database connection test failed.")
    except Exception as e:
        print(f"Error testing database connection: {e}")

def main():
    """Main function to parse arguments and execute commands."""
    parser = argparse.ArgumentParser(description="END Bot Database Administration Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Test connection command
    test_parser = subparsers.add_parser("test", help="Test database connection")
    
    # Guild commands
    guild_parser = subparsers.add_parser("guild", help="Guild management commands")
    guild_subparsers = guild_parser.add_subparsers(dest="guild_command", help="Guild command to execute")
    
    # List guilds
    list_guild_parser = guild_subparsers.add_parser("list", help="List all guilds")
    
    # Add guild
    add_guild_parser = guild_subparsers.add_parser("add", help="Add a new guild")
    add_guild_parser.add_argument("name", help="Guild name")
    add_guild_parser.add_argument("emoji", help="Guild emoji ID")
    add_guild_parser.add_argument("role_id", help="Guild role ID")
    
    # Update guild
    update_guild_parser = guild_subparsers.add_parser("update", help="Update an existing guild")
    update_guild_parser.add_argument("name", help="Guild name")
    update_guild_parser.add_argument("--emoji", help="New guild emoji ID")
    update_guild_parser.add_argument("--role_id", help="New guild role ID")
    
    # Delete guild
    delete_guild_parser = guild_subparsers.add_parser("delete", help="Delete a guild")
    delete_guild_parser.add_argument("name", help="Guild name")
    
    # Settings commands
    settings_parser = subparsers.add_parser("settings", help="Settings management commands")
    settings_subparsers = settings_parser.add_subparsers(dest="settings_command", help="Settings command to execute")
    
    # List settings
    list_settings_parser = settings_subparsers.add_parser("list", help="List all settings")
    
    # Update setting
    update_setting_parser = settings_subparsers.add_parser("update", help="Update a setting")
    update_setting_parser.add_argument("key", help="Setting key")
    update_setting_parser.add_argument("value", help="Setting value")
    
    # Ping history commands
    history_parser = subparsers.add_parser("history", help="Ping history commands")
    history_subparsers = history_parser.add_subparsers(dest="history_command", help="History command to execute")
    
    # List ping history
    list_history_parser = history_subparsers.add_parser("list", help="List ping history")
    list_history_parser.add_argument("--guild", help="Guild name (optional)")
    list_history_parser.add_argument("--days", type=int, default=7, help="Number of days to look back (default: 7)")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute commands
    if args.command == "test":
        test_connection()
    elif args.command == "guild":
        if args.guild_command == "list":
            list_guilds()
        elif args.guild_command == "add":
            add_new_guild(args.name, args.emoji, args.role_id)
        elif args.guild_command == "update":
            modify_guild(args.name, args.emoji, args.role_id)
        elif args.guild_command == "delete":
            remove_guild(args.name)
        else:
            guild_parser.print_help()
    elif args.command == "settings":
        if args.settings_command == "list":
            list_settings()
        elif args.settings_command == "update":
            update_setting(args.key, args.value)
        else:
            settings_parser.print_help()
    elif args.command == "history":
        if args.history_command == "list":
            list_ping_history(args.guild, args.days)
        else:
            history_parser.print_help()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
