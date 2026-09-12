import pytest
from app.providers.pagination import paginate


def test_paginate_slices() -> None:
    items = list(range(10))
    assert paginate(items, limit=3, offset=0) == [0, 1, 2]
    assert paginate(items, limit=3, offset=3) == [3, 4, 5]
    assert paginate(items, limit=3, offset=9) == [9]
    assert paginate(items, limit=3, offset=10) == []


def test_paginate_rejects_bad_params() -> None:
    with pytest.raises(ValueError):
        paginate([1], limit=0)
    with pytest.raises(ValueError):
        paginate([1], offset=-1)


def test_follow_next_pages_walks_until_exhausted() -> None:
    pages = {
        "/jobs": {
            "jobs": [1, 2],
            "paging": {"next": "/jobs?page=2"},
        },
        "/jobs?page=2": {"jobs": [3]},
    }

    def fetch(path: str, _params: dict[str, object] | None) -> dict[str, object]:
        return pages[path]

    from app.providers.pagination import follow_next_pages

    assert list(follow_next_pages(fetch, "jobs", initial_path="/jobs")) == [1, 2, 3]


def test_iter_offset_pages_covers_partial_last_page() -> None:
    items = list(range(5))

    def fetch_page(*, limit: int, offset: int) -> list[int]:
        return items[offset : offset + limit]

    from app.providers.pagination import iter_offset_pages

    assert list(iter_offset_pages(fetch_page, page_size=2)) == [0, 1, 2, 3, 4]


def test_mock_provider_pagination() -> None:
    from app.providers.mock import MockATSProvider

    provider = MockATSProvider()
    first = provider.list_jobs(limit=2, offset=0)
    second = provider.list_jobs(limit=2, offset=2)
    assert len(first) == 2
    assert len(second) == 2
    assert {job.external_id for job in first}.isdisjoint({job.external_id for job in second})
