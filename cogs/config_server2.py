import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
GUILD_ID = int(os.getenv('GUILD_ID', '1270112417921368238'))
PING_DEF_CHANNEL_ID = int(os.getenv('PING_DEF_CHANNEL_ID', '1375438298347995167'))
ALERTE_DEF_CHANNEL_ID = int(os.getenv('ALERTE_DEF_CHANNEL_ID', '1328087892266057778'))

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
    "GTO": {"emoji": "<:GTO:1270112417967243390>", "role_id": 1374691706473152614},
    "NOTORIOUS": {"emoji": "<:NOTORIOUS:1270112417938018331>", "role_id": 1374691693311295568},
    "Crescent": {"emoji": "<:Crescent:1270112417938018333>", "role_id": 1374691707567865937},
    "Jungle Diff": {"emoji": "<:JungleDiff:1270112417938018328>", "role_id": 1374691704749293600},
    "Mercenaires": {"emoji": "<:Mercenaires:1270112417967243394>", "role_id": 1374691703079964703},
    "Nomea": {"emoji": "<:Nomea:1270112417967243392>", "role_id": 1374691695811100693},
    "The Mortal Sworld": {"emoji": "<:MortalSworld:1270112417967243386>", "role_id": 1374691700689338450},
    "Naga": {"emoji": "<:Naga:1270112417967243395>", "role_id": 1374691697199419442},
    "Triade": {"emoji": "<:Triade:1270112417938018330>", "role_id": 1374691690308309052},
    "Universe": {"emoji": "<:Universe:1270112417967243389>", "role_id": 1374691687380684821},
    "Warrior Élite": {"emoji": "<:WarriorElite:1270112417967243393>", "role_id": 1374691686029983816},
    "Warriors Toxic": {"emoji": "<:WarriorsToxic:1270112417988345856>", "role_id": 1374691709115564042},
    "Monark": {"emoji": "<:Monark:1270112417967243391>", "role_id": 1374691702039646268},
    "Triade II": {"emoji": "<:TriadeII:1270112417938018329>", "role_id": 1374691688676855831},
    "RED END": {"emoji": "<:REDEND:1270112417938018327>", "role_id": 1374691691965186171},
    "Ennemi Public": {"emoji": "<:EnnemiPublic:1270112417938018332>", "role_id": 1374691704749293600},
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
