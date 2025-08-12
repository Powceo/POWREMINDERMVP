import subprocess
import threading
import re
import time
import os
from pathlib import Path

class TunnelManager:
    def __init__(self):
        self.url = None
        self.process = None
        
    def start_tunnel(self):
        """Start localhost.run tunnel in background"""
        print("Starting localhost.run tunnel...")
        
        def run_tunnel():
            self.process = subprocess.Popen(
                ['ssh', '-o', 'StrictHostKeyChecking=no', '-R', '80:localhost:800', 'nokey@localhost.run'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            for line in self.process.stdout:
                print(f"[Tunnel] {line.strip()}")
                
                # Look for the URL
                match = re.search(r'https://[a-z0-9-]+\.localhost\.run', line)
                if match and not self.url:
                    self.url = match.group(0)
                    print(f"\n✓ Tunnel established: {self.url}\n")
                    self.update_env_file()
        
        # Start tunnel in background thread
        tunnel_thread = threading.Thread(target=run_tunnel)
        tunnel_thread.daemon = True
        tunnel_thread.start()
        
        # Wait for URL to be detected
        timeout = time.time() + 30
        while not self.url and time.time() < timeout:
            time.sleep(1)
        
        if not self.url:
            print("ERROR: Could not establish tunnel")
            return False
        
        return True
    
    def update_env_file(self):
        """Update BASE_URL in .env automatically"""
        env_path = Path(__file__).parent / '.env'
        
        # Read current .env
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        # Update BASE_URL
        updated = False
        for i, line in enumerate(lines):
            if line.startswith('BASE_URL='):
                lines[i] = f'BASE_URL={self.url}\n'
                updated = True
                break
        
        if not updated:
            lines.append(f'\nBASE_URL={self.url}\n')
        
        # Write back
        with open(env_path, 'w') as f:
            f.writelines(lines)
        
        print(f"✓ Updated BASE_URL to: {self.url}")
    
    def stop_tunnel(self):
        """Stop the tunnel"""
        if self.process:
            self.process.terminate()
            print("Tunnel stopped")

# Global tunnel manager
tunnel_manager = TunnelManager()

def start_tunnel_service():
    """Start tunnel service - call this from main.py"""
    return tunnel_manager.start_tunnel()

if __name__ == "__main__":
    # Test the tunnel
    if tunnel_manager.start_tunnel():
        print("\nTunnel is running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            tunnel_manager.stop_tunnel()