import os
from datetime import date
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


def validate_dates(start_date: str, end_date: str) -> bool | ValueError:
    try:
        start_date = date.fromisoformat(start_date)
        end_date = date.fromisoformat(end_date)
    except ValueError:
        raise ValueError(f"❌ start_date or end_date has invalid format. Should be yyyy-mm-dd.")

    if start_date > end_date:
        raise ValueError(f"❌ start_date should be before end_date. Or end_date must before start_date.")

    return True
