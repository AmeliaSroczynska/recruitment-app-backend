from accounts.services import normalize_email


def test_normalize_email_removes_spaces_and_uppercase():
    assert normalize_email("  Anna.Nowak@Example.COM ") == "anna.nowak@example.com"
