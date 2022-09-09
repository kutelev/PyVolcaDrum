import os
import typing

__all__ = [
    'root_directory_path',
    'resources_directory_path',
    'config_path',
    'check_int_value',
]

root_directory_path = os.path.abspath(os.path.dirname(os.path.relpath(__file__)))
resources_directory_path = os.path.join(root_directory_path, '..', 'resources')
config_path = os.path.join(root_directory_path, '..', 'config.json')


def check_int_value(name: str, value: int, min_value: typing.Optional[int] = None, max_value: typing.Optional[int] = None) -> None:
    assert min_value is None or isinstance(min_value, int)
    assert max_value is None or isinstance(max_value, int)
    if not isinstance(value, int):
        raise TypeError(f'{name} must be of type int')
    if min_value is not None and max_value is not None:
        if not min_value <= value <= max_value:
            raise ValueError(f'{name} must be in the range from {min_value} to {max_value}')
    elif min_value is not None:
        if value < min_value:
            raise ValueError(f'{name} must be greater or equal to {min_value}')
    elif max_value is not None:
        if value > max_value:
            raise ValueError(f'{name} must be less or equal to {max_value}')


def check_bool_value(name: str, value: bool) -> None:
    if not isinstance(value, int):
        raise TypeError(f'{name} must be of type bool')
