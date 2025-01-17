from __future__ import annotations
import os
from pathlib import Path
from attr import define, field
from griptape.artifacts import ErrorArtifact, InfoArtifact, ListArtifact
from griptape.tools import BaseTool
from griptape.utils.decorators import activity
from griptape.loaders import FileLoader
from schema import Schema, Literal


@define
class FileManager(BaseTool):
    workdir: str = field(default=os.getcwd(), kw_only=True)

    @workdir.validator
    def validate_workdir(self, _, workdir: str) -> None:
        if not Path(workdir).is_absolute():
            raise ValueError("workdir has to be absolute absolute")

    @activity(config={
        "description": "Can be used to load files from disk",
        "schema": Schema({
            Literal(
                "paths",
                description="Paths to files to be loaded in the POSIX format. For example, ['foo/bar/file.txt']"
            ): []
        })
    })
    def load_files_from_disk(self, params: dict) -> ListArtifact | ErrorArtifact:
        list_artifact = ListArtifact()

        for path in params["values"]["paths"]:
            try:
                list_artifact.value.append(
                    FileLoader(workdir=self.workdir).load(Path(path))
                )
            except FileNotFoundError:
                return ErrorArtifact(f"file in path `{path}` not found")
            except Exception as e:
                return ErrorArtifact(f"error loading file: {e}")

        return list_artifact

    @activity(config={
        "description": "Can be used to save memory artifacts to disk",
        "schema": Schema(
            {
                Literal(
                    "dir_name",
                    description="Destination directory name on disk in the POSIX format. For example, 'foo/bar'"
                ): str,
                Literal(
                    "file_name",
                    description="Destination file name. For example, 'baz.txt'"
                ): str,
                "memory_name": str,
                "artifact_namespace": str
            }
        )
    })
    def save_memory_artifacts_to_disk(self, params: dict) -> ErrorArtifact | InfoArtifact:
        memory = self.find_input_memory(params["values"]["memory_name"])
        artifact_namespace = params["values"]["artifact_namespace"]
        dir_name = params["values"]["dir_name"]
        file_name = params["values"]["file_name"]

        if memory:
            artifacts = memory.load_artifacts(artifact_namespace)

            if len(artifacts) == 0:
                return ErrorArtifact("no artifacts found")
            elif len(artifacts) == 1:
                try:
                    self._save_to_disk(
                        os.path.join(self.workdir, dir_name, file_name),
                        artifacts[0].value
                    )

                    return InfoArtifact(f"saved successfully")
                except Exception as e:
                    return ErrorArtifact(f"error writing file to disk: {e}")
            else:
                try:
                    for a in artifacts:
                        self._save_to_disk(
                            os.path.join(self.workdir, dir_name, f"{a.name}-{file_name}"),
                            a.value
                        )

                    return InfoArtifact(f"saved successfully")
                except Exception as e:
                    return ErrorArtifact(f"error writing file to disk: {e}")
        else:
            return ErrorArtifact("memory not found")

    @activity(config={
        "description": "Can be used to save content to a file",
        "schema": Schema(
            {
                Literal(
                    "path",
                    description="Destination file path on disk in the POSIX format. For example, 'foo/bar/baz.txt'"
                ): str,
                "content": str
            }
        )
    })
    def save_content_to_file(self, params: dict) -> ErrorArtifact | InfoArtifact:
        content = params["values"]["content"]
        new_path = params["values"]["path"]
        full_path = os.path.join(self.workdir, new_path)

        try:
            self._save_to_disk(full_path, content)

            return InfoArtifact(f"saved successfully")
        except Exception as e:
            return ErrorArtifact(f"error writing file to disk: {e}")

    def _save_to_disk(self, path: str, value: any) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, "wb") as file:
            file.write(value.encode() if isinstance(value, str) else value)
