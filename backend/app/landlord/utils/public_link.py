from django.core import signing

_SALT = "issue-public-link-v1"


def make_token(ticket_no: str) -> str:
    return signing.dumps({"t": ticket_no}, salt=_SALT)


def parse_token(token: str) -> str:
    data = signing.loads(token, salt=_SALT)
    return str(data["t"])
