"""Compile Ress Vocal's Nitro source and write the Bitwig device document."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent / "ress-vocal" / "devkit"  # the shared device devkit
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(HERE)]

import compiler_profiles  # noqa: E402
import project_contracts  # noqa: E402
from document import document  # noqa: E402
from devices.common.document_graph import run  # noqa: E402


def main() -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--compiler-inputs", type=Path, required=True)
    cli.add_argument("--out", type=Path, help="destination .bwdevice file")
    cli.add_argument("--project-file", type=Path, default=HERE / "ress-amp.json")
    args = cli.parse_args()
    project_file = args.project_file.resolve()
    if project_file.parent != HERE:
        cli.error("--project-file must be in the device workspace")
    project = project_contracts.load(project_file)
    inputs, profile = compiler_profiles.validate_inputs(args.compiler_inputs)
    compiler_profiles.require_target(profile, project["target"])
    codec, _ = compiler_profiles.document_parser(inputs, profile)
    output = (args.out or HERE / project["output"]["path"]).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    nitro, = project["sources"]["nitro"]
    sksl, = project["sources"]["sksl"]
    with TemporaryDirectory(prefix="ress-amp-", dir=output.parent) as temporary:
        staging = Path(temporary)
        compiled = staging / "ress_amp.nitrobin"
        compiler_profiles.compile_source(HERE / nitro, compiled, args.compiler_inputs)
        source = staging / "device.json"
        source.write_text(json.dumps(document(
            project, compiled.read_bytes(), (HERE / sksl).read_text(encoding="utf-8")
        ), ensure_ascii=False), encoding="utf-8")
        candidate = staging / output.name
        run([str(codec), "from-json", str(source), str(candidate)])
        candidate.replace(output)

    print(f"{hashlib.sha256(output.read_bytes()).hexdigest()}  {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
