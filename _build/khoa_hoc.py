"""Khung chương trình: sinh /khoa-hoc/ (Việt) và /en/courses/ (Anh) từ khoa-hoc.yaml.

Mỗi khóa có một trang chi tiết kiểu daynentang.com/khoa-hoc/...: dòng phân cấp, bảng tóm tắt,
lịch theo tuần (bài, đoạn kinh, mục tiêu đo được), khoa học, giới hạn, "Dừng tập khi".
Đây là khung DỰ KIẾN; bài thật vẫn đi theo cổng xuất bản riêng.
"""
import html
import os

import yaml

from khung import CHUA_KIEM, DAYNENTANG_GIUP, DAYNENTANG_GIUP_EN, LoiNoiDung

TEP = 'khoa-hoc.yaml'
GOC_VI, GOC_EN = '/khoa-hoc/', '/en/courses/'

TRANG_THAI = {
    'dang-mo': ('Đang mở', 'Open'),
    'dang-soan': ('Đang soạn', 'In progress'),
    'chua-bat-dau': ('Chưa bắt đầu', 'Not started'),
}
DUYET = {
    'chu-du-an': ('Lên trang khi chủ dự án duyệt', 'Published once the project owner approves'),
    'truyen-thong': ('Cần người duyệt từ trong truyền thống', 'Needs a reviewer from within the tradition'),
    'truyen-thong-gt': ('Cần hai người duyệt từ hai truyền thống', 'Needs two reviewers from two traditions'),
    'noi-bo': ('Soạn ở khu nội bộ trước', 'Drafted internally first'),
}
LO_TRINH = [
    ('Th11–12/2026', 'Nov–Dec 2026', 'Giao thoa 0, tuần 3–6; dạy thử Góc trẻ', 'Convergence 0, weeks 3–6; trial-teach the kids’ corner'),
    ('Th1–2/2027', 'Jan–Feb 2027', 'Khắc kỷ 1: Điều trong tay ta', 'Stoicism 1: What is in our power'),
    ('Th3–4/2027', 'Mar–Apr 2027', 'Phật giáo 1; Giao thoa 1, tuần 7–9', 'Buddhism 1; Convergence 1, weeks 7–9'),
    ('Th5–6/2027', 'May–Jun 2027', 'Giao thoa 1, tuần 10–12; Thân thể 1', 'Convergence 1, weeks 10–12; Body 1'),
    ('Nửa cuối 2027', 'Second half of 2027', 'Khắc kỷ 2, Phật giáo 2; Tầng 1 của các truyền thống còn lại khi có người duyệt',
     'Stoicism 2, Buddhism 2; level 1 of the other traditions once reviewers are found'),
    ('2028', '2028', 'Tầng 3–4; Thân thể 3–4 sau khi chuyên gia dinh dưỡng duyệt',
     'Levels 3–4; Body 3–4 after review by a dietitian'),
]
TANG = [
    ('1', 'Nền móng', 'Foundations', 'Khái niệm cốt lõi, đọc chậm kinh', 'Core ideas, slow reading', '10–15'),
    ('2', 'Thực hành sâu', 'Deeper practice', 'Duy trì thực hành, nhận ra mẫu phản ứng', 'Sustained practice, noticing patterns', '20–30'),
    ('3', 'Bản chất', 'The nature of things', 'Tâm, ngã, vô thường, Thượng Đế, cái chết', 'Mind, self, change, God, death', '30–45'),
    ('4', 'Hòa nhập', 'Integration', 'Ăn uống, công việc, gia đình, phục vụ', 'Food, work, family, service', '–'),
]

e = html.escape


