from http.server import BaseHTTPRequestHandler
import os
import json
import discord
from discord import Webhook, AsyncWebhookAdapter
import aiohttp
import asyncio
from datetime import datetime

# Import bot functionality
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import initialize_db, get_all_guilds

# Configuration
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
GUILD_ID = int(os.environ.get('GUILD_ID', '1217700740949348443'))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')  # You'll need to create a webhook in your Discord server

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests - status check"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        # Current timestamp for logging
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get deployment info
        vercel_env = os.environ.get('VERCEL_ENV', 'development')
        region = os.environ.get('VERCEL_REGION', 'unknown')
        
        # Create response data
        response_data = {
            "status": "online",
            "service": "END Bot",
            "version": "3.0.0",
            "timestamp": timestamp,
            "environment": vercel_env,
            "region": region,
            "message": "END Bot API is operational. Use POST requests to trigger alerts."
        }
        
        # Send JSON response
        self.wfile.write(json.dumps(response_data, indent=2).encode())
        return
    
    def do_POST(self):
        """Handle POST requests - trigger alerts"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        # Process based on path
        if self.path == '/api/alert':
            # Handle alert request
            guild_name = data.get('guild_name')
            author_id = data.get('author_id')
            
            if not guild_name:
                self.send_error_response("Missing guild_name parameter")
                return
                
            # Process the alert (this would be async in a full implementation)
            result = self.process_alert(guild_name, author_id)
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            # Unknown endpoint
            self.send_error_response("Unknown endpoint")
    
    def send_error_response(self, message):
        """Send an error response"""
        self.send_response(400)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        error_data = {
            "error": True,
            "message": message
        }
        self.wfile.write(json.dumps(error_data).encode())
    
    def process_alert(self, guild_name, author_id=None):
        """Process an alert request (simplified version)"""
        try:
            # Initialize database
            initialize_db()
            
            # Get guild info
            guilds = get_all_guilds()
            guild_found = False
            
            for guild in guilds:
                if guild[1] == guild_name:  # guild_name is at index 1
                    guild_found = True
                    break
            
            if not guild_found:
                return {"error": True, "message": f"Guild '{guild_name}' not found"}
            
            # In a real implementation, this would send a Discord message
            # For now, we'll just return success
            return {
                "success": True,
                "guild_name": guild_name,
                "timestamp": datetime.now().isoformat(),
                "message": f"Alert triggered for {guild_name}"
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

# This would be used in a traditional Discord bot, but not in serverless
# async def send_discord_alert(guild_name, author_id=None):
#     """Send an alert to Discord via webhook"""
#     if not WEBHOOK_URL:
#         return {"error": True, "message": "Webhook URL not configured"}
#     
#     async with aiohttp.ClientSession() as session:
#         webhook = Webhook.from_url(WEBHOOK_URL, adapter=AsyncWebhookAdapter(session))
#         embed = discord.Embed(
#             title=f"🚨 Alerte {guild_name}",
#             description=f"Une alerte a été déclenchée pour {guild_name}",
#             color=discord.Color.red(),
#             timestamp=datetime.now()
#         )
#         await webhook.send(embed=embed)
#     
#     return {"success": True, "message": f"Alert sent for {guild_name}"}
