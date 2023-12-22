""" Helper functions or classes for various functionality
"""
import json
import __main__


def parse_tunnels_from_file(filename, format_type='json'):
    with open(f'{__main__.CONFIG_PATH}/{filename}') as file:
        json_data = json.load(file)
        return json_data['results']
