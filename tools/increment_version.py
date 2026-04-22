#!/usr/bin/env python3
from argparse import ArgumentParser
from re import search, sub

class VersionUpdater:

    def __init__(self, file_path):
        self.file_path = file_path
        self.current_version = self.get_current_version()

    def get_current_version(self):
        with open(self.file_path, 'r') as file:
            for line in file:
                if line.startswith('    VERSION ='):
                    return search(r'\d+\.\d+\.\d+', line).group()

    def update_version(self, new_version):
        with open(self.file_path, 'r') as file:
            lines = file.readlines()
        with open(self.file_path, 'w') as file:
            for line in lines:
                if line.startswith('    VERSION ='):
                    line = f"    VERSION = '{new_version}'\n"
                file.write(line)

    def increment_version(self, major=False, minor=False, patch=False):
        major_num, minor_num, patch_num = map(int, self.current_version.split('.'))
        if major:
            new_version = f'{major_num + 1}.0.0'
        elif minor:
            new_version = f'{major_num}.{minor_num + 1}.0'
        else:
            new_version = f'{major_num}.{minor_num}.{patch_num + 1}'
        self.update_version(new_version)
        self.current_version = new_version
        print(f'Version updated to {new_version}')

    def update_setup_py_version(self, file_path: str) -> None:
        with open(file_path, 'r') as file:
            file_data = file.read()
        updated_data = sub(r"version=['\"]\d+\.\d+\.\d+['\"]", f"version='{self.current_version}'", file_data)
        with open(file_path, 'w') as file:
            file.write(updated_data)

def main():
    parser = ArgumentParser(description='Increment version in controller.py')
    parser.add_argument('--major', action='store_true', help='Increment major version')
    parser.add_argument('--minor', action='store_true', help='Increment minor version')
    parser.add_argument('--patch', action='store_true', help='Increment patch version')
    args = parser.parse_args()
    updater = VersionUpdater('src/xmrsigner/controller.py')
    updater.increment_version(args.major, args.minor, args.patch)
    updater.update_setup_py_version('setup.py')

if __name__ == '__main__':
    main()
