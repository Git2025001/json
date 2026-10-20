import sys, json, io, secrets, base64, shutil, re, os, glob, fitz
sys.path.insert(0, "/tmp/w")
from lock import *
from PIL import Image

F = "/tmp/lf/liberation-fonts-ttf-2.1.5/"
FONTS = {"LiberationSans": F + "LiberationSans-Regular.ttf", "LiberationSans-Bold": F + "LiberationSans-Bold.ttf", "LiberationSans-Italic": F + "LiberationSans-Italic.ttf"}
FO = {k: fitz.Font(fontfile=v) for k, v in FONTS.items()}
ORANGE = (0xfd / 255, 0x63 / 255, 0x28 / 255)
BLACK = (0, 0, 0)
SZ = 11

# single-line replacements, keyed on the start of the existing line
R = {
    "Tour Leader password on": [("Tour Leader password at https://yourtour.info/?tour=6493.", "LiberationSans-Italic", BLACK)],
    "included in the group fare. $50.00 per": [("included in the group fare. $50.00 each", "LiberationSans", BLACK)],
    "flight direction ($100.00 round trip)": [("way at the airport, $45.00 if prepaid", "LiberationSans", BLACK)],
    "payable to the": [("online at aa.com; paid to the airline.", "LiberationSans", BLACK)],
    "booking record). Checked-bag fees are pa": [("booking record). Checked-bag fees are paid directly to American Airlines, online or at check-in.", "LiberationSans", BLACK)],
    "ONE JAMMING STREET PARTY": [("ONE JAMMIN STREET PARTY", "LiberationSans-Bold", ORANGE), ("     Duration: 8:00 pm to 12:00 am | Canaan/Bon Accord", "LiberationSans-Bold", BLACK)],
    "Organized by the Crown Point Art": [("Free. Organized by the Crown Point Art and Street Festival Committee, this gathering", "LiberationSans", BLACK)],
    "An energetic seaside event": [("An energetic beach party on the day of J'ouvert. Tickets start at TT$200 (Trinidad and Tobago", "LiberationSans", BLACK)],
    "from $30 to $45 USD per guest": [("dollars, about US$30 per guest) and are sold online at", "LiberationSans", BLACK)],
    "islandetickets.com/event/sandjam2026": [("islandetickets.com/event/sandjam2026. Bring photo identification. Private taxi transportation", "LiberationSans", BLACK)],
    "through the resort": [("can be coordinated directly through the resort reception.", "LiberationSans", BLACK)],
    "of Spain at approximately 12:45": [("of Spain at approximately 12:30 pm.", "LiberationSans", BLACK)],
    "type of weather or occasion. Bring white clothing": [("type of weather or occasion. Bring clothing you do not mind getting paint or powder on for", "LiberationSans", BLACK)],
    "light rain jacket for the rainforest.": [("the carnival, and a light rain jacket for the rainforest.", "LiberationSans", BLACK)],
}

# generic Day 7 carnival block, replacing the unverified parade section
GEN_HEAD = [("CARNIVAL STREET CELEBRATIONS", "LiberationSans-Bold", ORANGE), ("     Duration: Throughout the day | Scarborough and Crown Point", "LiberationSans-Bold", BLACK)]
GEN_ITEMS = [  # (kind, label, text)
    ("time", "Morning: ", "J'ouvert, the traditional opening of carnival, fills the streets with music, paint and powder as revelers dance through town."),
    ("time", "Afternoon and evening: ", "Music trucks, steelbands and costumed bands bring color and rhythm to the streets, with celebrations continuing into the night."),
    ("bullet", "Viewing: ", "Your tour leader will share the day's confirmed times and the best places to watch the celebrations."),
    ("bullet", "Getting Around: ", "Roads close for the processions, so allow extra time and travel with your group."),
    ("bullet", "Staying Together: ", "Agree on a meeting point and time before the celebrations begin, and keep your phone charged."),
    ("bullet", "Attire Note: ", "Wear light clothing you do not mind getting covered in paint or powder; this is a high-energy street celebration."),
]


def put(p, x, y, t, fn, c):
    p.insert_text((x, y), t, fontsize=SZ, fontfile=FONTS[fn], fontname=fn.replace("-", ""), color=c)
    return x + FO[fn].text_length(t, SZ)


def wrap(label, text, x0, xi, lim):
    """first line starts at x0 after the bold label, later lines at xi"""
    words = text.split(" "); lines = []; cur = ""
    start = x0 + FO["LiberationSans-Bold"].text_length(label, SZ)
    for w in words:
        trial = (cur + " " + w).strip()
        x = start if not lines else xi
        if x + FO["LiberationSans"].text_length(trial, SZ) <= lim:
            cur = trial
        else:
            lines.append(cur); cur = w
    lines.append(cur)
    return lines


