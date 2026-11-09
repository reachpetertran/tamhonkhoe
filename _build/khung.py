"""Khung chung cho tamhonkhoe.com: khuôn HTML, đọc bài, kiểm luật.

Lấy khuôn trang (header, footer, CSS, header bảo mật) từ daynentang và gộp vào một file.
Mọi khe, mọi chương trình dùng chung khung này; thêm khe mới chỉ cần thêm thư mục trong content/khe/.

Song ngữ (giống daynentang): bản tiếng Việt là bản gốc (bai.md); bản tiếng Anh nằm cạnh (bai.en.md)
và có địa chỉ riêng dưới /en/ bằng chữ tiếng Anh. Không tự chuyển ngôn ngữ; mỗi trang có nút chuyển.
"""
import html
import os
import re
import unicodedata

import markdown
import yaml

GOC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SITE = 'https://tamhonkhoe.com'
NGAY_CAP_NHAT = '04/11/2026'
NGAY_CAP_NHAT_EN = '4 November 2026'
DAYNENTANG_GIUP = 'https://daynentang.com/can-giup-ngay/'
DAYNENTANG_GIUP_EN = 'https://daynentang.com/en/get-help/'

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
LICENSE_TEN_EN = {
    'PD': 'Public domain', 'CC0': 'CC0', 'CC-BY': 'CC BY', 'CC-BY-NC': 'CC BY-NC',
    'NO-MODIFY': 'May be republished, not modified', 'COPYRIGHTED': 'In copyright',
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
    ('dao-giao', 'Đạo giáo'),
]
KHE_EN = {
    'phat-giao': 'Buddhism', 'kito-giao': 'Christianity', 'hoi-giao': 'Islam',
    'do-thai-giao': 'Judaism', 'khac-ky': 'Stoicism', 'bat-nhi': 'Non-duality / Presence',
    'dao-giao': 'Taoism',
}
# Thư mục tiếng Việt -> chữ dùng trong địa chỉ /en/
THU_MUC_EN = {
    'giao-thoa': 'convergence', 'khe': 'traditions', 'than-the': 'body', 'goc-rieng': 'family-corner', 'goc-tre': 'kids-corner',
    'phat-giao': 'buddhism', 'kito-giao': 'christianity', 'hoi-giao': 'islam',
    'do-thai-giao': 'judaism', 'khac-ky': 'stoicism', 'bat-nhi': 'non-duality', 'dao-giao': 'taoism',
    'khoa-hoc': 'courses',
    'nguon-va-ban-quyen': 'sources-and-licences', 'gioi-thieu': 'about', 'rieng-tu': 'privacy',
    'bang-chung': 'evidence', 'nhat-ky-sua-doi': 'changelog',
}
NHAN = {
    'Lời dạy truyền thống': 'truyen-thong',
    'Đã xác nhận': 'xac-nhan',
    'Suy luận': 'suy-luan',
    'Đánh giá chuyên môn': 'danh-gia',
    'Cần kiểm chứng': 'can-kiem-chung',
}
NHAN_EN = {
    'Traditional teaching': 'truyen-thong',
    'Verified': 'xac-nhan',
    'Inference': 'suy-luan',
    'Expert judgement': 'danh-gia',
    'Needs verification': 'can-kiem-chung',
}
CHUA_KIEM = ('[Cần kiểm chứng]', '[Needs verification]')
SLUG = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')


class LoiNoiDung(Exception):
    """Lỗi làm dừng build: nội dung vi phạm luật của kế hoạch."""


