#!/usr/bin/env bash
# รัน test suite ทั้งหมดของโปรเจกต์ Ai-commerce-os
# ใช้ unittest มาตรฐานของ Python (ไม่ต้องติดตั้ง pytest เพิ่ม)
set -e
cd "$(dirname "$0")"
python3 -m unittest discover -s tests -p "test_*.py" -v
