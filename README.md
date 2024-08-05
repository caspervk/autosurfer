# Autosurfer 🏄
Automatically open a bunch of random websites to thwart attempts at [illegal
internet surveillance](https://ulovliglogning.dk/). Privacy through obscurity?

<video src="/caspervk/autosurfer/raw/branch/master/img/preview.mp4" controls></video>


# Getting Started
```shell
podman run --rm -it quay.io/caspervk/autosurfer:latest
```

To show the Firefox GUI:
```shell
podman run --rm -it --network host --env DISPLAY --security-opt label=type:container_runtime_t quay.io/caspervk/autosurfer:latest
```


# Building
```shell
nix build .#oci
./result | podman load
podman run --rm -it autosurfer:dev
# podman push autosurfer:dev quay.io/caspervk/autosurfer:latest
```
