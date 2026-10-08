# indexor

A framework for keeping a **curated index of repositories**: one Markdown
file with a table of contents and sections, where every new entry is
requested through an issue and published automatically once an approver
accepts it. No dependencies: GitHub Actions and the Python standard library.

📖 The index: [INDEX.md](INDEX.md)

## How it works

1. **Submit** — someone opens an issue with the "Add to the index" form
   (name, URL, section, description, owner).
2. **Validate** — `index-validate` reviews the submission and comments the
   result: URL on an allowed host, existing section, no duplicates, length
   limits. Editing the issue validates it again.
3. **Approve** — an approver adds the **`approved`** label.
4. **Publish** — `index-publish` checks that whoever added the label is
   authorised, adds the entry to `data/entries.json`, regenerates
   `INDEX.md`, commits, closes the issue and deploys the site to GitHub
   Pages.

To reject a submission, just close the issue.

## Layout

```
indexor.config.json           Title, sections, allowed hosts, approvers
data/entries.json             Source of truth for the index
INDEX.md                      Published index (generated, do not edit by hand)
tools/indexor                 CLI (python3, no dependencies)
tools/site/                   The GitHub Pages site (HTML, CSS, JS)
.github/ISSUE_TEMPLATE/       Submission form (generated from the config)
.github/workflows/            Validation, publishing, lint and site
```

## Make your own

1. Click **Use this template** (or fork the repository). On a fork, also
   turn on **Issues** in Settings → General and enable workflows in the
   **Actions** tab — both are off by default on forks.
2. Edit `indexor.config.json`: title, description, sections and hosts.
3. Empty `data/entries.json` (`[]`) if you do not want the existing entries.
4. Run `tools/indexor build` and commit. This regenerates `INDEX.md` and the
   submission form with your sections.
5. In **Settings → Actions → General → Workflow permissions**, choose
   **Read and write permissions**.
6. In **Settings → Pages → Build and deployment → Source**, choose
   **GitHub Actions** (the workflow cannot enable Pages by itself).

The labels (`submission`, `invalid`, `approved`, `published`) are created
automatically with the first submission.

## Who can approve

- By default, anyone with the **Admin** or **Maintain** role on the
  repository.
- If `approvers` in `indexor.config.json` lists users, **only** they can:
  `"approvers": ["octocat"]`.

If someone without authorisation adds the label, the workflow removes it and
says so on the issue.

> **Main branch**: the bot publishes with a direct push to `main`. A ruleset
> that requires pull requests on `main` blocks that push, so the control here
> is the approver check, not the ruleset. Anyone with write access can still
> edit the files by hand; opening issues does not require it.

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
  and workflows that do not push do not keep credentials.
- The site sends a Content-Security-Policy that blocks everything not served
  from the site itself.

## CLI

```bash
tools/indexor build     # regenerate INDEX.md and the submission form
tools/indexor lint      # validate config, entries and generated files
tools/indexor site      # generate the site in _site/
tools/indexor add --name "My repo" --url https://github.com/owner/repo \
  --section backend --description "What it does"   # manual entry, no issue
```

To remove or fix an entry, edit `data/entries.json` and run
`tools/indexor build`.

## License

[MIT](LICENSE)
