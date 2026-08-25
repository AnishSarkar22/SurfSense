from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from time import perf_counter

import pytest
from pydantic import ValidationError

from app.sandbox.capabilities.disclosure import build_capability_disclosure
from app.sandbox.capabilities.filtering import CapabilityFilter
from app.sandbox.capabilities.loader import (
    CAPABILITY_INDEX_PATH,
    _parse_index,
    clear_capability_index_cache,
    load_capability_index,
)
from app.sandbox.capabilities.retrieval import (
    RetrievalQuery,
    RetrievedCapability,
    _tokens,
    retrieve_capabilities,
)
from app.sandbox.capabilities.schema import (
    CapabilityEnvelope,
    CapabilityIndex,
    CapabilityKind,
    CapabilityPostings,
    CapabilityTier,
)
from app.sandbox.capabilities.validation import (
    validate_capability_props,
    validate_selected_capability_ids,
)

pytestmark = pytest.mark.unit
REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
VIDEO_RUNTIME_ROOT = REPOSITORY_ROOT / "docker" / "sandbox" / "video-runtime"


class _Sandbox:
    session_id = "capability-test"

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.reads = 0

    async def read_file(self, path: str) -> bytes:
        assert path == CAPABILITY_INDEX_PATH
        self.reads += 1
        return self.data


def _capability(
    capability_id: str,
    *,
    category: str,
    summary: str,
    tags: tuple[str, ...],
    use_for: tuple[str, ...] = (),
    avoid_for: tuple[str, ...] = (),
    tier: CapabilityTier = CapabilityTier.VETTED,
) -> CapabilityEnvelope[dict[str, object]]:
    return CapabilityEnvelope[dict[str, object]](
        id=capability_id,
        kind=CapabilityKind.COMPONENT,
        domain="video",
        category=category,
        summary=summary,
        tags=tags,
        use_for=use_for,
        avoid_for=avoid_for,
        natural_frame_length=30,
        tier=tier,
        props_schema={"type": "object", "additionalProperties": False},
        declaration={},
        search_text=" ".join((summary, *tags, *use_for, *avoid_for)).casefold(),
    )


def _index_for(
    capabilities: tuple[CapabilityEnvelope[dict[str, object]], ...],
) -> CapabilityIndex:
    fields = {
        "all": lambda capability: " ".join(
            (
                capability.id,
                capability.summary,
                capability.category,
                *capability.tags,
                *capability.use_for,
                *capability.avoid_for,
            )
        ),
        "tags": lambda capability: " ".join(capability.tags),
        "use_for": lambda capability: " ".join(capability.use_for),
        "summary": lambda capability: capability.summary,
        "vibe": lambda capability: " ".join(capability.vibe),
        "category": lambda capability: capability.category,
        "avoid_for": lambda capability: " ".join(capability.avoid_for),
    }
    postings: dict[str, dict[str, list[str]]] = {
        field_name: {} for field_name in fields
    }
    for capability in capabilities:
        for field_name, text in fields.items():
            for term in set(re.findall(r"[a-z0-9]+", text(capability).casefold())):
                postings[field_name].setdefault(term, []).append(capability.id)

    return CapabilityIndex(
        schema_version=1,
        build_id="build-1",
        capabilities=capabilities,
        postings=CapabilityPostings.model_validate_json(json.dumps(postings)),
    )


def _index() -> CapabilityIndex:
    return _index_for(
        (
            _capability(
                "video.component.metric-grid",
                category="data",
                summary="Animated metric grid for KPI comparisons",
                tags=("metrics", "grid", "data"),
                use_for=("quarterly KPI comparison",),
            ),
            _capability(
                "video.component.metric-cards",
                category="data",
                summary="Metric cards for dashboards",
                tags=("metrics", "cards", "data"),
                use_for=("dashboard metrics",),
            ),
            _capability(
                "video.component.confetti",
                category="celebration",
                summary="Celebratory confetti burst",
                tags=("celebration",),
                avoid_for=("serious financial reporting",),
            ),
            _capability(
                "video.component.core.text",
                category="core",
                summary="General text composition fallback",
                tags=("text", "fallback"),
                tier=CapabilityTier.CORE,
            ),
        )
    )


def test_generic_envelope_is_strict_and_forbids_unknown_fields() -> None:
    document = _capability(
        "video.component.core.text",
        category="core",
        summary="Text",
        tags=("text",),
    ).model_dump()
    document["natural_frame_length"] = "30"
    document["implementation_path"] = "/private/source.tsx"

    with pytest.raises(ValidationError):
        CapabilityEnvelope[dict[str, object]].model_validate(document)


