import json
import jsonschema
import os
import typing


def load_config(content: typing.Optional[str] = None, file_path: typing.Optional[str] = None) -> dict:
    if content is None and file_path is None:
        # Nothing to load, return empty config.
        return {}

    if file_path is not None:
        try:
            with open(file_path) as f:
                content = f.read()
        except IOError:
            # Failed to load config from a given location, return empty config.
            return {}

    try:
        config = json.loads(content)
        with open(os.path.join(os.path.abspath(os.path.dirname(os.path.relpath(__file__))), 'config-schema.json')) as f:
            schema = json.loads(f.read())
        try:
            jsonschema.validate(config, schema)
        except jsonschema.ValidationError:
            # Given config is not conformant with the schema, return empty config.
            return {}
        return config
    except json.JSONDecodeError:
        # Given config is broken, return empty config.
        return {}


def store_config(config: dict, file_path: str) -> None:
    with open(file_path, 'w') as f:
        f.write(json.dumps(config, indent=2))
