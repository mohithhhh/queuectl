from job_queue import get_config_value, set_config

def get(key: str, default=None):
    val = get_config_value(key)
    return val if val is not None else default

def set(key: str, value: str):
    set_config(key, value)
     
