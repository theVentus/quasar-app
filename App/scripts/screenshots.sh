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

# burst <name> <first wait> <gap> <count> <launch args>: frames from one launch, to check motion and glass morphs
burst() {
  local name=$1 first=$2 gap=$3 n=$4; shift 4
  launch "$@"; sleep "$first"
  for i in $(seq 1 "$n"); do xcrun simctl io "$UDID" screenshot "$OUT/$name-$i.png" >/dev/null; sleep "$gap"; done
  echo "burst $name"
}

for mode in light dark; do
  xcrun simctl ui "$UDID" appearance $mode
  shot "home-$mode" -tab home
  shot "library-$mode" -tab library
  shot "course-$mode" -course YES
done
xcrun simctl ui "$UDID" appearance light
shot course-scrolled -course YES -scroll 2
shot lesson-sepia -open 0-1 -theme sepia
shot lesson-paper-compact -open 0-1 -theme paper -scroll 12
shot lesson-night -open 0-1 -theme night -scroll 30
shot panel -open 0-1 -theme sepia -showSettings YES
burst morph 2 0.6 4 -open 0-1 -theme paper -showSettings YES -slowmo YES
shot contents -open 0-1 -theme sepia -showContents YES
shot settings -tab home -appSettings YES
shot lab -tab lab
