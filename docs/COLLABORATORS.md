# Connecting to Transkribus

Each collaborator uses **their own Transkribus account**. Credentials live in
your shell environment, never in this repository.

## 1. Get access

- Ask Sinai to invite you as a GitHub collaborator on this repo.
- Ask Sinai (or the collection owner) to share Transkribus collection
  `2224542` with your Transkribus user. You need at least the *Transcriber*
  role to pull pages; *Editor* to push edits back as new layers.

## 2. Set your credentials

Add these two lines to `~/.zshrc` (macOS default) or `~/.bashrc` (Linux),
using **your own** Transkribus email and password:

```sh
export TRANSKRIBUS_USER='you@example.org'
export TRANSKRIBUS_PASS='your-password'
```

Then reload your shell:

```sh
source ~/.zshrc      # or ~/.bashrc
```

Check it worked:

```sh
echo $TRANSKRIBUS_USER
```

> **Never** put your password in a file inside this repo, in a commit
> message, or in a chat. The CLI reads it from your environment only.

### Auth route (you don't need to set this)

The CLI authenticates with the **legacy OpenID Connect route** by default
([docs](https://help.transkribus.org/transkribus-legacy-api)), which is what
ordinary Transkribus accounts use — so as a collaborator you set nothing
extra. Your `TRANSKRIBUS_USER`/`TRANSKRIBUS_PASS` are exchanged for a bearer
token automatically.

(The collection owner with privileged API access sets
`export TRANSKRIBUS_AUTH=login` to use the internal `/auth/login` route
instead. Leave it unset.)

## 3. Install Python dependency

```sh
pip install requests
```

## 4. Test the connection

From the repo root:

```sh
python3 -m code.transkribus.sync collections
```

You should see a table that includes our collection (`colId 2224542`). If
you get `Login failed`, double-check the env vars; if the collection isn't
in the list, your Transkribus user hasn't been invited yet. A
`token request failed (401)` means your email/password is wrong.

## 5. Common commands

```sh
# list pages of the notebook
python3 -m code.transkribus.sync pages --col 2224542 --doc 15908163

# pull all pages locally
python3 -m code.transkribus.sync pull --col 2224542 --doc 15908163 \
    --out data/notebook_15908163/page

# push an edited page back as a new transcript layer
python3 -m code.transkribus.sync push --col 2224542 \
    --file path/to/edited_page.xml
```

Each push creates a **new transcript layer** on top of the version you
pulled — collaborators' edits never overwrite each other on the server.
