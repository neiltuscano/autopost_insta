"""
f1jobs — Premium Daily Carousel Generator
Produces per carousel: 1 cover card + 5 individual job cards (all 1080x1080)
Run generate_all_carousels(jobs_25) to produce 5 carousels (30 images total).
"""
from __future__ import annotations  # Python 3.8 compat

from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import os, math

from config import FONT_DIR, OUTPUT_DIR, _ensure_fonts
_ensure_fonts()   # download Poppins if missing
FONT_DIR   = str(FONT_DIR)
OUTPUT_DIR = str(OUTPUT_DIR)

# ── Palette ───────────────────────────────────────────────────────────────────
C_BG      = (8,   11,  22)
C_SURFACE = (14,  18,  35)
C_CARD    = (18,  23,  45)
C_PANEL   = (24,  30,  58)
C_BORDER  = (32,  40,  72)
C_ORANGE  = (255, 95,  0)
C_ORANGE2 = (255, 140, 40)
C_GREEN   = (0,   210, 110)
C_GREEN2  = (0,   160, 85)
C_GOLD    = (255, 200, 0)
C_WHITE   = (255, 255, 255)
C_GRAY    = (120, 135, 165)
C_LGRAY   = (160, 175, 200)
C_TEAL    = (0,   195, 185)   # entry-level / new grad accent
C_TEAL2   = (0,   155, 148)

W = H = 1080

# Card accent colors cycling through jobs 1-5
ACCENTS = [
    (255, 95,   0),   # 1 — f1jobs orange
    (0,   180, 220),  # 2 — cyan
    (160,  80, 255),  # 3 — purple
    (0,   210, 130),  # 4 — green
    (255, 180,   0),  # 5 — amber
]


def poppins(style, size):
    return ImageFont.truetype(f"{FONT_DIR}/Poppins-{style}.ttf", size)


def text_w(font, text):
    bb = font.getbbox(text)
    return bb[2] - bb[0]


def text_h(font, text):
    bb = font.getbbox(text)
    return bb[3] - bb[1]


def draw_text_centered(draw, text, font, y, color, offset_x=0):
    x = (W - text_w(font, text)) // 2 + offset_x
    bb = font.getbbox(text)
    draw.text((x, y - bb[1]), text, font=font, fill=color)
    return text_h(font, text)


def draw_pill(draw, x, y, label, font, bg, fg=None, px=24, py=11, r=20):
    fg = fg or C_WHITE
    bb = font.getbbox(label)
    lw, lh = bb[2]-bb[0], bb[3]-bb[1]
    w2, h2 = lw + px*2, lh + py*2
    draw.rounded_rectangle([x, y, x+w2, y+h2], radius=r, fill=bg)
    draw.text((x+px, y+py-bb[1]), label, font=font, fill=fg)
    return x+w2, y+h2//2


def draw_bg(draw, accent=C_ORANGE):
    """Common dark background with subtle geometric lines."""
    draw.rectangle([(0,0),(W,H)], fill=C_BG)
    for i in range(10):
        x = W*0.2 + i*110
        draw.line([(x, 0), (x + W*0.5, H)], fill=(*accent, 5), width=1)
    draw.polygon([(W*0.7,0),(W,0),(W,H*0.3)], fill=(*accent, 12))
    draw.polygon([(0,H*0.8),(W*0.25,H),(0,H)], fill=(*accent, 8))
    draw.rectangle([(0,0),(W,8)], fill=accent)
    draw.rectangle([(0,H-8),(W,H)], fill=accent)


def brand_stamp(draw, fonts, accent=C_ORANGE, bottom=True):
    """f1jobs brand in bottom strip."""
    if not bottom:
        return
    strip_y = H - 80
    draw.rectangle([(0, strip_y),(W, H-8)], fill=C_SURFACE)
    # "f1" in orange, "jobs" in white
    f1w = text_w(fonts["brand"], "f1")
    total = f1w + text_w(fonts["brand"], "jobs")
    sx = (W - total) // 2
    bb = fonts["brand"].getbbox("f1")
    draw.text((sx, strip_y + 14 - bb[1]), "f1",   font=fonts["brand"], fill=accent)
    draw.text((sx+f1w, strip_y + 14 - bb[1]), "jobs", font=fonts["brand"], fill=C_WHITE)
    # handle right
    handle = "@f1jobs"
    hbb = fonts["small"].getbbox(handle)
    draw.text((W-54-(hbb[2]-hbb[0]), strip_y+22-hbb[1]), handle, font=fonts["small"], fill=C_GRAY)


