import psycopg2
import zstandard as zstd
import io
from io import StringIO
from dotenv import load_dotenv
import os

load_dotenv()

# ─── DB CONNECTION ───────────────────────────────────────
conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)
cursor = conn.cursor()

cursor.execute("TRUNCATE TABLE icann_domains;")
conn.commit()
print("🗑️ Old ICANN data cleared!")

zst_path = r"C:\Users\andre\OneDrive\Desktop\afternic-search-api\data\domains_02-18-2026.zst"

print("Loading full ICANN dataset from .zst file...")

with open(zst_path, 'rb') as f:
    dctx = zstd.ZstdDecompressor()
    stream = dctx.stream_reader(f)
    text_stream = io.TextIOWrapper(stream, encoding='utf-8')
    
    # Skip header line
    next(text_stream)
    
    buffer = StringIO()
    count = 0
    batch_size = 100000

    for line in text_stream:
        parts = line.strip().split(',')
        if len(parts) >= 2:
            domain = parts[0].strip('"')
            tld = parts[1].strip('"')
            buffer.write(f"{domain},{tld}\n")
            count += 1

        if count % batch_size == 0:
            buffer.seek(0)
            cursor.copy_from(buffer, 'icann_domains', sep=',', columns=['domain', 'tld'])
            conn.commit()
            buffer = StringIO()
            print(f"  Loaded {count} rows so far...")

    # Load remaining rows
    if buffer.tell() > 0:
        buffer.seek(0)
        cursor.copy_from(buffer, 'icann_domains', sep=',', columns=['domain', 'tld'])
        conn.commit()

print(f"✅ ICANN data loaded! Total: {count} rows")

cursor.close()
conn.close()
print("🎉 All done!")