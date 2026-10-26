# Rhythmic Translate — Advanced Edition

A responsive Flask translation app with a polished interface, language selection, browser speech tools, file text extraction, optional AI translation, account sign-up/login, and personal translation history.

## Run locally (Windows / VS Code)

1. Extract `Rhythmic-Translate-Advanced.zip`.
2. In VS Code, choose **File → Open Folder** and open the extracted `Rhythmic-Translate-Advanced` folder.
3. Open **Terminal → New Terminal**. If needed, run:
   ```powershell
   cd Rhythmic-Translate-Advanced
   ```
   (If VS Code already opened the extracted folder, you can skip this command.)
4. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
5. Start the app:
   ```powershell
   python app.py
   ```
6. Open **http://127.0.0.1:5000** in your browser. Keep the terminal running while you use the app. Press `Ctrl+C` in the terminal to stop it.

## Features

- Responsive translator UI with light/dark theme toggle
- 25+ language choices, language swapping, and character count
- Standard online translation through MyMemory (internet required)
- Optional AI translation through OpenAI API
- Browser speech recognition and text-to-speech (browser/device support varies)
- Import TXT, DOCX, PDF, and image files to extract text
- SQLite accounts with hashed passwords
- Personal history with search, favorites, delete, and text download

## Optional API keys

The core UI and standard text translation do not require an API key. Optional features need keys:

1. Copy `.env.example` to a new file named `.env` in this folder.
2. Add the relevant key(s):
   - `OPENAI_API_KEY` for AI-enhanced translation
   - `OCR_SPACE_API_KEY` for image OCR and scanned PDF OCR
3. Save `.env` and restart the app.

Never share your `.env` file or publish API keys. Text/PDF text extraction for selectable-text PDFs and DOCX/TXT files does not need OCR. Scanned documents need OCR.

## Notes

- Translation uses an external online service; do not submit private or confidential text.
- Speech input is supported only in compatible browsers and requires microphone permission. Chrome is a good first choice.
- The SQLite database is created automatically in `instance/` when the app starts.
- This is a local development project, not production-hardened. Before public deployment, set a strong `FLASK_SECRET_KEY`, disable debug mode, and add CSRF protection and other production security controls.


## PWA installation
The app includes a web app manifest, icons, service worker, offline fallback page, and an Install App button. Deploy over HTTPS (Render provides HTTPS on its `onrender.com` domain). On Android/Chrome, tap Install App when the browser offers installation. On iPhone, open the site in Safari, tap Share, then Add to Home Screen. HTML pages and API responses are deliberately not cached, so authenticated content and translation requests stay fresh.