def doc(src):
    """Đọc khoa-hoc.yaml. Trả về None nếu kho chưa có tệp này."""
    p = os.path.join(src, TEP)
    if not os.path.exists(p):
        return None
    with open(p, encoding='utf-8') as f:
        raw = f.read()
    data = yaml.safe_load(raw) or {}
    data['_raw'] = raw
    nhom_ids = {n['id'] for n in data.get('nhom', [])}
    nc = data.get('nghien_cuu') or {}
    ma_da_co = set()
    for k in data.get('khoa', []):
        for f in ('ma', 'slug', 'slug_en', 'nhom', 'ten', 'ten_en', 'mo_ta', 'mo_ta_en', 'trang_thai', 'duyet'):
            if not k.get(f):
                raise LoiNoiDung(f'{TEP}: khóa {k.get("ma", "?")} thiếu trường {f}')
        if k['ma'] in ma_da_co:
            raise LoiNoiDung(f'{TEP}: trùng mã khóa {k["ma"]}')
        ma_da_co.add(k['ma'])
        if k['nhom'] not in nhom_ids:
            raise LoiNoiDung(f'{TEP}: khóa {k["ma"]} có nhom "{k["nhom"]}" không có trong danh sách nhom')
        if k['trang_thai'] not in TRANG_THAI or k['duyet'] not in DUYET:
            raise LoiNoiDung(f'{TEP}: khóa {k["ma"]} có trang_thai hoặc duyet không hợp lệ')
        for nid in k.get('nghien_cuu') or []:
            if nid not in nc:
                raise LoiNoiDung(f'{TEP}: khóa {k["ma"]} dùng nghiên cứu "{nid}" chưa khai báo')
        k['_bai'] = [_tach_bai(k['ma'], d) for d in k.get('bai') or []]
        tep = k.get('bai_tep') or []
        if len(tep) > len(k['_bai']):
            raise LoiNoiDung(f'{TEP}: khóa {k["ma"]} có bai_tep dài hơn danh sách bai')
        for b, f in zip(k['_bai'], tep):
            b['tep'] = f or ''
    return data


def _tach_bai(ma, dong):
    phan = [p.strip() for p in str(dong).split('|')]
    # "Kinh VI || Kinh EN" bị tách thành 2 phần rỗng ở giữa -> ghép lại
    while len(phan) < 3:
        phan.append('')
    ten, ten_en = phan[0], phan[1]
    rest = phan[2:]
    if len(rest) >= 3 and rest[1] == '':
        kinh, kinh_en, rest = rest[0], rest[2], rest[3:]
    else:
        kinh, rest = rest[0], rest[1:]
        kinh_en = kinh
    muc = rest[0] if len(rest) > 0 else ''
    muc_en = rest[1] if len(rest) > 1 else ''
    if not ten or not ten_en:
        raise LoiNoiDung(f'{TEP}: khóa {ma} có dòng bài thiếu tên Việt hoặc Anh: {dong}')
    if bool(muc) != bool(muc_en):
        raise LoiNoiDung(f'{TEP}: khóa {ma} có mục tiêu chỉ ở một ngôn ngữ: {dong}')
    return {'ten': ten, 'ten_en': ten_en, 'kinh': kinh, 'kinh_en': kinh_en, 'muc': muc, 'muc_en': muc_en}


def url(k, en):
    return f'{GOC_EN}{k["slug_en"]}/' if en else f'{GOC_VI}{k["slug"]}/'


def _duyet(k):
    d = k['duyet']
    if d == 'truyen-thong' and k['nhom'] == 'giao-thoa':
        d = 'truyen-thong-gt'
    return DUYET[d]


def _so_tuan(k, en):
    n = len(k['_bai'])
    if k['nhom'] == 'goc-tre':
        return f'{n} activities' if en else f'{n} hoạt động'
    return (f'{n} weeks' if n != 1 else '1 week') if en else f'{n} tuần'


def _phut(k, en):
    p = k.get('phut_en') if en and k.get('phut_en') else k.get('phut', '')
    if any(c.isdigit() for c in str(p)):
        return f'{p} min/day' if en else f'{p} phút/ngày'
    return str(p)


def the(k, en):
    """Thẻ khóa kiểu daynentang: nhãn trạng thái, tên, mô tả, số tuần."""
    tt = TRANG_THAI[k['trang_thai']][1 if en else 0]
    cls = 'tag' if k['trang_thai'] == 'dang-mo' else 'tag soon'
    ten = k['ten_en'] if en else k['ten']
    mo = k['mo_ta_en'] if en else k['mo_ta']
    tang = k.get('tang', '–')
    tang_txt = '' if tang == '–' else (f' · Level {tang}' if en else f' · Tầng {tang}')
    return (f'<a class="card" href="{url(k, en)}"><span class="{cls}">{e(tt)}</span>'
            f'<h3><span class="ma">{e(k["ma"])}</span> {e(ten)}</h3><p>{e(mo)}</p>'
            f'<p class="muted small">{e(_so_tuan(k, en))}{e(tang_txt)} · {e(_phut(k, en))}</p></a>')


