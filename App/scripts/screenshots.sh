#!/usr/bin/env bash
# Builds for the simulator, launches the app in fixed states and saves screenshots to ./shots.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${UDID:?set UDID}"
BID=com.theventus.qbd
OUT="$(pwd)/../shots"; mkdir -p "$OUT"

xcodebuild -project QBD.xcodeproj -scheme QBD -configuration Debug -destination "id=$UDID" \
  -derivedDataPath build/sim -clonedSourcePackagesDirPath build/spm \
  -skipPackagePluginValidation COMPILER_INDEX_STORE_ENABLE=NO build -quiet
xcrun simctl boot "$UDID" 2>/dev/null || true
xcrun simctl bootstatus "$UDID" -b
xcrun simctl status_bar "$UDID" override --time 9:41 --batteryState charged --batteryLevel 100 \
  --cellularMode active --cellularBars 4 --wifiBars 3
xcrun simctl install "$UDID" build/sim/Build/Products/Debug-iphonesimulator/QBD.app
# Warm the screenshot pipeline once; the first capture on a fresh simulator takes 10–15 s.
xcrun simctl io "$UDID" screenshot /tmp/warm.png >/dev/null 2>&1 || true

launch() {
  xcrun simctl terminate "$UDID" "$BID" 2>/dev/null || true
  xcrun simctl launch "$UDID" "$BID" "$@" >/dev/null
}
DATA=$(xcrun simctl get_app_container "$UDID" "$BID" data)
# The app writes Documents/qbd-ready once a launch state has rendered (-readyFile YES); poll for it instead of
# sleeping a fixed time. Falls back to 6 s if the marker never appears.
shot() {
  local name=$1; shift
  rm -f "$DATA/Documents/qbd-ready"
  launch -readyFile YES "$@"
  for _ in $(seq 1 30); do [ -f "$DATA/Documents/qbd-ready" ] && break; sleep 0.2; done
  sleep 0.4
  xcrun simctl io "$UDID" screenshot "$OUT/$name.png" >/dev/null; echo "shot $name"
}

# burst <name> <first wait> <gap> <count> <launch args>: frames from one launch, to check motion and glass morphs
burst() {
  local name=$1 first=$2 gap=$3 n=$4; shift 4
  launch "$@"; sleep "$first"
  for i in $(seq 1 "$n"); do xcrun simctl io "$UDID" screenshot "$OUT/$name-$i.png" >/dev/null; sleep "$gap"; done
  echo "burst $name"
}

# The app is a reader; every state uses the original sample book (never a real book on public CI).
B=(-fixtureBooks YES)
for mode in light dark; do
  xcrun simctl ui "$UDID" appearance $mode
  shot "home-$mode" "${B[@]}" -tab home -last book:field-guide -skipEntrance YES
  shot "library-$mode" "${B[@]}" -tab library
done
xcrun simctl ui "$UDID" appearance dark
shot book-home-web "${B[@]}" -tab home -last book:field-guide -landing web -skipEntrance YES
shot book-home-web-late "${B[@]}" -tab home -last book:field-guide -landing web -scene 4 -skipEntrance YES
shot book-home-highlights "${B[@]}" -tab home -last book:field-guide -seedHighlights YES -skipEntrance YES -scroll 1
shot book-contents "${B[@]}" -bookContents field-guide -last book:field-guide
shot highlights-tab "${B[@]}" -tab highlights -seedHighlights YES
shot search "${B[@]}" -tab search
xcrun simctl ui "$UDID" appearance light
shot book-page-sepia "${B[@]}" -openBook field-guide -theme sepia
shot book-page-night "${B[@]}" -openBook field-guide -theme night -toc 1 -hideChrome YES
shot book-page-scroll "${B[@]}" -openBook field-guide -theme paper -bookPaged NO -toc 2
shot book-panel "${B[@]}" -openBook field-guide -theme sepia -showSettings YES
shot book-toc "${B[@]}" -openBook field-guide -theme dusk -showContents YES
shot book-highlight-page "${B[@]}" -openBook field-guide -theme sepia -toc 0 -seedHighlights YES
shot book-whoswho "${B[@]}" -openBook field-guide -theme sepia -toc 2 -showPeople YES
shot settings "${B[@]}" -tab library -appSettings YES
# Companion: X-Ray, living names, chapter opener, previously
shot book-xray "${B[@]}" -openBook field-guide -theme sepia -toc 2 -showPeople YES
shot book-opener "${B[@]}" -openBook field-guide -theme sepia -toc 1 -showOpener YES
shot book-opener-orbit "${B[@]}" -openBook field-guide -theme night -toc 2 -showOpener YES
shot book-previously "${B[@]}" -openBook field-guide -theme paper -toc 2 -reentry YES
