# Autosurfer 🏄
Automatically open a bunch of random websites to thwart attempts at [illegal
internet surveillance](https://ulovliglogning.dk/). Privacy through obscurity?

<video src="/caspervk/autosurfer/raw/branch/master/img/preview.mp4" controls></video>
[Video Preview](https://git.caspervk.net/caspervk/autosurfer/raw/branch/master/img/preview.mp4)

## Getting started
```shell
podman run --rm quay.io/caspervk/autosurfer:latest
```

To show the Firefox GUI:
```shell
podman run --rm --network host --env DISPLAY --security-opt label=type:container_runtime_t quay.io/caspervk/autosurfer:latest
```


## How does it work?
All certificates issued by publicly-trusted Certificate Authorities (CAs) are
published to the [Certificate Transparency (CT)
logs](https://certificate.transparency.dev/). Autosurfer connects to
[Certstream](https://certstream.calidog.io/) to retrieve real-time updates of
newly issued certificates and attempts to open the domain in Firefox using
Selenium.


## Development
```shell
# Build
nix build .#oci
./result | podman load
podman run --rm autosurfer:dev

# Release
podman push autosurfer:dev quay.io/caspervk/autosurfer:latest

# 👉😎👉
podman run --rm -v ./autosurfer/:/autosurfer/:ro --network host --env DISPLAY --security-opt label=type:container_runtime_t autosurfer:dev
```


## Future work
  - Embed [Certstream server](https://github.com/CaliDog/certstream-server)
  rather than relying on hosted service.
