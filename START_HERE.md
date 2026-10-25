# Gold Intelligence — open it on your phone

This package is source code, not an App Store download or hosted trading service.
The complete interface connects to the included FastAPI backend. The backend
produces live data context when sources are available; forecast probabilities
remain unavailable until the documented model/data gates pass. No orders occur.

## Fastest setup: computer + phone on the same Wi-Fi

Install Python 3.12 and a Node version compatible with Expo SDK 58 (Node 24 LTS
is a suitable starting point). Install the matching Expo Go on your phone.
Extract the ZIP first; do not run commands inside the compressed archive.

On Windows, open PowerShell in the extracted `gold-regime-terminal` folder:

```powershell
.\start-backend.ps1
```

If your machine blocks local scripts, run the equivalent commands from README.md
or follow your workplace IT policy. The launcher does not alter security policy.

On macOS/Linux, open Terminal in that folder:

```bash
bash start-backend.sh
```

Leave that terminal running. In a second terminal in the same folder:

```powershell
# Windows
.\start-phone.ps1
```

```bash
# macOS/Linux
bash start-phone.sh
```

Open the displayed QR code with compatible Expo Go. The app opens its connection
screen. Enter `http://YOUR_COMPUTER_LAN_IP:8000` and tap **Test connection & save**.
Use the computer's Wi-Fi IPv4 address (Windows: `ipconfig`; macOS/Linux: network
settings). Allow TCP port 8000 through the computer firewall. `localhost` on the
phone is the phone, not the computer. Do not enter the Expo development URL as
the backend address. The app remembers the tested backend URL across restarts.

The first report may take one or two minutes. Other tabs share that snapshot.
Reports update every five minutes while foregrounded and refresh on app resume.
Reconnect retries immediately. Old data keeps its timestamp and receives a
STALE DISPLAY banner after a failed connection or when over six minutes old.
Saved server settings persist; old market decisions are not persisted on phone.

## Use away from the computer's Wi-Fi

Deploy the backend using Render/Railway instructions in README.md, or your own
Docker-capable host. Then enter the resulting HTTPS backend URL in the app.
No hosting account or public domain has been created by this package. Free hosts
may sleep and lose SQLite history without persistent storage. Continuous data
collection needs an always-on service and durable DATA_DIR.

Local HTTPS alternative: run `ngrok http 8000` and use its HTTPS URL. The Expo
frontend tunnel is different from this backend tunnel. If local HTTP is blocked
by iOS, use HTTPS. Native app.json settings do not alter Expo Go itself.

Docker, from `backend`:

```bash
docker build -t gold-intelligence .
docker run --rm -p 8000:8000 -v gold-terminal-data:/data gold-intelligence
```

Docker was configured but is not assumed installed/tested on your computer.
Set optional source/API environment variables on the container/host. Never add
API keys to Expo public variables. Keep only one backend worker with SQLite.

## Standalone Android / iOS builds

`mobile/eas.json` includes preview and production build profiles. From mobile,
with an Expo account and appropriate platform credentials:

```bash
npx eas-cli@latest build:configure
npx eas-cli@latest build --platform android --profile preview
```

The preview Android output is an APK. iOS internal builds require Apple device
registration/provisioning and may require paid Apple membership. EAS may prompt
for account/project setup or incur plan usage. No binaries have been built or
signed here. Package identifiers in app.json are defaults: choose identifiers
you own before distributing. Expo Go is the quickest first device test.

Standalone apps still need a reachable backend. Set EXPO_PUBLIC_BACKEND_URL at
build time for your own default or use the connection screen after installation.

## Check the backend

- `/health`: server alive and whether a snapshot exists.
- `/capabilities`: version and configured data/model presence; file presence is
  not calibration or forecast readiness.
- `/regime`: all screens' shared snapshot including the new intelligence report.
- `/intelligence`: six-horizon report only.
- `/docs`: interactive API documentation.

## Why the app may correctly show NO TRADE

Default feeds cover only some required inputs. Fed futures distribution, verified
IAU/WGC inputs, trained models and current execution data are not invented.
See UPGRADE_V2.md for exact empty-template schemas, training-data contract,
chronological calibration and readiness gates. Missing probabilities display
Unavailable. The app is functional without pretending these data gaps are solved.

No historical forecasting accuracy or profitability has been established.
