from pathlib import Path
import json
from datetime import datetime


class ProjectManager:

    def __init__(self):

        self.root = Path("projects")

        self.root.mkdir(
            exist_ok=True
        )


    def create_project(
        self,
        name,
        description=""
    ):

        project_path = (
            self.root / name
        )

        project_path.mkdir(
            exist_ok=True
        )


        folders = [
            "data",
            "metadata",
            "output",
            "reports",
            "logs",
            "cache"
        ]


        for folder in folders:

            (
                project_path / folder
            ).mkdir(
                exist_ok=True
            )


        project = {

            "project_name": name,

            "description": description,

            "created_at":
                datetime.now().isoformat(),

            "status": "created",

            "data_sources": []

        }


        with open(
            project_path / "project.json",
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                project,
                f,
                indent=4,
                ensure_ascii=False
            )


        return project_path