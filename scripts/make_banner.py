"""Generate header-light.svg / header-dark.svg for the GitHub profile README.

All text is converted to outlines (no font loading inside <img>), shaped with
HarfBuzz so kerning matches the real typeface.
"""
import io
import sys
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

W, H = 900, 232
X0 = 6  # left margin


class Face:
    def __init__(self, path, wght=None):
        tt = TTFont(path)
        if wght is not None and "fvar" in tt:
            tt = instantiateVariableFont(tt, {"wght": wght})
        buf = io.BytesIO()
        tt.save(buf)
        data = buf.getvalue()
        self.tt = TTFont(io.BytesIO(data))
        self.gs = self.tt.getGlyphSet()
        self.upem = self.tt["head"].unitsPerEm
        self.hbfont = hb.Font(hb.Face(data))
        self.order = self.tt.getGlyphOrder()

    def shape(self, text):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hbfont, buf, {"kern": True, "liga": False})
        out, pen_x = [], 0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            out.append((self.order[info.codepoint], info.cluster, pen_x + pos.x_offset, pos.x_advance))
            pen_x += pos.x_advance
        return out, pen_x

    def glyph_path(self, gname, x, y, size):
        s = size / self.upem
        pen = SVGPathPen(self.gs, ntos=lambda v: ("%.1f" % v).rstrip("0").rstrip("."))
        self.gs[gname].draw(TransformPen(pen, (s, 0, 0, -s, x, y)))
        return pen.getCommands()

    def advance(self, ch, size):
        _, w = self.shape(ch)
        return w * size / self.upem

    def text_path(self, text, x, y, size):
        glyphs, total = self.shape(text)
        s = size / self.upem
        d = "".join(self.glyph_path(g, x + gx * s, y, size) for g, _, gx, _ in glyphs)
        return d, total * s


def build(theme):
    if theme == "light":
        ink, muted, err = "#1F2328", "#59636E", "#CF222E"
    else:
        ink, muted, err = "#E6EDF3", "#9198A1", "#FF7B72"

    lora = Face("fonts/Lora.ttf", wght=500)
    lora_i = Face("fonts/LoraItalic.ttf", wght=400)
    mono = Face("fonts/DMMono.ttf")

    # --- Name, glyph by glyph so three letters can arrive "corrupted" -------
    name, size, base = "Andre Phan", 108, 112
    corrupt = {2: "b", 6: "F", 8: "e"}  # d->b, P->F, a->e  (index in `name`)
    glyphs, _ = lora.shape(name)
    s = size / lora.upem

    clean, fixes, wrongs, marks = [], [], [], []
    for k, (g, cluster, gx, adv) in enumerate(glyphs):
        x = X0 + gx * s
        d = lora.glyph_path(g, x, base, size)
        if cluster in corrupt:
            order = sorted(corrupt).index(cluster) + 1
            fixes.append(f'<path class="fix e{order}" d="{d}"/>')
            # centre the wrong glyph in the right glyph's advance box
            wg, ww = lora.shape(corrupt[cluster])
            wx = x + (adv * s - ww * s) / 2
            wd = lora.glyph_path(wg[0][0], wx, base, size)
            wrongs.append(f'<g class="wrong e{order}"><path class="jit" d="{wd}"/></g>')
            marks.append(
                f'<rect class="mark e{order}" x="{x + adv * s * 0.18:.1f}" y="{base + 14}" '
                f'width="{adv * s * 0.64:.1f}" height="3" rx="1.5"/>'
            )
        else:
            clean.append(d)

    tag_d, _ = lora_i.text_path("Building AI systems that fail gracefully.", X0 + 2, 168, 27)
    s1_d, _ = mono.text_path("receiving 10 symbols ...", X0 + 3, 214, 14)
    s2_d, _ = mono.text_path("RS(255,223)  3 symbol errors corrected", X0 + 3, 214, 14)

    css = f"""
    .ink{{fill:{ink}}} .muted{{fill:{muted}}} .err{{fill:{err}}}
    .all{{animation:in .6s ease-out both}}
    .fix{{fill:{ink};opacity:0;animation:fixin .28s ease-out forwards}}
    .wrong{{fill:{err};animation:out .22s ease-in forwards}}
    .jit{{animation:jit .12s steps(2) infinite}}
    .mark{{fill:{err};animation:out .3s ease-in forwards}}
    .e1{{animation-delay:1.05s}} .e2{{animation-delay:1.45s}} .e3{{animation-delay:1.8s}}
    .s1{{fill:{muted};animation:out .2s linear 2.1s forwards}}
    .s2{{fill:{muted};opacity:0;animation:fixin .4s ease-out 2.2s forwards}}
    .tag{{fill:{muted};opacity:0;animation:fixin .6s ease-out .35s forwards}}
    @keyframes in{{from{{opacity:0}}to{{opacity:1}}}}
    @keyframes fixin{{to{{opacity:1}}}}
    @keyframes out{{to{{opacity:0}}}}
    @keyframes jit{{0%{{transform:translate(0,0)}}50%{{transform:translate(1.5px,-1px)}}100%{{transform:translate(-1px,1px)}}}}
    @media (prefers-reduced-motion:reduce){{
      *{{animation:none!important}}
      .wrong,.mark,.s1{{opacity:0}} .fix,.s2,.tag{{opacity:1}}
    }}"""

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">
  <title id="t">Andre Phan</title>
  <desc id="d">Andre Phan. Building AI systems that fail gracefully. Three letters of the name arrive corrupted and are corrected by a Reed-Solomon decoder.</desc>
  <style>{css}
  </style>
  <g class="all">
    <path class="ink" d="{''.join(clean)}"/>
    {''.join(fixes)}
    {''.join(wrongs)}
    {''.join(marks)}
    <path class="tag" d="{tag_d}"/>
    <path class="s1" d="{s1_d}"/>
    <path class="s2" d="{s2_d}"/>
  </g>
</svg>
"""
    return svg


def static(svg, state):
    """Freeze a frame for previewing (cairosvg ignores CSS animation)."""
    if state == "start":
        extra = ".fix,.s2{opacity:0!important} .tag{opacity:1!important} .wrong,.mark,.s1{opacity:1!important}"
    else:
        extra = ".fix,.s2,.tag{opacity:1!important} .wrong,.mark,.s1{opacity:0!important}"
    return svg.replace("</style>", extra + "</style>").replace("animation", "x-anim")


if __name__ == "__main__":
    import cairosvg
    for theme in ("light", "dark"):
        svg = build(theme)
        open(f"out/assets/header-{theme}.svg", "w").write(svg)
        bg = "#FFFFFF" if theme == "light" else "#0D1117"
        for st in ("start", "end"):
            cairosvg.svg2png(bytestring=static(svg, st).encode(), write_to=f"preview/{theme}-{st}.png",
                             output_width=1800, background_color=bg)
    print("ok")
