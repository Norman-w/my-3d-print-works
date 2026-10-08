#!/usr/bin/env python3
"""Prepare/audit one frozen Ø76 v5 shell. Never contacts a printer."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
from zipfile import ZipFile

from prepare_fan_tee_v5_print import ROOT, build, dump, sha
from verify_fan76_direct_v1_print import audit

OUT = ROOT / 'output/fan76-smooth-v5-20261008/print'
STL = OUT.parent / 'stl/fan76-smooth-v5-body-clean.stl'
EXPECTED_SHA = 'e0be6b465aebef9dff9f6886d6a49f9420e24ea8416c321caef14fc1e02a42fc'
TEMPLATE = ROOT / 'output/fan76-direct-longtravel-v1-20261007/print/slice/fan76-direct-v1-native-project.3mf'
BAMBU = Path('/Applications/BambuStudio.app/Contents/MacOS/BambuStudio')


def slice_candidate():
    """Isolated native CLI; GUI review and device checks remain separate gates."""
    prepared = OUT / 'fan76-smooth-v5-body-only-prepared.3mf'
    layout = json.loads((OUT / 'prepared-project.json').read_text())
    assert sha(prepared) == layout['sha256']
    assert layout['part_count'] == 1 and layout['parts'][0]['sha256'] == EXPECTED_SHA
    folder = OUT / 'slice'
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / 'fan76-smooth-v5-body-only-cli-candidate.3mf'
    with tempfile.TemporaryDirectory(prefix='fan76-v5-native-cli-') as data:
        command = [str(BAMBU), '--datadir', data, '--debug', '2', '--orient', '0',
                   '--arrange', '0', '--slice', '0', '--export-3mf', target.name,
                   '--outputdir', str(folder), str(prepared)]
        with (folder / 'cli.log').open('w') as log:
            run = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    assert run.returncode == 0, 'Read slice/cli.log; never dispatch a failed slice'
    result = json.loads((folder / 'result.json').read_text())
    assert result['return_code'] == 0 and len(result['sliced_plates']) == 1
    record = {'status': 'CLI_CANDIDATE_NEEDS_AUDIT_AND_GUI_REVIEW', 'command': command,
              'slicer_sha256': sha(BAMBU), 'input_sha256': sha(prepared),
              'package': str(target), 'sha256': sha(target),
              'plates': result['sliced_plates'], 'printer_contacted': False}
    dump(OUT / 'slice-provenance.json', record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'slice', 'audit'])
    parser.add_argument('--package', type=Path)
    parser.add_argument('--project', type=Path)
    args = parser.parse_args()
    assert sha(STL) == EXPECTED_SHA, 'Re-review any replacement geometry before slicing'
    if args.action == 'prepare':
        result = build({'connector': STL}, OUT, TEMPLATE,
                       layout=[('connector', (128., 128.))],
                       package_stem='fan76-smooth-v5-body-only',
                       plate_name='76 v5 - one shell only',
                       expected_parts=1, height_margin_mm=2)
    elif args.action == 'slice':
        result = slice_candidate()
    else:
        assert args.package and args.project
        result = audit(args.package.resolve(), args.project.resolve(), OUT / 'prepared-project.json',
                       expected_parts=1, mother_z_interval=(152, 188))
        with ZipFile(args.package) as archive:
            settings = json.loads(archive.read('Metadata/project_settings.config'))
        result['checks'].update({
            'current_v5_body_only': [r['sha256'] for r in result['parts']] == [EXPECTED_SHA],
            'native_height_margin_at_least_2mm': float(settings['printable_height']) - 248 >= 2,
            'agreed_four_wall_0_2mm_profile': settings['wall_loops'] == '4' and settings['layer_height'] == '0.2',
            'tree_on_build_plate_only': settings['support_on_build_plate_only'] == '1',
        })
        result['status'] = 'DIGITAL_SINGLE_BODY_SLICE_PASS' if all(result['checks'].values()) else 'SLICE_REVIEW_REQUIRED'
        result['native_printable_height_mm'] = float(settings['printable_height'])
        result['model_height_mm'] = 248
        result['no_new_cores_to_print'] = True
        dump(OUT / 'native-audit.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(args.action == 'audit' and not all(result['checks'].values()))


if __name__ == '__main__':
    raise SystemExit(main())
