# Object Storage

Canonical docs: https://github.com/yandex-cloud/docs/tree/master/ru/storage · Public: https://yandex.cloud/ru/docs/storage/

S3-compatible (mostly). Endpoint: `https://storage.yandexcloud.net`. Region: `ru-central1`.

## Two control planes

| Plane | Use |
|---|---|
| `yc storage` | YC-native: bucket lifecycle, metadata, policies via YC API |
| `aws s3` / `aws s3api` / S3 SDKs | Data-plane operations; signed with S3 v4 signature, ACL/policy via S3 API |

You can mix freely. For production, do bucket creation via `yc` + Terraform, data operations via SDKs.

## Auth for S3 clients

Generate static access keys from a **service account**, NOT user OAuth:

```bash
yc iam service-account create --name s3-writer
yc resource-manager folder add-access-binding $YC_FOLDER_ID \
  --role storage.editor --service-account-id $(yc iam service-account get s3-writer --format value)
yc iam access-key create --service-account-name s3-writer
# → prints access_key + secret — store in Lockbox or .aws/credentials
```

Then for `aws-cli`:

```bash
aws configure set aws_access_key_id YCAJ...
aws configure set aws_secret_access_key ...
aws configure set region ru-central1

# Always include endpoint
aws s3 ls --endpoint-url https://storage.yandexcloud.net
```

For SDKs (Node/Python): set `endpoint: 'https://storage.yandexcloud.net'`, `region: 'ru-central1'`, `forcePathStyle: false` (virtual-hosted style works).

## Bucket creation

```bash
yc storage bucket create \
  --name my-prod-uploads \
  --default-storage-class standard \
  --max-size 107374182400 \
  --acl private \
  --versioning versioning-enabled

# Allow website hosting
yc storage bucket update --name my-prod-uploads \
  --website index-file=index.html,error-file=404.html
```

## Storage classes

| Class | When | Retrieval cost |
|---|---|---|
| `standard` | Hot data | Free |
| `cold` | <1 access/month | Charged per GB retrieved |
| `ice` | Archive (1-90 day rare) | Higher retrieval fee + minimum 90-day commitment |

Use lifecycle policy to auto-transition: 30 days → cold, 180 → ice.

## Bucket policy (S3 JSON)

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::my-prod-uploads/public/*"
  }]
}
```

`yc storage bucket update --name X --policy-file policy.json` or via aws-cli `s3api put-bucket-policy`.

## Presigned URLs

Sign with S3 v4 — most SDKs Just Work; pass YC endpoint:

```ts
// Node (AWS SDK v3)
import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

const s3 = new S3Client({
  endpoint: 'https://storage.yandexcloud.net',
  region: 'ru-central1',
  credentials: { accessKeyId, secretAccessKey },
});

const url = await getSignedUrl(
  s3,
  new GetObjectCommand({ Bucket: 'my-prod-uploads', Key: 'foo.pdf' }),
  { expiresIn: 600 }
);
```

## CORS

JSON config, set via S3 API `put-bucket-cors` or YC console.

```json
{
  "CORSRules": [{
    "AllowedOrigins": ["https://app.example.com"],
    "AllowedMethods": ["GET", "PUT", "POST"],
    "AllowedHeaders": ["*"],
    "MaxAgeSeconds": 3000,
    "ExposeHeaders": ["ETag"]
  }]
}
```

## Static website hosting

```bash
yc storage bucket update --name my-site \
  --website index-file=index.html,error-file=404.html \
  --acl public-read
# Site URL: https://my-site.website.yandexcloud.net
```

For custom domain + TLS — front with **Yandex CDN** or **Application Load Balancer** with ACM cert.

## S3-incompatibilities (gotchas)

| Feature | YC behavior |
|---|---|
| **Multipart upload** | Supported; same API |
| **Server-side encryption** | YC encrypts at rest by default; no `x-amz-server-side-encryption` header — silently ignored |
| **`s3:CopyObject` cross-region** | YC has one region (`ru-central1`) — N/A |
| **Object Lock (WORM)** | Not supported |
| **Inventory reports** | Not supported |
| **Event notifications → Lambda** | Use Cloud Functions trigger instead — different API |
| **Requester Pays** | Not supported |

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `SignatureDoesNotMatch` | Wrong endpoint or region | endpoint `storage.yandexcloud.net`, region `ru-central1` |
| `403 AccessDenied` despite correct keys | Service account lacks `storage.editor` role on the folder | Add binding |
| Listing 1 file at a time | Forgot pagination | `aws s3api list-objects-v2 --max-items 1000 --starting-token ...` |
| Bucket policy "succeeds" but doesn't take effect | Object-level ACL conflicts; or policy syntax error silently rejected by older endpoints | Use `yc storage bucket get` to verify; test with curl |
| Egress bill spike | App fetches files repeatedly from outside YC | Front with CDN; cache aggressively; signed URLs with long expiry |
