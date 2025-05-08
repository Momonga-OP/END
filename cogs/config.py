import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
GUILD_ID = int(os.getenv('GUILD_ID', '1300093554064097400'))
PING_DEF_CHANNEL_ID = int(os.getenv('PING_DEF_CHANNEL_ID', '1307429490158342256'))
ALERTE_DEF_CHANNEL_ID = int(os.getenv('ALERTE_DEF_CHANNEL_ID', '1300093554399645715'))

# Test button configuration
TEST_BUTTON_ID = int(os.getenv('TEST_BUTTON_ID', '486652069831376943'))

# French alert messages
ALERT_MESSAGES = [
    "🚨 {role} go def zebi !",
    "⚔️ {role}, il est temps de défendre !",
    "🛡️ {role} Défendez votre guilde !",
    "💥 {role} est attaquée ! Rejoignez la défense !",
    "⚠️ {role}, mobilisez votre équipe pour défendre !",
    "🏹 Appel urgent pour {role} - La défense a besoin de vous !",
    "🔔 {role}, votre présence est cruciale pour la défense !",
]

# Guild emojis and roles will be loaded from database
# This is kept as a fallback in case database connection fails
DEFAULT_GUILD_EMOJIS_ROLES = {
    "GTO": {"emoji": "<:GTO:1307418692992237668>", "role_id": 1300093554080612363},
    "MERCENAIRES": {"emoji": "<:lmdf:1307418765142786179>", "role_id": 1300093554080612364},
    "Notorious": {"emoji": "<:notorious:1307418766266728500>", "role_id": 1300093554064097406},
    "Percophile": {"emoji": "<:percophile:1307418769764651228>", "role_id": 1300093554080612362},
    "Nightmare": {"emoji": "<:Nightmare:1342131008987730064>", "role_id": 1300093554080612367},
    "Crescent": {"emoji": "<:Crescent:1328374098262495232>", "role_id": 1300093554064097404},
    "Academie": {"emoji": "<:Academie:1333147586986774739>", "role_id": 1300093554080612365},
}

# This will be populated from the database
GUILD_EMOJIS_ROLES = {}

# Function to load guild data from database
def load_guild_data_from_db():
    """Load guild data from database and populate GUILD_EMOJIS_ROLES"""
    from database import get_all_guilds
    
    try:
        guilds = get_all_guilds()
        if guilds:
            for guild in guilds:
                # guild format: (id, guild_name, emoji_id, role_id)
                guild_name = guild[1]
                emoji_id = guild[2]
                role_id = int(guild[3])
                GUILD_EMOJIS_ROLES[guild_name] = {"emoji": emoji_id, "role_id": role_id}
        else:
            # If no guilds in database, use defaults
            global GUILD_EMOJIS_ROLES
            GUILD_EMOJIS_ROLES = DEFAULT_GUILD_EMOJIS_ROLES.copy()
    except Exception as e:
        print(f"Error loading guild data from database: {e}")
        # Fallback to default values
        global GUILD_EMOJIS_ROLES
        GUILD_EMOJIS_ROLES = DEFAULT_GUILD_EMOJIS_ROLES.copy()
