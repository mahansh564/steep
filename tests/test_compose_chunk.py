from steep_digest.deliver import _chunk_telegram


def test_chunk_telegram_splits():
    s = "x" * 200 + "\n\n" + "y" * 200
    parts = _chunk_telegram(s, max_len=250)
    assert len(parts) >= 2
    assert all(len(p) <= 250 for p in parts)
