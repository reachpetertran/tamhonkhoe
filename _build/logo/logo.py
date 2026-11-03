"""Sinh logo tamhonkhoe từ khung logo chung (daynentang/tienganhcanban).
Giữ nguyên hình, bố cục; chữ dựng lại bằng Inter Bold 28 (tracking 1.12) và Inter SemiBold 14 (tracking 2.1),
đúng thông số đo được từ logo daynentang."""
import re, sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from textpath import centered
INTER='/usr/share/fonts/opentype/inter/'
def make(frame_svg, accent, out):
    s=open(frame_svg).read()
    t,_=centered('TÂM HỒN KHỎE', INTER+'Inter-Bold.otf', 28, 200.2, 362, 1.12)
    b,_=centered('EST. 2026 · TAMHONKHOE.COM', INTER+'Inter-SemiBold.otf', 14, 200, 412, 2.1)
    s=s.replace('</svg>', f'<path fill="#1b2a41" d="{t}"/><path fill="{accent}" d="{b}"/></svg>')
    open(out,'w').write(s)
if __name__=='__main__':
    make(sys.argv[1], sys.argv[2], sys.argv[3])
# Cách dùng: python3 _build/logo/logo.py _build/logo/khung-logo-chung.svg "#f47b2a" assets/logo/tamhonkhoe-logo.svg
# Cần phông Inter (Inter-Bold.otf, Inter-SemiBold.otf) và fonttools.
