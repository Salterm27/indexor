"""Tests for tools/indexor. Standard library only: python3 -m unittest discover -s tests"""
import contextlib, glob, importlib.machinery, importlib.util, io, json, os, re, shutil, tempfile, types, unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_tool():
    loader = importlib.machinery.SourceFileLoader("indexor", os.path.join(REPO, "tools", "indexor"))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader("indexor", loader))
    loader.exec_module(module)
    return module


CONFIG = {
    "title": "Test index", "description": "For tests.", "output": "INDEX.md",
    "allowed_hosts": ["github.com"],
    "sections": [{"id": "backend", "name": "Backend", "description": "APIs."},
                 {"id": "docs", "name": "Docs & guides", "description": ""}],
}


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def issue(body, number=7, state="open"):
    return {"number": number, "state": state, "created_at": "2026-01-02T03:04:05Z",
            "user": {"login": "someone"}, "body": body}


def submission(name="Thing", url="https://github.com/acme/thing", section="Backend",
               description="Does a thing.", owner="@acme"):
    return issue(f"### Name\n\n{name}\n\n### Repository URL\n\n{url}\n\n### Section\n\n{section}\n\n"
                 f"### Description\n\n{description}\n\n### Owner\n\n{owner}")


def removal(url="https://github.com/acme/thing", reason="Archived."):
    return issue(f"### Repository to remove\n\n{url}\n\n### Reason\n\n{reason}", number=8)


