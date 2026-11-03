#!/usr/bin/env bash
# Builds for the simulator, launches the app in fixed states and saves screenshots to ./shots.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${UDID:?set UDID}"
BID=com.theventus.qbd
OUT="$(pwd)/../shots"; mkdir -p "$OUT"

xcodebuild -project QBD.xcodeproj -scheme QBD -configuration Debug -destination "id=$UDID" \
  -derivedDataPath build/sim build -quiet
xcrun simctl boot "$UDID" 2>/dev/null || true
xcrun simctl bootstatus "$UDID" -b
xcrun simctl status_bar "$UDID" override --time 9:41 --batteryState charged --batteryLevel 100 \
  --cellularMode active --cellularBars 4 --wifiBars 3
xcrun simctl install "$UDID" build/sim/Build/Products/Debug-iphonesimulator/QBD.app

launch() {
  xcrun simctl terminate "$UDID" "$BID" 2>/dev/null || true
  xcrun simctl launch "$UDID" "$BID" "$@" >/dev/null
}
shot() { local name=$1; shift; launch "$@"; sleep 6; xcrun simctl io "$UDID" screenshot "$OUT/$name.png" >/dev/null; echo "shot $name"; }

for mode in light dark; do
  xcrun simctl ui "$UDID" appearance $mode
  shot "library-$mode" -tab library
  shot "course-$mode" -course YES
done
xcrun simctl ui "$UDID" appearance light
for t in sepia paper dusk night; do shot "lesson-$t" -open 0-1 -theme $t; done
shot lesson-mid -open 0-1 -theme sepia -scroll 12
shot lesson-steps -open 0-1 -theme paper -scroll 24
shot lesson-end -open 0-1 -theme night -scroll 60
shot settings -open 0-1 -theme sepia -showSettings YES
shot lab -tab lab
shot search -tab search
