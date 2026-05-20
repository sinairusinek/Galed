"""Legacy Transkribus TrpServer REST client (two auth routes).

The REST surface (collections, docs, pages, transcripts) is identical for
everyone — only how a session authenticates differs:

  * "login"  — password grant to `POST /auth/login`, returns a JSESSIONID
               cookie the session reuses. This is the privileged/internal
               route; it works for accounts with elevated API access.
  * "oidc"   — the documented *legacy* route: OpenID Connect password grant
               to readcoop's token endpoint, then `Authorization: Bearer
               <access_token>` on every call (auto-refreshed). This is what
               collaborators with ordinary Transkribus accounts should use.
               https://help.transkribus.org/transkribus-legacy-api

Route selection (auto-detected, no CLI flag): `TRANSKRIBUS_AUTH` may be set to
"login" or "oidc"; if unset we default to "oidc" so collaborators get the
documented path with zero extra config and the privileged owner opts in with
`export TRANSKRIBUS_AUTH=login`.

Endpoints used:
  GET  /collections/list                        -> all collections the user can see
  GET  /collections/{cid}/list                  -> docs in a collection
  GET  /collections/{cid}/{did}/fulldoc         -> doc with pages + transcripts
  GET  <transcript.url>                         -> PAGE-XML
  POST /collections/{cid}/{did}/{pageNr}/text   -> upload a transcript layer
"""
from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from typing import Optional

import requests

DEFAULT_BASE = "https://transkribus.eu/TrpServer/rest"

# OpenID Connect (the documented legacy route).
OIDC_TOKEN_URL = (
    "https://account.readcoop.eu/auth/realms/readcoop/"
    "protocol/openid-connect/token"
)
OIDC_CLIENT_ID = "transkribus-api-client"

VALID_AUTH = ("login", "oidc")


class _BearerAuth(requests.auth.AuthBase):
    """Attaches `Authorization: Bearer <token>`, refreshing when near expiry.

    Holds the refresh state so all of TrpClient's methods can keep calling
    `self.session.get/post` unchanged — the header is (re)stamped per request.
    """

    def __init__(self, user: str, password: str) -> None:
        self.user = user
        self.password = password
        self._access: Optional[str] = None
        self._refresh: Optional[str] = None
        self._expires_at: float = 0.0

    def _token_request(self, data: dict) -> None:
        data = {"client_id": OIDC_CLIENT_ID, **data}
        r = requests.post(OIDC_TOKEN_URL, data=data, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(
                f"OIDC token request failed ({r.status_code}): {r.text[:200]}"
            )
        tok = r.json()
        self._access = tok["access_token"]
        self._refresh = tok.get("refresh_token")
        # refresh 30s before the server-stated expiry to avoid edge races
        self._expires_at = time.time() + int(tok.get("expires_in", 300)) - 30

    def login(self) -> None:
        self._token_request(
            {"grant_type": "password", "username": self.user, "password": self.password}
        )

    def _ensure_token(self) -> None:
        if self._access and time.time() < self._expires_at:
            return
        if self._refresh:
            try:
                self._token_request(
                    {"grant_type": "refresh_token", "refresh_token": self._refresh}
                )
                return
            except RuntimeError:
                pass  # refresh expired/revoked — fall back to a full login
        self.login()

    def __call__(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        self._ensure_token()
        request.headers["Authorization"] = f"Bearer {self._access}"
        return request


@dataclass
class TrpClient:
    user: str
    password: str
    base: str = DEFAULT_BASE
    auth: str = "oidc"
    session: requests.Session = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.auth not in VALID_AUTH:
            raise ValueError(f"auth must be one of {VALID_AUTH}, got {self.auth!r}")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    @classmethod
    def from_env(cls, base: Optional[str] = None) -> "TrpClient":
        try:
            user = os.environ["TRANSKRIBUS_USER"]
            pw = os.environ["TRANSKRIBUS_PASS"]
        except KeyError as e:
            raise SystemExit(f"Missing env var {e}. Set TRANSKRIBUS_USER and TRANSKRIBUS_PASS.")
        auth = os.environ.get("TRANSKRIBUS_AUTH", "oidc").strip().lower()
        if auth not in VALID_AUTH:
            raise SystemExit(
                f"TRANSKRIBUS_AUTH must be one of {VALID_AUTH}, got {auth!r}."
            )
        c = cls(user=user, password=pw, base=base or DEFAULT_BASE, auth=auth)
        c.login()
        return c

    def login(self) -> None:
        if self.auth == "oidc":
            bearer = _BearerAuth(self.user, self.password)
            bearer.login()  # fail fast on bad credentials
            self.session.auth = bearer
        else:
            # privileged JSESSIONID route
            resp = self.session.post(
                f"{self.base}/auth/login",
                data={"user": self.user, "pw": self.password},
                timeout=30,
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Login failed ({resp.status_code}): {resp.text[:200]}")
        # one-line reassurance for collaborators; goes to stderr so it never
        # pollutes table output piped on stdout
        print(f"[transkribus] authenticated as {self.user} via {self.auth} route",
              file=sys.stderr)

    def list_collections(self) -> list[dict]:
        r = self.session.get(f"{self.base}/collections/list", timeout=30)
        r.raise_for_status()
        return r.json()

    def list_docs(self, col_id: int) -> list[dict]:
        r = self.session.get(f"{self.base}/collections/{col_id}/list", timeout=60)
        r.raise_for_status()
        return r.json()

    def fulldoc(self, col_id: int, doc_id: int) -> dict:
        r = self.session.get(
            f"{self.base}/collections/{col_id}/{doc_id}/fulldoc", timeout=120
        )
        r.raise_for_status()
        return r.json()

    def fetch_transcript(self, url: str) -> str:
        r = self.session.get(url, timeout=60)
        r.raise_for_status()
        return r.text

    def fetch_image(self, url: str) -> bytes:
        """Download the page image bytes from its fulldoc `url` field."""
        r = self.session.get(url, timeout=180)
        r.raise_for_status()
        return r.content

    def push_transcript(
        self,
        col_id: int,
        doc_id: int,
        page_nr: int,
        page_xml: str,
        *,
        parent_tsid: Optional[int] = None,
        status: str = "IN_PROGRESS",
        note: Optional[str] = None,
        tool_name: str = "YiDraCor-annotation-pipeline",
    ) -> dict:
        """Upload a new PAGE-XML transcript layer to an existing page.

        Posts to `POST /collections/{col}/{doc}/{pageNr}/text` (legacy API).
        Returns the response JSON (typically the new tsId + url).
        """
        params: dict = {"toolName": tool_name, "status": status}
        if parent_tsid is not None:
            params["parent"] = parent_tsid
        if note is not None:
            params["note"] = note
        r = self.session.post(
            f"{self.base}/collections/{col_id}/{doc_id}/{page_nr}/text",
            params=params,
            data=page_xml.encode("utf-8"),
            headers={"Content-Type": "application/xml"},
            timeout=120,
        )
        if r.status_code >= 300:
            raise RuntimeError(f"Push failed ({r.status_code}): {r.text[:400]}")
        try:
            return r.json()
        except ValueError:
            return {"status_code": r.status_code, "text": r.text[:400]}
