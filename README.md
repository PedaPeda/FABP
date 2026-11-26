# FABP – Free All Bluetooth Printers

**▶ Open: https://pedapeda.github.io/FABP/**

🇬🇧 **English** – Print images on cheap Bluetooth thermal mini printers (“cat printers”, e.g. Mafiti X6 / Tiny Print) straight from your browser, without the manufacturer’s app. Includes dithering, brightness/contrast, an endless mode for banners up to 4 m and 10 languages. Works in Chrome or Edge (Windows, Mac, Android); on iPhone use the Bluefy browser.

🇩🇪 **Deutsch** – Drucke Bilder auf günstigen Bluetooth-Thermo-Minidruckern („Cat Printer“, z. B. Mafiti X6 / Tiny Print) direkt aus dem Browser, ohne die Hersteller-App. Mit Rasterung, Helligkeit/Kontrast, Endlos-Modus für Banner bis 4 m und 10 Sprachen. Läuft in Chrome oder Edge (Windows, Mac, Android); auf dem iPhone mit dem Browser Bluefy.

🇪🇸 **Español** – Imprime imágenes en mini impresoras térmicas Bluetooth baratas («cat printers», p. ej. Mafiti X6 / Tiny Print) directamente desde el navegador, sin la app del fabricante. Con tramado, brillo/contraste, modo continuo para pancartas de hasta 4 m y 10 idiomas. Funciona en Chrome o Edge (Windows, Mac, Android); en iPhone usa el navegador Bluefy.

🇫🇷 **Français** – Imprimez des images sur des mini imprimantes thermiques Bluetooth bon marché (« cat printers », p. ex. Mafiti X6 / Tiny Print) directement depuis le navigateur, sans l’appli du fabricant. Avec tramage, luminosité/contraste, mode continu pour des bannières jusqu’à 4 m et 10 langues. Fonctionne dans Chrome ou Edge (Windows, Mac, Android) ; sur iPhone, utilisez le navigateur Bluefy.

🇮🇹 **Italiano** – Stampa immagini su mini stampanti termiche Bluetooth economiche («cat printer», es. Mafiti X6 / Tiny Print) direttamente dal browser, senza l’app del produttore. Con retinatura, luminosità/contrasto, modalità continua per striscioni fino a 4 m e 10 lingue. Funziona in Chrome o Edge (Windows, Mac, Android); su iPhone usa il browser Bluefy.

🇵🇹 **Português** – Imprima imagens em mini impressoras térmicas Bluetooth baratas (“cat printers”, ex. Mafiti X6 / Tiny Print) diretamente do navegador, sem o app do fabricante. Com pontilhado, brilho/contraste, modo contínuo para faixas de até 4 m e 10 idiomas. Funciona no Chrome ou Edge (Windows, Mac, Android); no iPhone use o navegador Bluefy.

🇷🇺 **Русский** – Печать изображений на дешёвых Bluetooth-термопринтерах («cat printer», напр. Mafiti X6 / Tiny Print) прямо из браузера, без приложения производителя. Растрирование, яркость/контраст, бесконечный режим для баннеров до 4 м и 10 языков. Работает в Chrome или Edge (Windows, Mac, Android); на iPhone — в браузере Bluefy.

🇨🇳 **中文** – 直接在浏览器中通过蓝牙向廉价迷你热敏打印机（“猫咪打印机”，如 Mafiti X6 / Tiny Print）打印图片，无需厂商 App。支持抖动、亮度/对比度、最长 4 米横幅的连续模式以及 10 种语言。适用于 Chrome 或 Edge（Windows、Mac、Android）；iPhone 请使用 Bluefy 浏览器。

🇯🇵 **日本語** – 安価な Bluetooth ミニサーマルプリンター（「キャットプリンター」、例：Mafiti X6 / Tiny Print）に、メーカーのアプリなしでブラウザから直接画像を印刷できます。ディザリング、明るさ/コントラスト、最大 4 m のバナー用エンドレスモード、10 言語に対応。Chrome または Edge（Windows・Mac・Android）で動作し、iPhone では Bluefy ブラウザを使用します。

🇸🇦 **العربية** – اطبع الصور على طابعات حرارية صغيرة رخيصة تعمل بالبلوتوث (“cat printers”، مثل Mafiti X6 / Tiny Print) مباشرة من المتصفح، دون تطبيق الشركة المصنّعة. يتضمن التنقيط والسطوع/التباين ووضعًا مستمرًا للافتات حتى 4 م و10 لغات. يعمل في Chrome أو Edge (Windows وMac وAndroid)؛ وعلى iPhone استخدم متصفح Bluefy.

---

## 🐧 Linux version (native app)

The web page also runs in Chrome on Linux, but there Web Bluetooth is often turned off. The native Linux app in [`linux/`](linux/) works without a browser, with a window and a command line.

**Install** (once):

```bash
git clone https://github.com/PedaPeda/FABP.git
cd FABP/linux
./install.sh
```

Needs Python 3.9+, BlueZ (normal Linux Bluetooth) and tkinter (`sudo apt install python3-tk python3-venv` on Debian/Ubuntu/Mint).

**Use:** start **FABP** from the app menu, or in a terminal:

```bash
fabp                                  # open the window
fabp --scan                           # list printers nearby
fabp photo.jpg                        # print an image
fabp banner.png --endless --length 200    # 2 m banner
fabp photo.jpg --darkness 35 --dither at --copies 2
fabp --help                           # all options
```

Don't pair the printer in the system Bluetooth settings and close the phone app, so the printer is free.

---

☕ If FABP helped you, feel free to [buy me a coffee via PayPal](https://www.paypal.me/pedapedapeda).

Protocol based on the public reverse-engineering work of the “cat printer” community (e.g. [NaitLee/Cat-Printer](https://github.com/NaitLee/Cat-Printer)).
