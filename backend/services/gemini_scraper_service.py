"""
Gemini UI Scraper Service
Exact same functionality as geminiCompanyProfile.py but as a service
"""
from playwright.async_api import async_playwright
import time
import random
import os
import json
import re
import sys
import asyncio
from typing import Dict, Optional

# Fix for Windows: Set event loop policy for Playwright
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


# ---------- CONFIG ----------
# Session path relative to backend folder
SESSION_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "x_browser_session_gemini_company")
# Default to headless=True for server environments (no X server)
# Can be overridden with GEMINI_HEADLESS environment variable (set to "false" to disable headless)
HEADLESS = os.getenv("GEMINI_HEADLESS", "true").lower() == "true"
# If DISPLAY is not set, force headless mode
if not os.getenv("DISPLAY"):
    HEADLESS = True
CHROME_PATH = None
MOUSE_STEP_MS = 6
SELECTOR_MEMORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "working_selectors_company.json")
STABILIZE_SECONDS = 7
MIN_ACCEPT_CHARS = 300
# ----------------------------


# ---------- Human-like behavior ----------
def rand(a, b):
    return random.uniform(a, b)


# Removed sync human_wait - using async version only


async def async_human_wait(a=0.3, b=1.2):
    import asyncio
    await asyncio.sleep(rand(a, b))


async def human_type(el, text):
    """Type text character-by-character with random micro-delays."""
    for ch in text:
        await el.type(ch, delay=int(rand(20, 80)))
        if random.random() < 0.05:
            await async_human_wait(0.1, 0.4)


def bezier_interp(p0, p1, p2, p3, t):
    x = ((1 - t)**3)*p0[0] + 3*((1 - t)**2)*t*p1[0] + 3*(1 - t)*(t**2)*p2[0] + (t**3)*p3[0]
    y = ((1 - t)**3)*p0[1] + 3*((1 - t)**2)*t*p1[1] + 3*(1 - t)*(t**2)*p2[1] + (t**3)*p3[1]
    return x, y


async def human_move_mouse(mouse, start, end, steps=30):
    """Smooth curved mouse movement using Bézier interpolation."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    p0, p1, p2, p3 = start, (
        start[0] + dx * rand(0.2, 0.4) + rand(-50, 50),
        start[1] + dy * rand(0.2, 0.4) + rand(-50, 50)
    ), (
        start[0] + dx * rand(0.6, 0.8) + rand(-50, 50),
        start[1] + dy * rand(0.6, 0.8) + rand(-50, 50)
    ), end
    for i in range(steps):
        t = i / float(steps - 1)
        x, y = bezier_interp(p0, p1, p2, p3, t)
        await mouse.move(x + rand(-1.2, 1.2), y + rand(-1.2, 1.2))
        await async_human_wait(MOUSE_STEP_MS / 1000.0, MOUSE_STEP_MS / 1000.0)


async def human_click(page, el):
    """Perform a realistic mouse click on an element."""
    try:
        await el.scroll_into_view_if_needed(timeout=4000)
    except:
        pass
    box = await el.bounding_box()
    if not box:
        return
    start = (rand(100, 400), rand(100, 400))
    target = (box["x"] + rand(5, box["width"] - 5),
              box["y"] + rand(5, box["height"] - 5))
    await human_move_mouse(page.mouse, start, target, steps=random.randint(25, 45))
    await async_human_wait(0.05, 0.3)
    await page.mouse.down()
    await async_human_wait(0.02, 0.08)
    await page.mouse.up()


# ---------- Cleaner ----------
BANNED_PATTERNS = [
    r"^\s*\(function", r"use strict", r"const\s", r"let\s", r"var\s", r"class\s",
    r"throw\s+Error", r"theme-host", r"google-sans", r"old-google-sans",
    r"Sign in", r"Saving your chats", r"Sources\s", r"Gemini can make mistakes",
    r"Once you'?re signed in", r"iframe\s+src=", r"gbar_",
    r"window\.", r"document\.", r"try\s*\{", r"catch\s*\(", r"\.prototype\.",
    r"export\s+default", r"import\s+"
]
BANNED_REGEX = re.compile("|".join(BANNED_PATTERNS), re.IGNORECASE)


def looks_like_js_garbage(s: str) -> bool:
    if not s or len(s) < 40:
        return True
    punct = sum(s.count(ch) for ch in "{}();[]=<>")
    if punct > max(12, len(s) // 30):
        return True
    if BANNED_REGEX.search(s):
        return True
    if "theme" in s and "google" in s and "sans" in s:
        return True
    return False


def strong_clean(text: str) -> str:
    """Remove HTML, scripts, boilerplate, and duplicates."""
    if not text:
        return ""
    text = re.sub(r"(?is)<script.*?>.*?</script>", "", text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", "", text)
    text = re.sub(r"(?is)<.*?>", "", text)
    text = re.sub(r"(?is)Sign in.*?(?:\n|$)", " ", text)
    text = re.sub(r"(?is)Sources:?.*", " ", text)
    text = re.sub(r"(?is)Gemini can make mistakes.*", " ", text)
    text = re.sub(r"(?is)Once you'?re signed in.*", " ", text)
    text = re.sub(r"(?is)\(function.*?use strict.*?\)", " ", text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    seen, out = set(), []
    for l in lines:
        if looks_like_js_garbage(l):
            continue
        if l in seen:
            continue
        seen.add(l)
        out.append(l)
    text = " ".join(out)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


# ---------- Sentence-level de-duplication ----------
SENT_SEP_REGEX = re.compile(
    r'(?<=[.?!])\s+(?=[A-Z0-9"(\[])|(?<=\n)\s+'
)


def _normalize_sentence(s: str) -> str:
    s2 = s.strip()
    s2 = re.sub(r"\s+", " ", s2)
    s2 = s2.strip('"""\'`•–- ').lower()
    s2 = s2.replace(",", "")
    return s2


