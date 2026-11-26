#!/usr/bin/env python3
"""FABP – Free All Bluetooth Printers (Linux version)

Print images on cheap Bluetooth thermal mini printers ("cat printers",
e.g. Mafiti X6 / Tiny Print) without the manufacturer's app.

  fabp.py                         start the window (GUI)
  fabp.py --scan                  list printers nearby
  fabp.py photo.jpg               print an image
  fabp.py banner.png --endless --length 200   print a 2 m banner

Needs: Python 3.9+, BlueZ, `pip install bleak pillow` (GUI also needs tkinter).
"""
import argparse
import asyncio
import base64
import io
import sys
import threading

try:
    from PIL import Image, ImageOps
    from bleak import BleakClient, BleakScanner
except ImportError as e:
    sys.exit(f"Missing package: {e.name}. Install with:  pip install bleak pillow")

COFFEE = "https://www.paypal.me/pedapedapeda"
PX_PER_CM = 80          # 203 dpi ≈ 8 px per mm
MAX_PX = 32000          # ≈ 400 cm
SERVICES = ["0000ae30-0000-1000-8000-00805f9b34fb", "0000af30-0000-1000-8000-00805f9b34fb"]
WRITE = "0000ae01-0000-1000-8000-00805f9b34fb"
NOTIFY = "0000ae02-0000-1000-8000-00805f9b34fb"
KNOWN_NAMES = ("X6", "X5", "X7", "X8", "GB0", "GT01", "MX0", "YT01", "GB01", "GB02", "GB03", "MX05", "MX06", "MX08", "MX10")

# ---------- protocol ----------
_T = []
for i in range(256):
    c = i
    for _ in range(8):
        c = ((c << 1) ^ 0x07) & 0xFF if c & 0x80 else (c << 1) & 0xFF
    _T.append(c)
_REV = bytes(int(f"{b:08b}"[::-1], 2) for b in range(256))


def crc8(data):
    c = 0
    for b in data:
        c = _T[(c ^ b) & 0xFF]
    return c


def pkt(cmd, data):
    data = bytes(data)
    return bytes([0x51, 0x78, cmd, 0, len(data) & 0xFF, len(data) >> 8]) + data + bytes([crc8(data), 0xFF])


def le16(v):
    return [v & 0xFF, (v >> 8) & 0xFF]


def head(speed, energy):
    return b"".join([pkt(0xA3, [0]), pkt(0xA4, [50]), pkt(0xBD, [speed]), pkt(0xAF, le16(energy)),
                     pkt(0xBE, [1]), pkt(0xA9, [0]),
                     pkt(0xA6, [0xAA, 0x55, 0x17, 0x38, 0x44, 0x5F, 0x5F, 0x5F, 0x44, 0x38, 0x2C])])


def foot():
    return b"".join([pkt(0xA6, [0xAA, 0x55, 0x17, 0, 0, 0, 0, 0, 0, 0, 0x17]),
                     pkt(0xBD, [8]), pkt(0xA1, le16(90)), pkt(0xA3, [0])])