def en_path(vi_path):
    """Địa chỉ tiếng Việt của trang mục lục -> địa chỉ /en/ tương ứng (đổi từng đoạn theo THU_MUC_EN)."""
    phan = [p for p in vi_path.strip('/').split('/') if p]
    return '/en/' + ''.join(THU_MUC_EN.get(p, p) + '/' for p in phan)


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
        self.lang = 'en' if self.rel.endswith('.en.md') else 'vi'
        self.rel_vi = self.rel[:-len('.en.md')] + '.md' if self.lang == 'en' else self.rel
        self.cap = None          # bản ngôn ngữ còn lại (gán trong doc_tat_ca_bai)
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
    def url_vi(self):
        r = self.rel_vi[:-3]
        if r.startswith('trang/'):
            r = r[len('trang/'):]
            if r == 'index':
                return '/'
        if r.endswith('/index'):
            r = r[:-len('/index')]
        return '/' + r + '/'

    @property
    def url(self):
        if self.lang == 'vi':
            return self.url_vi
        phan = self.url_vi.strip('/').split('/')
        if phan == ['']:
            return '/en/'
        dau = ''.join(THU_MUC_EN.get(p, p) + '/' for p in phan[:-1])
        cuoi = self.meta.get('slug') or THU_MUC_EN.get(phan[-1])
        return '/en/' + dau + cuoi + '/'

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
        if self.lang == 'en':
            slug = m.get('slug')
            cuoi = self.url_vi.strip('/').split('/')[-1]
            if slug is None and self.url_vi != '/' and cuoi not in THU_MUC_EN:
                raise LoiNoiDung(f'{self.rel}: bản tiếng Anh cần slug (địa chỉ tiếng Anh), ví dụ slug: week-01')
            if slug is not None and not SLUG.match(str(slug)):
                raise LoiNoiDung(f'{self.rel}: slug "{slug}" chỉ được dùng chữ thường không dấu, số và dấu -')

    def _ly_do_rieng(self):
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
        for nhan in CHUA_KIEM:
            if nhan in self.body:
                ly_do.append(f'còn nhãn {nhan}')
        return ly_do

    def qua_cong(self):
        """(True, []) nếu bài đủ điều kiện lên public. Bài song ngữ: cả hai bản phải cùng qua cổng."""
        ly_do = self._ly_do_rieng()
        if self.cap is None:
            ly_do.append('chưa có bản tiếng Anh' if self.lang == 'vi' else 'chưa có bản tiếng Việt')
        elif self.cap._ly_do_rieng():
            ly_do.append('bản tiếng Anh chưa qua cổng' if self.lang == 'vi' else 'bản tiếng Việt chưa qua cổng')
        return (not ly_do), ly_do


def doc_tat_ca_bai(goc_content):
    ds = []
    for root, dirs, files in os.walk(goc_content):
        dirs.sort()
        for fn in sorted(files):
            if fn.endswith('.md') and not fn.startswith('README'):
                ds.append(Bai(os.path.join(root, fn), goc_content))
    theo_rel = {b.rel: b for b in ds if b.lang == 'vi'}
    for b in ds:
        if b.lang == 'en':
            vi = theo_rel.get(b.rel_vi)
            if vi is None:
                raise LoiNoiDung(f'{b.rel}: bản tiếng Anh phải có bản tiếng Việt gốc {b.rel_vi}')
            b.cap, vi.cap = vi, b
    urls = {}
    for b in ds:
        if b.url in urls:
            raise LoiNoiDung(f'Hai bài trùng địa chỉ {b.url}: {urls[b.url]} và {b.rel}')
        urls[b.url] = b.rel
    return ds


# ---------------------------------------------------------------- chuyển Markdown
KINH = re.compile(r'^::: *kinh +([\w-]+) +([\w-]+) *(?:\|([^\n]*))?\n(.*?)\n::: *$', re.M | re.S)
MODES = {'tu-dich', 'nguyen-van', 'trich'}
DUNG_TAP = re.compile(r'^#+ *(?:\d+[.)] *)?(?:Dừng tập khi|Stop practi[sc]ing if)', re.M | re.I)

# Ghi chú cho người duyệt viết trong <!-- ... -->: chỉ ở khu nội bộ, tự xóa khi publish
GHI_CHU = re.compile(r'[ \t]*<!--.*?-->[ \t]*\n?', re.S)


def bo_ghi_chu(text):
    """Xóa mọi ghi chú <!-- ... --> khỏi phần thân bài (không đụng front matter)."""
    m = FM.match(text)
    if not m:
        return GHI_CHU.sub('', text)
    dau = text[:m.start(2)]
    return dau + GHI_CHU.sub('', m.group(2))


def _md(text):
    return markdown.markdown(text, extensions=['tables', 'sane_lists', 'attr_list'])


def _a(url, text, en=False):
    if not url:
        return html.escape(text) + (' <span class="nhan can-kiem-chung">[no link yet]</span>' if en else
                                    ' <span class="nhan can-kiem-chung">[chưa có link]</span>')
    return f'<a href="{html.escape(url)}" rel="noopener">{html.escape(text)}</a>'