def dedupe_sentences(text: str) -> str:
    """Remove duplicate or near-duplicate sentences."""
    if not text:
        return text
    splits = SENT_SEP_REGEX.split(text)
    tmp = []
    for chunk in splits:
        if not chunk:
            continue
        sub = re.split(r'(?:(?<=\:)|(?<=\)))(?=\s+)|(?<=\n)|(?<=—)\s+', chunk)
        for s in sub:
            if s and s.strip():
                tmp.append(s.strip())
    seen = set()
    out = []
    for s in tmp:
        sub_sents = re.split(r'(?<=;)\s+|(?<=—)\s+|(?<=–)\s+', s)
        if len(sub_sents) > 1:
            for ss in sub_sents:
                _norm = _normalize_sentence(ss)
                if not _norm or len(_norm) < 5:
                    continue
                if _norm in seen:
                    continue
                seen.add(_norm)
                out.append(ss.strip())
        else:
            _norm = _normalize_sentence(s)
            if not _norm or len(_norm) < 5:
                continue
            if _norm in seen:
                continue
            seen.add(_norm)
            out.append(s.strip())
    cleaned = " ".join(out)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned


# ---------- Selector Set ----------
BASE_SELECTORS = list(dict.fromkeys([
    # Direct Gemini JSON response selectors (highest priority)
    "model-response message-content.model-response-text .markdown p",
    "model-response message-content.model-response-text p",
    "model-response message-content p",
    "message-content.model-response-text .markdown p",
    "message-content.model-response-text p",
    "response-container message-content p",
    # Gemini response container selectors
    "model-response",
    "response-container",
    "message-content.model-response-text",
    # Legacy selectors
    "div[data-message-author='ai']",
    "[data-message-author='ai']",
    "div[aria-live='polite']",
    "div[aria-live='assertive']",
    "[role='feed'] [role='article']",
    "article[aria-live]",
    "article[role='article']",
    "div[role='article']",
    "div[role='region'][aria-live]",
    "section[role='region'][aria-live]",
    "section[aria-live]",
    "div[role='main'] div[aria-live]",
    "main [aria-live]",
    "cib-response",
    "cib-serp",
    "chat-message[role='response']",
    "chat-message[data-author='ai']",
    "chat-turn",
    "chat-ui",
    "chat-line",
    "md-content",
    "md-output",
    "md-block",
    "div[class*='markdown' i]",
    "section[class*='markdown' i]",
    "span[class*='markdown' i]",
    "div[class*='prose' i]",
    "div[class*='content' i]",
    "div[class*='response' i]",
    "section[class*='response' i]",
    "div[class*='output' i]",
    "div[class*='assistant' i]",
    "div[class*='answer' i]",
    "div[class*='message' i]",
    "div[class*='msg' i]",
    "div[class*='ai' i]",
    "[aria-label*='response' i]",
    "[aria-label*='assistant' i]",
    "[aria-label*='answer' i]",
    "[aria-label*='message' i]",
    "article",
    "section",
    "div[dir='auto']",
    "div[role='region']",
    "div[role='main']",
    "main",
    "p",
    "pre",
    "code"
]))


async def collect_text_candidates(page, selectors):
    texts = []
    for sel in selectors:
        try:
            els = await page.query_selector_all(sel)
            if not els:
                continue
            for el in els:
                try:
                    if not el or not await el.is_visible():
                        continue
                    
                    tag_name = (await el.evaluate("el => el.tagName") or "").upper()
                    is_contenteditable = await el.evaluate("el => el.contentEditable === 'true'") or False
                    is_input = tag_name in ("INPUT", "TEXTAREA")
                    role = (await el.get_attribute("role") or "").lower()
                    
                    if is_input or (is_contenteditable and role in ("textbox", "combobox")):
                        continue
                    if role in ("navigation", "banner", "complementary", "contentinfo"):
                        continue
                    
                    t = await el.inner_text()
                    t = t.strip() if t else ""
                    if not t or len(t) < 40 or looks_like_js_garbage(t):
                        continue
                    
                    prompt_indicators = [
                        "Provide a complete and comprehensive",
                        "Return ONLY valid JSON",
                        "Return ONLY the JSON object"
                    ]
                    if any(indicator in t for indicator in prompt_indicators) and len(t) < 500:
                        continue
                    
                    texts.append(t)
                except:
                    continue
        except:
            continue
    return texts


