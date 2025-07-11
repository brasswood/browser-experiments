# https://wiki.nixos.org/wiki/Python
{
  lib,
  buildPythonPackage,
  fetchPypi,
  setuptools,
  pillow,
}:

buildPythonPackage rec {
  pname = "types-PyScreeze";
  version = "1.0.1.20250425";
 
  src = fetchPypi {
    inherit version;
    pname = "types_pyscreeze";
    hash = "sha256-OtiMi5R/iUXqVl3kSjKoFN15HG4cfyWj1YTxhwnUuvY=";
  };

  # do not run tests
  doCheck = false;

  dependencies = [
    pillow
  ];

  # specific to buildPythonPackage, see its reference
  pyproject = true;
  build-system = [
    setuptools
  ];
}
