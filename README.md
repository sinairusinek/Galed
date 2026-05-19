# Galed

Post-processing pipeline for the transcription of an archaeological notebook
on Transkribus (collection `2224542`, document `15908163`).

## Collaborators

This repository is shared by a small team. Each collaborator uses **their own
Transkribus account** — credentials are never committed. To get access:

1. Ask the repo owner to add you as a GitHub collaborator (private repo).
2. Ask the repo owner / collection owner to invite your Transkribus user to
   collection `2224542` with at least *Transcriber* permission.
3. Set your own Transkribus credentials in your shell (e.g. `~/.zshrc`):

   ```sh
   export TRANSKRIBUS_USER='you@example.org'
   export TRANSKRIBUS_PASS='your-password'
   ```

   Do **not** put credentials in any file inside this repo. `.env` is
   gitignored if you prefer that pattern, but env vars in your shell are
   simpler and what the code expects.

## Transkribus sync

The `code/transkribus/` module is adapted from
[YiDraCor](https://github.com/sinairusinek/YiDraCor); it talks to the
legacy Transkribus REST API (`transkribus.eu/TrpServer/rest`).

```sh
# from the repo root
pip install requests

# list collections you can see
python3 -m code.transkribus.sync collections

# list documents in our collection
python3 -m code.transkribus.sync docs --col 2224542

# list pages of the notebook
python3 -m code.transkribus.sync pages --col 2224542 --doc 15908163

# pull all pages as PAGE-XML
python3 -m code.transkribus.sync pull --col 2224542 --doc 15908163 \
    --out data/notebook_15908163/page

# push one edited page back as a new transcript layer
python3 -m code.transkribus.sync push --col 2224542 \
    --file data/notebook_15908163/page_final/0001_118820705.xml

# or push a whole directory
python3 -m code.transkribus.sync push-dir --col 2224542 \
    --dir data/notebook_15908163/page_final
```

Each push creates a **new transcript layer** parented to whatever revision
the file was pulled from (the parent `tsId` is read from
`<TranskribusMetadata>` inside the PAGE-XML), so collaborators' edits never
overwrite each other's work on the server — they stack as versions.

## Layout

```
code/transkribus/      legacy Transkribus REST client + sync CLI
data/notebook_15908163/
  page/                latest PAGE-XML pulled from Transkribus (input)
  page_final/          post-processed PAGE-XML, ready to push back
```
