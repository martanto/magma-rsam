import os
from typing import List


directory_structures: list[str] = ['sds', 'seisan']


def validate_matrices(matrices: List[str]) -> bool | ValueError:
    default_matrices: List[str] = ['min', 'mean', 'max', 'median', 'std']
    for metric in matrices:
        if metric not in default_matrices:
            raise ValueError(f"Metric {metric} is not valid. Please use one of {default_matrices}")
    return True


def validate_directory_structure(directory_structure: str) -> bool | ValueError:
    if directory_structure not in directory_structures:
        raise ValueError(f"Directory structure {directory_structure} is not valid. "
                         f"Please use one of {directory_structures}")
    return True


def validate_directory(directory: str) -> bool | ValueError:
    if not os.path.isdir(directory):
        raise ValueError(f"Directory {directory} is not valid. ")
    return True

