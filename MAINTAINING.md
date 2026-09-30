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

## One-time setup: the Play service account

The workflow reads the `PLAY_SERVICE_ACCOUNT_JSON` secret.

1. Google Cloud console, in the project linked under Play Console → Setup → API
   access: go to IAM & Admin → Service accounts → Create, then Keys → Add key →
   JSON.
2. Play Console → Users and permissions → Invite new users, using the service
   account's email. Under App permissions, add Strike Finance with:
   - View app information (read-only)
   - Release to production, exclude devices, and use Play App Signing. This is
     needed to download Play-signed APKs; the workflow never changes a release.
3. Add the key to this repo:
   `gh secret set PLAY_SERVICE_ACCOUNT_JSON --repo strike-finance/strike-android < key.json`,
   then delete `key.json`.
4. Run the workflow once by hand and check that it either publishes the live
   version or reports that it's already released.

A new Play Console permission can take up to a day to reach the API. Until it
does, runs fail with 401/403.

## If the signing key changes

After a Play app signing key upgrade, universal APKs may be signed with a
different certificate. Update `SIGNING_CERT_SHA256` in the workflow and the
certificate in the README. Also check that the web app's `assetlinks.json`
lists it.
