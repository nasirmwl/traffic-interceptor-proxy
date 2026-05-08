# mitm mocks

Simple mock API setup using `mitmproxy` + `mocks.json`.

## Files

- `mocks.json`: all mock rules
- `mock_gui.py`: small UI to edit mocks
- `dlp_in_mocks.py`: mitmproxy addon that serves mock responses
- `mock_engine.py`: matching logic used by both

## Setup

```bash
cd ~/mitm
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run GUI

```bash
source .venv/bin/activate
streamlit run mock_gui.py
```

## Run mitmproxy

```bash
source .venv/bin/activate
mitmproxy -s dlp_in_mocks.py
```

## Notes

- edit mocks in GUI or directly in `mocks.json`
- changes in `mocks.json` are auto-reloaded