def _is_entry_carousel(jobs: list[dict]) -> bool:
    """True when the majority of jobs in this carousel group are entry-level."""
    return sum(1 for j in jobs if j.get("level") == "entry") > len(jobs) / 2


# ─────────────────────────────────────────────────────────────────────────────
#  COVER CARD
# ─────────────────────────────────────────────────────────────────────────────
def make_cover(jobs: list[dict], carousel_num: int = 1) -> str:
    img  = Image.new("RGB", (W,H), C_BG)
    draw = ImageDraw.Draw(img, "RGBA")

    fonts = {
        "hero":    poppins("Bold",   96),
        "sub":     poppins("Bold",   52),
        "body":    poppins("Medium", 36),
        "small":   poppins("Regular",26),
        "tag":     poppins("Light",  24),
        "company": poppins("Bold",   30),
        "badge":   poppins("Bold",   22),
        "brand":   poppins("Bold",   28),
        "date":    poppins("Medium", 28),
    }

    is_entry = _is_entry_carousel(jobs)
    accent   = C_TEAL if is_entry else C_ORANGE

    draw_bg(draw, accent)

    # ── Date pill ─────────────────────────────────────────────────────────────
    today = datetime.now().strftime("%b %d, %Y")
    date_y = 60
    dw = text_w(fonts["date"], today)
    draw.rounded_rectangle([(W//2-dw//2-20, date_y),
                             (W//2+dw//2+20, date_y+50)],
                            radius=14, fill=C_PANEL)
    bb = fonts["date"].getbbox(today)
    draw.text((W//2 - dw//2, date_y+8-bb[1]), today, font=fonts["date"], fill=C_LGRAY)

    # ── Carousel number badge (top-left) ─────────────────────────────────────
    num_label = f"PART {carousel_num} OF 5"
    num_font  = poppins("Bold", 22)
    draw.rounded_rectangle([(54, 28), (54+text_w(num_font, num_label)+32, 68)],
                            radius=14, fill=C_PANEL)
    nbb = num_font.getbbox(num_label)
    draw.text((70, 38-nbb[1]), num_label, font=num_font, fill=accent)

    # ── Headline ──────────────────────────────────────────────────────────────
    if is_entry:
        hl1   = "TODAY'S"
        hl2   = "NEW GRAD PICKS"
        h1y   = 142
        draw_text_centered(draw, hl1, fonts["sub"], h1y, C_LGRAY)
        h1h   = text_h(fonts["sub"], hl1)

        h2y   = h1y + h1h + 10
        part1 = "NEW GRAD "
        part2 = "PICKS"
        p1w   = text_w(fonts["hero"], part1)
        p2w   = text_w(fonts["hero"], part2)
        hx    = (W - p1w - p2w) // 2
        bb1   = fonts["hero"].getbbox(part1)
        draw.text((hx, h2y-bb1[1]), part1, font=fonts["hero"], fill=C_TEAL)
        bb2   = fonts["hero"].getbbox(part2)
        draw.text((hx+p1w, h2y-bb2[1]), part2, font=fonts["hero"], fill=C_WHITE)
        h2h   = text_h(fonts["hero"], part2)

        sub_y = h2y + h2h + 18
        draw_text_centered(draw, "Entry Level · OPT Friendly · H-1B Sponsor", fonts["body"], sub_y, C_GRAY)
    else:
        hl1 = "SENIOR ROLES"
        hl2 = "PRO PICKS"
        h1y = 142
        draw_text_centered(draw, hl1, fonts["sub"], h1y, C_LGRAY)
        h1h = text_h(fonts["sub"], hl1)

        h2y = h1y + h1h + 10
        part1 = "PRO "
        part2 = "PICKS"
        p1w = text_w(fonts["hero"], part1)
        p2w = text_w(fonts["hero"], part2)
        hx  = (W - p1w - p2w) // 2
        bb1 = fonts["hero"].getbbox(part1)
        draw.text((hx, h2y-bb1[1]), part1, font=fonts["hero"], fill=C_ORANGE)
        bb2 = fonts["hero"].getbbox(part2)
        draw.text((hx+p1w, h2y-bb2[1]), part2, font=fonts["hero"], fill=C_WHITE)
        h2h = text_h(fonts["hero"], hl2)

        sub_y = h2y + h2h + 18
        draw_text_centered(draw, "5 Jobs · All H-1B Verified · Swipe", fonts["body"], sub_y, C_GRAY)
    sub_h = text_h(fonts["body"], "x")

    # ── Job list ──────────────────────────────────────────────────────────────
    list_top = sub_y + sub_h + 48
    slot_h   = 82
    slot_gap = 14

    for i, job in enumerate(jobs[:5]):
        acc = ACCENTS[i]
        sy  = list_top + i*(slot_h + slot_gap)
        ex  = W - 72

        draw.rounded_rectangle([(72, sy), (ex, sy+slot_h)], radius=16, fill=C_CARD)
        draw.rectangle([(72, sy+10), (78, sy+slot_h-10)], fill=acc)

        num_font2 = poppins("Bold", 22)
        nstr = str(i+1)
        draw.ellipse([(90, sy+22), (122, sy+54)], fill=acc)
        nbb = num_font2.getbbox(nstr)
        draw.text((106-(nbb[2]-nbb[0])//2, sy+30-nbb[1]), nstr, font=num_font2, fill=C_BG)

        comp = job.get("company","")[:22]
        draw.text((138, sy+14-fonts["company"].getbbox(comp)[1]),
                  comp, font=fonts["company"], fill=C_WHITE)

        title = job.get("title","")[:38]
        tbb = fonts["small"].getbbox(title)
        draw.text((138, sy+50-tbb[1]), title, font=fonts["small"], fill=C_GRAY)

        sal = job.get("salary","Competitive")
        sbb = fonts["body"].getbbox(sal)
        sw  = sbb[2]-sbb[0]
        draw.text((ex-20-sw, sy+22-sbb[1]), sal, font=fonts["body"], fill=C_GOLD)

    # ── CTA ───────────────────────────────────────────────────────────────────
    cta_y = list_top + 5*(slot_h+slot_gap) + 24
    draw_text_centered(draw, "Link in bio to apply  ↗", fonts["body"], cta_y, accent)

    brand_stamp(draw, fonts, accent)

    out = os.path.join(OUTPUT_DIR, f"carousel_{carousel_num:02d}_00_cover.png")
    img.save(out, "PNG")
    print(f"  ✓ Cover  [carousel {carousel_num}]")
    return out


# ─────────────────────────────────────────────────────────────────────────────
#  INDIVIDUAL JOB CARD
# ─────────────────────────────────────────────────────────────────────────────
def make_job_card(job: dict, index: int, carousel_num: int = 1) -> str:
    acc  = ACCENTS[index % len(ACCENTS)]
    acc2 = tuple(min(255, c+40) for c in acc)

    img  = Image.new("RGB", (W,H), C_BG)
    draw = ImageDraw.Draw(img, "RGBA")

    fonts = {
        "num":     poppins("Bold",   22),
        "company": poppins("Bold",   72),
        "title":   poppins("Medium", 40),
        "salary":  poppins("Bold",  108),
        "label":   poppins("Light",  26),
        "detail":  poppins("Medium", 32),
        "badge":   poppins("Bold",   26),
        "cta":     poppins("Bold",   34),
        "small":   poppins("Regular",24),
        "brand":   poppins("Bold",   28),
    }

    draw_bg(draw, acc)

    # ── Job number pill ───────────────────────────────────────────────────────
    num_label = f"JOB {index+1} OF 5"
    draw.rounded_rectangle([(54, 28), (54+text_w(fonts["num"],num_label)+32, 72)],
                            radius=14, fill=C_PANEL)
    nbb = fonts["num"].getbbox(num_label)
    draw.text((70, 38-nbb[1]), num_label, font=fonts["num"], fill=acc)

    # ── Company name ──────────────────────────────────────────────────────────
    company = job.get("company","")
    cfont   = fonts["company"]
    while text_w(cfont, company) > W-120 and cfont.size > 36:
        cfont = poppins("Bold", cfont.size - 6)

    cy = 108
    cbb = cfont.getbbox(company)
    draw.text((60, cy-cbb[1]), company, font=cfont, fill=C_WHITE)
    cy += cbb[3]-cbb[1]

    draw.rectangle([(60, cy+8), (60+text_w(cfont,company), cy+12)], fill=acc)
    cy += 28

    # ── Job title ─────────────────────────────────────────────────────────────
    title = job.get("title","")
    tbb   = fonts["title"].getbbox(title)
    draw.text((60, cy-tbb[1]), title, font=fonts["title"], fill=C_LGRAY)
    cy += tbb[3]-tbb[1] + 48

    # ── Divider ───────────────────────────────────────────────────────────────
    draw.line([(60,cy),(W-60,cy)], fill=C_BORDER, width=1)
    cy += 36

    # ── Salary ────────────────────────────────────────────────────────────────
    sal_label = "ANNUAL SALARY"
    slbb = fonts["label"].getbbox(sal_label)
    draw.text((60, cy-slbb[1]), sal_label, font=fonts["label"], fill=C_GRAY)
    cy += slbb[3]-slbb[1]+8

    salary = job.get("salary","Competitive")
    sfont  = fonts["salary"]
    while text_w(sfont, salary) > W-120 and sfont.size > 56:
        sfont = poppins("Bold", sfont.size - 8)
    sbb = sfont.getbbox(salary)

    for off in range(5, 0, -1):
        draw.text((60+off, cy+off-sbb[1]), salary, font=sfont, fill=(*C_GOLD, 20))
    draw.text((60, cy-sbb[1]), salary, font=sfont, fill=C_GOLD)
    cy += sbb[3]-sbb[1] + 44

    # ── Info row ──────────────────────────────────────────────────────────────
    draw.rounded_rectangle([(60, cy), (W-60, cy+90)], radius=18, fill=C_PANEL)

    loc = job.get("location","USA")
    loc_label = "LOCATION"
    lbb_l = fonts["label"].getbbox(loc_label)
    draw.text((90, cy+14-lbb_l[1]), loc_label, font=fonts["label"], fill=C_GRAY)
    lbb = fonts["detail"].getbbox(loc)
    draw.text((90, cy+42-lbb[1]), loc, font=fonts["detail"], fill=C_WHITE)

    jtype     = job.get("type","Full-time")
    typ_label = "JOB TYPE"
    mid_x     = W//2 + 40
    tl_bb     = fonts["label"].getbbox(typ_label)
    draw.text((mid_x, cy+14-tl_bb[1]), typ_label, font=fonts["label"], fill=C_GRAY)
    td_bb = fonts["detail"].getbbox(jtype)
    draw.text((mid_x, cy+42-td_bb[1]), jtype, font=fonts["detail"], fill=C_WHITE)
    draw.line([(W//2+10, cy+14),(W//2+10, cy+76)], fill=C_BORDER, width=1)
    cy += 110

    # ── Badges ────────────────────────────────────────────────────────────────
    bx = 60
    bx, _ = draw_pill(draw, bx, cy, "✓  H-1B Sponsorship", fonts["badge"],
                      bg=(*C_GREEN2, 255), fg=C_WHITE, px=22, py=12, r=22)
    bx += 14
    if job.get("level") == "entry":
        bx, _ = draw_pill(draw, bx, cy, "New Grad Friendly", fonts["badge"],
                          bg=(*C_TEAL2, 255), fg=C_WHITE, px=22, py=12, r=22)
        bx += 14
    cat = _category(job.get("title",""))
    draw_pill(draw, bx, cy, cat, fonts["badge"],
              bg=C_PANEL, fg=C_LGRAY, px=22, py=12, r=22)
    cy += 66

    # ── CTA strip ─────────────────────────────────────────────────────────────
    cta_top = H - 175
    draw.rounded_rectangle([(60, cta_top), (W-60, cta_top+80)], radius=22, fill=acc)
    cta  = "APPLY NOW  |  Link in Bio"
    cbb2 = fonts["cta"].getbbox(cta)
    cw   = cbb2[2]-cbb2[0]
    draw.text(((W-cw)//2, cta_top+20-cbb2[1]), cta, font=fonts["cta"], fill=C_WHITE)

    brand_stamp(draw, fonts, acc)

    safe = job.get("company","job")[:14].replace(" ","_")
    out  = os.path.join(OUTPUT_DIR, f"carousel_{carousel_num:02d}_{index+1:02d}_{safe}.png")
    img.save(out, "PNG")
    print(f"  ✓ Job {index+1}/5 — {job.get('company','')}  [carousel {carousel_num}]")
    return out


def _category(title):
    t = title.lower()
    if any(k in t for k in ["software","developer","sde","swe","backend","frontend","full stack"]):
        return "💻 Engineering"
    elif any(k in t for k in ["data","ml","machine learning","ai","analytics","scientist","computational"]):
        return "📊 Data / AI"
    elif any(k in t for k in ["cloud","devops","platform","infra","sre","kubernetes"]):
        return "☁️ Cloud / DevOps"
    elif any(k in t for k in ["product","pm","program manager"]):
        return "🎯 Product"
    elif any(k in t for k in ["security","cyber","infosec"]):
        return "🔒 Security"
    elif any(k in t for k in ["finance","accounting","quant"]):
        return "💼 Finance"
    elif any(k in t for k in ["embedded","systems","controls"]):
        return "⚙️ Systems"
    elif any(k in t for k in ["architect","architecture"]):
        return "🏗️ Architecture"
    return "🏢 Professional"


# ─────────────────────────────────────────────────────────────────────────────
#  SINGLE CAROUSEL  (1 cover + 5 job cards)
# ─────────────────────────────────────────────────────────────────────────────
def generate_daily_carousel(jobs: list[dict], carousel_num: int = 1) -> list[str]:
    """
    Generate cover + 5 job cards for one carousel.
    Pre-cleans any stale images for this carousel slot before generating.
    Returns list of 6 file paths in posting order.
    """
    jobs  = jobs[:5]
    paths = []

    # Pre-clean stale images from a previous run for this carousel slot
    import glob
    stale = glob.glob(os.path.join(OUTPUT_DIR, f"carousel_{carousel_num:02d}_*.png"))
    for f in stale:
        try:
            os.remove(f)
        except OSError:
            pass
    if stale:
        print(f"  Cleaned {len(stale)} stale image(s) for carousel {carousel_num}")

    print(f"\n  Generating carousel {carousel_num}/5 — {datetime.now().strftime('%b %d, %Y')}...")
    paths.append(make_cover(jobs, carousel_num))
    for i, job in enumerate(jobs):
        paths.append(make_job_card(job, i, carousel_num))
    return paths


# ─────────────────────────────────────────────────────────────────────────────
#  ALL 5 CAROUSELS  (25 jobs → 5 groups of 5)
# ─────────────────────────────────────────────────────────────────────────────
def generate_all_carousels(jobs: list[dict]) -> list[list[str]]:
    """
    Split 25 jobs into 5 groups and generate all carousels.
    Returns list of 5 path-lists, each with 6 images.
    """
    all_paths = []
    for i in range(5):
        group = jobs[i*5 : i*5 + 5]
        paths = generate_daily_carousel(group, carousel_num=i+1)
        all_paths.append(paths)
    total = sum(len(p) for p in all_paths)
    print(f"\n  ✓ All carousels complete — {total} cards total")
    return all_paths


if __name__ == "__main__":
    from fetcher import get_daily_jobs
    jobs      = get_daily_jobs(25)
    all_paths = generate_all_carousels(jobs)
    print("\n  Output files:")
    for i, paths in enumerate(all_paths, 1):
        print(f"    [Carousel {i}]")
        for p in paths:
            print(f"      {os.path.basename(p)}")
