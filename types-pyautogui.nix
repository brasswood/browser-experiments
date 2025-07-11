# https://wiki.nixos.org/wiki/Python
{
  lib,
  buildPythonPackage,
  types-PyScreeze,
  fetchPypi,
  setuptools,
  callPackage
}:

buildPythonPackage rec {
  pname = "types-PyAutoGUI";
  version = "0.9.3.20241230";

  src = fetchPypi {
    inherit version;
    pname = "types_pyautogui";
    hash = "sha256-4HX5gVpOcYHcOmPau18ma+fb6VNPqctTgHV5XbdtmK4=";
  };

  # do not run tests
  doCheck = false;

  # https://nixos.org/manual/nixpkgs/unstable/#handling-dependencies
  dependencies = [
    types-PyScreeze
  ];

  # specific to buildPythonPackage, see its reference
  pyproject = true;
  build-system = [
    setuptools
  ];

  
}
