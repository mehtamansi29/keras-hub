"""Script to create (and optionally install) a `.whl` archive for KerasHub.

By default this will also create a shim package for `keras-nlp` (the old
package name) that provides a backwards compatible namespace.

Usage:

1. Create `.whl` files in `dist/` and `keras_nlp/dist/`:

```
python3 pip_build.py
```

2. Also install the new packages immediately after:

```
python3 pip_build.py --install
```

3. Only build keras-hub:

```
python3 pip_build.py --install --skip_keras_nlp
```
"""

import argparse
import datetime
import os
import pathlib
import re
import shutil

hub_package = "keras_hub"
nlp_package = "keras_nlp"
build_directory = "tmp_build_dir"
dist_directory = "dist"
to_copy = ["pyproject.toml", "README.md"]


def ignore_files(_, filenames):
    return [f for f in filenames if "_test" in f]


def update_build_files(build_path, package, version, is_nightly=False):
    package_name = package.replace("-", "_")
    build_path = pathlib.Path(build_path)
    pyproj_file = build_path / "pyproject.toml"
    if is_nightly:
        pyproj_contents = pyproj_file.read_text().replace(
            f'name = "{package_name}"', f'name = "{package_name}-nightly"'
        )
        pyproj_file.write_text(pyproj_contents)

    # Update the version.
    if package == hub_package:
        # KerasHub pyproject reads the version dynamically from source.
        version_file = build_path / package / "src" / "version_utils.py"
        version_contents = version_file.read_text()
        version_contents = re.sub(
            "\n__version__ = .*\n",
            f'\n__version__ = "{version}"\n',
            version_contents,
        )
        version_file.write_text(version_contents)
    elif package == nlp_package:
        # For the KerasNLP shim we need to replace the version in the pyproject
        # file, so we can pin the version of the keras-hub in dependencies.
        pyproj_str = pyproj_file.read_text().replace("0.0.0", version)
        pyproj_file.write_text(pyproj_str)


def copy_source_to_build_directory(root_path, package):
    # Copy sources (`keras_hub/` directory and setup files) to build
    # directory
    shutil.copytree(
        root_path / package,
        root_path / build_directory / package,
        ignore=ignore_files,
    )
    for fname in to_copy:
        shutil.copy(root_path / fname, root_path / build_directory / fname)


def build_wheel(build_path, dist_path, version):
    # Build the package
    os.chdir(build_path)
    os.system("python3 -m build")

    # Save the dist files generated by the build process
    if not os.path.exists(dist_path):
        os.mkdir(dist_path)
    for fpath in (build_path / dist_directory).glob("*.*"):
        shutil.copy(fpath, dist_path)

    # Find the .whl file path
    for fname in os.listdir(dist_path):
        if version in fname and fname.endswith(".whl"):
            whl_path = dist_path / fname
            print(f"Build successful. Wheel file available at {whl_path}")
            return whl_path
    print("Build failed.")
    return None


def build(root_path, is_nightly=False, keras_nlp=True):
    if os.path.exists(build_directory):
        raise ValueError(f"Directory already exists: {build_directory}")

    from keras_hub.src.version_utils import __version__  # noqa: E402

    if is_nightly:
        date = datetime.datetime.now()
        version = re.sub(
            r"([0-9]+\.[0-9]+\.[0-9]+).*",  # Match version without suffix.
            r"\1.dev" + date.strftime("%Y%m%d%H%M"),  # Add dev{date} suffix.
            __version__,
        )
    else:
        version = __version__

    try:
        whls = []
        build_path = root_path / build_directory
        dist_path = root_path / dist_directory
        os.mkdir(build_path)

        copy_source_to_build_directory(root_path, hub_package)
        update_build_files(build_path, hub_package, version, is_nightly)
        whl = build_wheel(build_path, dist_path, version)
        whls.append(whl)

        if keras_nlp:
            build_path = root_path / build_directory / nlp_package
            dist_path = root_path / nlp_package / dist_directory

            copy_source_to_build_directory(root_path, nlp_package)
            update_build_files(build_path, nlp_package, version, is_nightly)
            whl = build_wheel(build_path, dist_path, version)
            whls.append(whl)

        return whls
    finally:
        # Clean up: remove the build directory (no longer needed)
        os.chdir(root_path)
        shutil.rmtree(root_path / build_directory)


def install_whl(whls):
    for path in whls:
        print(f"Installing wheel file: {path}")
        os.system(f"pip3 install {path} --force-reinstall --no-dependencies")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--install",
        action="store_true",
        help="Whether to install the generated wheel file.",
    )
    parser.add_argument(
        "--nightly",
        action="store_true",
        help="Whether to generate nightly wheel file.",
    )
    parser.add_argument(
        "--skip_keras_nlp",
        action="store_true",
        help="Whether to build the keras-nlp shim package.",
    )
    args = parser.parse_args()
    root_path = pathlib.Path(__file__).parent.resolve()
    whls = build(root_path, args.nightly, not args.skip_keras_nlp)
    if whls and args.install:
        install_whl(whls)
