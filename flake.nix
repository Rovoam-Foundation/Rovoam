{
  description = "Dev-shell flake";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs = { nixpkgs, ... }@inputs: 
  let
    pkgs = nixpkgs.legacyPackages."x86_64-linux";
    python = pkgs.python3;
  in {
    devShells.x86_64-linux.default = pkgs.mkShell {
      packages = with pkgs; [
        (python.withPackages(pypkgs: with pypkgs; [
          rich
	  openai
	  prompt_toolkit
        ]))
      ];
    };
  };
}
