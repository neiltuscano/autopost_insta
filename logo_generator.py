"""
f1jobs — Logo Generator
Creates the brand logo in multiple formats:
  - Icon (500x500) for Instagram profile pic
  - Horizontal (1200x400) for headers/watermarks
  - Dark splash (1080x1080) for brand reveal post
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math

from config import FONT_DIR, OUTPUT_DIR
FONT_DIR   = str(FONT_DIR)
OUTPUT_DIR = str(OUTPUT_DIR)

# ── Brand palette ──────────────────────────────────────────────────────────────
C_BG        = (8,   11,  22)
C_DARK      = (12,  15,  28)
C_CARD      = (16,  20,  38)
C_PANEL     = (22,  28,  50)
C_ORANGE    = (255, 95,  0)
C_ORANGE2   = (255, 140, 30)   # lighter orange for gradient feel
C_WHITE     = (255, 255, 255)
C_GRAY      = (130, 145, 175)
C_DIVIDER   = (30,  38,  65)

def poppins(style, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, f"Poppins-{style}.ttf"), size)


def draw_speed_lines(draw, cx, cy, color, alpha=40, count=5, spread=120, thickness=3):
    """Draw horizontal speed/motion lines trailing from a center point."""
    for i in range(count):
        offset = (i - count // 2) * (spread // count)
        length = 80 + (count - i) * 20
        y = cy + offset
        draw.line([(cx - length, y), (cx - 10, y)], fill=(*color, alpha - i * 6), width=thickness - 1)


def draw_diagonal_stripe(draw, x0, y0, x1, y1, w, h, color, alpha=18):
    """Draw a bold diagonal stripe across the canvas."""
    draw.polygon([(x0, y0), (x1, y0 - 40), (x1, y1 - 40), (x0, y1)],
                 fill=(*color, alpha))


def make_icon(size=500) -> str:
    """
    Square icon — clean app-icon style for Instagram profile.
    Dark bg, orange racing diagonal, bold f1 in orange, jobs in white.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")

    # ── Rounded square background ──────────────────────────────────────────────
    radius = size // 8
    draw.rounded_rectangle([(0, 0), (size, size)], radius=radius, fill=(*C_BG, 255))

    # ── Diagonal orange accent stripe (top-right corner) ──────────────────────
    # Bold stripe going from top-center to right-center
    stripe_pts = [
        (size * 0.42, 0),
        (size, 0),
        (size, size * 0.08),
        (size * 0.52, 0),
    ]
    draw.polygon(stripe_pts, fill=(*C_ORANGE, 255))

    # Subtle second stripe
    stripe2_pts = [
        (size * 0.55, 0),
        (size, 0),
        (size, size * 0.02),
    ]
    draw.polygon(stripe2_pts, fill=(*C_ORANGE2, 120))

    # ── Bottom accent bar ─────────────────────────────────────────────────────
    bar_h = max(6, size // 60)
    draw.rounded_rectangle([(0, size - bar_h), (size, size)],
                           radius=radius, fill=(*C_ORANGE, 255))

    # ── "f1" — large, bold, orange ────────────────────────────────────────────
    f1_size = int(size * 0.50)
    jobs_size = int(size * 0.195)

    f1_font   = poppins("Bold", f1_size)
    jobs_font = poppins("Medium", jobs_size)

    f1_text   = "f1"
    jobs_text = "jobs"

    # Measure
    f1_bbox   = f1_font.getbbox(f1_text)
    jobs_bbox = jobs_font.getbbox(jobs_text)

    f1_w   = f1_bbox[2] - f1_bbox[0]
    f1_h   = f1_bbox[3] - f1_bbox[1]
    jobs_w = jobs_bbox[2] - jobs_bbox[0]
    jobs_h = jobs_bbox[3] - jobs_bbox[1]

    # Vertical centering — treat f1 + jobs as a unit
    total_h = f1_h + jobs_h - int(size * 0.02)
    start_y = (size - total_h) // 2 - int(size * 0.04)

    # Center horizontally based on wider element
    max_w   = max(f1_w, jobs_w)
    f1_x    = (size - max_w) // 2 + (max_w - f1_w) // 2
    jobs_x  = (size - max_w) // 2 + (max_w - jobs_w) // 2

    # Draw subtle shadow/glow behind f1
    for offset in range(4, 0, -1):
        alpha = 30 + offset * 15
        draw.text((f1_x + offset, start_y + offset - f1_bbox[1]),
                  f1_text, font=f1_font, fill=(*C_ORANGE, alpha))

    # f1 in orange
    draw.text((f1_x, start_y - f1_bbox[1]),
              f1_text, font=f1_font, fill=C_ORANGE)

    # jobs in white, tight under f1
    jobs_y = start_y + f1_h - int(size * 0.05)
    draw.text((jobs_x, jobs_y - jobs_bbox[1]),
              jobs_text, font=jobs_font, fill=C_WHITE)

    # ── Thin orange border ring ────────────────────────────────────────────────
    border_w = max(2, size // 120)
    draw.rounded_rectangle([(border_w, border_w),
                             (size - border_w, size - border_w)],
                           radius=radius, outline=(*C_ORANGE, 90), width=border_w)

    # Save as RGBA PNG (transparent corners for circle crop on Instagram)
    out = os.path.join(OUTPUT_DIR, "f1jobs_icon.png")
    img.save(out, "PNG")
    print(f"  ✓ Icon saved: f1jobs_icon.png  ({size}x{size})")
    return out


def make_horizontal_logo(w=1200, h=400) -> str:
    """
    Wide horizontal logo — for card watermarks, headers, banners.
    """
    img = Image.new("RGB", (w, h), C_BG)
    draw = ImageDraw.Draw(img, "RGBA")

    # ── Speed stripe background ────────────────────────────────────────────────
    draw.polygon([(0, 0), (w * 0.6, 0), (w * 0.45, h), (0, h)],
                 fill=(*C_CARD, 255))

    # Top and bottom orange lines
    draw.rectangle([(0, 0), (w, 6)], fill=C_ORANGE)
    draw.rectangle([(0, h - 6), (w, h)], fill=C_ORANGE)

    # Diagonal accent stripes
    draw.polygon([(w * 0.55, 0), (w * 0.62, 0), (w * 0.47, h), (w * 0.40, h)],
                 fill=(*C_ORANGE, 18))
    draw.polygon([(w * 0.65, 0), (w * 0.70, 0), (w * 0.55, h), (w * 0.50, h)],
                 fill=(*C_ORANGE, 10))

    # ── Fonts ─────────────────────────────────────────────────────────────────
    f1_font      = poppins("Bold",    int(h * 0.68))
    jobs_font    = poppins("Bold",    int(h * 0.68))
    tagline_font = poppins("Light",   int(h * 0.14))
    dot_font     = poppins("Bold",    int(h * 0.68))

    # ── "f1" ──────────────────────────────────────────────────────────────────
    f1_bbox = f1_font.getbbox("f1")
    f1_w    = f1_bbox[2] - f1_bbox[0]

    # ── "jobs" ────────────────────────────────────────────────────────────────
    jobs_bbox = jobs_font.getbbox("jobs")
    jobs_w    = jobs_bbox[2] - jobs_bbox[0]

    total_text_w = f1_w + jobs_w
    start_x = (w - total_text_w) // 2 - int(h * 0.02)
    text_y  = (h - (f1_bbox[3] - f1_bbox[1])) // 2 - int(h * 0.06)

    # Shadow glow
    for offset in range(5, 0, -1):
        draw.text((start_x + offset, text_y + offset - f1_bbox[1]),
                  "f1", font=f1_font, fill=(*C_ORANGE, 25))

    # f1 in orange
    draw.text((start_x, text_y - f1_bbox[1]), "f1", font=f1_font, fill=C_ORANGE)

    # jobs in white
    draw.text((start_x + f1_w, text_y - jobs_bbox[1]), "jobs", font=jobs_font, fill=C_WHITE)

    # ── Tagline below ─────────────────────────────────────────────────────────
    tagline = "H-1B Jobs · Dallas Fort Worth"
    tag_bbox = tagline_font.getbbox(tagline)
    tag_w    = tag_bbox[2] - tag_bbox[0]
    tag_x    = (w - tag_w) // 2
    tag_y    = text_y + (f1_bbox[3] - f1_bbox[1]) + int(h * 0.01)

    # Small orange dots flanking tagline
    dot_w = int(h * 0.025)
    draw.ellipse([(tag_x - dot_w * 3, tag_y + dot_w),
                  (tag_x - dot_w, tag_y + dot_w * 3)], fill=C_ORANGE)
    draw.ellipse([(tag_x + tag_w + dot_w, tag_y + dot_w),
                  (tag_x + tag_w + dot_w * 3, tag_y + dot_w * 3)], fill=C_ORANGE)

    draw.text((tag_x, tag_y - tag_bbox[1]), tagline, font=tagline_font, fill=C_GRAY)

    out = os.path.join(OUTPUT_DIR, "f1jobs_logo_horizontal.png")
    img.save(out, "PNG")
    print(f"  ✓ Horizontal logo saved: f1jobs_logo_horizontal.png  ({w}x{h})")
    return out


def make_brand_splash() -> str:
    """
    1080x1080 brand splash card — for first Instagram post / pinned post.
    """
    W = H = 1080
    img = Image.new("RGB", (W, H), C_BG)
    draw = ImageDraw.Draw(img, "RGBA")

    # ── Background geometric shapes ───────────────────────────────────────────
    # Large diagonal orange shape top-right
    draw.polygon([(W * 0.55, 0), (W, 0), (W, H * 0.55)],
                 fill=(*C_ORANGE, 16))
    # Bottom-left subtle shape
    draw.polygon([(0, H * 0.75), (W * 0.35, H), (0, H)],
                 fill=(*C_ORANGE, 10))

    # Multiple thin diagonal lines
    for i in range(12):
        x_start = W * 0.3 + i * 60
        draw.line([(x_start, 0), (x_start + W * 0.45, H)],
                  fill=(*C_ORANGE, 6), width=1)

    # Orange bars top and bottom
    draw.rectangle([(0, 0),    (W, 10)], fill=C_ORANGE)
    draw.rectangle([(0, H-10), (W, H)], fill=C_ORANGE)

    # ── Center card ───────────────────────────────────────────────────────────
    draw.rounded_rectangle([(80, 220), (W-80, 780)],
                           radius=32, fill=(*C_CARD, 240),
                           outline=(*C_ORANGE, 50), width=1)

    # Left edge accent
    draw.rectangle([(80, 260), (88, 740)], fill=C_ORANGE)

    # ── Main f1jobs logotype ──────────────────────────────────────────────────
    f1_font   = poppins("Bold",   180)
    jobs_font = poppins("Bold",   180)
    tag_font  = poppins("Light",   38)
    sub_font  = poppins("Regular", 30)

    f1_bbox   = f1_font.getbbox("f1")
    jobs_bbox = jobs_font.getbbox("jobs")
    f1_w      = f1_bbox[2] - f1_bbox[0]
    jobs_w    = jobs_bbox[2] - jobs_bbox[0]

    total_w = f1_w + jobs_w
    sx = (W - total_w) // 2
    ty = 295

    # Shadow layers
    for off in range(6, 0, -1):
        draw.text((sx + off, ty + off - f1_bbox[1]),
                  "f1", font=f1_font, fill=(*C_ORANGE, 20))

    # f1 orange
    draw.text((sx, ty - f1_bbox[1]), "f1", font=f1_font, fill=C_ORANGE)
    # jobs white
    draw.text((sx + f1_w, ty - jobs_bbox[1]), "jobs", font=jobs_font, fill=C_WHITE)

    # ── Horizontal rule ───────────────────────────────────────────────────────
    div_y = ty + (f1_bbox[3] - f1_bbox[1]) + 30
    div_cx = W // 2
    draw.rectangle([(div_cx - 160, div_y), (div_cx - 10, div_y + 3)], fill=C_ORANGE)
    draw.rectangle([(div_cx + 10,  div_y), (div_cx + 160, div_y + 3)], fill=C_ORANGE)
    draw.ellipse([(div_cx - 6, div_y - 3), (div_cx + 6, div_y + 6)], fill=C_ORANGE)

    # ── Tagline ───────────────────────────────────────────────────────────────
    tagline = "H-1B Sponsorship Jobs · Dallas Fort Worth"
    tag_bbox = tag_font.getbbox(tagline)
    tag_w    = tag_bbox[2] - tag_bbox[0]
    draw.text(((W - tag_w) // 2, div_y + 22 - tag_bbox[1]),
              tagline, font=tag_font, fill=C_GRAY)

    # ── Three value props ─────────────────────────────────────────────────────
    props_y = div_y + 110
    props = [
        ("🎯", "H-1B Verified",  "Only sponsored jobs"),
        ("📍", "DFW Only",        "Plano · Irving · Dallas"),
        ("🔒", "No Spam",         "Curated daily drops"),
    ]

    col_w = (W - 200) // 3
    for i, (icon, title, sub) in enumerate(props):
        cx = 100 + i * col_w + col_w // 2

        icon_font = poppins("Regular", 44)
        title_font = poppins("Bold", 30)
        sub_font2 = poppins("Light", 24)

        # Icon
        i_bbox = icon_font.getbbox(icon)
        i_w = i_bbox[2] - i_bbox[0]
        draw.text((cx - i_w // 2, props_y - i_bbox[1]), icon, font=icon_font, fill=C_WHITE)

        # Title
        t_bbox = title_font.getbbox(title)
        t_w = t_bbox[2] - t_bbox[0]
        draw.text((cx - t_w // 2, props_y + 58 - t_bbox[1]), title, font=title_font, fill=C_WHITE)

        # Subtitle
        s_bbox = sub_font2.getbbox(sub)
        s_w = s_bbox[2] - s_bbox[0]
        draw.text((cx - s_w // 2, props_y + 100 - s_bbox[1]), sub, font=sub_font2, fill=C_GRAY)

        # Vertical divider between props
        if i < 2:
            draw.line([(100 + (i+1) * col_w, props_y + 10),
                       (100 + (i+1) * col_w, props_y + 130)],
                      fill=C_DIVIDER, width=1)

    # ── CTA strip at bottom of card ───────────────────────────────────────────
    draw.rounded_rectangle([(80, 700), (W-80, 780)],
                           radius=0, fill=C_ORANGE)
    draw.rounded_rectangle([(80, 700), (W-80, 780)],
                           radius=32, fill=C_ORANGE)

    cta = "Follow for daily H-1B job drops  🚀"
    cta_font = poppins("Bold", 34)
    c_bbox = cta_font.getbbox(cta)
    c_w = c_bbox[2] - c_bbox[0]
    draw.text(((W - c_w) // 2, 722 - c_bbox[1]), cta, font=cta_font, fill=C_WHITE)

    # ── Instagram handle at bottom ────────────────────────────────────────────
    handle_font = poppins("Medium", 30)
    handle = "@f1jobs.dfw"
    h_bbox = handle_font.getbbox(handle)
    h_w = h_bbox[2] - h_bbox[0]
    draw.text(((W - h_w) // 2, 820 - h_bbox[1]), handle, font=handle_font, fill=C_GRAY)

    tags_font = poppins("Light", 22)
    tags = "#f1jobs  #H1Bjobs  #DFWJobs  #NRIjobs  #OPTjobs  #DesiTech"
    t_bbox = tags_font.getbbox(tags)
    t_w = t_bbox[2] - t_bbox[0]
    draw.text(((W - t_w) // 2, 870 - t_bbox[1]), tags, font=tags_font, fill=C_GRAY)

    out = os.path.join(OUTPUT_DIR, "f1jobs_brand_splash.png")
    img.save(out, "PNG")
    print(f"  ✓ Brand splash saved: f1jobs_brand_splash.png  (1080x1080)")
    return out


if __name__ == "__main__":
    print("\nGenerating f1jobs logos...\n")
    make_icon(500)
    make_horizontal_logo(1200, 400)
    make_brand_splash()
    print(f"\n✓ All logos saved to {OUTPUT_DIR}/")
