#!/usr/bin/env python3
"""Build a release SBOM from the exact files published for one version.

The directory scan of a wheel folder catalogs that folder as an empty
``dist`` package. This script downloads the published wheels and sdist,
checks each SHA256 against the project index, and catalogs the wheels with
Syft's installed-package cataloger. Declared ``Requires-Dist`` entries stay
requirements. They are not recorded as resolved installations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT = "ferroguard"
SYFT_VERSION = "1.54.0"
INDEX = "https://pypi.org/pypi/{project}/{version}/json"
TAG_VERSION = re.compile(r"^v(\d+\.\d+\.\d+)$")
REQUIREMENT_NAME = re.compile(r"^([A-Za-z0-9_.-]+)")
EXTRA_MARKER = re.compile(r"""extra\s*==\s*['"]([^'"]+)['"]""")


def version_of(tag: str) -> str:
    match = TAG_VERSION.fullmatch(tag.strip())
    if not match:
        raise SystemExit(f"refusing {tag}; expected vX.Y.Z")
    return match.group(1)


def is_directory_only_sbom(document: dict) -> bool:
    """True for a scan that never catalogued a versioned distribution."""
    packages = document.get("packages") or []
    for package in packages:
        if package.get("name") == PROJECT and package.get("versionInfo") not in (
            None,
            "",
            "UNKNOWN",
            "NOASSERTION",
        ):
            return False
    if not packages:
        return True
    return all(package.get("filesAnalyzed") is False and not package.get("versionInfo") for package in packages)


def assert_release_sbom(document: dict, version: str) -> None:
    """Reject an empty directory scan and require this distribution version.

    Declared requirements use ``NOASSERTION`` as their version. A concrete
    version on any other package is a resolved installation, which the
    published wheels do not contain.
    """
    if is_directory_only_sbom(document):
        raise SystemExit("refusing directory-only SBOM; it has no catalogued distribution")
    if document.get("name") != f"{PROJECT}-{version}":
        raise SystemExit(f"SBOM name is not {PROJECT}-{version}")
    packages = document.get("packages") or []
    installed = [
        package
        for package in packages
        if package.get("name") == PROJECT and package.get("versionInfo") == version
    ]
    if len(installed) != 1:
        raise SystemExit(f"SBOM does not identify {PROJECT} {version}")
    if not str(installed[0].get("sourceInfo") or "").startswith("installed distribution"):
        raise SystemExit(f"SBOM does not mark {PROJECT} as the installed distribution")
    declared = [
        package
        for package in packages
        if str(package.get("sourceInfo") or "").startswith("declared Requires-Dist:")
    ]
    if not declared:
        raise SystemExit("SBOM does not record a declared requirement")
    for package in declared:
        if package.get("versionInfo") not in ("NOASSERTION",):
            raise SystemExit(f"declared requirement has a resolved version: {package.get('name')}")
    for package in packages:
        if package.get("name") == PROJECT:
            continue
        version_info = package.get("versionInfo")
        if version_info not in (None, "", "NOASSERTION"):
            raise SystemExit(
                f"SBOM records resolved {package.get('name')} {version_info}, "
                "which is not installed in the published wheels"
            )
    files = document.get("files") or []
    if not files:
        raise SystemExit("SBOM does not record published artifact hashes")
    for item in files:
        checksums = item.get("checksums") or []
        values = [entry.get("checksumValue") for entry in checksums if entry.get("algorithm") == "SHA256"]
        if not values or len(values[0]) != 64:
            raise SystemExit(f"published file has no SHA256: {item.get('fileName')}")


def _requirement_name(requirement: str) -> str:
    body = requirement.split(";", 1)[0].strip()
    match = REQUIREMENT_NAME.match(body)
    if not match:
        raise SystemExit(f"refusing requirement {requirement}")
    return match.group(1)


def _extra_name(requirement: str) -> str:
    match = EXTRA_MARKER.search(requirement)
    return match.group(1) if match else ""


def build_release_sbom(
    version: str,
    requires_dist: list[str],
    files: list[dict],
    created: str,
) -> dict:
    """Assemble SPDX from catalogued wheel metadata and published hashes."""
    if not requires_dist:
        raise SystemExit("published wheel has no declared requirements")
    package_id = "SPDXRef-Package-ferroguard"
    packages: list[dict] = [
        {
            "name": PROJECT,
            "SPDXID": package_id,
            "versionInfo": version,
            "downloadLocation": f"https://pypi.org/project/{PROJECT}/{version}/",
            "filesAnalyzed": True,
            "sourceInfo": (
                "installed distribution in the published wheels; "
                "third-party requirements are declared and are not vendored"
            ),
            "licenseConcluded": "NOASSERTION",
            "licenseDeclared": "NOASSERTION",
            "copyrightText": "NOASSERTION",
            "externalRefs": [
                {
                    "referenceCategory": "PACKAGE-MANAGER",
                    "referenceType": "purl",
                    "referenceLocator": f"pkg:pypi/{PROJECT}@{version}",
                }
            ],
        }
    ]
    relationships = [
        {
            "spdxElementId": "SPDXRef-DOCUMENT",
            "relationshipType": "DESCRIBES",
            "relatedSpdxElement": package_id,
        }
    ]
    for index, requirement in enumerate(requires_dist):
        dependency_id = f"SPDXRef-Declared-{index}"
        extra = _extra_name(requirement)
        note = f"declared Requires-Dist: {requirement}; not installed or resolved"
        if extra:
            note = f"{note}; optional extra {extra} is not installed in the base wheel"
        packages.append(
            {
                "name": _requirement_name(requirement),
                "SPDXID": dependency_id,
                "versionInfo": "NOASSERTION",
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "sourceInfo": note,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "copyrightText": "NOASSERTION",
            }
        )
        relationships.append(
            {
                "spdxElementId": package_id,
                "relationshipType": "DEPENDS_ON",
                "relatedSpdxElement": dependency_id,
                "comment": "declared requirement; not a resolved installation",
            }
        )
    spdx_files = []
    for index, item in enumerate(files):
        file_id = f"SPDXRef-File-{index}"
        spdx_files.append(
            {
                "fileName": item["filename"],
                "SPDXID": file_id,
                "checksums": [{"algorithm": "SHA256", "checksumValue": item["sha256"]}],
                "comment": "Published artifact. SHA256 matches the project index digest.",
            }
        )
        relationships.append(
            {
                "spdxElementId": package_id,
                "relationshipType": "OTHER",
                "relatedSpdxElement": file_id,
                "comment": "sha256-verified published artifact of this distribution",
            }
        )
    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"{PROJECT}-{version}",
        "documentNamespace": (
            f"https://github.com/melroyanthony/llm-guardrails/releases/download/v{version}/ferroguard.spdx.json"
        ),
        "creationInfo": {
            "created": created,
            "creators": [f"Tool: syft-{SYFT_VERSION}", "Tool: release_sbom.py"],
        },
        "packages": packages,
        "files": spdx_files,
        "relationships": relationships,
    }


def replacement_needed(documents: list[dict], version: str) -> bool:
    """True when an attached SPDX fails the release content check."""
    if not documents:
        return False
    for document in documents:
        try:
            assert_release_sbom(document, version)
        except SystemExit:
            return True
    return False


def verify_sha256(path: Path, expected: str) -> None:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected:
        raise SystemExit(f"hash mismatch for {path.name}: {digest} != {expected}")


def published_files(index: dict, version: str) -> list[dict]:
    """Return the index entries for this version, with their published digests."""
    info = index.get("info") or {}
    if info.get("version") != version:
        raise SystemExit(f"index version is {info.get('version')}, not {version}")
    files = []
    prefix = f"{PROJECT}-{version}-"
    sdist_name = f"{PROJECT}-{version}.tar.gz"
    for item in index.get("urls") or []:
        filename = item["filename"]
        if item.get("packagetype") == "bdist_wheel" and not filename.startswith(prefix):
            raise SystemExit(f"refusing unexpected wheel {filename}")
        if item.get("packagetype") == "sdist" and filename != sdist_name:
            raise SystemExit(f"refusing unexpected sdist {filename}")
        if item.get("packagetype") not in {"bdist_wheel", "sdist"}:
            raise SystemExit(f"refusing unexpected artifact {filename}")
        files.append(
            {
                "filename": filename,
                "url": item["url"],
                "sha256": item["digests"]["sha256"],
                "packagetype": item["packagetype"],
            }
        )
    wheels = [item for item in files if item["packagetype"] == "bdist_wheel"]
    sdists = [item for item in files if item["packagetype"] == "sdist"]
    if not wheels or len(sdists) != 1:
        raise SystemExit(f"expected wheels and one sdist, found { [item['filename'] for item in files] }")
    return files


def syft_argv(unpacked: Path, version: str) -> list[str]:
    """Scan an unpacked published wheel, not the directory that contains the wheels."""
    return [
        "syft",
        "scan",
        f"dir:{unpacked}",
        "--override-default-catalogers",
        "python-installed-package-cataloger",
        "--source-name",
        PROJECT,
        "--source-version",
        version,
        "-o",
        "syft-json",
    ]


def wheel_identity(document: dict, version: str) -> tuple:
    artifacts = document.get("artifacts") or []
    if len(artifacts) != 1:
        raise SystemExit(f"expected one catalogued distribution, found {len(artifacts)}")
    artifact = artifacts[0]
    if artifact.get("name") != PROJECT or artifact.get("version") != version:
        raise SystemExit(f"catalogued {artifact.get('name')} {artifact.get('version')}, not {PROJECT} {version}")
    if artifact.get("foundBy") != "python-installed-package-cataloger":
        raise SystemExit("wheel was not catalogued as an installed distribution")
    metadata = artifact.get("metadata") or {}
    requires = tuple(metadata.get("requiresDist") or [])
    if not requires:
        raise SystemExit("catalogued wheel has no declared requirements")
    return (artifact["name"], artifact["version"], requires)


def _download(url: str, path: Path) -> None:
    with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310
        path.write_bytes(response.read())


def _catalog(unpacked: Path, version: str, syft: str) -> dict:
    argv = syft_argv(unpacked, version)
    argv[0] = syft
    result = subprocess.run(argv, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "syft failed")
    return json.loads(result.stdout)


def generate_release_sbom(version: str, dest: Path, syft: str = "syft") -> dict:
    """Download the published files, verify their hashes, and catalog the wheels."""
    index_url = INDEX.format(project=PROJECT, version=version)
    with urllib.request.urlopen(index_url, timeout=60) as response:  # noqa: S310
        index = json.load(response)
    files = published_files(index, version)
    dest.mkdir(parents=True, exist_ok=True)
    identities = []
    for item in files:
        path = dest / item["filename"]
        _download(item["url"], path)
        verify_sha256(path, item["sha256"])
        if item["packagetype"] != "bdist_wheel":
            continue
        with tempfile.TemporaryDirectory() as raw:
            unpacked = Path(raw)
            with zipfile.ZipFile(path) as archive:
                archive.extractall(unpacked)
            identities.append(wheel_identity(_catalog(unpacked, version, syft), version))
    first = identities[0]
    for identity in identities[1:]:
        if identity != first:
            raise SystemExit("published wheels do not agree on name, version, or requirements")
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    document = build_release_sbom(version, list(first[2]), files, created)
    assert_release_sbom(document, version)
    return document


def bad_asset_names(documents: dict[str, dict], version: str) -> list[str]:
    """Names of attached SPDX files that fail the release content check."""
    bad = []
    for name, document in documents.items():
        try:
            assert_release_sbom(document, version)
        except SystemExit:
            bad.append(name)
    return bad


def delete_asset_argv(tag: str, name: str, repo: str) -> list[str]:
    if not TAG_VERSION.fullmatch(tag):
        raise SystemExit(f"refusing {tag}; expected vX.Y.Z")
    if not name.endswith(".spdx.json"):
        raise SystemExit(f"refusing to delete {name}")
    return ["gh", "release", "delete-asset", tag, name, "--repo", repo, "--yes"]


def self_test() -> None:
    """Check the empty-directory rejection and the declared-requirement shape."""
    empty = {
        "name": "dist",
        "packages": [{"name": "dist", "versionInfo": None, "filesAnalyzed": False}],
    }
    if not is_directory_only_sbom(empty):
        raise SystemExit("the directory-only SBOM was accepted")
    try:
        assert_release_sbom(empty, "0.3.1")
    except SystemExit as exc:
        if "directory-only" not in str(exc):
            raise
    else:
        raise SystemExit("directory-only SBOM passed the content check")
    files = [
        {"filename": "ferroguard-0.3.1-cp311-abi3-manylinux_2_17_x86_64.whl", "sha256": "a" * 64},
        {"filename": "ferroguard-0.3.1.tar.gz", "sha256": "b" * 64},
    ]
    requires = [
        "pydantic>=2.0,<3.0",
        "fastapi>=0.110,<1.0 ; extra == 'api'",
    ]
    document = build_release_sbom("0.3.1", requires, files, "2026-11-05T00:00:00Z")
    assert_release_sbom(document, "0.3.1")
    if replacement_needed([empty], "0.3.1") is not True:
        raise SystemExit("directory-only SBOM did not require replacement")
    if replacement_needed([document], "0.3.1") is not False:
        raise SystemExit("a catalogued SBOM was treated as empty")
    if "dir:dist" in " ".join(syft_argv(Path("wheel"), "0.3.1")):
        raise SystemExit("syft target is the wheel directory")
    print("release_sbom.py self-test ok")


def _gh_json(argv: list[str]) -> dict:
    result = subprocess.run(argv, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit((result.stderr or result.stdout or "gh failed").strip())
    return json.loads(result.stdout)


def delete_invalid_assets(tag: str, repo: str, version: str) -> list[str]:
    """Delete attached SPDX assets that fail the content check.

    A catalogued ``ferroguard`` SBOM is left in place. This does not delete
    the tag or any non-SBOM asset.
    """
    payload = _gh_json(["gh", "release", "view", tag, "--repo", repo, "--json", "assets"])
    names = [
        asset.get("name") or ""
        for asset in payload.get("assets") or []
        if (asset.get("name") or "").endswith(".spdx.json")
    ]
    if not names:
        return []
    with tempfile.TemporaryDirectory() as raw:
        dest = Path(raw)
        result = subprocess.run(
            [
                "gh",
                "release",
                "download",
                tag,
                "--repo",
                repo,
                "--dir",
                str(dest),
                "--pattern",
                "*.spdx.json",
                "--clobber",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise SystemExit((result.stderr or result.stdout or "gh release download failed").strip())
        documents = {}
        for name in names:
            path = dest / name
            if not path.is_file():
                raise SystemExit(f"SBOM asset was not downloaded: {name}")
            documents[name] = json.loads(path.read_text(encoding="utf-8"))
    removed = []
    for name in bad_asset_names(documents, version):
        argv = delete_asset_argv(tag, name, repo)
        result = subprocess.run(argv, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            raise SystemExit((result.stderr or result.stdout or f"could not delete {name}").strip())
        removed.append(name)
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--delete-invalid", action="store_true")
    parser.add_argument("--version", default="")
    parser.add_argument("--tag", default="")
    parser.add_argument("--repo", default="")
    parser.add_argument("--output", default="ferroguard.spdx.json")
    parser.add_argument("--syft", default="")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.delete_invalid:
        if not args.tag or not args.repo or not args.version:
            raise SystemExit("pass --tag, --repo, and --version")
        delete_invalid_assets(args.tag, args.repo, args.version)
        return
    if args.generate:
        if not args.version:
            raise SystemExit("pass --version")
        syft = args.syft or shutil.which("syft") or "syft"
        document = generate_release_sbom(args.version, Path("published-dist"), syft=syft)
        Path(args.output).write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        return
    parser.error("pass --self-test or --generate")


if __name__ == "__main__":
    main()