def the_nhom(data, nhom_id, en):
    """Lưới thẻ các khóa của một nhóm (dùng trên /giao-thoa/, /khe/<x>/, /than-the/)."""
    if not data:
        return ''
    ds = [k for k in data['khoa'] if k['nhom'] == nhom_id]
    if not ds:
        return ''
    tieu = 'Planned courses' if en else 'Các khóa dự kiến'
    xem = (f'<a href="{GOC_EN}">full curriculum</a>' if en else f'<a href="{GOC_VI}">toàn bộ khung chương trình</a>')
    return (f'<h2>{tieu}</h2><p class="muted small">{"See the" if en else "Xem"} {xem}.</p>'
            '<div class="grid">' + ''.join(the(k, en) for k in ds) + '</div>')


def _dung_tap(en):
    if en:
        return ('<section class="box warn"><h2>Stop practising if</h2><p>Stop or shorten practice and talk to a '
                'professional if you notice: rising anxiety or panic; low mood that lingers; feeling that you or the '
                'world is ‘not real’; flooding memories of trauma; several nights of poor sleep; hearing or seeing '
                'things others do not; thoughts of harming yourself. People with a history of psychosis, bipolar '
                'disorder or severe PTSD should ask a doctor before practising more than 20 minutes a day.</p>'
                f'<p><a class="btn warm" href="{DAYNENTANG_GIUP_EN}">Get help now</a></p></section>')
    return ('<section class="box warn"><h2>Dừng tập khi</h2><p>Dừng hoặc rút ngắn buổi tập và hỏi ý kiến chuyên gia '
            'nếu bạn thấy: lo âu hay hoảng sợ tăng lên; tâm trạng chùng xuống kéo dài; cảm giác mình hay thế giới '
            '"không thật"; ký ức sang chấn trỗi dậy dồn dập; mất ngủ nhiều đêm; nghe hoặc thấy điều người khác '
            'không thấy; ý nghĩ tự hại. Người có tiền sử loạn thần, rối loạn lưỡng cực hoặc PTSD nặng nên hỏi bác sĩ '
            'trước khi tập trên 20 phút mỗi ngày.</p>'
            f'<p><a class="btn warm" href="{DAYNENTANG_GIUP}">Cần giúp ngay</a></p></section>')


def _nc_li(nc, nid, en):
    n = nc[nid]
    link = f' · <a href="{e(n["url"])}" rel="noopener">{"source" if en else "nguồn"}</a>' if n.get('url') else ''
    return f'<li>{e(n["en"] if en else n["vi"])} <span class="muted small">({e(n["trich"])}{link})</span></li>'