class ToolCase(unittest.TestCase):
    """Runs the tool against a throwaway copy of the repository layout."""

    def setUp(self):
        self.t = load_tool()
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        self.t.ROOT = self.root
        self.t.CONFIG = os.path.join(self.root, "indexor.config.json")
        self.t.ENTRIES = os.path.join(self.root, "data", "entries")
        self.t.TEMPLATES = os.path.join(self.root, ".github", "ISSUE_TEMPLATE")
        os.makedirs(self.t.ENTRIES)
        with open(self.t.CONFIG, "w") as f:
            json.dump(CONFIG, f)

    def run_cmd(self, func, **args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = func(types.SimpleNamespace(**args))
        return code, out.getvalue().strip()

    def event(self, data):
        path = os.path.join(self.root, "event.json")
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def review(self, data, write=False):
        report = os.path.join(self.root, "report.md")
        _, state = self.run_cmd(self.t.cmd_review, issue=self.event(data), report=report, write=write)
        return state, read(report) if os.path.exists(report) else ""

    def entries(self):
        return self.t.load_entries()

    def index(self):
        return read(os.path.join(self.root, "INDEX.md"))


class ParsingTests(ToolCase):
    def test_reads_issue_form_fields(self):
        fields = self.t.issue_fields("### Name\r\n\r\nThing\r\n\r\n### Owner\r\n\r\n_No response_\r\n")
        self.assertEqual(fields, {"Name": "Thing", "Owner": ""})

    def test_accepts_webhook_event_or_bare_issue(self):
        bare = submission()
        for data in (bare, {"issue": bare}):
            entry = self.t.entry_from_issue(data, CONFIG)
            self.assertEqual((entry["name"], entry["section"], entry["issue"]), ("Thing", "backend", 7))
        self.assertEqual(entry["date"], "2026-01-02")

    def test_kinds(self):
        self.assertEqual(self.t.kind_of(submission(), CONFIG), "submission")
        self.assertEqual(self.t.kind_of(removal(), CONFIG), "removal")
        self.assertEqual(self.t.kind_of(issue("The site is broken"), CONFIG), "unrelated")
        self.assertEqual(self.t.kind_of(issue(None), CONFIG), "unrelated")


class ValidationTests(ToolCase):
    def problems(self, **fields):
        entry = self.t.entry_from_issue(submission(**fields), CONFIG)
        return " ".join(self.t.validate_entry(entry, CONFIG, self.entries()))

    def test_valid_entry_has_no_problems(self):
        self.assertEqual(self.problems(), "")

    def test_rejects_unsafe_or_foreign_urls(self):
        for url in ("http://github.com/acme/thing", "javascript:alert(1)", "github.com/acme/thing", ""):
            self.assertIn("https://", self.problems(url=url), url)
        self.assertIn("must be on", self.problems(url="https://evil.example/acme/thing"))
        self.assertIn("must be on", self.problems(url="https://github.com.evil.example/acme/thing"))

    def test_url_must_be_a_repository_root(self):
        for url in ("https://github.com/acme", "https://github.com/acme/thing/issues",
                    "https://github.com/acme/thing?x=1", "https://github.com/acme/thing#readme"):
            self.assertIn("root of a repository", self.problems(url=url), url)

    def test_rejects_unknown_section_and_missing_or_long_text(self):
        self.assertIn("section", self.problems(section="Nope"))
        self.assertIn("name", self.problems(name="_No response_"))
        self.assertIn("name", self.problems(name="x" * 61))
        self.assertIn("description", self.problems(description="x" * 201))
        self.assertIn("owner", self.problems(owner="x" * 61))

    def test_detects_duplicates_however_the_url_is_written(self):
        self.review(submission(), write=True)
        for url in ("https://github.com/acme/thing", "https://github.com/ACME/Thing/",
                    "https://github.com/acme/thing.git"):
            self.assertIn("already in the index", self.problems(url=url), url)


class EscapingTests(ToolCase):
    def test_markdown_is_escaped_and_flattened(self):
        self.assertEqual(self.t.md("a|b [x](y)\n<b>`c`"), "a\\|b \\[x\\](y) \\<b\\>\\`c\\`")

    def test_bot_comments_cannot_mention_people(self):
        self.assertNotIn("@octocat", self.t.quiet("hi @octocat"))

    def test_hostile_text_cannot_break_the_index_table(self):
        self.review(submission(name="Evil](https://evil.example) | x", description="a | b\n\n## Heading"), write=True)
        row = [line for line in self.index().splitlines() if "acme/thing" in line][0]
        self.assertEqual(row.count("|") - row.count("\\|"), 4)
        # The only unescaped "](" is the one closing the real link.
        self.assertEqual(re.findall(r"(?<!\\)\]\((\S+?)\)", row)[0], "https://github.com/acme/thing")
        self.assertNotRegex(row, r"(?<!\\)\]\(https://evil")
        self.assertNotIn("\n## Heading", self.index())


class RequestTests(ToolCase):
    def test_valid_submission_is_only_written_when_asked(self):
        state, report = self.review(submission())
        self.assertEqual(state, "valid")
        self.assertIn("Valid submission", report)
        self.assertEqual(self.entries(), [])
        self.review(submission(), write=True)
        self.assertEqual([e["url"] for e in self.entries()], ["https://github.com/acme/thing"])
        self.assertIn("[Thing](https://github.com/acme/thing)", self.index())

    def test_invalid_submission_reports_and_writes_nothing(self):
        state, report = self.review(submission(url="http://x"), write=True)
        self.assertEqual(state, "invalid")
        self.assertIn("needs changes", report)
        self.assertEqual(self.entries(), [])

    def test_unrelated_issue_is_ignored(self):
        self.assertEqual(self.review(issue("hello"), write=True), ("unrelated", ""))

    def test_removal_deletes_the_entry(self):
        self.review(submission(), write=True)
        state, report = self.review(removal(url="https://github.com/Acme/thing/"), write=True)
        self.assertEqual(state, "valid")
        self.assertIn("Valid removal request", report)
        self.assertEqual(self.entries(), [])
        self.assertNotIn("acme/thing", self.index())

    def test_removal_needs_an_existing_entry_and_a_reason(self):
        state, report = self.review(removal(reason="_No response_"), write=True)
        self.assertEqual(state, "invalid")
        self.assertIn("not in the index", report)
        self.assertIn("reason", report)

    def test_titles(self):
        self.review(submission(), write=True)
        self.assertEqual(self.run_cmd(self.t.cmd_title, issue=self.event(removal()))[1], "Remove Thing from the index")
        other = submission(name="Other", url="https://github.com/acme/other")
        self.assertEqual(self.run_cmd(self.t.cmd_title, issue=self.event(other))[1], "Add Other to the index")

    def test_report_can_be_a_bare_file_name(self):
        # Regression: the workflows pass a path with no directory.
        here = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, here)
        self.run_cmd(self.t.cmd_review, issue=self.event(submission()), report="report.md", write=False)
        self.assertTrue(os.path.exists(os.path.join(self.root, "report.md")))


