import json
from pathlib import Path

from create_dependency import _read_deps


def _serialize_sets(obj):
    if isinstance(obj, set):
        return list(obj)

    return obj


def create_version_tree(version, path):
    dependency_tree = _read_deps(path)
    trees = Path("trees")
    trees.mkdir(exist_ok=True)
    with open(Path(trees, version + ".json"), "wt") as fout:
        fout.write(json.dumps(dependency_tree, indent=4, default=_serialize_sets))


if __name__ == '__main__':
    create_version_tree("14.0", "~/odoo/versions/14.0")
    create_version_tree("15.0", "~/odoo/versions/15.0")
