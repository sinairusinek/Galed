# Transkribus sync

The `code/transkribus/` module is adapted from
[YiDraCor](https://github.com/sinairusinek/YiDraCor); it talks to the
legacy Transkribus REST API (`transkribus.eu/TrpServer/rest`) and exposes
a small CLI for pulling and pushing PAGE-XML.

For credential setup (per-collaborator env vars), see
[COLLABORATORS.md](COLLABORATORS.md).

## Install

```sh
pip install requests
```

That's the only runtime dependency.

## Commands

All commands run from the repo root.

```sh
# list collections you can see
python3 -m code.transkribus.sync collections

# list documents in a collection (notebook = 2224542, Khirbat al-Arais = 2388662)
python3 -m code.transkribus.sync docs --col 2224542

# list pages + latest transcript URL for a document
python3 -m code.transkribus.sync pages --col 2224542 --doc 15908163

# pull every page as PAGE-XML into a directory (plus a _manifest.json)
python3 -m code.transkribus.sync pull --col 2224542 --doc 15908163 \
    --out data/notebook_15908163/page

# push one edited PAGE-XML back as a new transcript layer
python3 -m code.transkribus.sync push --col 2224542 \
    --file data/notebook_15908163/page_final/0002_118820667.xml

# or push every *.xml in a directory in one go
python3 -m code.transkribus.sync push-dir --col 2224542 \
    --dir data/notebook_15908163/page_final
```

## How pushes work

Each `push` / `push-dir` creates a **new transcript layer** on top of the
revision the file was pulled from. The parent `tsId` is read out of the
`<TranskribusMetadata>` block inside the PAGE-XML, so:

- collaborators' edits never overwrite each other on the server — they
  stack as versions you can compare and revert in the Transkribus UI;
- you can re-pull at any time and the local file picks up whatever is
  current on the server.

## Mapping image filenames to pages

Transkribus renames images on ingest (e.g. `IMG_3635.jpg` becomes
`107452900.jpg` internally). The pulled PAGE-XML stores the *internal*
name in `imageFilename`, not the original. To map an original filename
to a page number, use the `fulldoc` API directly — the page record there
includes both:

```python
from code.transkribus.client import TrpClient
c = TrpClient.from_env()
doc = c.fulldoc(2224542, 15908163)
for p in doc['pageList']['pages']:
    if p['imgFileName'] == 'IMG_3635.jpg':
        print(p['pageNr'], p['pageId'])
```

## Tracked collections

| collection | docs | status |
|---|---|---|
| `2224542` — Galed notebook | `15908163` (89 pp.) | `GT` (ground-truth) |
| `2388662` — חירבת אל ערייס הצפונית | `15642626` (77 pp.), `15642625` (22 pp.), `15642624` (30 pp.) | `NEW` (unverified HTR) |
