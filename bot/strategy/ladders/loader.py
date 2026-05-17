import yaml

def load_ladder(path: str):
    with open(path, "r") as f:
        return yaml.safe_load(f)
