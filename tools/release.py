"""Build an addon zip and, with --upload, publish it on CurseForge.

Usage: python tools/release.py <Name> [--tag <Name>-<version>] [--upload]
Run from the repo root. Without --upload it only builds .release/<Name>-<version>.zip and prints what it would send.
--upload needs the CurseForge token in the environment variable CF_API_KEY.
The GitHub workflow runs this on a tag push. ClearMap is released from the local machine,
because its tiles are not in git.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile

CF = "https://wow.curseforge.com/api"
FOREVER_TYPE = 88568  # CurseForge gameVersionTypeID for WoW Forever, same value the BigWigs packager uses


def fail(message):
    sys.exit("release: " + message)


def read_toc(name):
    path = os.path.join("addons", name, name + ".toc")
    if not os.path.isfile(path):
        fail("no TOC at " + path)
    fields, files = {}, []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        field = re.match(r"##\s*([^:]+):\s*(.*)", line)
        if field:
            fields[field.group(1).strip()] = field.group(2).strip()
        elif line and not line.startswith("#"):
            files.append(line.replace("\\", "/"))
    return fields, files


def changelog_section(name, version):
    path = os.path.join("assets", name, "CHANGELOG.md")
    if not os.path.isfile(path):
        fail("no changelog at " + path)
    text = open(path, encoding="utf-8").read()
    section = re.search(r"^## " + re.escape(version) + r"[ \t]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not section or not section.group(1).strip():
        fail("%s has no section '## %s'. Rename 'Unreleased' before releasing." % (path, version))
    return section.group(1).strip()


def build_zip(name, version):
    root = os.path.join("addons", name)
    os.makedirs(".release", exist_ok=True)
    target = os.path.join(".release", "%s-%s.zip" % (name, version))
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for folder, folders, files in os.walk(root):
            folders.sort()
            for file in sorted(files):
                full = os.path.join(folder, file)
                archive.write(full, name + "/" + os.path.relpath(full, root).replace(os.sep, "/"))
    return target


def curl(arguments, token):
    # The token goes in through stdin so it never shows up in a process list or a log.
    config = 'header = "x-api-token: %s"\n' % token
    result = subprocess.run(["curl", "-sS", "--retry", "3", "-K", "-"] + arguments, input=config, capture_output=True, text=True)
    if result.returncode != 0:
        fail("curl failed: " + result.stderr.strip())
    return result.stdout


def pick_game_version(versions, interface):
    """Newest Forever version, or the one that matches the TOC Interface (16001 is 1.60.1)."""
    forever = [v for v in versions if v.get("gameVersionTypeID") == FOREVER_TYPE]
    if not forever:
        fail("CurseForge lists no game version of type %d" % FOREVER_TYPE)
    wanted = "%d.%d.%d" % (int(interface[0]), int(interface[1:3]), int(interface[3:]))
    exact = [v for v in forever if v["name"] == wanted]
    return (exact or [max(forever, key=lambda v: v["id"])])[0]


def main():
    arguments = sys.argv[1:]
    upload = "--upload" in arguments
    tag = arguments[arguments.index("--tag") + 1] if "--tag" in arguments else None
    names = [a for a in arguments if not a.startswith("--") and a != tag]
    if len(names) != 1:
        fail(__doc__)
    name = names[0]

    fields, files = read_toc(name)
    version, interface, project = fields.get("Version"), fields.get("Interface", ""), fields.get("X-Curse-Project-ID")
    if not version or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        fail("TOC Version must look like 1.2.3, got %r" % version)
    if not re.fullmatch(r"\d{5}", interface):
        fail("TOC Interface must be five digits, got %r" % interface)
    if tag and tag != "%s-%s" % (name, version):
        fail("tag %s does not match TOC version %s-%s" % (tag, name, version))
    missing = [f for f in files if not os.path.isfile(os.path.join("addons", name, f))]
    if missing:
        fail("files listed in the TOC are missing: " + ", ".join(missing))
    notes = changelog_section(name, version)
    archive = build_zip(name, version)
    print("built %s (%.1f MB)" % (archive, os.path.getsize(archive) / 1e6))

    if not upload:
        print("dry run, nothing uploaded. Release notes:\n" + notes)
        return
    if not project:
        fail("TOC has no '## X-Curse-Project-ID'. Create the project on CurseForge first.")
    token = os.environ.get("CF_API_KEY")
    if not token:
        fail("CF_API_KEY is not set")

    try:
        versions = json.loads(curl([CF + "/game/wow/versions"], token))
    except ValueError:
        fail("CurseForge did not return a version list. Check the token.")
    if not isinstance(versions, list):
        fail("CurseForge refused the version list: %s" % versions)
    game = pick_game_version(versions, interface)
    metadata = {
        "displayName": "%s %s" % (name, version),
        "gameVersions": [game["id"]],
        "releaseType": "release",
        "changelog": notes,
        "changelogType": "markdown",
    }
    with tempfile.TemporaryDirectory() as folder:
        metadata_path = os.path.join(folder, "metadata.json")
        json.dump(metadata, open(metadata_path, "w", encoding="utf-8"))
        answer = curl(["-w", "\n%{http_code}", "-F", "metadata=<" + metadata_path, "-F", "file=@" + archive,
                       "%s/projects/%s/upload-file" % (CF, project)], token)
    body, _, status = answer.rpartition("\n")
    if status != "200":
        fail("upload failed with HTTP %s: %s" % (status, body.strip()))
    print("uploaded %s %s for game version %s. CurseForge answered: %s" % (name, version, game["name"], body.strip()))


def self_check():
    versions = [{"id": 1, "gameVersionTypeID": 517, "name": "12.1.5"}, {"id": 7, "gameVersionTypeID": FOREVER_TYPE, "name": "1.60.1"},
                {"id": 9, "gameVersionTypeID": FOREVER_TYPE, "name": "1.60.2"}]
    assert pick_game_version(versions, "16001")["id"] == 7
    assert pick_game_version(versions, "16005")["id"] == 9, "unknown interface falls back to the newest Forever version"


if __name__ == "__main__":
    self_check()
    main()
