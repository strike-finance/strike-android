# Strike Finance for Android

**[Download the latest APK](https://github.com/strike-finance/strike-android/releases/latest/download/strike.apk)**

If your phone has Google Play, install from
[Google Play](https://play.google.com/store/apps/details?id=org.strikefinance.app)
instead. Play keeps the app updated for you.

This APK is the build that is live on Google Play, downloaded from Play
itself, so it carries Play's signing key. That means:

- Links to `app.strikefinance.org` open in the app.
- If you install Google Play later, it recognises the app and updates it.

To install, open the downloaded file and allow your browser or file manager to
install unknown apps when Android asks.

## Verify the file

Every release lists the file's SHA-256. The signing certificate is always:

```
SHA-256: 1C:BF:83:A9:B6:A2:BA:A5:CB:9A:31:95:75:AE:30:56:B0:0C:95:F1:E2:46:66:2C:7D:79:64:40:11:13:A2:47
```

Check a download with `apksigner verify --print-certs strike.apk` (Android SDK
build-tools).
