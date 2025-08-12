import subprocess
import re
import time
import os
from pathlib import Path

def get_localhost_run_url():
    """Start localhost.run tunnel and extract the URL"""
    print("Starting localhost.run tunnel...")
    
    # Start SSH tunnel in subprocess
    process = subprocess.Popen(
        ['ssh', '-R', '80:localhost:800', 'nokey@localhost.run'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )
    
    # Read output to find the URL
    url = None
    timeout = time.time() + 30  # 30 second timeout
    
    while time.time() < timeout:
        line = process.stdout.readline()
        if line:
            print(line.strip())
            
            # Look for the localhost.run URL
            match = re.search(r'https://[a-z0-9-]+\.localhost\.run', line)
            if match:
                url = match.group(0)
                print(f"\n✓ Found tunnel URL: {url}")
                break
    
    if not url:
        # Try stderr too
        for line in process.stderr:
            print(line.strip())
            match = re.search(r'https://[a-z0-9-]+\.localhost\.run', line)
            if match:
                url = match.group(0)
                print(f"\n✓ Found tunnel URL: {url}")
                break
    
    return url, process

def update_env_file(url):
    """Update the BASE_URL in .env file"""
    env_path = Path(__file__).parent / '.env'
    
    if not env_path.exists():
        print(f"ERROR: .env file not found at {env_path}")
        return False
    
    # Read current .env
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Update BASE_URL line
    updated = False
    for i, line in enumerate(lines):
        if line.startswith('BASE_URL='):
            lines[i] = f'BASE_URL={url}\n'
            updated = True
            break
    
    if not updated:
        # Add BASE_URL if not found
        lines.append(f'\nBASE_URL={url}\n')
    
    # Write back
    with open(env_path, 'w') as f:
        f.writelines(lines)
    
    print(f"✓ Updated BASE_URL in .env to: {url}")
    return True

def main():
    print("POW Reminder - Tunnel Setup")
    print("=" * 40)
    
    # Get the localhost.run URL
    url, process = get_localhost_run_url()
    
    if not url:
        print("\nERROR: Could not get localhost.run URL")
        print("Please run manually: ssh -R 80:localhost:800 nokey@localhost.run")
        return
    
    # Update .env file
    if update_env_file(url):
        print("\n" + "=" * 40)
        print("SUCCESS! Tunnel is running.")
        print(f"URL: {url}")
        print("\nNOTE: You need to restart the main app for the new URL to take effect.")
        print("Press Ctrl+C in the main app window and run start_app.bat again.")
        print("\nKEEP THIS WINDOW OPEN while using the app!")
        print("=" * 40)
        
        # Keep the tunnel running
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\nTunnel stopped.")
    else:
        print("\nERROR: Could not update .env file")
        process.terminate()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to exit...")