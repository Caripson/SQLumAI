# Release Process

## Versioning
- Maintain semantic versions (vMAJOR.MINOR.PATCH).
- Track notable changes in `docs/RELEASE_NOTES.md`.

## Tagging
```bash
git pull
export VERSION=v0.1.0
sed -i "s/^SQLumAI .*/SQLumAI $VERSION/" README.md || true
# Update notes
echo "## $VERSION ($(date -I))" >> docs/RELEASE_NOTES.md
echo "- Initial MVP 1–3 with LLM, CI, insights" >> docs/RELEASE_NOTES.md

git add -A && git commit -m "chore(release): $VERSION"
git tag -a "$VERSION" -m "$VERSION"
git push origin main --tags
```

## CI
- CI runs tests, Docker integration, and LLM smoke.
- Consider publishing artifacts (docs, reports) as needed.
