#!/bin/bash
html_files=$(ls ./html/*.html)
echo $html_files

ramalama --engine podman rag $html_files ./output/