# Lockbox & KMS

Canonical docs:
- Lockbox — https://github.com/yandex-cloud/docs/tree/master/ru/lockbox
- KMS — https://github.com/yandex-cloud/docs/tree/master/ru/kms

## Lockbox — secret store

Lockbox stores **named secret payloads** (key-value pairs) with versions. Each secret has multiple versions; old versions remain until you purge.

### Create a secret

```bash
yc lockbox secret create \
  --name app-prod-secrets \
  --description "Prod app secrets" \
  --payload '[{"key":"DATABASE_URL","text_value":"postgres://app:pwd@c-XXX.rw.mdb.yandexcloud.net:6432/appdb?sslmode=verify-full"},
              {"key":"JWT_SECRET","text_value":"'$(openssl rand -hex 32)'"},
              {"key":"OPENAI_API_KEY","text_value":"sk-..."}]'
```

For binary values use `binary_value` (base64-encoded). For keeping payloads out of shell history: `--payload @payload.json`.

### Read a secret (from a VM via metadata)

```bash
TOKEN=$(curl -s -H 'Metadata-Flavor: Google' \
  169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token | jq -r .access_token)

SECRET_ID=$(yc lockbox secret get app-prod-secrets --format value)

curl -s -H "Authorization: Bearer $TOKEN" \
  "https://payload.lockbox.api.cloud.yandex.net/lockbox/v1/secrets/$SECRET_ID/payload" \
  | jq -r '.entries[] | "export \(.key)=\(.text_value)"' > /run/secrets.env

# Use in systemd unit or PM2 ecosystem:
#   EnvironmentFile=/run/secrets.env
```

VM's SA must have `lockbox.payloadViewer` role.

### Versioning + rotation

```bash
# Add new version (old version stays usable until --scheduled-for purges it)
yc lockbox secret add-version \
  --name app-prod-secrets \
  --description "rotated 2026-05-16" \
  --payload '[{"key":"JWT_SECRET","text_value":"'$(openssl rand -hex 32)'"}]'

# List versions
yc lockbox secret list-versions --name app-prod-secrets

# Schedule old version for destruction (default delay 7 days)
yc lockbox secret schedule-version-destruction --name app-prod-secrets --version-id <old-id>

# Cancel destruction within window
yc lockbox secret cancel-version-destruction --name app-prod-secrets --version-id <old-id>
```

For rotation: add new version → roll deployments to read new → schedule destroy old after stable.

### Mounting in k8s

Two approaches:

1. **Sync to k8s Secret via External Secrets Operator** (recommended): install `external-secrets`, define `SecretStore` pointing at YC Lockbox SA, then `ExternalSecret` per secret.
2. **Sidecar fetcher**: container reads Lockbox via metadata-server token on startup, writes env file to shared volume.

### Use in Serverless

Cloud Functions / Serverless Containers: in `version create`, pass `--secrets environment-variable=DATABASE_URL,id=$SECRET_ID,key=DATABASE_URL`. YC injects at runtime.

## KMS — symmetric encryption keys

Use when you need to encrypt/decrypt **your own** data (e.g. files before uploading to Object Storage) with managed keys.

```bash
yc kms symmetric-key create --name app-data-key --default-algorithm aes-256

# Encrypt
yc kms symmetric-crypto encrypt \
  --key-name app-data-key \
  --plaintext-file plain.json \
  --ciphertext-file encrypted.bin

# Decrypt
yc kms symmetric-crypto decrypt \
  --key-name app-data-key \
  --ciphertext-file encrypted.bin \
  --plaintext-file decrypted.json
```

For envelope encryption (encrypt large file with DEK, encrypt DEK with KMS) use `generate-data-key`.

### Auto-rotation

```bash
yc kms symmetric-key update --name app-data-key --rotation-period 30d
```

Old key versions remain usable for decryption; new encryptions use the latest.

## When to use what

| Need | Use |
|---|---|
| App secret (DB URL, API key) | Lockbox |
| Encrypt user data at rest | KMS + your code |
| TLS certs | Certificate Manager (NOT Lockbox) |
| Object Storage at rest | Auto-encrypted by YC; KMS not required |
| Bucket-level encryption with own keys | KMS-CMK on bucket — supported, see Object Storage docs |

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `permission denied` reading Lockbox from VM | SA lacks `lockbox.payloadViewer` | Add binding |
| Lockbox payload returns empty | Version `SCHEDULED_FOR_DESTRUCTION` or destroyed | Add new version |
| Secret in plain text in `yc compute instance get` output | Used `--metadata KEY=VALUE` for secrets — anyone with VM read access sees it | NEVER put secrets in instance metadata; use Lockbox + metadata-token fetch |
| `--payload` shows in shell history | Used inline value | `--payload @file.json` + `chmod 600 file.json` + delete after |
| KMS decrypt fails after key rotation | Tried to decrypt with wrong version | Old ciphertext is still decryptable with whichever version encrypted it — version is encoded in ciphertext header |
