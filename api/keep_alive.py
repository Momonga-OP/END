from http.server import BaseHTTPRequestHandler
from datetime import datetime
import json
import os

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
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
            "message": "END Bot is operational. This endpoint can be used with external uptime monitoring services."
        }
        
        # Send JSON response
        self.wfile.write(json.dumps(response_data, indent=2).encode())
        return