def render_bai(bai, nguon, che_do):
    """Chuyển bài sang HTML và kiểm luật nguồn. che_do: 'noibo' hoặc 'public'."""
    en = bai.lang == 'en'
    lic_ten = LICENSE_TEN_EN if en else LICENSE_TEN
    body = bai.body
    if che_do == 'public':
        body = GHI_CHU.sub('', body)
    ngoai_khoi = KINH.sub('', body)
    if re.search(r'bản dịch tamhonkhoe|tamhonkhoe translation', ngoai_khoi, re.I):
        raise LoiNoiDung(f'{bai.rel}: chỉ khối "::: kinh ... tu-dich" mới được ghi "Bản dịch tamhonkhoe" / '
                         '"tamhonkhoe translation"; không viết tay dòng này')
    khai_bao = set(bai.meta.get('sources') or [])
    for sid in khai_bao:
        if sid not in nguon:
            raise LoiNoiDung(f'{bai.rel}: nguồn "{sid}" không có trong sources.yaml')
    doan = KINH.findall(body)
    if len(doan) > TOI_DA_DOAN_KINH:
        raise LoiNoiDung(f'{bai.rel}: có {len(doan)} đoạn kinh, tối đa {TOI_DA_DOAN_KINH}')
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
        if s.get('chi_link'):
            raise LoiNoiDung(f'{bai.rel}: nguồn "{sid}" có chi_link: true – chỉ được đặt link, '
                             'không được trích trong khối kinh')
        if mode == 'tu-dich' and not s.get('may_translate'):
            raise LoiNoiDung(f'{bai.rel}: nguồn "{sid}" ({LICENSE_TEN[lic]}) có may_translate: false, '
                             'không được ghi là bản dịch tamhonkhoe')
        if en and mode == 'tu-dich' and s.get('lang') == 'en':
            raise LoiNoiDung(f'{bai.rel}: nguồn "{sid}" đã là tiếng Anh; bản tiếng Anh phải dùng nguyen-van '
                             '(chép đúng bản gốc), không tự dịch')
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
        if lic == 'CC-BY-NC' and mode in ('tu-dich', 'nguyen-van'):
            giay_phep_trang = 'CC BY-NC 4.0'
        ten = f'{s["title"]}' + (f', {vi_tri}' if vi_tri else '')
        link = _a(s.get('url'), ten, en)
        dg = html.escape(s.get('translator', ''))
        if mode == 'tu-dich':
            cap = (f'tamhonkhoe translation from {link}, {dg}, {lic_ten[lic]}.' if en else
                   f'Bản dịch tamhonkhoe từ {link}, {dg}, {lic_ten[lic]}.')
        elif mode == 'nguyen-van':
            cap = (f'{link}, {dg}. Licence: {lic_ten[lic]}.' if en else
                   f'{link}, {dg}. Giấy phép: {lic_ten[lic]}.')
            if lic == 'NO-MODIFY':
                cap += ' Quoted verbatim, unmodified.' if en else ' Trích nguyên văn, không sửa.'
        else:
            cap = (f'Short quotation from {link}, {dg} (in copyright).' if en else
                   f'Trích ngắn từ {link}, {dg} (còn bản quyền).')
        return (f'\n<figure class="kinh"><blockquote>{_md(text)}</blockquote>'
                f'<figcaption>{cap}</figcaption></figure>\n')

    body = KINH.sub(thay, body)
    if che_do == 'public':
        for nhan in CHUA_KIEM:
            if nhan in body:
                raise LoiNoiDung(f'{bai.rel}: còn nhãn {nhan}, không được lên public')
    phut = bai.meta.get('thuc_hanh_phut') or 0
    if phut > 20 and not DUNG_TAP.search(body):
        raise LoiNoiDung(f'{bai.rel}: thực hành {phut} phút (trên 20) nhưng thiếu mục '
                         + ('"Stop practising if"' if en else '"Dừng tập khi"'))
    out = _md(body)
    # Bảng rộng cuộn ngang trong khung riêng, không làm tràn trang trên điện thoại
    out = out.replace('<table>', '<div class="table-wrap"><table>').replace('</table>', '</table></div>')
    for ten, cls in (NHAN_EN if en else NHAN).items():
        out = out.replace(f'[{ten}]', f'<span class="nhan {cls}">[{ten}]</span>')
    return out, giay_phep_trang, sorted(set(khai_bao))


# ---------------------------------------------------------------- khuôn trang
NAV = [
    ('/', 'Trang chủ'),
    ('/khoa-hoc/', 'Khóa học'),
    ('/giao-thoa/', 'Giao thoa'),
    ('/khe/', 'Các truyền thống'),
    ('/than-the/', 'Thân thể'),
    ('/nguon-va-ban-quyen/', 'Nguồn'),
]
NAV_EN = [
    ('/en/', 'Home'),
    ('/en/courses/', 'Courses'),
    ('/en/convergence/', 'Convergence'),
    ('/en/traditions/', 'Traditions'),
    ('/en/body/', 'Body'),
    ('/en/sources-and-licences/', 'Sources'),
]


