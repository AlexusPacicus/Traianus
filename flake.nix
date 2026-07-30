{
  description = "Traianus - Deterministic Computational Substrate for Autonomous Spatial State Governance";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        # Entorno Python con las dependencias declaradas en pyproject.toml
        pythonEnv = pkgs.python311.withPackages (ps: with ps; [
          fastapi
          uvicorn
          pydantic
          sentence-transformers
          numpy
          # Dependencias opcionales de test
          pytest
          pytest-asyncio
          httpx
        ]);
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            pythonEnv
            pkgs.sqlite
          ];

          shellHook = ''
            echo "Traianus Nix Development Shell Activated"
            echo "Python environment: $(python --version)"
            echo "Run 'pytest tests/test_control_plane.py' to execute isolated test suite."
          '';
        };
      }
    );
}
