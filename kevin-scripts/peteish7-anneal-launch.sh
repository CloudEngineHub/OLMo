#!/usr/bin/env bash

set -ex

# CONFIG_NAME="peteish7-anneal"
# CONFIG_NAME="peteish7-anneal-B34v0x10"
# CONFIG_NAME="peteish7-anneal-B34v0.1x50"

# bash sewon-scripts/peteish7-anneal-launch.ch peteish7-anneal-from-1T-scitech_sw
# bash sewon-scripts/peteish7-anneal-launch.ch peteish7-anneal-from-1T-edu
# bash sewon-scripts/peteish7-anneal-launch.ch peteish7-anneal-from-1T-health

# bash sewon-scripts/peteish7-anneal-launch.ch peteish7-anneal-from-1T-history
# bash sewon-scripts/peteish7-anneal-launch.ch peteish7-anneal-from-1T-ent_sports
# bash sewon-scripts/peteish7-anneal-launch.ch peteish7-anneal-from-1T-lit

# bash sewon-scripts/peteish7-anneal-launch.ch peteish7-anneal-from-1T-politics
# bash sewon-scripts/peteish7-anneal-launch.ch peteish7-anneal-from-1T-fin
# bash sewon-scripts/peteish7-anneal-launch.ch peteish7-anneal-from-1T-others

CONFIG_NAME=$1
NUM_NODES=8

gantry run \
  --workspace ai2/ds-olmo \
  --task-name ${CONFIG_NAME} \
  --description ${CONFIG_NAME} \
  --priority high \
  --beaker-image petew/olmo-torch23-gantry \
  --cluster ai2/jupiter-cirrascale-2 \
  --gpus 8 \
  --replicas "${NUM_NODES}" \
  --leader-selection \
  --host-networking \
  --budget ai2/oe-training \
  --no-nfs \
  --weka oe-training-default:/weka/oe-training-default \
  --propagate-failure \
  --propagate-preemption \
  --synchronized-start-timeout 90m \
  --no-python \
  --env LOG_FILTER_TYPE=local_rank0_only \
  --env OMP_NUM_THREADS=8 \
  --env OLMO_TASK=model \
  --env S3_PROFILE=default \
  --env WEKA_PROFILE=default \
  --env-secret AWS_CONFIG=KEVINFARHAT_AWS_CONFIG \
  --env-secret AWS_CREDENTIALS=KEVINFARHAT_AWS_CREDENTIALS \
  --env-secret WANDB_API_KEY=KEVINFARHAT_WANDB_API_KEY \
  --shared-memory 10GiB \
  --yes \
  --timeout=259200 \
  -- /bin/bash -c "kevin-scripts/peteish7.sh \$BEAKER_LEADER_REPLICA_HOSTNAME ${NUM_NODES} \$BEAKER_REPLICA_RANK ${CONFIG_PATH}"
  # --preemptible \

