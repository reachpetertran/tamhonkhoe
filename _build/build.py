"""Sinh trang tĩnh cho tamhonkhoe (song ngữ: tiếng Việt ở /, tiếng Anh ở /en/).

    python3 _build/build.py --site noibo                 # mọi bài -> public/ (site nội bộ, khóa mật khẩu)
    python3 _build/build.py --site public --src <kho>    # chỉ dùng trong publish.py

Dừng build (thoát mã 1) khi nội dung vi phạm luật: dịch nguồn không cho dịch, trích quá dài,
quá 3 đoạn kinh, thiếu "Dừng tập khi", nguồn chưa xác nhận khi lên public...
"""
import argparse
import html
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
from khung import (DAYNENTANG_GIUP, DAYNENTANG_GIUP_EN, GATE_KEYS, GATE_TEN, HEADERS_CHUNG,
                   HEADERS_NOIBO_THEM, KHE, KHE_EN, LICENSE_TEN, LICENSE_TEN_EN, LoiNoiDung,
                   doc_nguon, doc_tat_ca_bai, en_path, render_bai, trang)
import khoa_hoc

NHAN_STATUS = {'nhap': 'Bản nháp', 'day-thu': 'Đang dạy thử', 'da-duyet': 'Đã duyệt'}
NHAN_STATUS_EN = {'nhap': 'Draft', 'day-thu': 'In trial teaching', 'da-duyet': 'Reviewed'}


def _the(b, che_do):
    if che_do != 'noibo':
        return ''
    m = b.meta
    en = b.lang == 'en'
    vis = ('Public' if m['visibility'] == 'public' else ('Admin only' if en else 'Chỉ admin'))
    ok = sum(1 for k in GATE_KEYS if m['gate'][k])
    st = (NHAN_STATUS_EN if en else NHAN_STATUS)[m['status']]
    cong = f'Gate {ok}/5' if en else f'Cổng {ok}/5'
    return f'<span class="tag">{vis}</span> <span class="tag soon">{st}</span> <span class="tag soon">{cong}</span>'


def _ds(bais, che_do, en=False):
    if not bais:
        return f'<p class="muted">{"No articles yet." if en else "Chưa có bài."}</p>'
    return ''.join(f'<a class="card" href="{b.url}">{_the(b, che_do)}<h3>{html.escape(b.title)}</h3>'
                   f'<p>{html.escape(str(b.meta.get("description", "")))}</p></a>' for b in bais)