async def deep_shadow_text(page) -> str:
    try:
        return await page.evaluate("""() => {
            function visible(e){
                const st = (el)=>getComputedStyle(el);
                if(!e || !(e instanceof Element)) return false;
                const s = st(e);
                if (s && (s.visibility === 'hidden' || s.display === 'none' || parseFloat(s.opacity||'1') < 0.05)) return false;
                const r = e.getBoundingClientRect();
                if ((r.width===0 && r.height===0) || (r.bottom < 0) || (r.right < 0)) return false;
                return true;
            }
            function deepText(e){
                if(!e) return '';
                let t='';
                if(e.shadowRoot) t+=deepText(e.shadowRoot);
                for(const n of e.childNodes){
                    if(n.nodeType===Node.TEXT_NODE) t+=n.textContent;
                    else if(n.nodeType===Node.ELEMENT_NODE){
                        if(visible(n)) t+=deepText(n);
                    }
                }
                return t;
            }
            return deepText(document.body);
        }""")
    except:
        return ""


def stabilize_text(current: str, last: str, stable_since: float):
    """Return updated stability state for response text."""
    now = time.time()
    if current != last:
        return current, now, False
    if now - stable_since >= STABILIZE_SECONDS:
        return last, stable_since, True
    return last, stable_since, False


async def get_json_directly_from_dom(page, user_prompt: str, timeout_ms=60000) -> Optional[str]:
    """Extract JSON directly from DOM using specific selectors - fastest method."""
    print("📋 Attempting to extract JSON directly from DOM...")
    
    start = time.time()
    user_prompt_clean = user_prompt.strip()
    
    json_selectors = [
        "model-response message-content.model-response-text .markdown p",
        "model-response message-content.model-response-text p",
        "model-response message-content p",
        "message-content.model-response-text .markdown p",
        "message-content.model-response-text p",
        "response-container message-content p",
    ]
    
    print("⏳ Waiting for Gemini JSON response to appear...")
    await async_human_wait(3.0, 3.0)
    
    while (time.time() - start) * 1000 < timeout_ms:
        try:
            for selector in json_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        latest_element = elements[-1]
                        if latest_element and await latest_element.is_visible():
                            json_text = await latest_element.inner_text()
                            json_text = json_text.strip()
                            
                            if user_prompt_clean in json_text or json_text == user_prompt_clean:
                                continue
                            
                            if json_text.startswith('{') and len(json_text) > MIN_ACCEPT_CHARS:
                                await async_human_wait(5.0, 5.0)
                                
                                stable_count = 0
                                last_json_text = json_text
                                for _ in range(3):
                                    await async_human_wait(2.0, 2.0)
                                    elements = await page.query_selector_all(selector)
                                    if elements:
                                        latest_element = elements[-1]
                                        current_json_text = await latest_element.inner_text()
                                        current_json_text = current_json_text.strip()
                                        
                                        if current_json_text == last_json_text:
                                            stable_count += 1
                                        else:
                                            stable_count = 0
                                            last_json_text = current_json_text
                                        
                                        if stable_count >= 2:
                                            json_text = current_json_text
                                            break
                                        json_text = current_json_text
                                
                                if json_text.startswith('{') and user_prompt_clean not in json_text and len(json_text) > MIN_ACCEPT_CHARS:
                                    try:
                                        test_parse = json.loads(json_text)
                                        if isinstance(test_parse, dict):
                                            expected_keys = ['What', 'When', 'Where', 'How', 'Who']
                                            if sum(1 for key in expected_keys if key in test_parse) >= 3:
                                                print("✅ Successfully extracted complete JSON directly from DOM!")
                                                return json_text
                                            elif len(json_text) > 2000:
                                                print("✅ Successfully extracted JSON directly from DOM!")
                                                return json_text
                                    except:
                                        pass
                                    
                                    if len(json_text) > 500:
                                        print("✅ Successfully extracted JSON directly from DOM!")
                                        return json_text
                except:
                    continue
            
            response_elements = await page.query_selector_all("model-response, response-container")
            if response_elements:
                latest_response = response_elements[-1]
                try:
                    message_content = await latest_response.query_selector("message-content.model-response-text")
                    if message_content and await message_content.is_visible():
                        json_text = await message_content.inner_text()
                        json_text = json_text.strip()
                        if json_text.startswith('{') and user_prompt_clean not in json_text and len(json_text) > MIN_ACCEPT_CHARS:
                            await async_human_wait(5.0, 5.0)
                            stable_count = 0
                            last_json_text = json_text
                            for _ in range(3):
                                await async_human_wait(2.0, 2.0)
                                current_json_text = await message_content.inner_text()
                                current_json_text = current_json_text.strip()
                                if current_json_text == last_json_text:
                                    stable_count += 1
                                else:
                                    stable_count = 0
                                    last_json_text = current_json_text
                                if stable_count >= 2:
                                    json_text = current_json_text
                                    break
                                json_text = current_json_text
                            
                            if json_text.startswith('{') and len(json_text) > MIN_ACCEPT_CHARS:
                                try:
                                    test_parse = json.loads(json_text)
                                    if isinstance(test_parse, dict):
                                        expected_keys = ['What', 'When', 'Where', 'How', 'Who']
                                        if sum(1 for key in expected_keys if key in test_parse) >= 3 or len(json_text) > 2000:
                                            print("✅ Successfully extracted complete JSON directly from DOM!")
                                            return json_text
                                except:
                                    if len(json_text) > 500:
                                        print("✅ Successfully extracted JSON directly from DOM!")
                                        return json_text
                except:
                    pass
        except:
            pass
        
        await async_human_wait(1.0, 1.0)
    
    print("⚠️ Direct JSON extraction failed. Trying copy button method...")
    return None


