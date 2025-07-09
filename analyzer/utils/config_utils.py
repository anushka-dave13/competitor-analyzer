import os
import json

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'keywords_config.json')
CONFIG_PATH = os.path.abspath(CONFIG_PATH)

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)

def get_buckets(config):
    return {k: v for k, v in config.items() if not k.startswith("_")}
