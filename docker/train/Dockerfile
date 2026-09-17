# Training image for the FixHome detector.
#
# Built once, pushed to a registry, and pulled whenever a GPU is rented. The
# point is that renting a machine costs a pull and nothing else: no pip install
# over a slow link, no CUDA mismatch to rediscover, no half-remembered setup
# steps. Everything that takes time to install lives in the image; everything
# that changes often (dataset, weights, results) is fetched at run time.
#
#   docker build -f docker/train/Dockerfile -t <user>/fixhome-trainer:1.0 .
#   docker push <user>/fixhome-trainer:1.0
#
# Versions are pinned rather than floating. An image that silently upgrades
# torch between two rentals produces numbers that cannot be compared, which is
# exactly what a reproducible experiment must not do.

FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Ultralytics otherwise writes settings and downloads into a home directory
    # that does not survive the container, and phones home on every run.
    YOLO_CONFIG_DIR=/workspace/.ultralytics \
    ULTRALYTICS_NO_ANALYTICS=1 \
    HF_HOME=/workspace/.cache/huggingface \
    MPLBACKEND=Agg

# libgl and libglib are needed by OpenCV, which Ultralytics pulls in; without
# them training fails at the first image read with an unhelpful import error.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements-model.txt requirements-train.txt ./
RUN pip install --no-cache-dir -r requirements-train.txt

# The project code is small and changes often, so it is copied last: editing it
# rebuilds one thin layer instead of reinstalling the whole toolchain.
# Neither the corpus nor the chat tools are read by entrypoint.sh: it pulls the
# dataset from the Hub and runs `yolo detect train`. Copying them in meant every
# corpus edit rebuilt this image and replaced :latest — including while a rented
# box was halfway through pulling it, which leaves the pull retrying against
# layers that no longer exist. Three machines sat at "loading" that way.
COPY docker/train/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
CMD ["train"]