def parade(p):
    """replace the Steelpan and Powder Parade block with the generic block; returns True if done"""
    head = None; end = None
    lines = []
    for b in p.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            lines.append(l)
    lines.sort(key=lambda l: (l["bbox"][1], l["bbox"][0]))
    for l in lines:
        s = "".join(x["text"] for x in l["spans"])
        if s.startswith("STEELPAN AND POWDER PARADE"): head = l
        if s.startswith("ONE JAMMING STREET PARTY") or s.startswith("ONE JAMMIN STREET PARTY"): end = l
    if not head: return False
    y0 = head["bbox"][1]; y1 = end["bbox"][1]
    block = [l for l in lines if y0 - 0.5 <= l["bbox"][1] < y1 - 0.5]
    # baselines of the original block, in order, with the x of each line start
    base = sorted({round(l["spans"][0]["origin"][1], 1) for l in block if "".join(x["text"] for x in l["spans"]).strip() not in ("•",)})
    p.add_redact_annot(fitz.Rect(73, y0 + 0.5, 539, block[-1]["bbox"][3] - 0.5), fill=None)
    p.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=0, text=0)
    yb = base[0]
    x = 77.1
    for t, fn, c in GEN_HEAD:
        x = put(p, x, yb, t, fn, c)
    assert x <= 539, x
    # lay the items out on the original rhythm: 18.2 before each item, 13.2 within
    y = yb; prev = "time"
    for kind, label, text in GEN_ITEMS:
        y += 18.2 if (kind == "time" or prev == "time") else 16.2
        prev = kind
        if kind == "time":
            x0 = 77.1; xi = 77.1
        else:
            x0 = 99.1; xi = 99.1
            put(p, 86.1, y, "•", "LiberationSans", BLACK)
        ls = wrap(label, text, x0, xi, 535)
        assert len(ls) <= 2, (label, ls)
        x = put(p, x0, y, label, "LiberationSans-Bold", BLACK)
        put(p, x, y, ls[0], "LiberationSans", BLACK)
        for extra in ls[1:]:
            y += 13.2
            put(p, xi, y, extra, "LiberationSans", BLACK)
    assert y <= y1 - 6, (y, y1)
    return True


def edit(src, out):
    d = fitz.open(src); changed = []
    for i, p in enumerate(d):
        did = parade(p)
        todo = []
        for b in p.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                s = "".join(x["text"] for x in l["spans"]).replace("\xa0", " ")
                for k, v in R.items():
                    if s.startswith(k): todo.append((l, v))
        if not todo and not did: continue
        for l, v in todo:
            r = fitz.Rect(l["bbox"])
            p.add_redact_annot(fitz.Rect(r.x0 - 0.5, r.y0 + 0.5, (540 if r.x0 < 300 else 525) + 0.5, r.y1 - 0.5), fill=None)
        p.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=0, text=0)
        for l, v in todo:
            x = l["bbox"][0]; y = l["spans"][0]["origin"][1]; lim = 540 if x < 300 else 526
            for t, fn, c in v:
                w = FO[fn].text_length(t, SZ); assert x + w <= lim, (t, x + w)
                x = put(p, x, y, t, fn, c)
        changed.append(i)
    d.save(out, garbage=3, deflate=True); return changed


T = "public/tours/6493/traveler/"; L = "public/tours/6493/leader/"
def rnd(): return secrets.token_hex(5)
def render(page, width):
    z = width / page.rect.width; pm = page.get_pixmap(matrix=fitz.Matrix(z, z), alpha=False)
    im = Image.frombytes("RGB", (pm.width, pm.height), pm.samples); b = io.BytesIO(); im.save(b, "JPEG", quality=86, optimize=True, progressive=True); return b.getvalue()
def words(page):
    W, H = page.rect.width, page.rect.height
    return [[round(w[0] / W, 4), round(w[1] / H, 4), round(w[2] / W, 4), round(w[3] / H, 4), w[4]] for w in page.get_text("words")]


