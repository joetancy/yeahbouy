#!/usr/bin/env bash
set -euo pipefail

# Keep native output separate from older generated Python app bundles.
case "$(uname -s)" in
  Darwin)
    app="dist/native/YeahBouy.app"
    mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
    cp target/release/yeahbouy "$app/Contents/MacOS/yeahbouy"
    cp assets/Info.plist "$app/Contents/Info.plist"
    cp assets/yeahbouy.icns "$app/Contents/Resources/yeahbouy.icns"
    codesign --force --sign - "$app"
    ;;
  MINGW*|MSYS*)
    mkdir -p dist/native/YeahBouy
    cp target/release/yeahbouy.exe dist/native/YeahBouy/
    ;;
  *)
    mkdir -p dist/native/YeahBouy
    cp target/release/yeahbouy dist/native/YeahBouy/
    ;;
esac