def trang(out_root, path, title, desc, body, che_do, giay_phep='CC BY 4.0', current=None,
          lang='vi', alt=None):
    """Viết một trang HTML. lang: 'vi' | 'en'. alt: địa chỉ bản ngôn ngữ còn lại (nếu có)."""
    noibo = che_do == 'noibo'
    en = lang == 'en'
    cur = ' aria-current="page"'
    if en:
        nav_items = NAV_EN + ([('/quan-tri/', 'Admin')] if noibo else [])
    else:
        nav_items = NAV + ([('/goc-rieng/', 'Góc riêng'), ('/quan-tri/', 'Quản trị')] if noibo else [])
    nav = ''.join(f'<a href="{h}"{cur if h == current else ""}>{t}</a>' for h, t in nav_items)
    if en:
        nav += f'<a class="lang" href="{alt or "/"}" hreflang="vi" lang="vi">Tiếng Việt</a>'
        nav += f'<a class="help" href="{DAYNENTANG_GIUP_EN}">Get help now</a>'
    else:
        if alt:
            nav += f'<a class="lang" href="{alt}" hreflang="en" lang="en">English</a>'
        nav += f'<a class="help" href="{DAYNENTANG_GIUP}">Cần giúp ngay</a>'
    ten_site = 'noibo.tamhonkhoe.com' if noibo else 'tamhonkhoe.com'
    full = title if title.endswith('tamhonkhoe.com') else f'{title} – tamhonkhoe.com'
    robots = '<meta name="robots" content="noindex, nofollow">\n' if noibo else ''
    canon = '' if noibo else f'<link rel="canonical" href="{SITE}{path}">\n'
    hreflang = ''
    if alt:
        vi_p, en_p = (alt, path) if en else (path, alt)
        hreflang = (f'<link rel="alternate" hreflang="vi" href="{SITE}{vi_p}">\n'
                    f'<link rel="alternate" hreflang="en" href="{SITE}{en_p}">\n'
                    f'<link rel="alternate" hreflang="x-default" href="{SITE}{vi_p}">\n')
    if noibo:
        banner = ('<div class="noibo-banner"><div class="wrap"><p><strong>Internal area</strong> – drafts and '
                  'admin-only content. Do not share the link.</p></div></div>\n') if en else (
                  '<div class="noibo-banner"><div class="wrap"><p><strong>Khu nội bộ</strong> – bản nháp và nội dung '
                  'chỉ dành cho admin. Không chia sẻ link.</p></div></div>\n')
    else:
        banner = ''
    gp_link = ('https://creativecommons.org/licenses/by-nc/4.0/' if 'NC' in giay_phep
               else 'https://creativecommons.org/licenses/by/4.0/')
    if en:
        skip, nav_lab, home = 'Skip to content', 'Main navigation', '/en/'
        foot = f'''<div>
        <p><strong>tamhonkhoe.com</strong> – self-study of the spiritual life through original scriptures.</p>
        <p>No ads. No cookies. No user tracking.</p>
      </div>
      <div>
        <p><a href="{DAYNENTANG_GIUP_EN}">Get help now</a> · <a href="/en/sources-and-licences/">Sources &amp; licences</a></p>
        <p>Content: <a href="{gp_link}" rel="license noopener">{giay_phep}</a> © tamhonkhoe.com. Logo and name: all rights reserved.</p>
      </div>
      <div>
        <p>Sister sites: <a href="https://daynentang.com/en/">daynentang.com</a> · <a href="https://tienganhcanban.com">tienganhcanban.com</a></p>
        <p>Updated: {NGAY_CAP_NHAT_EN}. The Vietnamese version is the original.</p>
      </div>'''
    else:
        skip, nav_lab, home = 'Bỏ qua, đến nội dung', 'Điều hướng chính', '/'
        foot = f'''<div>
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
      </div>'''
    doc = f'''<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(full)}</title>
<meta name="description" content="{html.escape(desc)}">
{robots}{canon}{hreflang}<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#1b2a41">
<link rel="stylesheet" href="/assets/style.css">
</head>
<body>
<a class="skip" href="#noi-dung">{skip}</a>
{banner}<header class="site-head">
  <div class="wrap">
    <a class="brand" href="{home}"><img src="/assets/logo/tamhonkhoe-icon.svg" alt="" width="40" height="40">{ten_site}</a>
    <nav class="nav" aria-label="{nav_lab}">{nav}</nav>
  </div>
</header>
<main id="noi-dung"><div class="wrap">
{body}
</div></main>
<footer class="site-foot">
  <div class="wrap">
    <div class="cols">
      {foot}
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
