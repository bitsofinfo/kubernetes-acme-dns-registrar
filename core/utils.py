import re

def re_compile_patterns(kv_dict, list_keys):
    for key,dict_value in kv_dict.items():
        for key_name in list_keys:
            if key_name in dict_value and dict_value[key_name]:
                compiled = []
                for exp in dict_value[key_name]:
                    compiled.append(re.compile(exp))
                dict_value[key_name] = compiled
