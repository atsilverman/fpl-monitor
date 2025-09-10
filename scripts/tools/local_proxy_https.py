#!/usr/bin/env python3
"""
HTTPS local proxy server to forward iOS Simulator requests to production backend
This solves the ATS issue by providing HTTPS locally
"""

import http.server
import socketserver
import urllib.request
import urllib.parse
import json
import ssl
from urllib.error import URLError

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    PRODUCTION_URL = "http://138.68.28.59:8000"
    
    def do_GET(self):
        try:
            # Forward request to production server
            target_url = f"{self.PRODUCTION_URL}{self.path}"
            print(f"Forwarding: {self.path} -> {target_url}")
            
            with urllib.request.urlopen(target_url) as response:
                data = response.read()
                
                # Send response back to iOS app
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(data)
                
        except URLError as e:
            print(f"Error forwarding request: {e}")
            self.send_error(500, f"Proxy error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
            self.send_error(500, f"Unexpected error: {e}")
    
    def do_POST(self):
        # Handle POST requests if needed
        self.do_GET()
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

if __name__ == "__main__":
    PORT = 8443  # HTTPS port
    print(f"Starting HTTPS local proxy on port {PORT}")
    print(f"Forwarding requests to: {ProxyHandler.PRODUCTION_URL}")
    print("iOS app should now connect to localhost:8443")
    
    with socketserver.TCPServer(("", PORT), ProxyHandler) as httpd:
        # Create SSL context
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain('localhost.pem', 'localhost-key.pem')
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nProxy server stopped")
