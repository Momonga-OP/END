from http.server import BaseHTTPRequestHandler
import os
import json
from datetime import datetime

# Import bot functionality
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
GUILD_ID = int(os.environ.get('GUILD_ID', '1217700740949348443'))

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
            "message": "END Bot API is operational. This is a lightweight endpoint for Vercel deployment."
        }
        
        # Send JSON response
        self.wfile.write(json.dumps(response_data, indent=2).encode())
        return

# End of file
