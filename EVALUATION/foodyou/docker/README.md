# Running the FoodYou SUT without installing anything locally

FoodYou is a Compose **Multiplatform** app targeting **Android + iOS only** (no
web/desktop target). On an Apple-Silicon Mac with Docker Desktop you cannot run
the Android *emulator* in a container (no `/dev/kvm` / nested virtualization), so
the split is:

| Stage | Where | Why |
|-------|-------|-----|
| **Build** the APK | Docker (this dir) | keeps JDK 21 + Android SDK 36 + Gradle off the host |
| **View / drive** the UI | Appetize.io (browser) | cloud emulator with a real GPU; zero local install |

## 1. Build the APK (Docker only)

```bash
EVALUATION/foodyou/docker/build_apk.sh
```

What it does:
- base image `ghcr.io/cirruslabs/android-sdk:36` (bundles JDK 21.0.9, SDK 36,
  build-tools 36.0.0) run as `--platform linux/amd64` (Rosetta);
- mounts the vendored source `EVALUATION/foodyou/sut/foodyou` and a persistent
  `foodyou-gradle` volume for the Gradle cache;
- compiles Kotlin **in-process** and disables the configuration cache so the
  build fits the ~7.75 GB Docker VM (the project otherwise asks for 4 G + 3 G);
- runs `:app:assembleDebug` (auto-signed debug build — installable anywhere).

Output:
```
EVALUATION/foodyou/sut/foodyou/app/build/outputs/apk/debug/app-debug.apk
```

## 2. View the UI in the browser (Appetize.io)

1. Create a free account at <https://appetize.io> (free tier ≈ 100 min/month).
2. **Upload** → drag in `app-debug.apk`.
3. Pick a device (e.g. Pixel 7, Android 13+) and **Tap to start** — the real app
   streams to your browser; click/scroll to drive it.

Notes:
- The APK leaves your machine (it is uploaded to Appetize's cloud). It is an
  open-source app with no secrets, so this is fine.
- The debug build embeds all ABIs the project compiles; Appetize runs an x86
  image, which is fine for the diary/search UI we model. Barcode scanning (the
  one native feature) may be limited on the cloud emulator — not part of the
  abstract model anyway.

## Why not fully in Docker?

`docker-android` / noVNC emulator images require `--device /dev/kvm`, which
Docker Desktop on macOS never exposes. A non-accelerated ARM emulator is
unusably slow. Hence build-in-Docker + view-in-browser.
