import re
from typing import List
from re import Pattern

def re_compile_patterns(kv_dict, list_keys):
    for key,dict_value in kv_dict.items():
        for key_name in list_keys:
            if key_name in dict_value and dict_value[key_name]:
                compiled = []
                for exp in dict_value[key_name]:
                    x = re.compile(exp)
                    compiled.append(x)
                dict_value[key_name] = compiled

def any_pattern_matches(patterns:List[Pattern], value:str):
    if patterns and len(patterns) > 0:
        for p in patterns:
            if p.match(value):
                return True

    return False


def find_config(config_map:dict, to_match) -> dict: 
    for conf_name, config in config_map.items():

        if "excludes" in config and any_pattern_matches(config["excludes"],to_match):
            continue
        if "includes" in config and any_pattern_matches(config["includes"],to_match):
            return config

def get_relative_recordset_name(name:str, zone_name:str):
    hostname = name.replace(zone_name,'').replace('*','').strip('.')
    if hostname:
        hostname = f".{hostname}"
    return f"_acme-challenge{hostname}"
