import os
import json
import subprocess
import sys

CONFIG_DIR = os.path.expanduser("~/.gh-sub")
PROFILES_FILE = os.path.join(CONFIG_DIR, "profiles.json")

def initialize():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    if not os.path.exists(PROFILES_FILE):
        with open(PROFILES_FILE, "w") as f:
            json.dump({"profiles": {}}, f, indent=2)

def load_profiles():
    initialize()
    with open(PROFILES_FILE, "r") as f:
        return json.load(f)

def save_profiles(data):
    with open(PROFILES_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_git_remote_url():
    try:
        url = subprocess.check_output(["git", "remote", "get-url", "origin"]).decode("utf-8").strip()
        return url
    except Exception:
        return None

def set_git_config(name, email, ssh_host):
    try:
        subprocess.check_call(["git", "config", "user.name", name])
        subprocess.check_call(["git", "config", "user.email", email])
        
        current_url = get_git_remote_url()
        if current_url:
            # git@github.com:owner/repo.git or git@github.com-alias:owner/repo.git
            if ":" in current_url:
                parts = current_url.split(":")
                repo_path = parts[1]
                new_url = f"git@{ssh_host}:{repo_path}"
                subprocess.check_call(["git", "remote", "set-url", "origin", new_url])
        return True
    except Exception as e:
        print(f"Error updating git config: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: gh-sub <command> [args]")
        sys.exit(1)
        
    cmd = sys.argv[1]
    
    if cmd == "list":
        data = load_profiles()
        profiles = data.get("profiles", {})
        if not profiles:
            print("No profiles found.")
        else:
            print("Available Git Profiles:")
            for p_id, info in profiles.items():
                print(f"- {p_id}: {info['user_name']} <{info['user_email']}> (SSH: {info.get('ssh_host', 'default')})")
                
    elif cmd == "add":
        if len(sys.argv) != 6:
            print("Usage: gh-sub add <id> <name> <email> <ssh_host>")
            sys.exit(1)
        p_id, name, email, ssh_host = sys.argv[2:]
        data = load_profiles()
        data["profiles"][p_id] = {
            "user_name": name,
            "user_email": email,
            "ssh_host": ssh_host
        }
        save_profiles(data)
        print(f"Profile '{p_id}' added successfully.")
        
    elif cmd == "switch":
        if len(sys.argv) != 3:
            print("Usage: gh-sub switch <id>")
            sys.exit(1)
        p_id = sys.argv[2]
        data = load_profiles()
        profile = data.get("profiles", {}).get(p_id)
        if not profile:
            print(f"Profile '{p_id}' not found.")
            sys.exit(1)
        
        if set_git_config(profile["user_name"], profile["user_email"], profile["ssh_host"]):
            print(f"Switched repository identity to '{p_id}'.")
        else:
            sys.exit(1)
            
    elif cmd == "status":
        try:
            name = subprocess.check_output(["git", "config", "user.name"]).decode("utf-8").strip()
            email = subprocess.check_output(["git", "config", "user.email"]).decode("utf-8").strip()
            url = get_git_remote_url()
            print(f"Current Identity: {name} <{email}>")
            print(f"Remote URL: {url}")
        except Exception:
            print("Not inside a git repository or no config found.")

if __name__ == "__main__":
    main()
