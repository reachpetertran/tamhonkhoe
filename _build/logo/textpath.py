from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
import unicodedata
_cache={}
def font(p):
    if p not in _cache: _cache[p]=TTFont(p)
    return _cache[p]
def text_path(txt, fontpath, size, x0, baseline, tracking=0.0):
    f=font(fontpath); gs=f.getGlyphSet(); cmap=f.getBestCmap(); upm=f['head'].unitsPerEm
    sc=size/upm; pen=SVGPathPen(gs); x=x0; bp=BoundsPen(gs)
    txt=unicodedata.normalize('NFC',txt)
    for ch in txt:
        g=cmap.get(ord(ch))
        if g is None: raise ValueError(f'missing glyph {ch!r}')
        t=(sc,0,0,-sc,x,baseline)
        gs[g].draw(TransformPen(pen,t)); gs[g].draw(TransformPen(bp,t))
        x+=gs[g].width*sc+tracking
    return pen.getCommands(), x-tracking-x0, bp.bounds
def centered(txt,fontpath,size,cx,baseline,tracking=0.0):
    _,w,b=text_path(txt,fontpath,size,0,baseline,tracking)
    # center by ink bounds
    x0=cx-(b[0]+b[2])/2
    d,w,b=text_path(txt,fontpath,size,x0,baseline,tracking)
    return d,b
