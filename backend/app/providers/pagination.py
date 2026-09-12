from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from typing import Any


def paginate[T](
    items: Sequence[T],
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[T]:
    """Slice a sequence. Used by the mock provider and offset-based adapters."""
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if offset < 0:
        raise ValueError("offset must be >= 0")
    return list(items[offset : offset + limit])


def iter_offset_pages[T](
    fetch_page: Callable[..., Sequence[T]],
    *,
    page_size: int = 50,
) -> Iterator[T]:
    """Walk an offset/limit API until a short or empty page. Never stops after the first page."""
    if page_size < 1:
        raise ValueError("page_size must be >= 1")
    offset = 0
    while True:
        batch = list(fetch_page(limit=page_size, offset=offset))
        if not batch:
            return
        yield from batch
        if len(batch) < page_size:
            return
        offset += len(batch)


def follow_next_pages(
    fetch: Callable[[str, dict[str, Any] | None], dict[str, Any]],
    collection_key: str,
    *,
    initial_path: str,
    initial_params: dict[str, Any] | None = None,
) -> Iterator[Any]:
    """Walk Workable-style `paging.next` URLs until the collection is exhausted."""
    path: str | None = initial_path
    params: dict[str, Any] | None = dict(initial_params or {})
    seen: set[str] = set()
    while path:
        identity = path if params is None else f"{path}?{sorted(params.items())}"
        if identity in seen:
            return
        seen.add(identity)
        payload = fetch(path, params)
        if not isinstance(payload, dict):
            raise ValueError(f"Expected an object for '{collection_key}' page, got {type(payload).__name__}")
        items = payload.get(collection_key)
        if items is None:
            items = []
        if not isinstance(items, list):
            raise ValueError(f"Expected '{collection_key}' to be a list")
        yield from items
        paging = payload.get("paging")
        next_url = paging.get("next") if isinstance(paging, dict) else None
        if not next_url or not isinstance(next_url, str):
            return
        path = next_url
        params = None
