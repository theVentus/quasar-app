#!/usr/bin/env bash
# Dev-sandbox helper: waits for the latest iOS run on HEAD, prints each job's steps and annotations.
R=theVentus/quasar-app; SHA=$(git rev-parse HEAD)
until ID=$(gh api "repos/$R/actions/workflows/ios.yml/runs?head_sha=$SHA" --jq '.workflow_runs[0].id // empty') && [ -n "$ID" ]; do sleep 10; done
until s=$(gh api repos/$R/actions/runs/$ID --jq '.status+" "+(.conclusion//"")'); [[ $s == completed* ]]; do sleep 30; done
echo "run $ID: $s"
for J in $(gh api repos/$R/actions/runs/$ID/jobs --jq '.jobs[].id'); do
  gh api repos/$R/actions/jobs/$J --jq '"== \(.name): \(.conclusion) (\(((.completed_at|fromdate) - (.started_at|fromdate))/60|floor) min)"'
  gh api repos/$R/actions/jobs/$J --jq '.steps[] | "\(.conclusion) \(.name)"' | grep -v '^success Post\|^success Set up\|^success Complete\|^skipped Report'
  gh api repos/$R/check-runs/$J/annotations --jq '.[] | "[\(.annotation_level)] \(.title // ""): \(.message)"' | grep -v "capacity constraints\|Test Case\|Test Suite\|Executed"
done
