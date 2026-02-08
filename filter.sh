#!/bin/sh
# step 1: a=pip-conda-kbn
# step 2:
a=pip-pyenv-cp314

prepare() {
  cut -d ' ' -f 1 pip-pyenv-cp314.list > pip-pyenv-cp314.pkg-names
  cut -d ' ' -f 1 pip-conda-kbn.list > pip-conda-kbn.pkg-names
  diff pip-pyenv-cp314.pkg-names pip-conda-kbn.pkg-names | \
    grep '^> ' | cut -d' ' -f2 > pip-conda-kbn.extra
}

awk 'NR==FNR{a[$1];next} !($1 in a)' $a.extra $a.list > $a.list.filtered

torch_cpu() {
  pip install torch==2.10.0+cpu -f https://download.pytorch.org/whl/cpu/torch
  pip3 install torch --index-url https://download.pytorch.org/whl/cpu
}

# filter_list.py
#with open('a.extra', 'r') as f_extra:
    # Read extra packages into a set for O(1) lookup, strip to remove whitespace
#    extras = {line.strip() for line in f_extra if line.strip()}

#with open('a.list', 'r') as f_list, open('a.list.new', 'w') as f_new:
#    for line in f_list:
        # Get the package name (first column)
#        pkg = line.split()[0]
#        if pkg not in extras:
#            f_new.write(line)

# pyproject.toml sample
# see https://docs.astral.sh/uv/guides/integration/pytorch/#using-a-pytorch-index
# [project]
# name = "project"
# version = "0.1.0"
# requires-python = ">=3.14.0"
# dependencies = [
#   "torch>=2.9.1",
#   "torchvision>=0.24.1",
# ]
##
# [tool.uv.sources]
# torch = [
#     { index = "pytorch-cpu" },
# ]
# torchvision = [
#     { index = "pytorch-cpu" },
# ]
##
# [[tool.uv.index]]
# name = "pytorch-cpu"
# url = "https://download.pytorch.org/whl/cpu"
# explicit = true
