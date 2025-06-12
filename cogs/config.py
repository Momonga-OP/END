import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
GUILD_ID = int(os.getenv('GUILD_ID', '1263938704670593085'))
PING_DEF_CHANNEL_ID = int(os.getenv('PING_DEF_CHANNEL_ID', '1369382571363930174'))
ALERTE_DEF_CHANNEL_ID = int(os.getenv('ALERTE_DEF_CHANNEL_ID', '1264140175395655712'))

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
    "GTO": {"emoji": "<:GTO:1358125135814463739>", "role_id": 1350869727551164416},
    "NOTORIOUS": {"emoji": "<:NOTORIOUS:1306689408526848041>", "role_id": 1350870052429238377},
    "Crescent": {"emoji": "<:Crescent:1306689408526848041>", "role_id": 1348444561802006658},
    "Jungle gap": {"emoji": "<:JungleGap:1306689440881840178>", "role_id": 1265060172607525028},
    "Nomea": {"emoji": "<:Nomea:1306689555717558322>", "role_id": 1284258627196162179},
    "MS Mafia": {"emoji": "<:MSMafia:1306689457898000516>", "role_id": 1264990097863086080},
    "Prism": {"emoji": "<:Prism:1382514856002982049>", "role_id": 1264133637729943625},
    "HONORIS": {"emoji": "<:HONORIS:1382403651594752010>", "role_id": 1372318425405329571},
    "Triade": {"emoji": "<:Triade:1306689570334834728>", "role_id": 1264843747456188456},
    "Universe": {"emoji": "<:Universe:1306689599929712812>", "role_id": 1264141015514873886},
    "Warrior Elite": {"emoji": "<:WarriorElite:1306689667726311455>", "role_id": 1306699042763309179},
    "Warriors Toxic": {"emoji": "<:WarriorsToxic:1306689680535720007>", "role_id": 1264141342154686534},
    "Monark": {"emoji": "<:Monark:1306689408526848041>", "role_id": 1332465195452207183},
    "RED END": {"emoji": "<:REDEND:1306689408526848041>", "role_id": 1367513954187739187},
}

# This will be populated from the database
GUILD_EMOJIS_ROLES = {}

# Function to load guild data from database
def load_guild_data_from_db():
    """Load guild data from database and populate GUILD_EMOJIS_ROLES"""
    from database import get_all_guilds
    
    # Declare global variable at the beginning of the function
    global GUILD_EMOJIS_ROLES
    
    try:
        guilds = get_all_guilds()
        if guilds:
            # Clear existing data and start fresh
            GUILD_EMOJIS_ROLES = {}
            for guild in guilds:
                # guild format: (id, guild_name, emoji_id, role_id)
                guild_name = guild[1]
                emoji_id = guild[2]
                role_id = int(guild[3])
                GUILD_EMOJIS_ROLES[guild_name] = {"emoji": emoji_id, "role_id": role_id}
        else:
            # If no guilds in database, use defaults
            GUILD_EMOJIS_ROLES = DEFAULT_GUILD_EMOJIS_ROLES.copy()
    except Exception as e:
        print(f"Error loading guild data from database: {e}")
        # Fallback to default values
        GUILD_EMOJIS_ROLES = DEFAULT_GUILD_EMOJIS_ROLES.copy()
