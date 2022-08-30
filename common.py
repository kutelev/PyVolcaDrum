import os

__all__ = [
    'root_directory_path',
    'resources_directory_path',
    'config_path',
    'check_int_value',
]

root_directory_path = os.path.abspath(os.path.dirname(os.path.relpath(__file__)))
resources_directory_path = os.path.join(root_directory_path, 'resources')
config_path = os.path.join(root_directory_path, 'config.json')


def check_int_value(name: str, value: int, min_value: int, max_value: int) -> None:
    if not isinstance(value, int):
        raise TypeError(f'{name} must be of type int')
    if not min_value <= value <= max_value:
        raise TypeError(f'{name} must in the range from {min_value} to {max_value}')
