{
  inputs = {
    nixpkgs-unstable = {
      url = "github:NixOS/nixpkgs/nixos-unstable";
    };
  };

  outputs = {
    self,
    nixpkgs,
    ...
  }: let
    system = "x86_64-linux";
    pkgs = nixpkgs.legacyPackages.${system};
    env = pkgs.buildEnv {
      name = "autosurfer-env";
      pathsToLink = ["/bin" "/autosurfer"];
      paths = [
        (pkgs.lib.fileset.toSource {
          root = ./.;
          fileset = ./autosurfer;
        })
        # https://discourse.nixos.org/t/declare-firefox-extensions-and-settings/36265/7
        (pkgs.wrapFirefox pkgs.firefox-unwrapped {
          # https://mozilla.github.io/policy-templates/
          extraPolicies = {
            # We *want* to leak DNS requests
            DNSOverHTTPS = {
              Enabled = false;
            };
            # cba leaking tabs
            PopupBlocking = {
              Default = true;
              Locked = true; # doesn't work without locking
            };
            # Disable downloading
            DownloadDirectory = "/unwritable-downloads";
            ExtensionSettings = {
              "uBlock0@raymondhill.net" = {
                install_url = "https://addons.mozilla.org/firefox/downloads/latest/ublock-origin/latest.xpi";
                installation_mode = "force_installed";
              };
            };
          };
        })
        pkgs.geckodriver
        (pkgs.python3.withPackages (ps: [
          ps.selenium
          ps.websockets
        ]))
        pkgs.bash
        pkgs.coreutils
      ];
    };
  in {
    # https://wiki.nixos.org/wiki/Flakes

    # `nix build`
    packages.${system} = {
      # https://wiki.nixos.org/wiki/Docker#Creating_images
      # https://nixos.org/manual/nixpkgs/stable/#sec-pkgs-dockerTools
      # https://github.com/NixOS/nixpkgs/blob/master/pkgs/build-support/docker/examples.nix
      oci = pkgs.dockerTools.streamLayeredImage {
        name = "autosurfer";
        tag = "dev";
        created = builtins.substring 0 8 self.lastModifiedDate;
        contents = [
          env
          # Firefox ships with its own certificate store, but the websockets
          # python library does not.
          pkgs.dockerTools.caCertificates
        ];
        extraCommands = ''
          # Selenium requires /tmp
          mkdir --mode=1777 tmp/
          # There doesn't seem to be a way to disable downloads in Firefox, but
          # they will all fail if the downloads folder is unwritable.
          mkdir unwritable-downloads/
          ${pkgs.busybox}/bin/chattr +i unwritable-downloads/
        '';
        config = {
          Env = [
            # HOME is not set by podman (but it is by docker??), and is
            # required for Firefox to start.
            "HOME=/"
          ];
          Entrypoint = ["python" "/autosurfer/main.py"];
        };
      };

      # `nix shell`
      default = env;
    };
  };
}
