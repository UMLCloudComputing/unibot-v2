#!/bin/bash

helm repo add nvidia https://helm.ngc.nvidia.com/nvidia \
&& helm repo update

helm install gpu-operator nvidia/gpu-operator \
--namespace gpu-operator \
--create-namespace \
--version=v25.10.0 \
--wait \
--timeout 15m


