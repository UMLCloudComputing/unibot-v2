#!/bin/bash

eval "mkdir html"

while IFS= read -r line; do
    outfile="$(echo "$line" | sed 's/[^A-Za-z0-9._-]/_/g').html"
    curl -sL "$line" -o "./html/$outfile"
    
done < "$1"