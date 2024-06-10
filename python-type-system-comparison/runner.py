import argparse
import json
import os
import sys


parser = argparse.ArgumentParser("Run code on supported python type systems")
parser.add_argument('-f', '--filename', help='The Python code to be type checked.')
args = parser.parse_args()

if args.filename is None:
    print('Please use -f to specify the target Python code.')
    sys.exit()

print(args.filename)

print('>>> python runtime <<<')
os.system(f'./env/bin/python3 {args.filename}')

print('>>> mypy <<<')
os.system(f'./env/bin/mypy {args.filename}')

print('>>> pytype <<<')
os.system(f'./env/bin/pytype {args.filename}')

print('>>> pyright <<<')
os.system(f'./env/bin/pyright {args.filename}')

# For pyre, we need to create a tmp folder to run on a single target.
print('>>> pyre <<<')
os.system('mkdir ./pyre_dir')
os.system(f'cp ./{args.filename} ./pyre_dir')
os.system('rm ./.pyre_configuration')
pyre_configuration = {
    "site_package_search_strategy": "pep561",
    "source_directories": [f"./pyre_dir"],
}
with open('./.pyre_configuration', 'w') as f:
    json.dump(pyre_configuration, f)
os.system(f"./env/bin/pyre")
os.system('rm -rf ./pyre_dir')
