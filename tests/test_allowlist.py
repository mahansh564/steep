from steep_digest.allowlist import (
    email_allowed,
    gmail_from_query_fragment,
    sender_email_from_header,
)


def test_gmail_from_query_fragment():
    q = gmail_from_query_fragment(["a@b.com", "@beehiiv.com", "substack.com"])
    assert "from:a@b.com" in q
    assert "from:beehiiv.com" in q
    assert "from:substack.com" in q
    assert q.startswith("(") and q.endswith(")")


def test_sender_email_from_header():
    assert sender_email_from_header('"Name" <x@y.com>') == "x@y.com"


def test_email_allowed_domain():
    assert email_allowed("n@beehiiv.com", ["@beehiiv.com"])
    assert not email_allowed("n@evil.com", ["@beehiiv.com"])


def test_email_allowed_full():
    assert email_allowed("only@x.com", ["only@x.com", "@y.com"])
    assert not email_allowed("other@x.com", ["only@x.com"])
