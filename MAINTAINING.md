# How releases get here

Nobody uploads APKs by hand. `.github/workflows/sync-apk.yml` runs every 30
minutes, and you can also start it from Actions → Sync APK from Google Play →
Run workflow. Each run:

1. Asks the Play Developer API for the highest version code in a fully
   rolled-out production release. Staged rollouts are skipped until they reach
   100%.
2. Stops if a release tagged `v<versionName>-<versionCode>` already exists.
3. Downloads Play's signed universal APK for that version, the same file as
   Play Console → App bundle explorer → Downloads → "Signed, universal APK".
4. Checks the package name and version code, and that the APK is signed with
   the Play app signing certificate `1C:BF…A2:47`. If any check fails, the run
   fails and nothing is published.
5. Publishes it as the latest release, with the asset named `strike.apk`.

`https://github.com/strike-finance/strike-android/releases/latest/download/strike.apk`
therefore always serves the current build. The web app's Mobile Login page and
the landing page link to that URL.

Run the workflow with **rehearse** ticked to download and verify the live
version without publishing anything. It's useful after changing the key or the
Play permissions.

## How the Play key is protected

- The key is the `PLAY_SERVICE_ACCOUNT_JSON` secret in the **`play`**
  environment. Only `main` may use that environment, so a workflow pushed on
  any other branch gets nothing.
- `main` is covered by a ruleset: changes need a pull request approved by the
  code owner (`.github/CODEOWNERS`), and it can't be force-pushed or deleted.
  Repository admins can bypass it.
- Releases are immutable. Once published, a release's APK and tag can't be
  replaced.
- The script uses only Python's standard library and the runner's `openssl`,
  so no third-party package runs next to the key. `actions/checkout` is pinned
  to a commit SHA.

## The Play service account

`apk-sync@strike-play-api.iam.gserviceaccount.com`, in the Google Cloud project
`strike-play-api`. It needs no Cloud IAM roles. In Play Console → Users and
permissions it has access to the Strike Finance app only, with:

- View app information (read-only)
- Release to production, exclude devices, and use Play App Signing. Downloading
  Play-signed APKs is part of Play App Signing. Nothing in this repo creates or
  changes a release.

### Rotating the key

1. Google Cloud → IAM & Admin → Service accounts → `apk-sync` → Keys → Add key
   → JSON.
2. `gh secret set PLAY_SERVICE_ACCOUNT_JSON --env play --repo strike-finance/strike-android < key.json && rm key.json`
3. Run the workflow with **rehearse** ticked and check that it passes.
4. Delete the old key on the same Keys page.

A new Play Console permission can take up to a day to reach the API. Until it
does, runs fail with 401/403.

## If the signing key changes

After a Play app signing key upgrade, universal APKs may be signed with a
different certificate. Update `SIGNING_CERT_SHA256` in the workflow and the
certificate in the README. Also check that the web app's `assetlinks.json`
lists it.