def trang_khoa(k, data, en, bai_url=None):
    nhom = {n['id']: n for n in data['nhom']}[k['nhom']]
    tt = TRANG_THAI[k['trang_thai']][1 if en else 0]
    ten = k['ten_en'] if en else k['ten']
    ten_nhom = nhom['ten_en'] if en else nhom['ten']
    goc = GOC_EN if en else GOC_VI
    crumb = (f'<p class="eyebrow"><a href="{goc}">{"Courses" if en else "Khóa học"}</a> · {e(ten_nhom)} · '
             f'{"Course" if en else "Khóa"} {e(k["ma"])} · {e(tt)}</p>')
    du_kien = ('<div class="box"><p><strong>Planned outline.</strong> These lessons are not published yet. Lesson '
               'titles and passages may change during writing and review.</p></div>') if en else (
              '<div class="box"><p><strong>Khung dự kiến.</strong> Các bài này chưa lên trang. Tên bài và đoạn kinh '
              'có thể đổi khi soạn và duyệt.</p></div>')
    if k['nhom'] == 'goc-tre':
        cho = 'Children 6+ with an adult' if en else 'Trẻ từ 6 tuổi, luôn có người lớn đi cùng'
    else:
        cho = ('Adults learning on their own' if en else 'Người lớn tự học') + (
            '' if (k.get('tang') in ('3',) and not k.get('co_goc_tre')) or k['nhom'] == 'than-the' else
            ('; each lesson has a short kids’ corner' if en else '; mỗi bài có mục Góc trẻ ngắn'))
    tien_do = k.get('tien_do_en' if en else 'tien_do')
    tinh_trang = tt + (f' – {tien_do}' if tien_do else '')
    rows = [
        ('For' if en else 'Dành cho', cho),
        ('Length' if en else 'Thời lượng', f'{_so_tuan(k, en)} · {_phut(k, en)}'),
        ('Level' if en else 'Tầng', k.get('tang', '–')),
        ('Status' if en else 'Tình trạng', tinh_trang),
        ('Publishing' if en else 'Lên trang', _duyet(k)[1 if en else 0]),
        ('Expected' if en else 'Dự kiến', k.get('ra_mat_en' if en else 'ra_mat', '–')),
    ]
    bang = ('<div class="table-wrap"><table><tbody>' +
            ''.join(f'<tr><th scope="row">{e(a)}</th><td>{e(str(b))}</td></tr>' for a, b in rows) +
            '</tbody></table></div>')
    bai_url = bai_url or {}
    da_len = [b for b in k['_bai'] if b.get('tep') in bai_url]
    if da_len:
        du_kien = ('<div class="box"><p><strong>Lessons with a link are published.</strong> Lessons without a link '
                   'are still a planned outline; their titles and passages may change during writing and review.</p></div>'
                   ) if en else (
                  '<div class="box"><p><strong>Bài có link đã lên trang.</strong> Bài chưa có link vẫn là khung dự kiến; '
                  'tên bài và đoạn kinh có thể đổi khi soạn và duyệt.</p></div>')
    co_muc = any(b['muc'] for b in k['_bai'])
    don_vi = ('Activity' if en else 'Hoạt động') if k['nhom'] == 'goc-tre' else ('Week' if en else 'Tuần')
    head = (f'<th>{don_vi}</th><th>{"Lesson" if en else "Bài"}</th><th>{"Passages" if en else "Đoạn kinh"}</th>'
            + (f'<th>{"Measurable goal" if en else "Mục tiêu đo được"}</th>' if co_muc else ''))
    body = ''
    for i, b in enumerate(k['_bai'], 1):
        kinh = b['kinh_en'] if en else b['kinh']
        ten_bai = e(b["ten_en"] if en else b["ten"])
        if b.get('tep') in bai_url:
            ten_bai = f'<a href="{e(bai_url[b["tep"]][1 if en else 0])}">{ten_bai}</a>'
        body += (f'<tr><td>{i}</td><td>{ten_bai}</td><td>{e(kinh or "–")}</td>'
                 + (f'<td>{e(b["muc_en"] if en else b["muc"])}</td>' if co_muc else '') + '</tr>')
    lich_tieu = (f'Plan: {_so_tuan(k, True)}' if en else f'Lịch {_so_tuan(k, False)}')
    lich = (f'<h2>{e(lich_tieu)}</h2><div class="table-wrap"><table><thead><tr>{head}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>')
    nc = data.get('nghien_cuu') or {}
    ids = k.get('nghien_cuu') or []
    khoa_hoc = ''
    if ids:
        khoa_hoc = (f'<h2>{"What science finds" if en else "Khoa học thấy gì"}</h2><ul>'
                    + ''.join(_nc_li(nc, i, en) for i in ids) + '</ul>')
    gh = k.get('gioi_han_en' if en else 'gioi_han')
    gioi = f'<h2>{"Limits, honestly" if en else "Giới hạn, nói thật"}</h2><p>{e(gh)}</p>' if gh else ''
    ve = f'<p><a href="{goc}">← {"All courses" if en else "Tất cả khóa học"}</a></p>'
    return (f'{crumb}<h1>{e(ten)}</h1><p class="lead">{e(k["mo_ta_en"] if en else k["mo_ta"])}</p>'
            f'{du_kien}{bang}{lich}{khoa_hoc}{gioi}{_dung_tap(en)}{ve}')


