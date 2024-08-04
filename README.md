# Autosurfer 🏄
Automatically open a bunch of random websites to thwart attempts at [illegal
internet surveillance](https://ulovliglogning.dk/). Privacy through obscurity?


# Getting Started
```shell
podman run --rm -it quay.io/caspervk/autosurfer:latest
```


# Building
```shell
nix build .#oci
./result | podman load
podman run --rm -it autosurfer:0.0.1
# podman push autosurfer:0.0.1 quay.io/caspervk/autosurfer:0.0.1
```