def test_node_generated_index_satisfies_python_contract(tmp_path: Path) -> None:
    if (
        shutil.which("node") is None
        or not (VIDEO_RUNTIME_ROOT / "node_modules").is_dir()
    ):
        pytest.skip("Node and installed video-runtime dependencies are required")

    output = tmp_path / "capabilities"
    subprocess.run(
        ["node", "scripts/build-capabilities.mjs"],
        cwd=VIDEO_RUNTIME_ROOT,
        env={**os.environ, "SURFSENSE_CAPABILITY_OUTPUT": str(output)},
        check=True,
        capture_output=True,
        text=True,
    )
    index = _parse_index((output / "index.json").read_bytes())

    assert index.schema_version == 1
    assert index.build_id
    assert tuple(capability.id for capability in index.capabilities) == tuple(
        sorted(capability.id for capability in index.capabilities)
    )
    known_ids = set(index.by_id())
    assert known_ids
    assert all(
        set(posting_ids) <= known_ids
        for field_name in type(index.postings).model_fields
        for posting_ids in getattr(index.postings, field_name).values()
    )
    assert all(
        capability.domain == "video" and capability.declaration["deterministic"] is True
        for capability in index.capabilities
    )
    animated_bar_chart = index.by_id()["video.component.animated-bar-chart"]
    disclosure = build_capability_disclosure(
        index.build_id,
        (
            RetrievedCapability(
                capability=animated_bar_chart,
                score=100,
                matched_terms=("chart",),
            ),
        ),
    )
    assert disclosure.candidates[0].props_schema["required"] == ["data"]
    assert json.loads(disclosure.model_dump_json())["candidates"][0]["props_schema"][
        "required"
    ] == ["data"]
    validate_capability_props(
        index,
        (
            (
                animated_bar_chart.id,
                CapabilityKind.COMPONENT,
                {"data": [10, 20], "labels": ["A", "B"]},
            ),
        ),
    )
    with pytest.raises(ValueError, match="invalid props"):
        validate_capability_props(
            index,
            (
                (
                    animated_bar_chart.id,
                    CapabilityKind.COMPONENT,
                    {"data": [10], "arbitrary": True},
                ),
            ),
        )


async def test_loader_reads_live_and_caches_only_immutable_digest_identity() -> None:
    clear_capability_index_cache()
    sandbox = _Sandbox(_index().model_dump_json().encode())
    digest = f"sha256:{'a' * 64}"

    first = await load_capability_index(sandbox, image_digest=digest)
    second = await load_capability_index(sandbox, image_digest=digest)
    mutable_first = await load_capability_index(sandbox, image_digest="dev:latest")
    mutable_second = await load_capability_index(sandbox, image_digest="dev:latest")

    assert sandbox.reads == 4
    assert first is second
    assert mutable_first is not mutable_second
    with pytest.raises(TypeError, match="immutable"):
        first.capabilities[0].props_schema["type"] = "string"


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": 2},
        {"build_id": "other"},
    ],
)
async def test_loader_rejects_version_or_expected_build_mismatch(change) -> None:
    document = _index().model_dump(mode="json")
    document.update(change)
    sandbox = _Sandbox(json.dumps(document).encode())

    with pytest.raises((ValueError, ValidationError), match=r"schema|build"):
        await load_capability_index(
            sandbox,
            image_digest=None,
            expected_build_id="build-1",
        )


def test_retrieval_is_deterministic_diverse_and_keeps_core_fallback() -> None:
    query = RetrievalQuery(
        text="serious quarterly KPI metric comparison",
        facets=CapabilityFilter(
            domains=frozenset({"video"}),
            kinds=frozenset({CapabilityKind.COMPONENT}),
        ),
        avoid=("confetti", "celebration"),
        top_k=3,
    )

    first = retrieve_capabilities(_index(), query)
    second = retrieve_capabilities(_index(), query)

    assert first == second
    assert first[0].capability.id == "video.component.metric-grid"
    assert any(item.capability.tier is CapabilityTier.CORE for item in first)
    assert all(item.capability.id != "video.component.confetti" for item in first)


def test_tokenization_preserves_unicode_terms_like_the_build_index() -> None:
    assert _tokens("Café 数据 Δelta") == frozenset({"cafe", "数据", "δelta"})


def test_weighted_postings_keep_a_200_item_catalog_search_fast() -> None:
    index = _index_for(
        (
            *(
                _capability(
                    f"video.component.catalog-{position:03d}",
                    category="catalog",
                    summary=f"Specialized visual capability number {position}",
                    tags=(f"intent{position}", "visual"),
                )
                for position in range(199)
            ),
            _capability(
                "video.component.core.primitives",
                category="core",
                summary="General composition fallback",
                tags=("fallback",),
                tier=CapabilityTier.CORE,
            ),
        )
    )
    query = RetrievalQuery(text="intent137 specialized visual", top_k=3)

    started = perf_counter()
    for _ in range(500):
        result = retrieve_capabilities(index, query)
    elapsed = perf_counter() - started

    assert result[0].capability.id == "video.component.catalog-137"
    assert elapsed < 0.5


def test_disclosure_is_bounded_deduplicated_and_selected_ids_are_closed() -> None:
    retrieved = retrieve_capabilities(
        _index(),
        RetrievalQuery(text="metric comparison", top_k=4),
    )
    disclosure = build_capability_disclosure(
        "build-1",
        (*retrieved, *retrieved),
        max_candidates=3,
    )

    assert len(disclosure.candidates) == 3
    assert len(set(disclosure.disclosed_ids)) == 3
    assert disclosure.candidates[0].props_schema == {
        "type": "object",
        "additionalProperties": False,
    }
    assert validate_selected_capability_ids(
        [disclosure.disclosed_ids[0], disclosure.disclosed_ids[0]],
        disclosure,
        build_id="build-1",
    ) == (disclosure.disclosed_ids[0],)
    with pytest.raises(ValueError, match="not disclosed"):
        validate_selected_capability_ids(
            ["video.component.untrusted.arbitrary"],
            disclosure,
        )
