"""
Department registry service.
"""

import json
from pathlib import Path


class DepartmentService:
    """
    Load and resolve Kerala Government department names.
    """

    def __init__(self) -> None:
        self._departments = self._load_departments()

    @staticmethod
    def _load_departments() -> list[dict]:
        """
        Load departments from the JSON registry.
        """

        project_root = Path(__file__).resolve().parents[2]

        registry_path = (
            project_root
            / "data"
            / "config"
            / "departments.json"
        )

        with registry_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    @property
    def departments(self) -> list[dict]:
        """
        Return the department registry.
        """

        return self._departments

    def resolve(
        self,
        value: str,
    ) -> str | None:
        """
        Resolve a department name or alias.

        Returns:
            Canonical department name if found,
            otherwise None.
        """

        normalized = " ".join(
            value.strip().lower().split()
        )

        for department in self._departments:
            canonical = department["name"]

            if normalized == canonical.lower():
                return canonical

            for alias in department.get("aliases", []):
                if normalized == alias.lower():
                    return canonical

            for code in department.get("codes", []):
                if normalized == code.lower():
                    return canonical

        return None


department_service = DepartmentService()