def build(src, out, che_do):
    nguon = doc_nguon(os.path.join(src, 'sources.yaml'))
    kh = khoa_hoc.doc(src)
    bais = doc_tat_ca_bai(os.path.join(src, 'content'))
    if che_do == 'public':
        sai = [b.rel for b in bais if not b.qua_cong()[0]]
        if sai:
            raise LoiNoiDung('Có bài chưa qua cổng trong bản public: ' + ', '.join(sai))
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)

    # Tài nguyên tĩnh
    shutil.copytree(os.path.join(src, 'assets'), os.path.join(out, 'assets'))
    for fn in ('favicon.svg', 'favicon.ico', 'apple-touch-icon.png'):
        p = os.path.join(src, 'assets', 'logo', fn)
        if os.path.exists(p):
            shutil.copy(p, os.path.join(out, fn))

    # Bài
    da_co = set()
    for b in bais:
        en = b.lang == 'en'
        noi_dung, gp, ds_nguon = render_bai(b, nguon, che_do)
        alt = b.cap.url if b.cap else None
        meta = ''
        if che_do == 'noibo':
            gate = ''.join(f'<li>{"✔" if b.meta["gate"][k] else "✘"} {GATE_TEN[k]}</li>' for k in GATE_KEYS)
            duyet = ', '.join(b.meta.get('reviewers') or []) or ('none yet' if en else 'chưa có')
            cap = (f'<a href="{b.cap.url}">{"bản tiếng Việt" if en else "bản tiếng Anh"}</a>' if b.cap
                   else ('<strong>chưa có bản tiếng Việt</strong>' if en else '<strong>chưa có bản tiếng Anh</strong>'))
            meta = (f'<div class="box noibo-meta"><p>{_the(b, che_do)}</p><p class="small">Tệp: <code>'
                    f'{html.escape(b.rel)}</code> · Người duyệt: {html.escape(duyet)} · Song ngữ: {cap}</p>'
                    f'<ul class="small">{gate}</ul></div>')
        nguon_html = ''
        if ds_nguon:
            lt = LICENSE_TEN_EN if en else LICENSE_TEN
            nguon_html = (f'<section class="sec"><h2>{"Scripture sources" if en else "Nguồn kinh điển"}</h2><ul>'
                          + ''.join(
                              f'<li>{html.escape(nguon[s]["title"])} – {html.escape(nguon[s].get("translator", ""))} '
                              f'({lt[nguon[s]["license"]]})'
                              + (f' · <a href="{html.escape(nguon[s]["url"])}" rel="noopener">link</a>'
                                 if nguon[s].get('url') else '')
                              + '</li>' for s in ds_nguon) + '</ul></section>')
        ghi_duyet = ''
        if b.meta.get('muc_duyet') == 'chu-du-an' and not b.rel.startswith('trang/'):
            ghi_duyet = ('<div class="box small"><p>Published after review by the project owner. No reviewer from '
                         'within a tradition has checked this page yet.</p></div>' if en else
                         '<div class="box small"><p>Bài lên trang theo duyệt của chủ dự án. Chưa có người duyệt từ '
                         'trong truyền thống kiểm bài này.</p></div>')
        trang(out, b.url, b.title, str(b.meta.get('description', b.title)),
              f'<article class="lesson">{meta}<h1>{html.escape(b.title)}</h1>{ghi_duyet}{noi_dung}{nguon_html}</article>',
              che_do, giay_phep=gp, lang=b.lang, alt=alt)
        da_co.add(b.url)

    # Bài thật của từng khóa (khoa-hoc.yaml: bai_tep) -> link trong lịch tuần, chỉ khi bài có trong bản build này
    bai_url = {b.rel_vi[:-3]: (b.url, b.cap.url if b.cap else b.url) for b in bais if b.lang == 'vi'}
    khoa_hoc.build(kh, out, che_do, trang, da_co, bai_url)
    tk = lambda nhom_id, en=False: khoa_hoc.the_nhom(kh, nhom_id, en)

    vi_bais = [b for b in bais if b.lang == 'vi']
    en_bais = [b for b in bais if b.lang == 'en']
    nhom = lambda ds, pre: [b for b in ds if b.rel_vi.startswith(pre)]

    # Trang mục lục: sinh cả bản Việt và bản Anh, trừ khi đã có bài tự viết cho địa chỉ đó.
    def muc(url, title, desc, body, title_en, desc_en, body_en, current=None, chi_vi=False):
        url_en = None if chi_vi else en_path(url)
        if url not in da_co:
            trang(out, url, title, desc, body, che_do, current=current, alt=url_en)
            da_co.add(url)
        if url_en and url_en not in da_co:
            trang(out, url_en, title_en, desc_en, body_en, che_do, current=en_path(current) if current else None,
                  lang='en', alt=url)
            da_co.add(url_en)

    muc('/', 'Tâm Hồn Khỏe', 'Tự học đời sống tinh thần qua kinh điển gốc của nhiều truyền thống.',
        '<p class="eyebrow">Tự học miễn phí</p><h1>Tâm Hồn Khỏe</h1>'
        '<p class="lead">Trang đang được xây dựng. Các bài sẽ lên đây khi đã được người trong từng truyền thống duyệt.</p>'
        '<div class="cta"><a class="btn primary" href="/giao-thoa/">Giao thoa</a>'
        '<a class="btn" href="/khe/">Các truyền thống</a>'
        f'<a class="btn warm" href="{DAYNENTANG_GIUP}">Tôi cần giúp ngay</a></div>',
        'Tâm Hồn Khỏe – Healthy Soul', 'Free self-study of the spiritual life through the original scriptures of many traditions.',
        '<p class="eyebrow">Free self-study</p><h1>Tâm Hồn Khỏe – Healthy Soul</h1>'
        '<p class="lead">This site is being built. Articles will appear here once reviewers from each tradition '
        'have checked them.</p>'
        '<div class="cta"><a class="btn primary" href="/en/convergence/">Convergence</a>'
        '<a class="btn" href="/en/traditions/">Traditions</a>'
        f'<a class="btn warm" href="{DAYNENTANG_GIUP_EN}">I need help now</a></div>', current='/')
    muc('/giao-thoa/', 'Giao thoa', 'Những điểm chung trong thực hành của các truyền thống.',
        '<h1>Giao thoa</h1>' + _ds(nhom(vi_bais, 'giao-thoa/'), che_do) + tk('giao-thoa'),
        'Convergence', 'Practices that many traditions share – and where they differ.',
        '<h1>Convergence</h1>' + _ds(nhom(en_bais, 'giao-thoa/'), che_do, en=True) + tk('giao-thoa', True),
        current='/giao-thoa/')
    khe_html, khe_html_en = '', ''
    for slug, ten in KHE:
        ds, ds_en = nhom(vi_bais, f'khe/{slug}/'), nhom(en_bais, f'khe/{slug}/')
        ten_en = KHE_EN[slug]
        muc(f'/khe/{slug}/', ten, f'Khe {ten} trên tamhonkhoe.com', f'<h1>{ten}</h1>' + _ds(ds, che_do) + tk(slug),
            ten_en, f'{ten_en} on tamhonkhoe.com',
            f'<h1>{ten_en}</h1>' + _ds(ds_en, che_do, en=True) + tk(slug, True))
        khe_html += f'<a class="card" href="/khe/{slug}/"><h3>{ten}</h3><p class="muted">{len(ds)} bài</p></a>'
        khe_html_en += (f'<a class="card" href="{en_path(f"/khe/{slug}/")}"><h3>{ten_en}</h3>'
                        f'<p class="muted">{len(ds_en)} {"article" if len(ds_en) == 1 else "articles"}</p></a>')
    muc('/khe/', 'Các truyền thống', 'Các khe truyền thống trên tamhonkhoe.com',
        '<h1>Các truyền thống</h1><p>Mỗi truyền thống được trình bày theo lời của chính truyền thống đó, '
        'không xếp hơn kém.</p><div class="grid">' + khe_html + '</div>',
        'Traditions', 'The traditions covered on tamhonkhoe.com',
        '<h1>Traditions</h1><p>Each tradition is presented in its own words, without ranking one above another.</p>'
        '<div class="grid">' + khe_html_en + '</div>', current='/khe/')
    muc('/than-the/', 'Thân thể', 'Ăn uống và kỷ luật thân thể như một lựa chọn tùy ý cho người lớn khỏe mạnh.',
        '<h1>Thân thể</h1>' + _ds(nhom(vi_bais, 'than-the/'), che_do) + tk('than-the'),
        'Body', 'Eating and bodily discipline as an optional choice for healthy adults.',
        '<h1>Body</h1>' + _ds(nhom(en_bais, 'than-the/'), che_do, en=True) + tk('than-the', True),
        current='/than-the/')

    # Nguồn và bản quyền – sinh tự động từ sources.yaml
    def bang_nguon(en):
        lt = LICENSE_TEN_EN if en else LICENSE_TEN
        co, khong, chua = ('Yes', 'No', 'not checked') if en else ('Có', 'Không', 'chưa kiểm')
        return ''.join(
            f'<tr><td>{html.escape(s["title"])}</td><td>{html.escape(s.get("translator", ""))}</td>'
            f'<td>{lt[s["license"]]}</td><td>{co if s.get("may_translate") else khong}</td>'
            f'<td>{html.escape(str(s.get("checked_on") or chua))}</td>'
            f'<td>{"<a href=" + chr(34) + html.escape(s["url"]) + chr(34) + " rel=noopener>link</a>" if s.get("url") else "–"}</td></tr>'
            for sid, s in nguon.items())
    muc('/nguon-va-ban-quyen/', 'Nguồn và bản quyền', 'Danh mục nguồn kinh điển và giấy phép.',
        '<h1>Nguồn và bản quyền</h1><p>Bài viết, hình SVG và bản tự dịch của tamhonkhoe dùng '
        '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. Trang dùng nguồn CC BY-NC '
        'dùng CC BY-NC 4.0 cho toàn trang. Đoạn trích từ nguồn không cho sửa ghi giấy phép gốc ngay dưới đoạn trích.</p>'
        '<div class="table-wrap"><table><thead><tr><th>Nguồn</th><th>Dịch giả</th><th>Giấy phép</th>'
        '<th>Được tự dịch</th><th>Ngày kiểm</th><th>Link</th></tr></thead><tbody>' + bang_nguon(False)
        + '</tbody></table></div>',
        'Sources and licences', 'List of scripture sources and their licences.',
        '<h1>Sources and licences</h1><p>Articles, SVG images and tamhonkhoe’s own translations are licensed '
        '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. A page that uses a CC BY-NC source '
        'is CC BY-NC 4.0 as a whole. Passages from sources that may not be modified carry their original licence '
        'directly below the passage.</p>'
        '<div class="table-wrap"><table><thead><tr><th>Source</th><th>Translator</th><th>Licence</th>'
        '<th>May be translated</th><th>Checked on</th><th>Link</th></tr></thead><tbody>' + bang_nguon(True)
        + '</tbody></table></div>', current='/nguon-va-ban-quyen/')

    if che_do == 'noibo':
        trang(out, '/goc-rieng/', 'Góc riêng', 'Góc riêng của gia đình – luôn là admin.',
              '<h1>Góc riêng</h1>' + _ds(nhom(vi_bais, 'goc-rieng/'), che_do), che_do, current='/goc-rieng/')
        rows = ''
        for b in bais:
            ok, ly_do = b.qua_cong()
            rows += (f'<tr><td><a href="{b.url}">{html.escape(b.title)}</a><br><code class="small">{html.escape(b.rel)}</code></td>'
                     f'<td>{"EN" if b.lang == "en" else "VI"}</td>'
                     f'<td>{b.meta["visibility"]}</td><td>{NHAN_STATUS[b.meta["status"]]}</td>'
                     f'<td>{"Sẽ lên public" if ok else html.escape("; ".join(ly_do))}</td></tr>')
        trang(out, '/quan-tri/', 'Quản trị', 'Tình trạng cổng xuất bản của từng bài.',
              '<h1>Quản trị: cổng xuất bản</h1><p>Bảng này cho biết bài nào sẽ được publish.py sao chép sang kho '
              'public. Bài song ngữ chỉ lên public khi cả bản tiếng Việt và bản tiếng Anh cùng qua cổng.</p>'
              '<div class="table-wrap"><table><thead><tr><th>Bài</th><th>Ngôn ngữ</th><th>Hiển thị</th>'
              '<th>Trạng thái</th><th>Cổng</th></tr></thead><tbody>'
              + (rows or '<tr><td colspan="5">Chưa có bài.</td></tr>') + '</tbody></table></div>',
              che_do, current='/quan-tri/')
        da_co.update({'/goc-rieng/', '/quan-tri/'})

    trang(out, '/404.html', 'Không tìm thấy trang / Page not found', 'Trang không tồn tại. Page not found.',
          '<h1>Không tìm thấy trang</h1><p>Trang này không có hoặc đã đổi địa chỉ.</p>'
          '<p><a class="btn primary" href="/">Về trang chủ</a></p>'
          '<h2 lang="en">Page not found</h2><p lang="en">This page does not exist or has moved.</p>'
          '<p lang="en"><a class="btn" href="/en/">English home page</a></p>', che_do)

    # Header bảo mật, robots, sitemap
    with open(os.path.join(out, '_headers'), 'w', encoding='utf-8') as f:
        f.write(HEADERS_CHUNG + (HEADERS_NOIBO_THEM if che_do == 'noibo' else ''))
    with open(os.path.join(out, 'robots.txt'), 'w', encoding='utf-8') as f:
        if che_do == 'noibo':
            f.write('User-agent: *\nDisallow: /\n')
        else:
            f.write('User-agent: *\nAllow: /\n\nSitemap: https://tamhonkhoe.com/sitemap.xml\n')
    if che_do == 'public':
        urls = sorted(u for u in da_co if u != '/404.html')
        with open(os.path.join(out, 'sitemap.xml'), 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                    + ''.join(f'  <url><loc>https://tamhonkhoe.com{u}</loc></url>\n' for u in urls) + '</urlset>\n')
    return bais


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', choices=['noibo', 'public'], default='noibo')
    ap.add_argument('--src', default=os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    out = a.out or os.path.join(a.src, 'public')
    try:
        bais = build(a.src, out, a.site)
    except LoiNoiDung as e:
        print('DỪNG BUILD:', e, file=sys.stderr)
        sys.exit(1)
    print(f'Đã build {len(bais)} bài, site {a.site} -> {out}')


if __name__ == '__main__':
    main()
