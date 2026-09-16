# The whole service on one rented GPU: vLLM, YOLO, retrieval and the API.
#
# Everything in one container because everything shares one card. Running Qwen
# on a rented box while the API and the detector stayed on a laptop worked for
# testing and is not the deployment: the detector then runs on a CPU at 60ms
# instead of a GPU at 10ms, and Backend has to reach a laptop.
#
# Built on the vLLM image rather than installing vLLM onto a CUDA base. That
# image already carries a matched torch, CUDA and vLLM, and matching them by
# hand is the single most reliable way to lose an afternoon.
FROM vllm/vllm-openai:v0.29.0

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/workspace/.hf \
    YOLO_CONFIG_DIR=/workspace/.ultralytics \
    # Where the two servers listen. vLLM stays on loopback: nothing outside
    # this container has any business talking to the model directly, and the
    # rented box publishes ports to the open internet.
    VLM_PORT=8001 \
    API_PORT=8000

WORKDIR /workspace

# Ultralytics pulls its own torch if left alone, which would replace the one
# vLLM is built against and break both. The base image's torch is kept.
COPY requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /tmp/requirements.txt \
    && python3 -m pip install --no-cache-dir --no-deps "ultralytics==8.3.*" \
    && python3 -m pip install --no-cache-dir "huggingface_hub>=0.26" "py-cpuinfo" "seaborn" \
    && python3 -c "import torch, ultralytics; print('torch', torch.__version__)"

COPY app/ /workspace/app/
COPY docker/serve/entrypoint.sh /usr/local/bin/serve-entrypoint.sh
RUN chmod +x /usr/local/bin/serve-entrypoint.sh

EXPOSE 8000

# The base image's entrypoint is vLLM itself; this replaces it, because the
# container now starts two processes and has to decide when the second may run.
ENTRYPOINT ["/usr/local/bin/serve-entrypoint.sh"]
