#!/bin/env python3

"""A small wrapper script to call CodeNarc and interpret its output."""

import os
import subprocess
import sys
import xmltodict


CODENARC_OUTPUT_FILE = 'codenarc-output.xml'


def _print_violations(package_file_path, violations):
    for violation in violations:
        violation_message = f'{violation["@ruleName"]}: {violation["Message"]}'
        print(f'{package_file_path}:{violation["@lineNumber"]}: {violation_message}')


def _print_violations_in_file(package_path, files):
    for package_file in files:
        _print_violations(
            f'{package_path}/{package_file["@name"]}',
            _safe_list_wrapper(package_file["Violation"]),
        )


def _print_violations_in_package(packages):
    for package in [p for p in packages if p['@filesWithViolations'] > 0]:
        # CodeNarc uses the empty string for the top-level package, which we translate to
        # '.', which prevents the violation files from appearing as belonging to '/'.
        package_path = package["@path"]
        if not package_path:
            package_path = '.'

        _print_violations_in_file(package_path, _safe_list_wrapper(package["File"]))


def _remove_report_file():
    if os.path.exists(CODENARC_OUTPUT_FILE):
        os.remove(CODENARC_OUTPUT_FILE)


def _safe_list_wrapper(element):
    """Wrap an XML element in a list if necessary.

    This function is used to safely handle data from xmltodict. If an XML element has
    multiple children, they will be returned in a list. However, a single child is
    returned as a dict. By wrapping single elements in a list, we can use the same code to
    handle both cases.
    """
    return element if isinstance(element, list) else [element]


def main():
    """Run CodeNarc on specified code."""
    parsed_args = sys.argv[1:]

    # -rulesetfiles must not be an absolute path, only a relative one to the CLASSPATH
    codenarc_call = [
        '/usr/bin/codenarc.sh',
        '-rulesetfiles=ruleset.groovy',
        f'-report=xml:{CODENARC_OUTPUT_FILE}',
    ] + parsed_args

    output = subprocess.run(
        codenarc_call,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
    )
    sys.stdout.buffer.write(output.stdout)

    # CodeNarc doesn't fail on compilation errors (?)
    if 'Compilation failed' in str(output.stdout):
        print('Error when compiling files!')
        _remove_report_file()
        return 1

    print(f'CodeNarc finished with code: {output.returncode}')
    if output.returncode != 0:
        _remove_report_file()
        return output.returncode
    if not os.path.exists(CODENARC_OUTPUT_FILE):
        print(f'Error: {CODENARC_OUTPUT_FILE} was not generated, aborting!')
        _remove_report_file()
        return 1

    with open(CODENARC_OUTPUT_FILE) as xml_file:
        xml_doc = xmltodict.parse(xml_file.read())
    _remove_report_file()

    package_summary = xml_doc['CodeNarc']['PackageSummary']
    total_files_scanned = package_summary['@totalFiles']
    total_violations = package_summary['@filesWithViolations']

    print(f'Scanned {total_files_scanned} files')
    if total_violations == '0':
        print('No violations found')
        return 0

    print(f'Found {total_violations} violation(s):')
    _print_violations_in_package(_safe_list_wrapper(xml_doc["CodeNarc"]["Package"]))

    return 1


if __name__ == '__main__':
    sys.exit(main())
