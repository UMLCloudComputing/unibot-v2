#!/bin/zsh

helm uninstall uni-chatbot

helm install uni-chatbot $PWD
