from datetime import UTC, datetime, timedelta

from app.sync.watermarks import effective_since, format_spi_timestamp


def test_effective_since_applies_overlap() -> None:
    watermark = datetime(2026, 9, 12, 15, 0, tzinfo=UTC)
    assert effective_since(watermark, 120) == watermark - timedelta(seconds=120)


def test_effective_since_none() -> None:
    assert effective_since(None, 120) is None


def test_format_spi_timestamp_matches_official_example() -> None:
    value = datetime(2015, 7, 8, 11, 56, 16, tzinfo=UTC)
    assert format_spi_timestamp(value) == "20150708T115616Z"