def trang_muc_luc(data, en):
    khoa = data['khoa']
    so_tuan = sum(len(k['_bai']) for k in khoa if k['nhom'] != 'goc-tre')
    if en:
        mo = (f'<p class="eyebrow">Curriculum</p><h1>All courses</h1><p class="lead">The full plan for '
              f'tamhonkhoe.com: {len(khoa)} courses, about {so_tuan} weeks of lessons. Lessons go live one at a time '
              'as they are written and reviewed.</p>')
    else:
        mo = (f'<p class="eyebrow">Khung chương trình</p><h1>Khóa học</h1><p class="lead">Toàn bộ kế hoạch nội dung '
              f'của tamhonkhoe.com: {len(khoa)} khóa, khoảng {so_tuan} tuần bài học. Bài lên trang dần, khi đã soạn '
              'và duyệt xong.</p>')
    # Bốn tầng
    tang = ''.join(f'<tr><td>{t[0]}</td><td>{e(t[2] if en else t[1])}</td><td>{e(t[4] if en else t[3])}</td>'
                   f'<td>{e(t[5])}</td></tr>' for t in TANG)
    tang_html = (f'<h2>{"Four levels" if en else "Bốn tầng"}</h2><div class="table-wrap"><table><thead><tr>'
                 f'<th>{"Level" if en else "Tầng"}</th><th>{"Name" if en else "Tên"}</th>'
                 f'<th>{"Content" if en else "Nội dung"}</th><th>{"Min/day" if en else "Phút/ngày"}</th></tr></thead>'
                 f'<tbody>{tang}</tbody></table></div>')
    # Nhóm
    nhom_html = ''
    for n in data['nhom']:
        ds = [k for k in khoa if k['nhom'] == n['id']]
        if not ds:
            continue
        nhom_html += (f'<h2 id="{e(n["id"])}">{e(n["ten_en"] if en else n["ten"])}</h2>'
                      f'<p class="muted">{e(n["mo_ta_en"] if en else n["mo_ta"])}</p>'
                      '<div class="grid">' + ''.join(the(k, en) for k in ds) + '</div>')
    # Lộ trình
    lt = ''.join(f'<tr><td>{e(r[1] if en else r[0])}</td><td>{e(r[3] if en else r[2])}</td></tr>' for r in LO_TRINH)
    lo_trinh = (f'<h2 id="lo-trinh">{"Release plan" if en else "Lộ trình"}</h2>'
                f'<p>{"A one-person project, so the plan is deliberately slow." if en else "Dự án do một người làm, nên lộ trình cố ý đi chậm."}</p>'
                f'<div class="table-wrap"><table><thead><tr><th>{"When" if en else "Khi nào"}</th>'
                f'<th>{"What" if en else "Việc"}</th></tr></thead><tbody>{lt}</tbody></table></div>')
    # Cách đăng
    if en:
        dang = ('<h2>How a course goes live</h2><ul>'
                '<li><strong>Published once the project owner approves</strong>: less sensitive courses that do not '
                'set out the doctrine or ritual of one religion (Stoicism, Body 1–2, this outline). The page says '
                'clearly that no reviewer from a tradition has checked it.</li>'
                '<li><strong>Needs a reviewer from the tradition</strong>: courses about one religion need at least '
                'one reviewer from within it; Convergence needs two reviewers from two traditions.</li>'
                '<li><strong>Drafted internally first</strong>: level 3 (God, self, death), detailed fasting, and '
                'anything still being debated.</li></ul>'
                '<p>Every lesson still has to be descriptive, non-divisive, use cleanly licensed sources and include '
                'safety notes. See <a href="/en/about/">About and principles</a>.</p>')
    else:
        dang = ('<h2>Một khóa lên trang thế nào</h2><ul>'
                '<li><strong>Lên trang khi chủ dự án duyệt</strong>: khóa ít nhạy cảm, không trình bày giáo lý hay '
                'nghi lễ riêng của một tôn giáo (Khắc kỷ, Thân thể 1–2, chính trang khung này). Trang ghi rõ là chưa '
                'có người duyệt từ trong truyền thống.</li>'
                '<li><strong>Cần người duyệt từ trong truyền thống</strong>: khóa về một tôn giáo cần ít nhất một '
                'người duyệt từ trong truyền thống đó; Giao thoa cần hai người duyệt từ hai truyền thống.</li>'
                '<li><strong>Soạn ở khu nội bộ trước</strong>: Tầng 3 (Thượng Đế, ngã, cái chết), nhịn ăn chi tiết, '
                'nội dung đang tranh luận.</li></ul>'
                '<p>Mọi bài vẫn phải mô tả, không chia rẽ, dùng nguồn có giấy phép rõ và có phần an toàn. Xem '
                '<a href="/gioi-thieu/">Giới thiệu và nguyên tắc</a>.</p>')
    # Nghiên cứu
    nc = data.get('nghien_cuu') or {}
    dung = {}
    for k in khoa:
        for nid in k.get('nghien_cuu') or []:
            dung.setdefault(nid, []).append(k['ma'])
    rows = ''
    for nid, n in nc.items():
        link = f'<a href="{e(n["url"])}" rel="noopener">{e(n["trich"])}</a>' if n.get('url') else e(n['trich'])
        rows += (f'<tr><td>{e(n["en"] if en else n["vi"])}</td><td>{link}</td>'
                 f'<td>{e(", ".join(dung.get(nid, [])) or "–")}</td></tr>')
    nghien = (f'<h2 id="nghien-cuu">{"Studies used in this outline" if en else "Nghiên cứu dùng trong khung"}</h2>'
              f'<p class="small">{"Studies that only show a correlation are marked as such." if en else "Nghiên cứu chỉ cho thấy tương quan được ghi rõ là tương quan."}</p>'
              f'<div class="table-wrap"><table><thead><tr><th>{"Finding" if en else "Thấy gì"}</th>'
              f'<th>{"Source" if en else "Nguồn"}</th><th>{"Used in" if en else "Dùng ở"}</th></tr></thead>'
              f'<tbody>{rows}</tbody></table></div>')
    muc = (f'<nav class="box small" aria-label="{"On this page" if en else "Trên trang này"}"><p>'
           + ' · '.join(f'<a href="#{e(n["id"])}">{e(n["ten_en"] if en else n["ten"])}</a>'
                        for n in data['nhom'] if any(k['nhom'] == n['id'] for k in khoa))
           + f' · <a href="#lo-trinh">{"Release plan" if en else "Lộ trình"}</a>'
           + f' · <a href="#nghien-cuu">{"Studies" if en else "Nghiên cứu"}</a></p></nav>')
    return mo + muc + tang_html + nhom_html + lo_trinh + dang + nghien


