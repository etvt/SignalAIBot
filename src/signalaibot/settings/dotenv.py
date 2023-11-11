def dotenv_values(file_path: str) -> dict[str, str]:
    env_vars = {}
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith(';'):
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    return env_vars
