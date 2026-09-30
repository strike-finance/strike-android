"""Find and download the APK that Google Play serves for the live production release.

    python scripts/play_apk.py latest              # prints version_code=<n>
    python scripts/play_apk.py download <n> <file>

Env: PLAY_SERVICE_ACCOUNT_JSON (service account key), PACKAGE_NAME,
SIGNING_CERT_SHA256 (Play app signing certificate the APK must carry).
"""

import base64
import binascii
import json
import os
import sys

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

API = "https://androidpublisher.googleapis.com/androidpublisher/v3/applications"
PACKAGE = os.environ["PACKAGE_NAME"]


def session() -> AuthorizedSession:
    info = json.loads(os.environ["PLAY_SERVICE_ACCOUNT_JSON"])
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/androidpublisher"]
    )
    return AuthorizedSession(creds)


def check(response):
    if not response.ok:
        sys.exit(f"{response.request.method} {response.url} -> {response.status_code}: {response.text}")
    return response


def live_version_code(s: AuthorizedSession) -> int:
    """Highest version code in a fully rolled-out production release.

    Tracks are only readable inside an edit; the edit is thrown away unchanged.
    """
    edit = check(s.post(f"{API}/{PACKAGE}/edits", json={})).json()["id"]
    try:
        track = check(s.get(f"{API}/{PACKAGE}/edits/{edit}/tracks/production")).json()
    finally:
        s.delete(f"{API}/{PACKAGE}/edits/{edit}")
    codes = [
        int(code)
        for release in track.get("releases", [])
        if release.get("status") == "completed"
        for code in release.get("versionCodes", [])
    ]
    if not codes:
        sys.exit(f"No completed production release: {json.dumps(track)}")
    return max(codes)


def normalize_sha256(value: str) -> str:
    """Hex without colons, lowercase; the API may also return base64."""
    plain = value.replace(":", "").strip().lower()
    if len(plain) == 64 and all(c in "0123456789abcdef" for c in plain):
        return plain
    try:
        return base64.b64decode(value + "=" * (-len(value) % 4)).hex()
    except (binascii.Error, ValueError):
        return plain


def download(s: AuthorizedSession, version_code: int, path: str) -> None:
    want = normalize_sha256(os.environ["SIGNING_CERT_SHA256"])
    listing = check(s.get(f"{API}/{PACKAGE}/generatedApks/{version_code}")).json()
    candidates = [
        entry
        for entry in listing.get("generatedApks", [])
        if "generatedUniversalApk" in entry
        and normalize_sha256(entry.get("certificateSha256Hash", "")) == want
    ]
    if not candidates:
        sys.exit(f"No universal APK signed with {want}: {json.dumps(listing)}")
    download_id = candidates[0]["generatedUniversalApk"]["downloadId"]
    url = f"{API}/{PACKAGE}/generatedApks/{version_code}/downloads/{download_id}:download"
    with check(s.get(url, params={"alt": "media"}, stream=True)) as response, open(path, "wb") as out:
        for chunk in response.iter_content(chunk_size=1 << 20):
            out.write(chunk)


def main() -> None:
    if sys.argv[1:2] == ["latest"] and len(sys.argv) == 2:
        print(f"version_code={live_version_code(session())}")
    elif sys.argv[1:2] == ["download"] and len(sys.argv) == 4:
        download(session(), int(sys.argv[2]), sys.argv[3])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
