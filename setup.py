"""Setuptools configuration.
Attributes:
    REQUIREMENT_LINE_REGEX (re.Pattern): Requirement line regular expression pattern.
.. _Building and Distributing Packages with Setuptools:
    https://setuptools.pypa.io/en/latest/setuptools.html
"""
import os
import re
from typing import List

from setuptools import setup

# Groups "pkg<=x.y.z,..." into ("pkg", "<=x.y.z,...").
REQUIREMENT_LINE_REGEX = re.compile(r'([a-zA-Z0-9-_.]+)([<>=][^#\s]+)?')

def load_requirements(*requirements_paths: str) -> List[str]:
    """
    Load requirements.
    Args:
        *requirements_paths: List of requirement file paths.
    Returns:
        list: A list of package requirement strings.
    Attributes:
        requirements (dict): Dictionary with requirements.
        constraints_files (set): Set of constraints files paths.
    """
    requirements = {}
    constraints_files = set()


    def is_requirement(line: str) -> bool:
        """Check if line is a package requirement.
        Args:
            line: Requirements file line.
        Returns:
            bool: True if the line is not blank, a comment, a URL, or an included file.
        """
        return line and line.strip() and not line.startswith(('-r', '#', '-e', 'git+', '-c'))


    def is_constraints_file(line: str) -> bool:
        """Check if line is a constraints file path.
        Args:
            line: Requirements file line.
        Returns:
            bool: True if the string is not blank, starts with `-c` and not with `-c http`.
        .. _pip-tools documentation: Workflow for layered requirements
            https://pip-tools.readthedocs.io/en/stable/#workflow-for-layered-requirements
        """
        return line and line.startswith('-c') and not line.startswith('-c http')


    def raise_constraint_duplicate(
        requirements: dict,
        package: str,
        constraint: str,
    ):
        """Raise `Exception` if constraint definition is duplicated.
        Args:
            requirements: Dictionary with requirements.
            package: Package name.
            constraint: Package constraint.
        Raises:
            Exception: If duplicate constraint definition is found.
        """
        existing_constraint = requirements.get(package, '')

        if existing_constraint and existing_constraint != constraint:
            raise Exception(  # pylint: disable=broad-exception-raised
                f'Multiple constraint definitions found for {package}:'
                f' "{existing_constraint}" and "{existing_constraint}".'
                f'Combine constraints into one location with {package}'
                f'{existing_constraint},{existing_constraint}.',
            )


    def read_requirements_line(
        path: str,
        line: str,
        always_add_constraint: bool = True,
    ):
        """Read requirements file line.
        Args:
            path: Requirements file path.
            line: Requirements file line.
            always_add_constraint: Always add package constraint
                even if the package is not found in `requirements`.
        """
        # Store line into constraints file list.
        if is_constraints_file(line):
            constraints_files.add(
                f'{os.path.dirname(path)}/'
                f"{line.split('#')[0].replace('-c', '').strip()}",
            )
            return

        # Ignore if line is not a requirement.
        if not is_requirement(line):
            return

        match = REQUIREMENT_LINE_REGEX.match(line)

        # Ignore if line doesn't match requirement regex.
        if not match:
            return

        package = match.group(1)
        constraint = match.group(2)
        raise_constraint_duplicate(requirements, package, constraint)

        # Add package constraint if package is in requirements dictionary
        # or the constraint must be added even is is not found.
        if package in requirements or always_add_constraint:
            requirements[package] = constraint

        return


    # Read each requirement from all requirements.txt files.
    for path in requirements_paths:
        with open(path, encoding='utf-8') as file:
            for line in file:
                read_requirements_line(path, line)

    # Read each constraint from all constraints.txt files.
    for path in constraints_files:
        with open(path, encoding='utf-8') as file:
            for line in file:
                read_requirements_line(path, line, False)

    # Transform requirements into list of `pkg><=constraints` strings.
    return [
        f'{package}{version or ""}'
        for (package, version) in sorted(requirements.items())
    ]


setup(install_requires=load_requirements('requirements/base.in'))