async def get_response_via_copy_button(page, user_prompt: str, timeout_ms=120000) -> Optional[str]:
    """Get Gemini response by clicking copy button and reading from clipboard."""
    print("📋 Attempting to get response via copy button...")
    
    start = time.time()
    user_prompt_clean = user_prompt.strip()
    
    print("⏳ Waiting for Gemini response to appear...")
    await async_human_wait(3.0, 3.0)
    
    latest_response_element = None
    
    while (time.time() - start) * 1000 < timeout_ms:
        try:
            response_elements = await page.query_selector_all("model-response")
            if not response_elements or len(response_elements) == 0:
                response_elements = await page.query_selector_all("response-container")
            if not response_elements or len(response_elements) == 0:
                response_elements = await page.query_selector_all("message-content.model-response-text")
            if not response_elements or len(response_elements) == 0:
                response_elements = await page.query_selector_all(
                    "div[data-message-author-role='model'], div[data-message-author-role='assistant']"
                )
            
            if response_elements and len(response_elements) > 0:
                latest_response_element = response_elements[-1]
                response_text_dom = await latest_response_element.inner_text()
                response_text_dom = response_text_dom.strip()
                
                if user_prompt_clean in response_text_dom or response_text_dom == user_prompt_clean:
                    await async_human_wait(1.0, 1.0)
                    continue
                
                if len(response_text_dom) > MIN_ACCEPT_CHARS and response_text_dom != user_prompt_clean:
                    await async_human_wait(2.0, 2.0)
                    response_elements = await page.query_selector_all("model-response")
                    if not response_elements or len(response_elements) == 0:
                        response_elements = await page.query_selector_all("response-container")
                    if not response_elements or len(response_elements) == 0:
                        response_elements = await page.query_selector_all("message-content.model-response-text")
                    if response_elements:
                        latest_response_element = response_elements[-1]
                        response_text_dom = await latest_response_element.inner_text()
                        response_text_dom = response_text_dom.strip()
                        if user_prompt_clean not in response_text_dom and len(response_text_dom) > MIN_ACCEPT_CHARS:
                            break
        except Exception as e:
            pass
        
        await async_human_wait(1.0, 1.0)
    
    if not latest_response_element:
        print("⚠️ Gemini response element not found. Falling back to DOM scraping...")
        return None
    
    try:
        copy_button = None
        copy_button = await latest_response_element.query_selector("copy-button button[data-test-id='copy-button']")
        if not copy_button:
            copy_button = await latest_response_element.query_selector("copy-button button[aria-label='Copy']")
        if not copy_button:
            copy_button = await latest_response_element.query_selector("copy-button button")
        
        if not copy_button:
            response_container = await latest_response_element.query_selector("response-container")
            if response_container:
                copy_button = await response_container.query_selector("copy-button button[data-test-id='copy-button']")
                if not copy_button:
                    copy_button = await response_container.query_selector("message-actions copy-button button[data-test-id='copy-button']")
                    if not copy_button:
                        copy_button = await response_container.query_selector("button[aria-label*='Copy' i]")
        
        if not copy_button:
            copy_button = await latest_response_element.query_selector("button[aria-label*='Copy' i]")
            if copy_button:
                is_in_user_query = await copy_button.evaluate("""
                    (button) => {
                        let parent = button.parentElement;
                        while (parent) {
                            if (parent.tagName && parent.tagName.toLowerCase() === 'user-query') {
                                return true;
                            }
                            parent = parent.parentElement;
                        }
                        return false;
                    }
                """)
                if is_in_user_query:
                    copy_button = None
        
        if not copy_button:
            print("⚠️ Copy button not found in response element. Falling back to DOM scraping...")
            return None
        
        print("🖱️ Clicking copy button...")
        await copy_button.scroll_into_view_if_needed()
        await async_human_wait(0.3, 0.6)
        await copy_button.click(timeout=5000)
        await async_human_wait(0.5, 1.0)
        
        print("📋 Reading from clipboard...")
        clipboard_text = None
        
        try:
            clipboard_text = await page.evaluate("""async () => {
                try {
                    const text = await navigator.clipboard.readText();
                    return text;
                } catch (err) {
                    return null;
                }
            }""")
        except Exception as e:
            print(f"⚠️ Clipboard API error: {e}. Trying alternative method...")
        
        if not clipboard_text:
            try:
                import pyperclip
                clipboard_text = pyperclip.paste()
            except (ImportError, Exception):
                pass
        
        if not clipboard_text:
            print("⚠️ Failed to read clipboard. Falling back to DOM scraping...")
            return None
        
        clipboard_text = clipboard_text.strip()
        
        if user_prompt_clean in clipboard_text or clipboard_text == user_prompt_clean:
            print("⚠️ Clipboard contains user prompt, not response. Falling back to DOM scraping...")
            return None
        
        if len(clipboard_text) < MIN_ACCEPT_CHARS:
            print("⚠️ Clipboard content too short. Falling back to DOM scraping...")
            return None
        
        prompt_keywords = [
            "Provide a complete and comprehensive company profile",
            "Return ONLY valid JSON",
            "Return ONLY the JSON object"
        ]
        if any(keyword in clipboard_text for keyword in prompt_keywords) and len(clipboard_text) < 500:
            print("⚠️ Clipboard appears to contain prompt text. Falling back to DOM scraping...")
            return None
        
        print("✅ Successfully copied response from clipboard!")
        return clipboard_text
        
    except Exception as e:
        print(f"⚠️ Error with copy button: {e}. Falling back to DOM scraping...")
        return None


