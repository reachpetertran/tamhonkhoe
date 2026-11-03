"""Khung chung cho tamhonkhoe.com: khuôn HTML, đọc bài, kiểm luật.

Lấy khuôn trang (header, footer, CSS, header bảo mật) từ daynentang và gộp vào một file.
Mọi khe, mọi chương trình dùng chung khung này; thêm khe mới chỉ cần thêm thư mục trong content/khe/.
"""
import html
import os
import re
import unicodedata

import markdown
import yaml

GOC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
NGAY_CAP_NHAT = '03/11/2026'
DAYNENTANG_GIUP = 'https://daynentang.com/can-giup-ngay/'

VISIBILITY = {'admin', 'public'}
STATUS = {'nhap', 'day-thu', 'da-duyet'}
GATE_KEYS = ['mo-ta', 'khong-chia-re', 'nguon-sach', 'da-duyet', 'an-toan']
GATE_TEN = {
    'mo-ta': 'Mô tả, không phán xét',
    'khong-chia-re': 'Không gây chia rẽ',
    'nguon-sach': 'Nguồn sạch',
    'da-duyet': 'Đã duyệt',
    'an-toan': 'An toàn',
}
LICENSES = {'PD', 'CC0', 'CC-BY', 'CC-BY-NC', 'NO-MODIFY', 'COPYRIGHTED'}
LICENSE_TEN = {
    'PD': 'Phạm vi công cộng', 'CC0': 'CC0', 'CC-BY': 'CC BY', 'CC-BY-NC': 'CC BY-NC',
    'NO-MODIFY': 'Được đăng lại, không được sửa', 'COPYRIGHTED': 'Còn bản quyền',
}
DICH_DUOC = {'PD', 'CC0', 'CC-BY', 'CC-BY-NC'}
TOI_DA_DOAN_KINH = 3
TOI_DA_CHU_TRICH = 15

KHE = [
    ('phat-giao', 'Phật giáo'),
    ('kito-giao', 'Kitô giáo'),
    ('hoi-giao', 'Hồi giáo'),
    ('do-thai-giao', 'Do Thái giáo'),
    ('khac-ky', 'Khắc kỷ'),
    ('bat-nhi', 'Bất nhị / Hiện diện'),
]
NHAN = {
    'Lời dạy truyền thống': 'truyen-thong',
    'Đã xác nhận': 'xac-nhan',
    'Suy luận': 'suy-luan',
    'Đánh giá chuyên môn': 'danh-gia',
    'Cần kiểm chứng': 'can-kiem-chung',
}


class LoiNoiDung(Exception):
    """Lỗi làm dừng build: nội dung vi phạm luật của kế hoạch."""


