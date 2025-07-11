# https://wiki.nixos.org/wiki/Python
{
  lib,
  buildPythonPackage,
  fetchPypi,
  setuptools,
  pillow,
}:

buildPythonPackage rec {
  pname = "types-pyperclip";
  version = "1.9.0.20250218";
 
  src = fetchPypi {
    inherit version;
    pname = "types_pyperclip";
    hash = "sha256-jAOhbBf64rHlJ+SzUF1xGnfZqplhdjAmzHX7pNMkaeU=";
  };

  # do not run tests
  doCheck = false;

  dependencies = [
  ];

  # specific to buildPythonPackage, see its reference
  pyproject = true;
  build-system = [
    setuptools
  ];
}