async def scrape_gemini_response(page, timeout_ms=120000) -> str:
    """Scrape Gemini's response text from the UI, waiting until it stabilizes. (Fallback method)"""
    start = time.time()
    last_clean = ""
    stable_since = time.time()

    saved = []
    if os.path.exists(SELECTOR_MEMORY_FILE):
        try:
            with open(SELECTOR_MEMORY_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
        except:
            saved = []

    selectors_to_try = list(dict.fromkeys(saved + BASE_SELECTORS))
    successful = set()

    print("⏳ Waiting for Gemini AI response...")
    while (time.time() - start) * 1000 < timeout_ms:
        chunks = await collect_text_candidates(page, selectors_to_try)
        shadow = await deep_shadow_text(page)
        if shadow and len(shadow) > MIN_ACCEPT_CHARS and not looks_like_js_garbage(shadow):
            chunks.append(shadow)

        combined_raw = " ".join(dict.fromkeys(chunks))
        clean = strong_clean(combined_raw)
        clean = dedupe_sentences(clean)

        if chunks:
            for sel in selectors_to_try:
                try:
                    els = await page.query_selector_all(sel)
                    for el in els:
                        if not el or not await el.is_visible():
                            continue
                        t = await el.inner_text()
                        t = t.strip() if t else ""
                        if t and len(t) >= MIN_ACCEPT_CHARS and not looks_like_js_garbage(t):
                            successful.add(sel)
                            break
                except:
                    continue

        if len(clean) >= MIN_ACCEPT_CHARS:
            last_clean, stable_since, ok = stabilize_text(clean, last_clean, stable_since)
            if ok:
                print("✅ Gemini output stabilized.")
                if successful:
                    try:
                        with open(SELECTOR_MEMORY_FILE, "w", encoding="utf-8") as f:
                            json.dump(sorted(list(successful)), f, indent=2, ensure_ascii=False)
                        print(f"💾 Saved {len(successful)} working selectors.")
                    except:
                        pass

                final_text = clean.strip()
                final_text = re.sub(r"(?i)opens in a new window", "", final_text)
                final_text = re.sub(r"(?i)about gemini.*$", "", final_text)
                final_text = final_text.strip()
                
                prompt_indicators = [
                    "Provide a complete and comprehensive company profile",
                    "Return ONLY valid JSON",
                    "Return ONLY the JSON object"
                ]
                if any(indicator in final_text for indicator in prompt_indicators) and len(final_text) < 500:
                    print("⚠️ Detected prompt text in response. Waiting longer for actual response...")
                    await async_human_wait(3.0, 3.0)
                    continue

                return final_text

        await async_human_wait(1.0, 1.0)

    print("⚠️ No complete Gemini response detected (timeout). Returning best-effort text.")
    if last_clean:
        prompt_indicators = [
            "Provide a complete and comprehensive company profile",
            "Return ONLY valid JSON",
            "Return ONLY the JSON object"
        ]
        if any(indicator in last_clean for indicator in prompt_indicators) and len(last_clean) < 500:
            print("⚠️ Warning: Response appears to be prompt text, not actual response.")
    return last_clean


def extract_and_parse_json(response_text: str) -> Optional[Dict]:
    """Extract JSON from response text and parse it."""
    if not response_text:
        return None
    
    response_stripped = response_text.strip()
    
    if response_stripped.startswith('"') and '{' in response_stripped:
        try:
            parsed_string = json.loads(response_stripped)
            if isinstance(parsed_string, str):
                parsed = json.loads(parsed_string)
                if isinstance(parsed, dict) and any(key in parsed for key in ['What', 'When', 'Where', 'How', 'Who']):
                    return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    
    if response_stripped.startswith('{'):
        try:
            parsed = json.loads(response_stripped)
            if isinstance(parsed, dict) and any(key in parsed for key in ['What', 'When', 'Where', 'How', 'Who']):
                return parsed
        except json.JSONDecodeError:
            pass
    
    code_block_patterns = [
        r'```json\s*(\{.*?\})\s*```',
        r'```\s*(\{.*?\})\s*```',
    ]
    
    for pattern in code_block_patterns:
        match = re.search(pattern, response_text, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
            try:
                parsed = json.loads(json_str)
                if isinstance(parsed, dict) and any(key in parsed for key in ['What', 'When', 'Where', 'How', 'Who']):
                    return parsed
            except json.JSONDecodeError:
                continue
    
    if '"' in response_stripped and response_stripped.count('"') >= 2:
        first_quote = response_stripped.find('"')
        last_quote = response_stripped.rfind('"')
        if first_quote != -1 and last_quote != -1 and last_quote > first_quote:
            potential_escaped = response_stripped[first_quote:last_quote + 1]
            try:
                unescaped = json.loads(potential_escaped)
                if isinstance(unescaped, str) and unescaped.strip().startswith('{'):
                    parsed = json.loads(unescaped)
                    if isinstance(parsed, dict) and any(key in parsed for key in ['What', 'When', 'Where', 'How', 'Who']):
                        return parsed
            except (json.JSONDecodeError, TypeError):
                pass
    
    brace_count = 0
    start_idx = -1
    candidates = []
    
    for i, char in enumerate(response_text):
        if char == '{':
            if brace_count == 0:
                start_idx = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_idx != -1:
                json_str = response_text[start_idx:i + 1]
                candidates.append((start_idx, i + 1, json_str))
                start_idx = -1
    
    for start, end, json_str in candidates:
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict):
                if any(key in parsed for key in ['What', 'When', 'Where', 'How', 'Who']):
                    return parsed
        except json.JSONDecodeError:
            try:
                if json_str.startswith('"') and json_str.endswith('"'):
                    unescaped = json.loads(json_str)
                    if isinstance(unescaped, str):
                        parsed = json.loads(unescaped)
                        if isinstance(parsed, dict) and any(key in parsed for key in ['What', 'When', 'Where', 'How', 'Who']):
                            return parsed
            except (json.JSONDecodeError, TypeError):
                continue
    
    json_start = response_text.find('{')
    json_end = response_text.rfind('}')
    
    if json_start != -1 and json_end != -1 and json_end > json_start:
        json_str = response_text[json_start:json_end + 1]
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict) and any(key in parsed for key in ['What', 'When', 'Where', 'How', 'Who']):
                return parsed
        except json.JSONDecodeError:
            if json_start > 0:
                before_brace = response_text[:json_start].strip()
                if before_brace.endswith('"'):
                    quote_start = response_text.rfind('"', 0, json_start)
                    if quote_start != -1:
                        potential_escaped = response_text[quote_start:json_end + 2]
                        try:
                            unescaped = json.loads(potential_escaped)
                            if isinstance(unescaped, str) and unescaped.strip().startswith('{'):
                                parsed = json.loads(unescaped)
                                if isinstance(parsed, dict) and any(key in parsed for key in ['What', 'When', 'Where', 'How', 'Who']):
                                    return parsed
                        except (json.JSONDecodeError, TypeError, IndexError):
                            pass
    
    return None


