{
  pkgs ? import <nixpkgs> { }
}:

with pkgs;
let
  rust = import (fetchTarball "https://github.com/nix-community/fenix/archive/main.tar.gz") { };
  types-PyScreeze = python3Packages.callPackage ./types-pyscreeze.nix { };
  types-PyAutoGUI = python3Packages.callPackage ./types-pyautogui.nix { inherit types-PyScreeze; };
  types-pyperclip = python3Packages.callPackage ./types-pyperclip.nix { };
in

python3Packages.buildPythonPackage rec {
  pname = "experiment";
  version = "0.0.6";
  src = ./.;
  nativeBuildInputs = with python3Packages; [
    mypy
    scrot
    xclip
    rust.stable.toolchain
  ];
  pyproject = true;
  propagatedBuildInputs = with python3Packages; [
    opencv-python
    pyautogui
    tkinter
    humanize
    pyperclip
    pathspec
    types-PyAutoGUI
    types-pyperclip
  ];
}