if __name__ == "__main__":
    TJ, LBK = sys.argv[1], sys.argv[2]   # current traveler json name, leader book name
    out = {}
    ct = edit("/tmp/w/tb_src.pdf", "/tmp/w/tb8.pdf"); cti = edit("/tmp/w/ti_src.pdf", "/tmp/w/ti8.pdf")
    ch = edit("/tmp/w/hb.pdf", "/tmp/w/hb8.pdf"); ci = edit("/tmp/w/it.pdf", "/tmp/w/it8.pdf")
    print("changed tb", ct, "ti", cti, "hb", ch, "it", ci)
    # traveler flip book: page n = pdf index n
    j = json.load(open(T + TJ)); d = fitz.open("/tmp/w/tb8.pdf")
    for i in ct:
        n = i; pg = d[i]
        assert [w[4] for w in j["book"]["pages"][n - 1]["w"][:3]] == [w[4] for w in words(pg)[:3]], n
        sn = f"{rnd()}_cv6493_tb_p{n:02d}.jpg"; hn = f"{rnd()}_cv6493_tb_p{n:02d}_hi.jpg"
        open(T + sn, "wb").write(render(pg, 1240)); open(T + hn, "wb").write(render(pg, 1860))
        j["img"][str(n)] = {"s": "/tours/6493/traveler/" + sn, "h": "/tours/6493/traveler/" + hn}; j["book"]["pages"][n - 1]["w"] = words(pg)
    out["tjson"] = f"{rnd()}_cv6493_tb_book.json"; json.dump(j, open(T + out["tjson"], "w"), separators=(",", ":"))
    # leader flip book: page n = pdf index + 1
    lb = json.loads(dec_page(L + "book/" + LBK)); d = fitz.open("/tmp/w/hb8.pdf")
    for i in ch:
        n = i + 1; pg = d[i]
        assert [w[4] for w in lb["book"]["pages"][n - 1]["w"][:3]] == [w[4] for w in words(pg)[:3]], n
        sn = f"{rnd()}_cv6493_tl_p{n:02d}.bin"; hn = f"{rnd()}_cv6493_tl_p{n:02d}_hi.bin"
        open(L + "book/" + sn, "wb").write(enc_page(render(pg, 1240))); open(L + "book/" + hn, "wb").write(enc_page(render(pg, 1860)))
        lb["img"][str(n)] = {"s": "/tours/6493/leader/book/" + sn, "h": "/tours/6493/leader/book/" + hn}; lb["book"]["pages"][n - 1]["w"] = words(pg)
    out["lbook"] = f"{rnd()}_cv6493_tl_book.bin"; open(L + "book/" + out["lbook"], "wb").write(enc_page(json.dumps(lb, separators=(",", ":")).encode()))
    docs = {}
    for k, src in (("Tour Leader Handbook", "/tmp/w/hb8.pdf"), ("Tour Leader Itinerary", "/tmp/w/it8.pdf"), ("Tour Leader Welcome Kit", "/tmp/w/wk4.pdf")):
        iv, c = enc_doc(open(src, "rb").read()); tag = {"Tour Leader Handbook": "hb", "Tour Leader Itinerary": "it", "Tour Leader Welcome Kit": "wk"}[k]
        fn = f"{rnd()}_cv_tl_{tag}.bin"; open(L + fn, "wb").write(c); docs[k] = ("/tours/6493/leader/" + fn, base64.b64encode(iv).decode())
    shutil.copy("/tmp/w/tb8.pdf", T + "6493_Travelers_Booklet.pdf"); shutil.copy("/tmp/w/ti8.pdf", T + "6493_Traveler_Itinerary.pdf")
    # leaderDocuments.js: change only the 6493 section
    p = "src/data/leaderDocuments.js"; src = open(p).read()
    a = src.index('"6493": {'); b = src.index('"6491": {'); mid = src[a:b]
    for title, (u, iv) in docs.items():
        mid, nsub = re.subn(r'(\{ title: "%s",[^\n]*?url: ")[^"]+(", iv: ")[^"]+(")' % re.escape(title), lambda m: m.group(1) + u + m.group(2) + iv + m.group(3), mid, count=1)
        assert nsub == 1, title
    hb = fitz.open("/tmp/w/hb8.pdf")
    for k in range(1, 9):
        n = fitz.open(); n.insert_pdf(hb, from_page=13 + k, to_page=13 + k); n.insert_pdf(hb, from_page=4, to_page=4)
        assert ("Day %d |" % k) in n[0].get_text()
        iv, c = enc_doc(n.tobytes(garbage=3, deflate=True)); fn = "%s_cv_tl_day%02d.bin" % (rnd(), k); open(L + "days/" + fn, "wb").write(c)
        mid, nsub = re.subn(r'(\{ day: %d, [^\n]*?url: ")[^"]+(", iv: ")[^"]+(")' % k, lambda m: m.group(1) + "/tours/6493/leader/days/" + fn + m.group(2) + base64.b64encode(iv).decode() + m.group(3), mid, count=1)
        assert nsub == 1, k
    open(p, "w").write(src[:a] + mid + src[b:])
    # verify
    src = open(p).read(); mid = src[src.index('"6493": {'):src.index('"6491": {')]
    for m in re.finditer(r'(?:title: "([^"]+)"|day: (\d))[^\n]*?url: "([^"]+)", iv: "([^"]+)"', mid):
        t = " ".join(pg.get_text() for pg in fitz.open(stream=dec_doc("public" + m.group(3), m.group(4)), filetype="pdf"))
        print(m.group(1) or "day " + m.group(2), "| powder-parade:", "Powder Parade" in t, "| generic:", "CARNIVAL STREET CELEBRATIONS" in t, "| TT$200:", "TT$200" in t, "| rice:", "hill rice, served" in t)
    for fn in ["6493_Travelers_Booklet.pdf", "6493_Traveler_Itinerary.pdf"]:
        t = " ".join(pg.get_text() for pg in fitz.open(T + fn)); print(fn, "Powder Parade" in t, "CARNIVAL STREET CELEBRATIONS" in t, "TT$200" in t, "12:30 pm" in t, "Canaan" in t)
    json.dump(out, open("/tmp/w/out8.json", "w")); print(out)