def _run_playwright_sync(ticker: str) -> Optional[Dict]:
    """Run Playwright in a new event loop (for Windows compatibility)"""
    # Create new event loop with ProactorEventLoop policy for Windows
    if sys.platform == 'win32':
        policy = asyncio.WindowsProactorEventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(_fetch_company_profile_async(ticker))
    finally:
        loop.close()


async def fetch_company_profile_from_gemini(ticker: str) -> Optional[Dict]:
    """
    Launch Gemini browser, send company profile query, collect response.
    Returns parsed JSON dict or None.
    """
    # On Windows, check if we need to run in a separate thread with new event loop
    if sys.platform == 'win32':
        try:
            loop = asyncio.get_running_loop()
            # If current loop is not ProactorEventLoop, run in thread
            if not isinstance(loop, asyncio.ProactorEventLoop):
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(_run_playwright_sync, ticker)
                    return future.result()
        except RuntimeError:
            # No running loop, continue normally
            pass
    
    # Normal async execution (works if event loop policy is set correctly)
    return await _fetch_company_profile_async(ticker)


async def _fetch_company_profile_async(ticker: str) -> Optional[Dict]:
    """
    Internal async function to fetch company profile from Gemini.
    This is called by _run_playwright_sync for Windows compatibility.
    """
    # Ensure session directory exists
    os.makedirs(SESSION_PATH, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=SESSION_PATH,
            headless=HEADLESS,
            executable_path=CHROME_PATH if CHROME_PATH else None,
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
        )
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1366, "height": 768})
        print(f"🌐 Opening Gemini...")
        await page.goto("https://gemini.google.com/app", timeout=60000)
        await async_human_wait(2.0, 3.5)

        if "accounts.google.com" in (page.url or "").lower():
            print(f"⚠️ Please log in manually; session will persist.")
            # Note: In API context, we can't pause, so we'll wait a bit
            await async_human_wait(10.0, 10.0)

        query = f"""Provide a complete and comprehensive company profile for stock ticker {ticker} in JSON format. 

Return ONLY valid JSON with the following structure (no markdown, no code blocks, just pure JSON):

{{
  "What": {{
    "Sector": "sector name",
    "Industry": "industry name",
    "Niche": "niche or business focus",
    "Description": "detailed description of what the company does",
    "Products": "main products, services, or offerings (consolidated list)",
    "MarketPosition": "business category and market position",
    "Monetization": "how the company makes money (describe before revenue streams)",
    "RevenueStreams": "list of primary revenue streams with percentages or qualitative sizing"
  }},
  "When": {{
    "FoundedYear": "founded year",
    "FoundedDetails": "founding details",
    "IPODate": "IPO date if publicly traded",
    "KeyMilestones": "key milestones and growth timeline",
    "Acquisitions": "major acquisitions or expansions",
    "InvestmentTimeline": "chronological timeline of funding rounds, major investors, and amounts",
    "RecentEvents": [
      "Bullet 1 - most recent dated event",
      "Bullet 2 - next most recent event",
      "Bullet 3",
      "Bullet 4",
      "Bullet 5",
      "Bullet 6",
      "Bullet 7",
      "Bullet 8",
      "Bullet 9",
      "Bullet 10 - oldest of the recent set"
    ]
  }},
  "Where": {{
    "Headquarters": "full headquarters address",
    "City": "city",
    "State": "state/province",
    "Country": "country",
    "OperationalFootprint": "where they operate",
    "OfficeLocations": "key office locations or facilities",
    "GeographicPresence": "geographic presence"
  }},
  "How": {{
    "BusinessModel": "business model and how the company operates",
    "MarketStrategy": "go-to-market and customer acquisition strategy",
    "CompetitiveAdvantages": "competitive advantages or unique selling points",
    "OperationalHighlights": "key operational details, capacity, supply chain, or execution notes"
  }},
  "Who": {{
    "CEO": "current CEO name and title",
    "LeadershipTeam": "key leadership team members",
    "Founders": "founder(s) name(s) and background",
    "Investors": "complete list of major institutional and strategic investors with ownership info",
    "InstitutionalOwnership": "institutional ownership percentage if available",
    "MajorShareholders": "major shareholders or stakeholders",
    "BoardOfDirectors": "board of directors if available"
  }},
  "Sources": {{
    "URLs": ["list of URLs"],
    "References": ["list of references, articles, websites"]
  }}
}}

Provide factual, detailed, and comprehensive information about {ticker}. For the "RecentEvents" array, include exactly 10 bullet-style strings (most recent first), each summarizing a distinct recent development with dates if available. Return ONLY the JSON object, nothing else."""


        print(f"💬 Sending company profile query for {ticker}...")
        input_box = None

        for s in [
            "textarea[aria-label*='Message' i]",
            "textarea[aria-label*='Ask Gemini' i]",
            "textarea",
            "div[contenteditable='true']",
            "div[role='textbox']",
            "div[aria-label*='Message' i]",
            "div[aria-label*='Ask Gemini' i]",
            "input[aria-label*='Ask Gemini' i]",
        ]:
            try:
                el = await page.query_selector(s)
                if el and await el.is_visible():
                    input_box = el
                    break
            except:
                continue

        if not input_box:
            print(f"❌ Input box not found.")
            await browser.close()
            return None

        await human_click(page, input_box)
        await async_human_wait(0.3, 0.8)
        
        try:
            await input_box.fill("")
        except:
            pass
        
        try:
            await input_box.fill(query)
        except:
            try:
                await input_box.evaluate("""
                    (element, text) => {
                        element.focus();
                        element.innerHTML = '';
                        element.textContent = text;
                        const inputEvent = new Event('input', { bubbles: true });
                        element.dispatchEvent(inputEvent);
                        const changeEvent = new Event('change', { bubbles: true });
                        element.dispatchEvent(changeEvent);
                    }
                """, query)
            except:
                query_single_line = query.replace('\n', ' ')
                await human_type(input_box, query_single_line)
        
        await async_human_wait(0.5, 1.0)
        await page.keyboard.press("Enter")
        
        print("⏳ Waiting for Gemini to start generating response...")
        await async_human_wait(5.0, 8.0)

        response_text = await get_json_directly_from_dom(page, query)
        
        if not response_text:
            response_text = await get_response_via_copy_button(page, query)
        
        if not response_text:
            print("📋 Falling back to DOM scraping method...")
            response_text = await scrape_gemini_response(page)
            
            if query and query in response_text:
                response_text = response_text.replace(query, "").strip()
            
            prompt_keywords = [
                "Provide a complete and comprehensive company profile",
                "Return ONLY valid JSON",
                "Return ONLY the JSON object"
            ]
            for keyword in prompt_keywords:
                if keyword in response_text and len(response_text) < 500:
                    print("⚠️ Warning: Response may contain prompt text. Waiting longer...")
                    await async_human_wait(3.0, 5.0)
                    response_text = await scrape_gemini_response(page, timeout_ms=30000)
                    if query and query in response_text:
                        response_text = response_text.replace(query, "").strip()
                    break
        
        if response_text:
            print(f"📋 Response preview: {response_text[:200]}...")
            print(f"   Response length: {len(response_text)} chars")
        else:
            print("❌ Failed to get response from Gemini")
            print("⏳ Waiting a bit more in case response is still generating...")
            await async_human_wait(5.0, 8.0)
            response_text = await scrape_gemini_response(page, timeout_ms=30000)
            if not response_text:
                print("❌ Still no response after extended wait. Closing browser.")
                await browser.close()
                return None
        
        await browser.close()
        print(f"✅ Company profile extracted for {ticker}")
        
        # Parse JSON from response
        cleaned_response = response_text.strip()
        
        prompt_keywords = [
            "Provide a complete and comprehensive company profile",
            "Return ONLY valid JSON",
            "Return ONLY the JSON object",
            "with the following structure",
            "no markdown, no code blocks"
        ]
        for keyword in prompt_keywords:
            if keyword in cleaned_response:
                keyword_pos = cleaned_response.find(keyword)
                json_start = cleaned_response.find('{', keyword_pos)
                if json_start != -1:
                    cleaned_response = cleaned_response[json_start:]
                    break
                lines = cleaned_response.split('\n')
                cleaned_response = '\n'.join([line for line in lines if keyword not in line])
        
        parsed_json = None
        try:
            parsed_json = json.loads(cleaned_response)
            if isinstance(parsed_json, dict):
                if "Response" in parsed_json and len(parsed_json) <= 3:
                    inner_response = parsed_json.get("Response", "")
                    if isinstance(inner_response, str):
                        try:
                            parsed_json = json.loads(inner_response)
                        except:
                            if inner_response.strip().startswith('"') and inner_response.strip().endswith('"'):
                                unescaped = json.loads(inner_response.strip())
                                if isinstance(unescaped, str):
                                    parsed_json = json.loads(unescaped)
        except (json.JSONDecodeError, TypeError):
            pass
        
        if not parsed_json:
            try:
                if cleaned_response.startswith('"') and cleaned_response.endswith('"'):
                    unescaped = json.loads(cleaned_response)
                    if isinstance(unescaped, str) and unescaped.strip().startswith('{'):
                        parsed_json = json.loads(unescaped)
            except (json.JSONDecodeError, TypeError):
                pass
        
        if not parsed_json:
            try:
                cleaned = cleaned_response.replace('\\r\\n', '\n').replace('\\n', '\n')
                parsed_json = json.loads(cleaned)
            except (json.JSONDecodeError, TypeError):
                pass
        
        if parsed_json and isinstance(parsed_json, dict):
            expected_keys = ['What', 'When', 'Where', 'How', 'Who']
            found_keys = [key for key in expected_keys if key in parsed_json]
            
            if len(found_keys) < 3:
                brace_start = cleaned_response.find('{')
                if brace_start != -1:
                    brace_count = 0
                    brace_end = -1
                    for i in range(brace_start, len(cleaned_response)):
                        if cleaned_response[i] == '{':
                            brace_count += 1
                        elif cleaned_response[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                brace_end = i
                                break
                    if brace_end != -1:
                        complete_json_str = cleaned_response[brace_start:brace_end + 1]
                        try:
                            complete_json = json.loads(complete_json_str)
                            if isinstance(complete_json, dict):
                                complete_found_keys = [key for key in expected_keys if key in complete_json]
                                if len(complete_found_keys) > len(found_keys):
                                    print(f"✅ Found more complete JSON with {len(complete_found_keys)} sections")
                                    parsed_json = complete_json
                                    found_keys = complete_found_keys
                        except:
                            pass
            
            return parsed_json
        else:
            parsed_json = extract_and_parse_json(cleaned_response)
            if parsed_json:
                return parsed_json
            
            brace_starts = []
            for i, char in enumerate(cleaned_response):
                if char == '{':
                    brace_starts.append(i)
            
            parsed_json = None
            json_candidates = []
            
            for brace_start in brace_starts:
                brace_count = 0
                brace_end = -1
                for i in range(brace_start, len(cleaned_response)):
                    if cleaned_response[i] == '{':
                        brace_count += 1
                    elif cleaned_response[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            brace_end = i
                            break
                
                if brace_end != -1:
                    json_str = cleaned_response[brace_start:brace_end + 1]
                    if len(json_str) < 100:
                        continue
                    
                    try:
                        candidate_json = json.loads(json_str)
                        if isinstance(candidate_json, dict):
                            json_candidates.append((len(json_str), candidate_json, json_str))
                    except:
                        try:
                            json_str_clean = json_str.replace('\\r\\n', '\n').replace('\\n', '\n')
                            candidate_json = json.loads(json_str_clean)
                            if isinstance(candidate_json, dict):
                                json_candidates.append((len(json_str_clean), candidate_json, json_str_clean))
                        except:
                            pass
            
            json_candidates.sort(reverse=True, key=lambda x: x[0])
            
            expected_keys = ['What', 'When', 'Where', 'How', 'Who']
            for size, candidate_json, json_str in json_candidates:
                if all(key in candidate_json for key in expected_keys):
                    parsed_json = candidate_json
                    break
                elif sum(1 for key in expected_keys if key in candidate_json) >= 4:
                    parsed_json = candidate_json
                    break
            
            if not parsed_json and json_candidates:
                parsed_json = json_candidates[0][1]
            
            return parsed_json

