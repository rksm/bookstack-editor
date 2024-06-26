{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
    let
      pkgs = import nixpkgs { inherit system; };
      pythonPackages = pkgs.python311Packages;
      python = pkgs.python311;

      version-from-pyproject = file:
        with builtins; with pkgs.lib;
        let
          content = readFile file;
          line = findFirst (line: isString line && hasPrefix "version" line) "" (split "\n" content);
          version = (elemAt (splitString "\"" line) 1);
        in
        version;

      bookstack = pythonPackages.buildPythonPackage {
        pname = "bookstack";
        version = "0.1.0";
        build-system = [
          pythonPackages.setuptools-scm
        ];
        propagatedBuildInputs = with pythonPackages; [
          requests
          inflection
          cached-property
          setuptools
        ];
        src = pkgs.fetchFromGitHub {
          owner = "coffeepenbit";
          repo = "bookstack";
          rev = "b88a01a";
          sha256 = "sha256-OJDZ283byQdCyxKPPg68IhkDIn/XrQN+pmab6PqiVQ0=";
        };
        meta = {
          description = "bookstack lib";
        };
        doCheck = false;
      };

      pkg = pythonPackages.buildPythonApplication {
        pname = "bookstack-editor";
        version = version-from-pyproject "${self}/pyproject.toml";
        meta = with pkgs.lib; {
          description = "bookstack editor (client)";
          license = licenses.mit;
        };

        pyproject = true;

        build-system = [
          pythonPackages.setuptools-scm
        ];

        src = ./.;

        propagatedBuildInputs = with pythonPackages; [
          pydantic
          loguru
          bookstack
          tqdm
          python-dotenv
        ];

        pythonRuntimeDepsCheck = false;
      };

    in
    {
      packages.default = pkg;

      devShells.default = pkgs.mkShell {
        venvDir = ".venv";

        buildInputs = [
          pythonPackages.venvShellHook
        ];

        packages = with pkgs; [
          pkg
          python
          zlib
        ];

        postVenvCreation = ''
          unset SOURCE_DATE_EPOCH
        '';

        LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
          pkgs.zlib
          pkgs.stdenv.cc.cc
        ];
      };
    }
    );
}
