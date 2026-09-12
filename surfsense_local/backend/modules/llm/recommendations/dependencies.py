from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from pydantic import ValidationError

from modules.llm.providers import get_provider
from modules.llm.recommendations.catalog import CatalogService
from modules.llm.recommendations.curated_models import (
    CuratedModelsManifest,
    load_curated_models,
)
from modules.llm.recommendations.llmfit import LlmfitAdvisor
from modules.llm.recommendations.protocols import LocalRuntime
from modules.llm.recommendations.types import RecommendationWarning
from shared.config import get_llm_settings, get_storage_settings


@lru_cache
def get_catalog_service() -> CatalogService:
    settings = get_llm_settings()
    provider = get_provider("ollama")
    runtimes = [provider] if isinstance(provider, LocalRuntime) else []
    warnings: tuple[RecommendationWarning, ...] = ()
    try:
        curated_models = load_curated_models()
    except (OSError, ValidationError, ValueError):
        curated_models = CuratedModelsManifest(schema_version=1, models=[])
        warnings = (
            RecommendationWarning(
                "invalid_curated_models",
                "SurfSense Recommended models are temporarily unavailable.",
            ),
        )
    # The pinned quantization travels with each id: it is the `--quant`
    # argument, so curated models are scored as the artifact we install.
    curated = tuple(
        (
            model.model_id,
            None
            if model.artifacts.ollama is None
            else model.artifacts.ollama.quantization,
        )
        for model in curated_models.models
    )
    advisor = LlmfitAdvisor(
        settings.llmfit_path,
        settings.llmfit_expected_version,
        settings.llmfit_timeout_seconds,
        curated,
        cache_path=get_storage_settings().scan_cache_path,
        bulk_limit=settings.llmfit_bulk_limit,
        deadline_seconds=settings.llmfit_scan_deadline_seconds,
    )
    storage = (
        {"ollama": settings.ollama_models_dir}
        if settings.ollama_models_dir is not None
        else {}
    )
    return CatalogService(
        advisor,
        runtimes,
        curated_models,
        max_context=settings.llmfit_max_context,
        runtime_storage=storage,
        initial_warnings=warnings,
    )


CatalogServiceDep = Annotated[CatalogService, Depends(get_catalog_service)]
