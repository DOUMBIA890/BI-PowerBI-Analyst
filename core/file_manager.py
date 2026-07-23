from pathlib import Path
import json
import shutil


class FileManager:


    def add_files(
        self,
        files,
        project_path
    ):

        data_folder = (
            Path(project_path)
            / "data"
        )


        data_folder.mkdir(
            exist_ok=True
        )


        added_files = []


        for file in files:

            destination = (
                data_folder
                /
                file.name
            )


            with open(
                destination,
                "wb"
            ) as f:

                f.write(
                    file.getbuffer()
                )


            added_files.append(
                file.name
            )


        return added_files


    def save_json(
        self,
        project_path,
        filename: str,
        data: dict
    ) -> Path:
        """Sauvegarde un livrable JSON dans le dossier data/ du projet."""

        data_folder = (
            Path(project_path)
            / "data"
        )
        data_folder.mkdir(exist_ok=True)

        destination = data_folder / filename
        with open(destination, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return destination