"""Writes altstore.json (AltStore Classic source) for the IPA CI just built.
Usage: python3 altstore-source.py <ipa> <version> <build> <out.json>"""
import json, os, sys, datetime

ipa, version, build, out = sys.argv[1:5]
repo = os.environ.get("GITHUB_REPOSITORY", "theVentus/quasar-app")
source = {
    "name": "Quasar",
    "identifier": "com.theventus.qbd.source",
    "subtitle": "Courses you can read, test and play with",
    "sourceURL": f"https://github.com/{repo}/releases/download/latest/altstore.json",
    "apps": [{
        "name": "Quasar",
        "bundleIdentifier": "com.theventus.qbd",
        "developerName": "theVentus",
        "subtitle": "Courses you can read, test and play with",
        "localizedDescription": "A library of rigorous, interactive courses. The first one goes from quasars to the blue dot on your map.",
        "iconURL": f"https://raw.githubusercontent.com/{repo}/main/App/QBD/Assets.xcassets/AppIcon.appiconset/icon-1024.png",
        "tintColor": "#3A84FF",
        "appPermissions": {"entitlements": [], "privacy": {}},
        "versions": [{
            "version": version,
            "buildVersion": build,
            "date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "localizedDescription": f"Build {build} from {os.environ.get('GITHUB_SHA', '')[:7]}",
            "downloadURL": f"https://github.com/{repo}/releases/download/latest/QBD.ipa",
            "size": os.path.getsize(ipa),
            "minOSVersion": "26.1",
        }],
    }],
    "news": [],
}
json.dump(source, open(out, "w"), indent=2)
print(f"wrote {out}: Quasar {version} ({build})")
