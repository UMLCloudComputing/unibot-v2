#!/bin/bash

VERBOSE=false  # Default verbose level

# Parse command-line arguments
while getopts ":v" opt; do
  case "$opt" in
    v)
      VERBOSE=true
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done

log() {
  if [ "$VERBOSE" = true ]; then
    echo "[VERBOSE] $*"
  fi
}

# Check if an input file was provided
if [[ -z "$1" ]]; then
  echo "$0: Usage: $0 [-v] <file_with_urls>"
  exit 1
fi

# Shift off the parsed options
shift $((OPTIND - 1))


if [ -d html ]; then
    echo "Directory 'html' already exists. Assuming data is already downloaded..."
    exit 0
fi

mkdir -p html

echo "Downloading data..."

while IFS= read -r line; do
    log "Processing line: $line"

    outfile="$(echo "$line" | sed 's/[^A-Za-z0-9._-]/_/g').html"
    curl -sL "$line" -o "./html/$outfile"

    log "Downloaded to: ./html/$outfile"

done < "$1"

echo "Download complete."

