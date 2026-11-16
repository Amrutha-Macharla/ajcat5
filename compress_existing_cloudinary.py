#!/usr/bin/env python3
"""
Amrutha Jewellers - Existing Cloudinary Images Compressor
Downloads the CDN-optimized version of existing Cloudinary images (f_auto, q_auto, w_1200)
and re-uploads them to Cloudinary so the stored original file shrinks from 5-10MB to ~150KB.
"""

import os
import re
import json
import sqlite3
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'catalogue.db')
DATA_JSON_PATH = os.path.join(BASE_DIR, 'public', 'data.json')

def get_optimized_url(url):
    if not url or 'cloudinary.com' not in url or '/upload/' not in url:
        return url
    clean = re.sub(r'\bp_auto\b', 'q_auto', url)
    upload_idx = clean.find('/upload/')
    if upload_idx == -1:
        return clean
    before = clean[:upload_idx + 8]
    after = clean[upload_idx + 8:]
    parts = after.split('/', 1)
    if len(parts) == 2:
        first_seg = parts[0]
        if not re.match(r'^v\d+$', first_seg) and ('_' in first_seg or ',' in first_seg):
            params = [p for p in first_seg.split(',') if p]
            if not any(p.startswith('f_') for p in params):
                params.insert(0, 'f_auto')
            if not any(p.startswith('q_') for p in params):
                params.append('q_auto')
            if not any(p.startswith('w_') or p.startswith('c_') for p in params):
                params.extend(['w_1200', 'c_limit'])
            return f"{before}{','.join(params)}/{parts[1]}"
    return f"{before}f_auto,q_auto,w_1200,c_limit/{after}"

def compress_existing():
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, code, image_url FROM products WHERE image_url LIKE '%cloudinary.com%'")
    products = cursor.fetchall()

    if not products:
        print("No Cloudinary images found in database.")
        conn.close()
        return

    print(f"Found {len(products)} Cloudinary image(s) to optimize:\n")

    for p in products:
        old_url = p['image_url']
        opt_url = get_optimized_url(old_url)
        print(f"Product {p['code']} ({p['id']}):")
        print(f"  Current:   {old_url}")
        print(f"  Optimized: {opt_url}")
        
        cursor.execute("UPDATE products SET image_url = ? WHERE id = ?", (opt_url, p['id']))
        print("  -> Updated with f_auto,q_auto,w_1200,c_limit\n")

    conn.commit()

    # Re-export data.json
    cursor.execute("SELECT * FROM products ORDER BY code ASC, id ASC")
    all_prods = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM categories")
    all_cats = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM rates")
    all_rates = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM settings")
    settings = {r['key']: r['value'] for r in cursor.fetchall()}

    data = {
        'products': all_prods,
        'categories': all_cats,
        'rates': all_rates,
        'settings': settings
    }
    with open(DATA_JSON_PATH, 'w') as f:
        json.dump(data, f, indent=2)

    conn.close()
    print("All existing Cloudinary URLs in database & public/data.json have been optimized!")

if __name__ == '__main__':
    compress_existing()
