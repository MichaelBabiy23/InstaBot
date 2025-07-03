import yaml
import json
import os


CONFIG_FILE = "accounts/michael.babiy1/follow_any.yml"
INTERACTED_USERS_FILE = "accounts/michael.babiy1/interacted_users.json"


def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return yaml.safe_load(f)


def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        yaml.safe_dump(config, f,
                      sort_keys=False,
                      default_flow_style=True)


def load_interacted_users():
    if not os.path.exists(INTERACTED_USERS_FILE):
        return {}
    with open(INTERACTED_USERS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def load_scraped_users(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        users = [line.strip() for line in f if line.strip()]
    return users


def update_blogger_followers(scraped_file=None):
    config = load_config()
    interacted_users = load_interacted_users()

    current_followers = config.get('actions', {}).get('blogger-followers', [])
    updated_followers = []

    # Filter out users who have been followed or unfollowed
    for user in current_followers:
        if (
            user not in interacted_users
            or (
                interacted_users[user].get('following_status') != 'followed'
                and interacted_users[user].get('following_status') != 'unfollowed'
            )
        ):
            updated_followers.append(user)

    # Add newly scraped users
    if scraped_file:
        new_scraped_users = load_scraped_users(scraped_file)
        for user in new_scraped_users:
            if user not in updated_followers:
                updated_followers.append(user)

    if 'actions' not in config:
        config['actions'] = {}
    config['actions']['blogger-followers'] = updated_followers

    save_config(config)
    print(f"Updated {CONFIG_FILE}'s blogger-followers list.")


if __name__ == "__main__":
    # When running directly, you might call it with a specific scraped file
    # For example: python3 manage_sources.py scraped_high_follower_users.txt
    import sys
    scraped_file_arg = sys.argv[1] if len(sys.argv) > 1 else None
    update_blogger_followers(scraped_file_arg) 