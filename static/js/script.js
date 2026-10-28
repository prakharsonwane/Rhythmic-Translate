const $ = id => document.getElementById(id);
const themeToggle = $('themeToggle');
try { if (localStorage.getItem('rt-theme') === 'dark') document.body.classList.add('dark'); } catch (_) {}
if (themeToggle) themeToggle.addEventListener('click', () => {
  document.body.classList.toggle('dark');
  try { localStorage.setItem('rt-theme', document.body.classList.contains('dark') ? 'dark' : 'light'); } catch (_) {}
});
const source = $('sourceText'), result = $('resultText'), status = $('status');
function message(text, error = false) {
  if (!status) return;
  status.textContent = text;
  status.className = 'status' + (error ? ' error' : '');
}
const speechLocales = {en:'en-US',hi:'hi-IN',es:'es-ES',fr:'fr-FR',de:'de-DE',it:'it-IT',pt:'pt-PT',ru:'ru-RU',ja:'ja-JP',ko:'ko-KR',zh:'zh-CN',ar:'ar-SA',bn:'bn-IN',ur:'ur-PK',mr:'mr-IN',ta:'ta-IN',te:'te-IN',gu:'gu-IN',pa:'pa-IN',nl:'nl-NL',tr:'tr-TR',id:'id-ID',th:'th-TH',vi:'vi-VN',pl:'pl-PL',uk:'uk-UA',sv:'sv-SE'};
if (source) source.addEventListener('input', () => { if ($('count')) $('count').textContent = `${source.value.length} / 4500`; });
const translateButton = $('translateBtn');
if (translateButton) translateButton.addEventListener('click', async () => {
  // Guard every required element so stale/cached markup cannot cause a null.value crash.
  const sourceField = $('sourceText');
  const resultField = $('resultText');
  const sourceSelect = $('sourceLang');
  const targetSelect = $('targetLang');
  const providerLabel = $('provider');
  if (!sourceField || !resultField || !sourceSelect || !targetSelect) {
    message('Translator controls did not load correctly. Refresh the page and try again.', true);
    return;
  }
  const text = sourceField.value.trim();
  if (!text) { message('Type or paste some text first.', true); sourceField.focus(); return; }
  if (text.length > 4500) { message('Please keep text under 4,500 characters.', true); sourceField.focus(); return; }
  const sourceLang = sourceSelect.value || 'auto';
  const targetLang = targetSelect.value || 'hi';
  if (targetLang === 'auto') { message('Choose a target language.', true); return; }
  message('Translating your words…'); translateButton.disabled = true;
  try {
    const response = await fetch('/api/translate', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text, source_lang:sourceLang, target_lang:targetLang, mode:'standard'})
    });
    let data;
    try { data = await response.json(); }
    catch (_) { throw new Error('The server returned an unreadable response. Please retry.'); }
    if (!response.ok) throw new Error(data.error || `Translation failed (HTTP ${response.status}). Please try again.`);
    if (typeof data.translated_text !== 'string') throw new Error('The translation service returned an invalid result. Please retry.');
    resultField.value = data.translated_text;
    if (providerLabel) providerLabel.textContent = (data.provider || 'TRANSLATED').toUpperCase();
    message(data.saved ? 'Done — this translation was saved to your history.' : 'Translation complete. Sign in to save it in your history.');
  } catch (error) { message(error.message || 'Something went wrong. Check your connection and retry.', true); }
  finally { translateButton.disabled = false; }
});
if ($('swapBtn')) $('swapBtn').addEventListener('click', () => {
  const s = $('sourceLang'), t = $('targetLang');
  if (s.value === 'auto') { message('Choose a source language before swapping.', true); return; }
  const oldLang = s.value; s.value = t.value; t.value = oldLang;
  const oldText = source.value; source.value = result.value; result.value = oldText;
  if ($('count')) $('count').textContent = `${source.value.length} / 4500`;
  message('Languages swapped.');
});
if ($('clearBtn')) $('clearBtn').addEventListener('click', () => {
  source.value = ''; result.value = ''; $('provider').textContent = 'READY WHEN YOU ARE';
  if ($('count')) $('count').textContent = '0 / 4500'; message('Cleared. Ready for your next translation.'); source.focus();
});
if ($('copyBtn')) $('copyBtn').addEventListener('click', async () => {
  if (!result.value) { message('Nothing to copy yet.', true); return; }
  try { await navigator.clipboard.writeText(result.value); message('Translation copied to clipboard.'); }
  catch (_) { result.select(); document.execCommand('copy'); message('Translation copied.'); }
});
if ($('downloadBtn')) $('downloadBtn').addEventListener('click', () => {
  if (!result.value) { message('Translate some text first.', true); return; }
  const url = URL.createObjectURL(new Blob([result.value], {type:'text/plain;charset=utf-8'}));
  const a = document.createElement('a'); a.href = url; a.download = 'rhythmic-translation.txt'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
if ($('speakBtn')) $('speakBtn').addEventListener('click', () => {
  const text = result.value.trim();
  if (!text) { message('Translate some text first, then tap Listen.', true); return; }
  if (!('speechSynthesis' in window) || !('SpeechSynthesisUtterance' in window)) { message('Listen is not supported in this browser. Try Chrome or Edge.', true); return; }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  const lang = $('targetLang').value;
  utterance.lang = speechLocales[lang] || lang || 'en-US';
  const voices = window.speechSynthesis.getVoices();
  const wanted = utterance.lang.toLowerCase().split('-')[0];
  const voice = voices.find(v => v.lang.toLowerCase() === utterance.lang.toLowerCase()) || voices.find(v => v.lang.toLowerCase().startsWith(wanted));
  if (voice) utterance.voice = voice;
  utterance.onstart = () => message('Playing your translation…');
  utterance.onend = () => message('Finished listening.');
  utterance.onerror = event => message('Voice playback failed (' + (event.error || 'unknown error') + '). Check your device text-to-speech settings.', true);
  window.speechSynthesis.speak(utterance);
  message('Starting voice playback…');
});
if ($('micBtn')) $('micBtn').addEventListener('click', () => {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) { message('Voice input is not supported here. Try Chrome and allow microphone access.', true); return; }
  const recognition = new Recognition(); const lang = $('sourceLang').value;
  recognition.lang = speechLocales[lang] || (lang === 'auto' ? 'en-US' : lang); recognition.interimResults = false; recognition.maxAlternatives = 1;
  recognition.onstart = () => message('Listening… speak now.');
  recognition.onresult = event => { source.value = event.results[0][0].transcript; if ($('count')) $('count').textContent = `${source.value.length} / 4500`; message('Voice captured. Press Translate text when ready.'); };
  recognition.onerror = event => message(event.error === 'not-allowed' ? 'Microphone permission was denied. Allow it in browser settings.' : 'Could not capture speech. Try again.', true);
  recognition.onend = () => {};
  try { recognition.start(); } catch (_) { message('Voice input is already active. Try again in a moment.', true); }
});
if ($('fileInput')) $('fileInput').addEventListener('change', async event => {
  const file = event.target.files[0]; if (!file) return;
  if (file.size > 12 * 1024 * 1024) { message('Please choose a file smaller than 12 MB.', true); event.target.value = ''; return; }
  message(`Reading ${file.name}…`); const form = new FormData(); form.append('file', file);
  try {
    const response = await fetch('/api/extract', {method:'POST', body:form}); const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Could not read this file.');
    source.value = data.text.slice(0,4500); if ($('count')) $('count').textContent = `${source.value.length} / 4500`;
    message(`Text extracted from ${data.filename}. ${data.text.length > 4500 ? 'Only the first 4,500 characters are shown.' : 'Ready to translate.'}`);
  } catch (error) { message(error.message || 'Could not read this file.', true); }
  finally { event.target.value = ''; }
});

if ($('cameraInput')) $('cameraInput').addEventListener('change', async event => {
  const file = event.target.files[0]; if (!file) return;
  if (file.size > 12 * 1024 * 1024) { message('Please capture a smaller image (under 12 MB).', true); event.target.value = ''; return; }
  message('Reading your camera photo…'); const form = new FormData(); form.append('file', file, file.name || 'camera-photo.jpg');
  try {
    const response = await fetch('/api/extract', {method:'POST', body:form}); const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Could not read this photo.');
    source.value = data.text.slice(0,4500); if ($('count')) $('count').textContent = `${source.value.length} / 4500`;
    message(`Text extracted from camera photo. ${data.text.length > 4500 ? 'Only the first 4,500 characters are shown.' : 'Ready to translate.'}`);
  } catch (error) { message(error.message || 'Could not read camera photo. Check OCR setup.', true); }
  finally { event.target.value = ''; }
});
