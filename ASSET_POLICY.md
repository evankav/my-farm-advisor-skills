# Asset Policy

## Repository hygiene

- Do not commit generated or downloaded runtime assets.
- Keep build artifacts, cache directories, and generated outputs out of Git.
- Geoadmin payloads such as `countries.geojson` and `states_usa.geojson` are runtime data, not repository content.

## Large file handling

- Binary assets larger than 1 MB must use Git LFS.
- Required LFS-backed formats in this repo include `.npy`, `.npz`, `.raw`, `.bin`, `.so`, `.dylib`, and `.dll`.
- JSON and GeoJSON metadata files remain normal text files and must not be moved to Git LFS by default.

## Review requirements

- Any large file addition requires explicit reviewer approval.
- If a file should be regenerated or downloaded at runtime, exclude it instead of tracking it with Git or Git LFS.
