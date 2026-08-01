{
  description = "Traianus - Deterministic Computational Substrate for Autonomous Spatial State Governance";

  inputs = {
    # Pinned (Step 4.1 / finding M8): nixos-unstable frozen at a revision
    # with known hash (commit 148bab9c1c3c53136ecb44a6ea356a0ed5b39b06,
    # 2026-08-01). Without pinning, every evaluation drifts and the
    # reproducibility promise is false. To pin the full lock, run on a
    # Nix host: `nix flake lock` and commit the generated flake.lock.
    nixpkgs.url = "github:NixOS/nixpkgs/148bab9c1c3c53136ecb44a6ea356a0ed5b39b06";
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
            echo "Run 'pytest tests/' for the full suite (hermetic + E2E model)."
            echo "Run 'pytest tests/ -m not model' for the hermetic suite (no model, offline)."
            echo "Run 'pytest tests/ -m model' for E2E with the real model (offline, cached)."
          '';
        };
      }
    );
}
