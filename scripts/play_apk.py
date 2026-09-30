"""Find and download the APK that Google Play serves for the live production release.

    python3 scripts/play_apk.py latest              # prints version_code=<n>
    python3 scripts/play_apk.py download <n> <file>

Env: PLAY_SERVICE_ACCOUNT_JSON (service account key), PACKAGE_NAME,
SIGNING_CERT_SHA256 (Play app signing certificate the APK must carry).

Standard library only, and the OAuth token is signed with the runner's openssl,
so no third-party package ever runs next to the key.
"""

import base64
import binascii
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://androidpublisher.googleapis.com/androidpublisher/v3/applications"
SCOPE = "https://www.googleapis.com/auth/androidpublisher"
PACKAGE = os.environ.get("PACKAGE_NAME", "")


class _DropAuthOffHost(urllib.request.HTTPRedirectHandler):
    """Follow redirects, but never send the bearer token to another host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and urllib.parse.urlsplit(newurl).hostname != urllib.parse.urlsplit(req.full_url).hostname:
            new.remove_header("Authorization")
        return new


_opener = urllib.request.build_opener(_DropAuthOffHost)


def call(method, url, token=None, body=None, content_type="application/json", out=None, check=True):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if body is not None:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with _opener.open(req, timeout=600) as response:
            if out is not None:
                shutil.copyfileobj(response, out, 1 << 20)
                return None
            return response.read()
    except urllib.error.HTTPError as err:
        if not check:
            return None
        sys.exit(f"{method} {url.split('?')[0]} -> {err.code}: {err.read().decode(errors='replace')[:2000]}")


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def access_token() -> str:
    """OAuth token for the service account (JWT bearer grant, RFC 7523)."""
    key = json.loads(os.environ["PLAY_SERVICE_ACCOUNT_JSON"])
    token_uri = key.get("token_uri", "https://oauth2.googleapis.com/token")
    now = int(time.time())
    header = b64url(json.dumps({"alg": "RS256", "typ": "JWT", "kid": key["private_key_id"]}).encode())
    claims = b64url(
        json.dumps(
            {"iss": key["client_email"], "scope": SCOPE, "aud": token_uri, "iat": now, "exp": now + 600}
        ).encode()
    )
    signing_input = f"{header}.{claims}".encode()
    # NamedTemporaryFile is created 0600 and removed on close.
    with tempfile.NamedTemporaryFile("w", suffix=".pem") as pem:
        pem.write(key["private_key"])
        pem.flush()
        signature = subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", pem.name],
            input=signing_input,
            capture_output=True,
            check=True,
        ).stdout
    body = urllib.parse.urlencode(
        {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": f"{header}.{claims}.{b64url(signature)}",
        }
    ).encode()
    response = call("POST", token_uri, body=body, content_type="application/x-www-form-urlencoded")
    return json.loads(response)["access_token"]


def live_version_code(token: str) -> int:
    """Highest version code in a fully rolled-out production release.

    Tracks are only readable inside an edit; the edit is thrown away unchanged.
    """
    edit = json.loads(call("POST", f"{API}/{PACKAGE}/edits", token, body=b"{}"))["id"]
    try:
        track = json.loads(call("GET", f"{API}/{PACKAGE}/edits/{edit}/tracks/production", token))
    finally:
        call("DELETE", f"{API}/{PACKAGE}/edits/{edit}", token, check=False)
    codes = [
        int(code)
        for release in track.get("releases", [])
        if release.get("status") == "completed"
        for code in release.get("versionCodes", [])
    ]
    if not codes:
        sys.exit("No completed production release")
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


def download(token: str, version_code: int, path: str) -> None:
    want = normalize_sha256(os.environ["SIGNING_CERT_SHA256"])
    listing = json.loads(call("GET", f"{API}/{PACKAGE}/generatedApks/{version_code}", token))
    candidates = [
        entry
        for entry in listing.get("generatedApks", [])
        if "generatedUniversalApk" in entry
        and normalize_sha256(entry.get("certificateSha256Hash", "")) == want
    ]
    if not candidates:
        found = [normalize_sha256(e.get("certificateSha256Hash", "")) for e in listing.get("generatedApks", [])]
        sys.exit(f"No universal APK signed with {want}; signing certificates offered: {found}")
    download_id = urllib.parse.quote(candidates[0]["generatedUniversalApk"]["downloadId"], safe="")
    url = f"{API}/{PACKAGE}/generatedApks/{version_code}/downloads/{download_id}:download?alt=media"
    with open(path, "wb") as out:
        call("GET", url, token, out=out)


def main() -> None:
    if sys.argv[1:2] == ["latest"] and len(sys.argv) == 2:
        print(f"version_code={live_version_code(access_token())}")
    elif sys.argv[1:2] == ["download"] and len(sys.argv) == 4:
        download(access_token(), int(sys.argv[2]), sys.argv[3])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