# ---------- image ----------
def prepare(path_or_img, width=384, endless=False, length_cm=0, rotate=None,
            brightness=20, contrast=10, dither="fs", invert=False):
    """Return a 1-bit PIL image (width px wide) ready to print, and the rotation used."""
    im = path_or_img if isinstance(path_or_img, Image.Image) else Image.open(path_or_img)
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, "white")
        bg.alpha_composite(im)
        im = bg
    im = im.convert("L")
    if rotate is None:
        rotate = (90 if im.width > im.height else 0) if endless else (90 if im.width > im.height * 1.2 else 0)
    if rotate:
        im = im.rotate(-rotate, expand=True)  # clockwise
    iw, ih = im.size
    s = width / iw
    len_px = min(MAX_PX, max(0, length_cm) * PX_PER_CM)
    if endless and len_px:
        s = min(len_px / ih, width / iw)
    if ih * s > MAX_PX:
        s = MAX_PX / ih
    nw, nh = max(1, round(iw * s)), max(1, round(ih * s))
    im = im.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("L", (width, nh), 255)
    canvas.paste(im, ((width - nw) // 2, 0))
    b = brightness * 1.28
    k0 = contrast * 1.28
    k = (259 * (k0 + 255)) / (255 * (259 - k0))
    lut = []
    for v in range(256):
        l = (v - 128) * k + 128 + b
        if invert:
            l = 255 - l
        lut.append(max(0, min(255, round(l))))
    g = canvas.point(lut)
    if dither == "th":
        out = g.point(lambda v: 255 if v >= 128 else 0).convert("1", dither=Image.Dither.NONE)
    elif dither == "at":
        out = _atkinson(g)
    else:
        out = g.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    return out, rotate


def _atkinson(g):
    w, h = g.size
    px = [float(v) for v in g.getdata()]
    for y in range(h):
        row = y * w
        for x in range(w):
            i = row + x
            o = px[i]
            n = 0.0 if o < 128 else 255.0
            px[i] = n
            e = (o - n) / 8
            if e:
                if x + 1 < w: px[i + 1] += e
                if x + 2 < w: px[i + 2] += e
                if y + 1 < h:
                    j = i + w
                    if x > 0: px[j - 1] += e
                    px[j] += e
                    if x + 1 < w: px[j + 1] += e
                if y + 2 < h: px[i + 2 * w] += e
    out = Image.new("L", (w, h))
    out.putdata([int(v) for v in px])
    return out.convert("1", dither=Image.Dither.NONE)


def lines(img1):
    """Printer lines: 1 = black, leftmost pixel = lowest bit."""
    w, h = img1.size
    raw = img1.tobytes()  # MSB first, 1 = white
    bpl = w // 8
    for y in range(h):
        row = raw[y * bpl:(y + 1) * bpl]
        yield pkt(0xA2, bytes(_REV[b ^ 0xFF] for b in row))


# ---------- bluetooth ----------
async def scan(timeout=6.0):
    found = await BleakScanner.discover(timeout=timeout, return_adv=True)
    res = []
    for d, adv in found.values():
        uuids = [u.lower() for u in (adv.service_uuids or [])]
        name = d.name or adv.local_name or ""
        likely = any(u in uuids for u in SERVICES) or name.upper().startswith(KNOWN_NAMES)
        res.append((likely, name, d.address, adv.rssi))
    res.sort(key=lambda r: (not r[0], -(r[3] or -999)))
    return res


async def print_image(img1, address, copies=1, darkness=25, speed=32, endless=False,
                      chunk=120, delay_ms=8, progress=None, cancel=None, log=print):
    energy = round(darkness / 100 * 0xFFFF)
    paused = asyncio.Event()

    def on_note(_, data):
        if len(data) > 6 and data[2] == 0xAE:
            (paused.set if data[6] == 0x10 else paused.clear)()
        elif len(data) > 6 and data[2] == 0xA3 and data[6]:
            log(f"Printer status: {data[6]}" + (" (no paper?)" if data[6] & 1 else "")
                + (" (lid open?)" if data[6] & 2 else "") + (" (overheat?)" if data[6] & 4 else ""))

    async with BleakClient(address, timeout=20) as c:
        log(f"Connected: {address}")
        try:
            await c.start_notify(NOTIFY, on_note)
        except Exception:
            log("No notifications (flow control off)")
        size = max(20, min(chunk, (getattr(c, "mtu_size", 23) or 23) - 3))

        async def send(data):
            for o in range(0, len(data), size):
                while paused.is_set():
                    await asyncio.sleep(0.03)
                await c.write_gatt_char(WRITE, data[o:o + size], response=False)
                if delay_ms:
                    await asyncio.sleep(delay_ms / 1000)

        h = img1.size[1]
        total = h * copies
        done = 0
        is_open = False
        for n in range(copies):
            if cancel and cancel.is_set():
                break
            if not is_open:
                await send(head(speed, energy))
                is_open = True
            batch = []
            for ln in lines(img1):
                if cancel and cancel.is_set():
                    break
                batch.append(ln)
                if len(batch) == 32:
                    await send(b"".join(batch))
                    done += len(batch)
                    batch = []
                    if progress:
                        progress(done / total)
            if batch:
                await send(b"".join(batch))
                done += len(batch)
            if not endless or n == copies - 1:
                await send(foot())
                is_open = False
        if is_open:
            await send(foot())
        if progress:
            progress(1.0)
        log("Stopped" if cancel and cancel.is_set() else "Done")


# ---------- GUI ----------
def gui():
    try:
        import tkinter as tk
        from tkinter import filedialog, ttk
    except ImportError:
        sys.exit("tkinter missing. Install it, e.g.:  sudo apt install python3-tk  |  sudo dnf install python3-tkinter  |  sudo pacman -S tk")
    import webbrowser

    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    run = lambda coro: asyncio.run_coroutine_threadsafe(coro, loop)

    root = tk.Tk()
    root.title("FABP – Free All Bluetooth Printers")
    root.geometry("820x640")
    st = {"src": None, "rot": None, "img1": None, "devs": [], "cancel": None, "busy": False}

    left = ttk.Frame(root, padding=12)
    left.pack(side="left", fill="y")
    right = ttk.Frame(root, padding=12)
    right.pack(side="left", fill="both", expand=True)

    ttk.Label(left, text="FABP", font=("Sans", 22, "bold")).pack(anchor="w")
    ttk.Label(left, text="Free All Bluetooth Printers").pack(anchor="w", pady=(0, 10))

    # printer
    ttk.Label(left, text="1. Printer", font=("Sans", 11, "bold")).pack(anchor="w")
    dev_var = tk.StringVar()
    dev_box = ttk.Combobox(left, textvariable=dev_var, width=34, state="readonly")
    dev_box.pack(anchor="w", pady=2)
    scan_btn = ttk.Button(left, text="Scan for printers")
    scan_btn.pack(anchor="w", pady=(2, 10))

    # image
    ttk.Label(left, text="2. Image", font=("Sans", 11, "bold")).pack(anchor="w")
    row = ttk.Frame(left); row.pack(anchor="w", pady=2)
    open_btn = ttk.Button(row, text="Choose image…"); open_btn.pack(side="left")
    rot_btn = ttk.Button(row, text="Rotate ↻"); rot_btn.pack(side="left", padx=6)

    vars_ = {}
    def slider(label, key, lo, hi, val, rerender=True):
        f = ttk.Frame(left); f.pack(anchor="w", fill="x")
        ttk.Label(f, text=label, width=11).pack(side="left")
        v = tk.IntVar(value=val); vars_[key] = v
        out = ttk.Label(f, text=str(val), width=4)
        s = ttk.Scale(f, from_=lo, to=hi, orient="horizontal", length=170,
                      command=lambda x: (v.set(round(float(x))), out.config(text=str(v.get()))))
        s.set(val); s.pack(side="left"); out.pack(side="left")
        if rerender:
            s.bind("<ButtonRelease-1>", lambda e: render())
    slider("Brightness", "br", -100, 100, 20)
    slider("Contrast", "ct", -100, 100, 10)
    f = ttk.Frame(left); f.pack(anchor="w", fill="x", pady=2)
    ttk.Label(f, text="Dithering", width=11).pack(side="left")
    dm = ttk.Combobox(f, state="readonly", width=24,
                      values=["Photo (Floyd-Steinberg)", "Photo light (Atkinson)", "Black/white (text, logos)"])
    dm.current(0); dm.pack(side="left"); dm.bind("<<ComboboxSelected>>", lambda e: render())
    inv = tk.BooleanVar(); ttk.Checkbutton(left, text="Invert", variable=inv, command=lambda: render()).pack(anchor="w")
    endless = tk.BooleanVar()
    ttk.Checkbutton(left, text="Endless mode (long banner)", variable=endless,
                    command=lambda: (st.update(rot=None), render())).pack(anchor="w")
    f = ttk.Frame(left); f.pack(anchor="w", fill="x")
    ttk.Label(f, text="Length (cm)", width=11).pack(side="left")
    length = tk.StringVar(value="0")
    le = ttk.Entry(f, textvariable=length, width=6); le.pack(side="left")
    ttk.Label(f, text="0 = auto, max 400").pack(side="left", padx=6)
    le.bind("<Return>", lambda e: render()); le.bind("<FocusOut>", lambda e: render())

    # print
    ttk.Label(left, text="3. Print", font=("Sans", 11, "bold")).pack(anchor="w", pady=(10, 0))
    slider("Darkness", "en", 5, 70, 25, False)
    slider("Copies", "cp", 1, 10, 1, False)
    slider("Speed", "sp", 10, 60, 32, False)
    pr_btn = ttk.Button(left, text="Print"); pr_btn.pack(anchor="w", fill="x", pady=6)
    pg = ttk.Progressbar(left, maximum=1.0); pg.pack(anchor="w", fill="x")
    status = ttk.Label(left, text="", wraplength=300, foreground="#555"); status.pack(anchor="w", pady=4)
    coffee = ttk.Label(left, text="If FABP helped you, feel free to buy me a coffee ☕",
                       foreground="#3b6fb6", cursor="hand2")
    coffee.pack(side="bottom", anchor="w")
    coffee.bind("<Button-1>", lambda e: webbrowser.open(COFFEE))

    # preview
    info = ttk.Label(right, text="No image chosen yet"); info.pack(anchor="w")
    cf = ttk.Frame(right); cf.pack(fill="both", expand=True)
    cv = tk.Canvas(cf, bg="#e9eef4", highlightthickness=0)
    sb = ttk.Scrollbar(cf, orient="vertical", command=cv.yview)
    cv.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y"); cv.pack(side="left", fill="both", expand=True)
    cv.bind_all("<Button-4>", lambda e: cv.yview_scroll(-3, "units"))
    cv.bind_all("<Button-5>", lambda e: cv.yview_scroll(3, "units"))
    cv.bind_all("<MouseWheel>", lambda e: cv.yview_scroll(-1 if e.delta > 0 else 1, "units"))

    def say(msg):
        root.after(0, lambda: status.config(text=msg))

    def render():
        if not st["src"]:
            return
        try:
            L = float(length.get().replace(",", ".") or 0)
        except ValueError:
            L = 0
        img1, st["rot"] = prepare(st["src"], endless=endless.get(), length_cm=L, rotate=st["rot"],
                                  brightness=vars_["br"].get(), contrast=vars_["ct"].get(),
                                  dither=["fs", "at", "th"][dm.current()], invert=inv.get())
        st["img1"] = img1
        buf = io.BytesIO(); img1.convert("L").save(buf, "PNG")
        st["photo"] = tk.PhotoImage(data=base64.b64encode(buf.getvalue()))
        cv.delete("all")
        cv.create_image(10, 10, image=st["photo"], anchor="nw")
        cv.configure(scrollregion=(0, 0, img1.size[0] + 20, img1.size[1] + 20))
        info.config(text=f"Print length ≈ {img1.size[1] / PX_PER_CM:.1f} cm")

    def choose():
        p = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp *.tif *.tiff"), ("All", "*")])
        if p:
            try:
                st["src"] = Image.open(p); st["src"].load(); st["rot"] = None; render()
            except Exception as e:
                say(f"Could not load image: {e}")

    def rotate():
        if st["rot"] is not None:
            st["rot"] = (st["rot"] + (180 if endless.get() else 90)) % 360
            render()

    def do_scan():
        say("Scanning … (6 s)"); scan_btn.state(["disabled"])
        def done(fut):
            def ui():
                scan_btn.state(["!disabled"])
                try:
                    st["devs"] = fut.result()
                except Exception as e:
                    say(f"Bluetooth error: {e}\nIs Bluetooth switched on? Try: bluetoothctl power on"); return
                dev_box["values"] = [f"{'★ ' if l else ''}{n or '(no name)'}  [{a}]" for l, n, a, _ in st["devs"]]
                if st["devs"]:
                    dev_box.current(0)
                say(f"{len(st['devs'])} device(s) found. ★ = likely printer")
            root.after(0, ui)
        run(scan()).add_done_callback(done)

    def do_print():
        if st["busy"]:
            st["cancel"].set(); return
        if not st["img1"]:
            say("Choose an image first"); return
        if dev_box.current() < 0:
            say("Scan and choose a printer first"); return
        addr = st["devs"][dev_box.current()][2]
        st["busy"] = True; pr_btn.config(text="Stop")
        ev = threading.Event(); st["cancel"] = ev
        fut = run(print_image(st["img1"], addr, copies=vars_["cp"].get(), darkness=vars_["en"].get(),
                              speed=vars_["sp"].get(), endless=endless.get(), cancel=ev,
                              progress=lambda p: root.after(0, lambda: pg.config(value=p)), log=say))
        def done(f):
            def ui():
                st["busy"] = False; pr_btn.config(text="Print"); pg.config(value=0)
                if f.exception():
                    say(f"Print error: {f.exception()}")
            root.after(0, ui)
        fut.add_done_callback(done)

    open_btn.config(command=choose); rot_btn.config(command=rotate)
    scan_btn.config(command=do_scan); pr_btn.config(command=do_print)
    root.after(300, do_scan)
    root.mainloop()


# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser(description="FABP – Free All Bluetooth Printers")
    ap.add_argument("image", nargs="?", help="image to print (no image = open the window)")
    ap.add_argument("--scan", action="store_true", help="list Bluetooth devices nearby")
    ap.add_argument("-a", "--address", help="printer MAC address (default: first printer found)")
    ap.add_argument("--endless", action="store_true", help="endless mode: long side runs along the paper")
    ap.add_argument("--length", type=float, default=0, help="banner length in cm (endless mode, 0 = auto, max 400)")
    ap.add_argument("--rotate", type=int, choices=[0, 90, 180, 270], help="rotation (default: automatic)")
    ap.add_argument("--brightness", type=int, default=20)
    ap.add_argument("--contrast", type=int, default=10)
    ap.add_argument("--dither", choices=["fs", "at", "th"], default="fs", help="fs=photo, at=photo light, th=black/white")
    ap.add_argument("--invert", action="store_true")
    ap.add_argument("--darkness", type=int, default=25, help="5–70 (default 25)")
    ap.add_argument("--copies", type=int, default=1)
    ap.add_argument("--speed", type=int, default=32, help="lower = faster")
    ap.add_argument("--width", type=int, default=384, choices=[384, 576])
    ap.add_argument("--preview", metavar="PNG", help="save the processed image instead of printing")
    a = ap.parse_args()

    if a.scan:
        for likely, name, addr, rssi in asyncio.run(scan()):
            print(f"{'★' if likely else ' '} {addr}  {rssi or '':>4}  {name}")
        return
    if not a.image:
        return gui()
    img1, _ = prepare(a.image, a.width, a.endless, a.length, a.rotate, a.brightness, a.contrast, a.dither, a.invert)
    print(f"Print length ≈ {img1.size[1] / PX_PER_CM:.1f} cm")
    if a.preview:
        img1.save(a.preview); print(f"Saved {a.preview}"); return

    async def go():
        addr = a.address
        if not addr:
            devs = [d for d in await scan() if d[0]]
            if not devs:
                sys.exit("No printer found. Is it switched on and not connected to a phone? Try --scan.")
            addr = devs[0][2]
            print(f"Using {devs[0][1]} [{addr}]")
        last = [-1]
        def prog(p):
            pct = int(p * 100)
            if pct != last[0]:
                last[0] = pct
                print(f"\r{pct:3d} %", end="", flush=True)
        await print_image(img1, addr, a.copies, a.darkness, a.speed, a.endless, progress=prog,
                          log=lambda m: print("\n" + m))
    try:
        asyncio.run(go())
    except KeyboardInterrupt:
        print("\nAborted")


if __name__ == "__main__":
    main()
