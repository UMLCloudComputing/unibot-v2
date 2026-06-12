#! /bin/bash 
# Usage: ./build-rag DATA-LIST MODE DIRECTORY/OCI-IMAGE

if [[ "$(ls ./html > /dev/null)" ]]; then
    echo "WARNING: 'html' directory is not empty. Using existing data for RAG generation."
    if ! ./vectorize.sh "$2" "$3"; then 
        echo "ERROR: Incorrect args"
        echo "Usage: ./build-rag <DATA-LIST> <MODE> <DIRECTORY/OCI-IMAGE>"
        exit 1
    fi
fi

if ! ./fetch-data.sh "$1"; then
   echo "ERROR: Incorrect args"
   echo "Usage: ./build-rag <DATA-LIST> <MODE> <DIRECTORY/OCI-IMAGE>"
   exit 1
fi

./vectorize.sh $2 $3

