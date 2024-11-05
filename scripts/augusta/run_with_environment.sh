#!/bin/bash

set -euxo pipefail

FIRST_HOST=$1
shift

NUM_NODES=$1
shift

source ~/venv/OLMo/bin/activate

cd ~/OLMo
NCCL_LIB_DIR=/var/lib/tcpxo/lib64 source /var/lib/tcpxo/lib64/nccl-env-profile.sh
export NCCL_NET=FasTrak
HOST_NODE_ADDR=$FIRST_HOST:12345
export OMP_NUM_THREADS=16
export GOOGLE_CLOUD_PROJECT=h100-cluster-owner
#export NCCL_DEBUG=INFO

# Redirect stdout and stderr so that we get a prefix with the node name
export NODENAME=$(hostname -s)
exec > >(trap "" INT TERM; sed -u "s/^/$NODENAME out: /")
exec 2> >(trap "" INT TERM; sed -u "s/^/$NODENAME err: /" >&2)

# kill all other processes consuming GPUs
nvidia-smi --query-compute-apps=pid --format=csv,noheader | xargs -r kill

torchrun --nproc_per_node=8 --nnodes=$NUM_NODES --rdzv-backend=c10d --rdzv-endpoint=$HOST_NODE_ADDR scripts/train.py "$@"
