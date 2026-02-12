# Master Node IP
`192.168.0.232`

# Worker Node IP
`192.168.2.3`
`192.168.1.104`

# Get Kubeconfig
`talosctl kubeconfig --talosconfig <(sops -d talosconfig)`
# Operating on talos config files
Files are secured using [`sops`](https://github.com/getsops/sops).
Keys are stored on AWS KMS

Editing files:
- `sops edit FILENAME`
    - Handles decryption to `/tmp`
    - Opens in default text editor
    - Automatically re-encrypts and overwrites the original
    - Deletes temporary cleartext file from `/tmp`

To use with talosctl commands:
- Use process substitution to prevent accidentally committing a decrypted config file
- IE: `talosctl apply-config -n <NODE-IP> --file <(sops -d controlplane.yaml)`

More on [`sops`](https://github.com/getsops/sops)