class GenerationTests(ToolCase):
    def test_contents_link_to_sections_and_count_entries(self):
        self.review(submission(section="Docs & guides"), write=True)
        text = self.index()
        self.assertIn("- [Docs & guides](#docs--guides) (1)", text)
        self.assertIn("- [Backend](#backend) (0)", text)
        self.assertIn("**1** repository.", text)

    def test_lint_passes_after_build_and_catches_stale_files(self):
        self.review(submission(), write=True)
        self.assertEqual(self.run_cmd(self.t.cmd_build)[0], 0)
        self.assertEqual(self.run_cmd(self.t.cmd_lint)[0], 0)
        with open(os.path.join(self.root, "INDEX.md"), "a") as f:
            f.write("edited by hand\n")
        code, out = self.run_cmd(self.t.cmd_lint)
        self.assertEqual(code, 1)
        self.assertIn("out of date", out)

    def test_lint_catches_duplicate_entry_files(self):
        self.review(submission(), write=True)
        files = self.t.entry_files()
        shutil.copy(files[0], os.path.join(self.t.ENTRIES, "copy.json"))
        self.run_cmd(self.t.cmd_build)
        self.assertEqual(self.run_cmd(self.t.cmd_lint)[0], 1)

    def test_site_data_exposes_only_public_fields(self):
        self.review(submission(), write=True)
        dest = os.path.join(self.root, "_site")
        self.run_cmd(self.t.cmd_site, dest=dest)
        data = json.loads(read(os.path.join(dest, "index.json")))
        self.assertEqual(sorted(data["entries"][0]), ["date", "description", "name", "owner", "section", "url"])
        self.assertTrue(os.path.exists(os.path.join(dest, "index.html")))


class RepositoryTests(unittest.TestCase):
    """Checks on the real repository files."""

    def workflows(self):
        return {f: read(f) for f in glob.glob(os.path.join(REPO, ".github", "workflows", "*.yml"))}

    def test_repository_passes_its_own_lint(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = load_tool().cmd_lint(None)
        self.assertEqual(code, 0, out.getvalue())

    def test_workflows_never_put_issue_text_in_a_command(self):
        # Titles, bodies, labels and branch names are attacker-controlled.
        risky = re.compile(r"\$\{\{[^}]*(\.title|\.body|\.label\.name|head_ref|head\.ref|\.login)[^}]*\}\}")
        for path, text in self.workflows().items():
            in_run = False
            for line in text.splitlines():
                if re.match(r"\s*(- )?run:", line):
                    in_run, indent = True, len(line) - len(line.lstrip())
                elif in_run and line.strip() and len(line) - len(line.lstrip()) <= indent:
                    in_run = False
                if in_run:
                    self.assertIsNone(risky.search(line), f"{os.path.basename(path)}: {line.strip()}")

    def test_actions_are_pinned_to_commit_hashes(self):
        for path, text in self.workflows().items():
            for ref in re.findall(r"uses:\s*(\S+)", text):
                if not ref.startswith("./"):
                    self.assertRegex(ref, r"@[0-9a-f]{40}$", os.path.basename(path))

    def test_site_always_revalidates_its_data(self):
        # Regression: a cached index.json hid newly published entries.
        self.assertIn('fetch("index.json", { cache: "no-cache" })', read(os.path.join(REPO, "tools", "site", "app.js")))

    def test_site_loads_nothing_from_other_domains(self):
        for path in glob.glob(os.path.join(REPO, "tools", "site", "*")):
            text = read(path)
            for tag in re.findall(r"<(?:script|link|img)[^>]*>", text, flags=re.IGNORECASE):
                self.assertNotRegex(tag, r"(src|href)=[\"']?(https?:)?//", os.path.basename(path))
            self.assertNotRegex(text, r"@import|url\(\s*[\"']?https?:", os.path.basename(path))


if __name__ == "__main__":
    unittest.main()
