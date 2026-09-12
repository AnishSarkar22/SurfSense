from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OllamaArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    quantization: str | None = None


class CuratedModelArtifacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ollama: OllamaArtifact | None = None


class CuratedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str = Field(min_length=1)
    family: str = Field(min_length=1)
    minimum_context: int = Field(gt=0)
    allowed_quantizations: list[str]
    artifacts: CuratedModelArtifacts


class CuratedModelsManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int
    models: list[CuratedModel]

    @model_validator(mode="after")
    def validate_manifest(self) -> "CuratedModelsManifest":
        if self.schema_version != 1:
            raise ValueError(f"unsupported curated-model schema: {self.schema_version}")
        ids = [model.model_id for model in self.models]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate model_id in curated-model manifest")
        targets = [
            ("ollama", model.artifacts.ollama.name)
            for model in self.models
            if model.artifacts.ollama is not None
        ]
        if len(targets) != len(set(targets)):
            raise ValueError("duplicate runtime target in curated-model manifest")
        # The pinned quantization is passed to `llmfit plan --quant`, so a
        # manifest that contradicts its own allow-list would score one artifact
        # and install another. Catch it at load, not at scan time.
        for model in self.models:
            ollama = model.artifacts.ollama
            if ollama is None or ollama.quantization is None:
                continue
            if ollama.quantization not in model.allowed_quantizations:
                raise ValueError(
                    f"{model.model_id}: pinned quantization "
                    f"{ollama.quantization} is not in allowed_quantizations"
                )
        return self


def load_curated_models(path: Path | None = None) -> CuratedModelsManifest:
    manifest_path = path or Path(__file__).with_name("curated-models.json")
    return CuratedModelsManifest.model_validate_json(manifest_path.read_text())