def build(data, out, che_do, trang, da_co, bai_url=None):
    """Sinh trang mục lục và trang từng khóa, cả hai ngôn ngữ."""
    if not data:
        return
    if che_do == 'public':
        for nhan in CHUA_KIEM:
            if nhan in data['_raw']:
                raise LoiNoiDung(f'{TEP}: còn nhãn {nhan}, không được lên public')
    trang(out, GOC_VI, 'Khóa học', 'Khung chương trình của tamhonkhoe.com: các khóa, lịch từng tuần và lộ trình.',
          trang_muc_luc(data, False), che_do, current=GOC_VI, alt=GOC_EN)
    trang(out, GOC_EN, 'Courses', 'The tamhonkhoe.com curriculum: courses, weekly plans and release plan.',
          trang_muc_luc(data, True), che_do, current=GOC_EN, lang='en', alt=GOC_VI)
    da_co.update({GOC_VI, GOC_EN})
    for k in data['khoa']:
        vi, en = url(k, False), url(k, True)
        trang(out, vi, f'{k["ma"]} · {k["ten"]}', k['mo_ta'], trang_khoa(k, data, False, bai_url), che_do,
              current=GOC_VI, alt=en)
        trang(out, en, f'{k["ma"]} · {k["ten_en"]}', k['mo_ta_en'], trang_khoa(k, data, True, bai_url), che_do,
              current=GOC_EN, lang='en', alt=vi)
        da_co.update({vi, en})
