#!/usr/bin/env bash
# Dockerized FoodYou APK build — keeps the whole Android toolchain (JDK 21 +
# SDK 36 + Gradle) inside a container so nothing is installed on the host.
#
# Runs as linux/amd64 (under Rosetta on Apple Silicon) because Android's
# build-tools binaries (aapt2 etc.) are x86_64. Output:
#   systems/foodyou/sut/foodyou/app/build/outputs/apk/debug/app-debug.apk
#
# Memory: the project's gradle.properties asks for 4G (Gradle) + 3G (Kotlin
# daemon). To fit the ~7.75G Docker VM we compile Kotlin IN-PROCESS (single
# JVM) and disable the configuration cache for this one-off build.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
SRC="$ROOT/systems/foodyou/sut/foodyou"
IMG="ghcr.io/cirruslabs/android-sdk:36"

echo ">> Building app-debug.apk in $IMG (linux/amd64)"
docker run --rm --platform linux/amd64 \
  -v "$SRC":/workspace -w /workspace \
  -v foodyou-gradle:/gradle -e GRADLE_USER_HOME=/gradle \
  "$IMG" \
  bash -lc '
    set -e
    java -version
    ./gradlew --no-daemon --no-configuration-cache --no-watch-fs --stacktrace \
      -Dorg.gradle.vfs.watch=false \
      -Dkotlin.compiler.execution.strategy=in-process \
      :app:assembleDebug
  '

APK="$SRC/app/build/outputs/apk/debug/app-debug.apk"
if [ -f "$APK" ]; then
  echo ">> APK ready:"; ls -lh "$APK"
else
  echo ">> APK not found at $APK — check the build log above." >&2
  exit 1
fi