# ---------------------------------------------------------------- nguồn
def doc_nguon(path=None):
    path = path or os.path.join(GOC, 'sources.yaml')
    with open(path, encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    for sid, s in data.items():
        lic = s.get('license')
        if lic not in LICENSES:
            raise LoiNoiDung(f'sources.yaml: {sid} có license "{lic}" không hợp lệ')
        if s.get('may_translate') and lic not in DICH_DUOC:
            raise LoiNoiDung(f'sources.yaml: {sid} ghi may_translate: true nhưng giấy phép {lic} không cho dịch')
    return data


# ---------------------------------------------------------------- bài viết
FM = re.compile(r'\A---\s*\n(.*?)\n---\s*\n(.*)\Z', re.S)


class Bai:
    def __init__(self, path, goc_content):
        self.path = path
        self.rel = os.path.relpath(path, goc_content).replace(os.sep, '/')
        with open(path, encoding='utf-8') as f:
            raw = unicodedata.normalize('NFC', f.read())
        m = FM.match(raw)
        if not m:
            raise LoiNoiDung(f'{self.rel}: thiếu phần đầu (front matter) giữa hai dòng ---')
        self.meta = yaml.safe_load(m.group(1)) or {}
        self.body = m.group(2)
        self._kiem_meta()

    @property
    def title(self):
        return str(self.meta.get('title', '')).strip()

    @property
    def url(self):
        r = self.rel[:-3]
        if r.startswith('trang/'):
            r = r[len('trang/'):]
            if r == 'index':
                return '/'
        if r.endswith('/index'):
            r = r[:-len('/index')]
        return '/' + r + '/'

    @property
    def rieng(self):
        return self.rel.startswith('goc-rieng/') or '/_mau/' in '/' + self.rel

    def _kiem_meta(self):
        m = self.meta
        if not self.title:
            raise LoiNoiDung(f'{self.rel}: thiếu title')
        if m.get('visibility') not in VISIBILITY:
            raise LoiNoiDung(f'{self.rel}: visibility phải là admin hoặc public')
        if m.get('status') not in STATUS:
            raise LoiNoiDung(f'{self.rel}: status phải là nhap, day-thu hoặc da-duyet')
        gate = m.get('gate')
        if not isinstance(gate, dict) or set(gate) != set(GATE_KEYS):
            raise LoiNoiDung(f'{self.rel}: gate phải có đủ 5 ô: {", ".join(GATE_KEYS)}')
        if any(not isinstance(v, bool) for v in gate.values()):
            raise LoiNoiDung(f'{self.rel}: mỗi ô gate phải là true hoặc false')
        if not isinstance(m.get('sources', []), list) or not isinstance(m.get('reviewers', []), list):
            raise LoiNoiDung(f'{self.rel}: sources và reviewers phải là danh sách [...]')
        if self.rieng and m.get('visibility') == 'public':
            raise LoiNoiDung(f'{self.rel}: bài trong goc-rieng/ hoặc _mau/ không bao giờ được là public')

    def qua_cong(self):
        """Trả về (True, []) nếu bài đủ điều kiện lên public; nếu không, kèm danh sách lý do."""
        m = self.meta
        ly_do = []
        if self.rieng:
            ly_do.append('nằm trong goc-rieng/ hoặc _mau/')
        if m.get('visibility') != 'public':
            ly_do.append('visibility chưa là public')
        if m.get('status') != 'da-duyet':
            ly_do.append('status chưa là da-duyet')
        thieu = [GATE_TEN[k] for k in GATE_KEYS if not m['gate'].get(k)]
        if thieu:
            ly_do.append('cổng chưa đạt: ' + ', '.join(thieu))
        if '[Cần kiểm chứng]' in self.body:
            ly_do.append('còn nhãn [Cần kiểm chứng]')
        return (not ly_do), ly_do


def doc_tat_ca_bai(goc_content):
    ds = []
    for root, dirs, files in os.walk(goc_content):
        dirs.sort()
        for fn in sorted(files):
            if fn.endswith('.md') and not fn.startswith('README'):
                ds.append(Bai(os.path.join(root, fn), goc_content))
    urls = {}
    for b in ds:
        if b.url in urls:
            raise LoiNoiDung(f'Hai bài trùng địa chỉ {b.url}: {urls[b.url]} và {b.rel}')
        urls[b.url] = b.rel
    return ds


# ---------------------------------------------------------------- chuyển Markdown
KINH = re.compile(r'^::: *kinh +([\w-]+) +([\w-]+) *(?:\|(.*))?\n(.*?)\n::: *$', re.M | re.S)
MODES = {'tu-dich', 'nguyen-van', 'trich'}


def _md(text):
    return markdown.markdown(text, extensions=['tables', 'sane_lists', 'attr_list'])


def _a(url, text):
    if not url:
        return html.escape(text) + ' <span class="nhan can-kiem-chung">[chưa có link]</span>'
    return f'<a href="{html.escape(url)}" rel="noopener">{html.escape(text)}</a>'


def render_bai(bai, nguon, che_do):
    """Chuyển bài sang HTML và kiểm luật nguồn. che_do: 'noibo' hoặc 'public'."""
    body = bai.body
    if re.search(r'bản dịch tamhonkhoe', KINH.sub('', body), re.I):
        raise LoiNoiDung(f'{bai.rel}: chỉ khối "::: kinh ... tu-dich" mới được ghi "Bản dịch tamhonkhoe"; '
                         'không viết tay dòng này')
    khai_bao = set(bai.meta.get('sources') or [])
    for sid in khai_bao:
        if sid not in nguon:
            raise LoiNoiDung(f'{bai.rel}: nguồn "{sid}" không có trong sources.yaml')
    doan = KINH.findall(body)
    if len(doan) > TOI_DA_DOAN_KINH:
        raise LoiNoiDung(f'{bai.rel}: có {len(doan)} đoạn kinh, tối đa {TOI_DA_DOAN_KINH}')
    dung = []
    giay_phep_trang = 'CC BY 4.0'

    def thay(m):
        nonlocal giay_phep_trang
        sid, mode, vi_tri, text = m.group(1), m.group(2), (m.group(3) or '').strip(), m.group(4).strip()
        if sid not in nguon:
            raise LoiNoiDung(f'{bai.rel}: khối kinh dùng nguồn "{sid}" không có trong sources.yaml')
        if sid not in khai_bao:
            raise LoiNoiDung(f'{bai.rel}: nguồn "{sid}" dùng trong bài nhưng chưa ghi ở sources: [...]')
        if mode not in MODES:
            raise LoiNoiDung(f'{bai.rel}: cách dùng "{mode}" không hợp lệ (tu-dich | nguyen-van | trich)')
        s = nguon[sid]
        lic = s['license']
        if mode == 'tu-dich' and not s.get('may_translate'):
            raise LoiNoiDung(f'{bai.rel}: nguồn "{sid}" ({LICENSE_TEN[lic]}) có may_translate: false, '
                             'không được ghi là bản dịch tamhonkhoe')
        if lic == 'COPYRIGHTED':
            if mode != 'trich':
                raise LoiNoiDung(f'{bai.rel}: nguồn "{sid}" còn bản quyền, chỉ được dùng kiểu trich')
            so_chu = len(re.findall(r'\w+', text))
            if so_chu >= TOI_DA_CHU_TRICH:
                raise LoiNoiDung(f'{bai.rel}: trích "{sid}" dài {so_chu} chữ; nguồn còn bản quyền phải dưới '
                                 f'{TOI_DA_CHU_TRICH} chữ')
        if lic == 'NO-MODIFY' and mode != 'nguyen-van':
            raise LoiNoiDung(f'{bai.rel}: nguồn "{sid}" không cho sửa, chỉ được dùng kiểu nguyen-van')
        if che_do == 'public' and not s.get('checked_on'):
            raise LoiNoiDung(f'{bai.rel}: nguồn "{sid}" chưa có checked_on (Peter chưa xác nhận giấy phép)')
        if mode == 'tu-dich' and lic == 'CC-BY-NC':
            giay_phep_trang = 'CC BY-NC 4.0'
        dung.append(sid)
        ten = f'{s["title"]}' + (f', {vi_tri}' if vi_tri else '')
        if mode == 'tu-dich':
            cap = (f'Bản dịch tamhonkhoe từ {_a(s.get("url"), ten)}, {html.escape(s.get("translator", ""))}, '
                   f'{LICENSE_TEN[lic]}.')
        elif mode == 'nguyen-van':
            cap = f'{_a(s.get("url"), ten)}, {html.escape(s.get("translator", ""))}. Giấy phép: {LICENSE_TEN[lic]}.'
            if lic == 'NO-MODIFY':
                cap += ' Trích nguyên văn, không sửa.'
        else:
            cap = f'Trích ngắn từ {_a(s.get("url"), ten)}, {html.escape(s.get("translator", ""))} (còn bản quyền).'
        return (f'\n<figure class="kinh"><blockquote>{_md(text)}</blockquote>'
                f'<figcaption>{cap}</figcaption></figure>\n')

    body = KINH.sub(thay, body)
    if che_do == 'public' and '[Cần kiểm chứng]' in body:
        raise LoiNoiDung(f'{bai.rel}: còn nhãn [Cần kiểm chứng], không được lên public')
    phut = bai.meta.get('thuc_hanh_phut') or 0
    if phut > 20 and not re.search(r'^#+ *Dừng tập khi', body, re.M | re.I):
        raise LoiNoiDung(f'{bai.rel}: thực hành {phut} phút (trên 20) nhưng thiếu mục "Dừng tập khi"')
    out = _md(body)
    for ten, cls in NHAN.items():
        out = out.replace(f'[{ten}]', f'<span class="nhan {cls}">[{ten}]</span>')
    return out, giay_phep_trang, sorted(set(khai_bao))


# ---------------------------------------------------------------- khuôn trang
NAV = [
    ('/', 'Trang chủ'),
    ('/giao-thoa/', 'Giao thoa'),
    ('/khe/', 'Các truyền thống'),
    ('/than-the/', 'Thân thể'),
    ('/nguon-va-ban-quyen/', 'Nguồn'),
]


def trang(out_root, path, title, desc, body, che_do, giay_phep='CC BY 4.0', current=None):
    noibo = che_do == 'noibo'
    nav_items = NAV + ([('/goc-rieng/', 'Góc riêng'), ('/quan-tri/', 'Quản trị')] if noibo else [])
    cur = ' aria-current="page"'
    nav = ''.join(f'<a href="{h}"{cur if h == current else ""}>{t}</a>' for h, t in nav_items)
    nav += f'<a class="help" href="{DAYNENTANG_GIUP}">Cần giúp ngay</a>'
    ten_site = 'noibo.tamhonkhoe.com' if noibo else 'tamhonkhoe.com'
    full = title if title.endswith('tamhonkhoe.com') else f'{title} – tamhonkhoe.com'
    robots = '<meta name="robots" content="noindex, nofollow">\n' if noibo else ''
    canon = '' if noibo else f'<link rel="canonical" href="https://tamhonkhoe.com{path}">\n'
    banner = ('<div class="noibo-banner"><div class="wrap"><p><strong>Khu nội bộ</strong> – bản nháp và nội dung '
              'chỉ dành cho admin. Không chia sẻ link.</p></div></div>\n') if noibo else ''
    gp_link = ('https://creativecommons.org/licenses/by-nc/4.0/' if 'NC' in giay_phep
               else 'https://creativecommons.org/licenses/by/4.0/')
    doc = f'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(full)}</title>
<meta name="description" content="{html.escape(desc)}">
{robots}{canon}<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#1b2a41">
<link rel="stylesheet" href="/assets/style.css">
</head>
<body>
<a class="skip" href="#noi-dung">Bỏ qua, đến nội dung</a>
{banner}<header class="site-head">
  <div class="wrap">
    <a class="brand" href="/"><img src="/assets/logo/tamhonkhoe-icon.svg" alt="" width="40" height="40">{ten_site}</a>
    <nav class="nav" aria-label="Điều hướng chính">{nav}</nav>
  </div>
</header>
<main id="noi-dung"><div class="wrap">
{body}
</div></main>
<footer class="site-foot">
  <div class="wrap">
    <div class="cols">
      <div>
        <p><strong>tamhonkhoe.com</strong> – tự học đời sống tinh thần qua kinh điển gốc.</p>
        <p>Không quảng cáo. Không cookie. Không theo dõi người dùng.</p>
      </div>
      <div>
        <p><a href="{DAYNENTANG_GIUP}">Cần giúp ngay</a> · <a href="/nguon-va-ban-quyen/">Nguồn &amp; bản quyền</a></p>
        <p>Nội dung: <a href="{gp_link}" rel="license noopener">{giay_phep}</a> © tamhonkhoe.com. Logo và tên thương hiệu giữ mọi quyền.</p>
      </div>
      <div>
        <p>Trang chị em: <a href="https://daynentang.com">daynentang.com</a> · <a href="https://tienganhcanban.com">tienganhcanban.com</a></p>
        <p>Cập nhật: {NGAY_CAP_NHAT}</p>
      </div>
    </div>
  </div>
</footer>
</body>
</html>
'''
    out = os.path.join(out_root, path.lstrip('/'))
    if out.endswith('/') or path == '/':
        out = os.path.join(out, 'index.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(doc)
    return out


# Header bảo mật (giống daynentang; site không dùng JavaScript nên chặn hẳn script)
HEADERS_CHUNG = '''/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()
  Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'none'
  X-Frame-Options: DENY
'''
HEADERS_NOIBO_THEM = '''  X-Robots-Tag: noindex, nofollow, noarchive
  Cache-Control: private, no-store
'''
