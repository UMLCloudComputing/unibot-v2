#!/bin/zsh

helm uninstall uni-chatbot --wait

helm install uni-chatbot $PWD --wait
