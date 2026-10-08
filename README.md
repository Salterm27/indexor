# indexor

A framework for keeping a **curated index of repositories**: one Markdown
file with a table of contents and sections, where every new entry is
requested through an issue, turned into a pull request by a bot, and
published when a maintainer merges it. No dependencies: GitHub Actions and the Python standard library.

📖 The index: [INDEX.md](INDEX.md)

## How it works

1. **Submit** — someone opens an issue with the "Add to the index" form
   (name, URL, section, description, owner).
2. **Validate** — `index-submissions` reviews it and comments the result:
   URL on an allowed host, existing section, no duplicates, length limits.
   Editing the issue validates it again.
3. **Propose** — for a valid submission, the bot opens a pull request that
   adds the entry and the regenerated `INDEX.md`.
4. **Approve** — a maintainer merges the pull request. That publishes the
   entry, deploys the site to GitHub Pages and closes the issue.

To reject a submission, close the issue or its pull request.

### Removing an entry

Removal works the same way in reverse. Anyone can open the "Remove from the
index" form — every entry on the site has a **Request removal** link that
fills in the URL — and give a reason. The bot opens a pull request that
deletes the entry, and a maintainer merges it to take the entry out.

Each entry is its own file, and open submission pull requests are rebuilt
whenever `main` changes, so several submissions can be pending at once
without conflicting.

## Layout

```
indexor.config.json           Title, sections, allowed hosts
data/entries/                 Source of truth: one JSON file per entry
INDEX.md                      Published index (generated, do not edit by hand)
tools/indexor                 CLI (python3, no dependencies)
tools/site/                   The GitHub Pages site (HTML, CSS, JS)
.github/ISSUE_TEMPLATE/       Submission and removal forms (generated)
.github/workflows/            Submissions, lint and site
```

## Make your own

1. Click **Use this template** (or fork the repository). On a fork, also
   turn on **Issues** in Settings → General and enable workflows in the
   **Actions** tab — both are off by default on forks.
2. Edit `indexor.config.json`: title, description, sections and hosts.
3. Delete the files in `data/entries/` if you do not want the existing
   entries.
4. Run `tools/indexor build` and commit. This regenerates `INDEX.md` and the
   submission form with your sections.
5. In **Settings → Actions → General → Workflow permissions**, choose
   **Read and write permissions** and tick **Allow GitHub Actions to create
   and approve pull requests**.
6. In **Settings → Pages → Build and deployment → Source**, choose
   **GitHub Actions** (the workflow cannot enable Pages by itself).

The labels (`submission`, `removal`, `invalid`, `published`, `removed`) are
created automatically with the first request.

## Who can approve

Whoever is allowed to merge pull requests into `main`. Protect the branch
with a ruleset (Settings → Rules → Rulesets) that requires a pull request,
and the only way into the index is a merged, reviewable diff. Add required
approvals or code owners there if you want a narrower set of approvers.

Two things to know when writing that ruleset:

- Pull requests opened by the bot do not trigger other workflows, so do not
  add **required status checks**: they would never report. The bot runs the
  same lint itself before it opens the pull request.
- Do not require a **deployment** before merging: a submission branch is
  never deployed.

## Dependencies and security

- **No packages to install.** The CLI is one Python file using only the
  standard library; the site is plain HTML, CSS and JavaScript with no
  libraries, no fonts or scripts from other domains, and no build step.
- **The only external code** is four official GitHub Actions (`checkout`,
  `configure-pages`, `upload-pages-artifact`, `deploy-pages`), pinned to
  commit hashes. Dependabot proposes updates monthly.
- **Submissions are untrusted input.** Issue content is read from the event
  file and never interpolated into a shell command. URLs must be `https`,
  on an allowed host, and point at a repository root; text is escaped
  before it reaches Markdown, and the site only ever writes it as text.
- **Least privilege.** Each workflow declares the minimum token permissions,
  and workflows that do not push do not keep credentials. The bot can only
  push `index/issue-N` branches; it cannot change `main`.
- The site sends a Content-Security-Policy that blocks everything not served
  from the site itself.

## CLI

```bash
tools/indexor build     # regenerate INDEX.md and the issue forms
tools/indexor lint      # validate config, entries and generated files
tools/indexor site      # generate the site in _site/
tools/indexor add --name "My repo" --url https://github.com/owner/repo \
  --section backend --description "What it does"   # manual entry, no issue
```

To remove or fix an entry, delete or edit its file in `data/entries/`, run
`tools/indexor build`, and open a pull request.

## License

[MIT](LICENSE)
