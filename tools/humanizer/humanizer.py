import os
import base64
import random
import time
import threading
from pathlib import Path
from typing import Optional, Any, List

from core.token_parser import TokenEntry
from core.proxy_manager import ProxyEntry
from core.discord_api import DiscordAPI, ApiErrorType, connect_to_gateway
from core.logger import AppLogger
from tools.base_tool import BaseTool

class Humanizer(BaseTool):
    """
    Humanizer Tool — Make Discord tokens appear like real humans.
    """
    
    TOOL_NAME = "humanizer"
    
    DISPLAY_NAMES_EN = [
        'Alex', 'Jordan', 'Sam', 'Charlie', 'Morgan', 'Riley', 'Casey', 'Quinn', 'Avery', 'Taylor', 'Dakota', 'River', 'Skyler', 'Sage', 'Phoenix', 'Blake', 'Jamie', 'Rowan', 'Harper', 'Emerson', 'Finley', 'Hayden', 'Kendall', 'Logan', 'Parker', 'Reese', 'Sydney', 'Spencer', 'Adrian', 'Cameron', 'Devon', 'Ellis', 'Gray', 'Haven', 'Indie', 'Jules', 'Kai', 'Lane', 'Mika', 'Nova', 'Oakley', 'Peyton', 'Ray', 'Scout', 'Tatum', 'Val', 'Wren', 'Zion', 'Luna', 'Aria', 'Stella', 'Ivy', 'Aurora', 'Violet', 'Hazel', 'Jade', 'Lyric', 'Eden', 'Astrid', 'Ember', 'Winter', 'Storm', 'Cloud', 'Zen', 'Max', 'Leo', 'Milo', 'Felix', 'Oscar', 'Theo', 'Hugo', 'Ezra', 'Arlo', 'Jasper', 'Atlas', 'Orion', 'Axel', 'Rex', 'Neo', 'Zane', 'Chloe', 'Sophia', 'Liam', 'Noah', 'Emma', 'Olivia', 'Ethan', 'Aiden', 'Mason', 'Lucas', 'Ella', 'Mia', 'James', 'Benjamin', 'Amelia', 'Charlotte', 'Henry', 'Jack', 'Daniel', 'Grace', 'Lily', 'Nora', 'Ellie', 'Hannah', 'Scarlett', 'Zoey', 'Penelope', 'Layla', 'Nate', 'Caleb', 'Ryan', 'Owen', 'Dylan', 'Nathan', 'Hunter', 'Tyler', 'Luke', 'Isaac', 'Evan', 'Connor', 'Savannah', 'Madelyn', 'Alice', 'Claire', 'Ruby', 'Sadie', 'Willow', 'Piper', 'kira', 'yuki', 'ren', 'haru', 'sora', 'niko', 'kai', 'rio', 'ace', 'blaze', 'echo', 'frost', 'ghost', 'hawk', 'jett', 'rogue', 'shadow', 'stark', 'viper', 'wolf', 'cyber', 'pixel', 'glitch', 'neon'
    ]
    
    DISPLAY_NAMES_AR = [
        'أحمد', 'محمد', 'عبدالله', 'فهد', 'خالد', 'سلطان', 'عمر', 'سعود', 'نايف', 'ياسر', 'طارق', 'ماجد', 'بدر', 'سلمان', 'عادل', 'مشاري', 'سارة', 'نورة', 'لينا', 'دانة', 'ريم', 'هند', 'لمى', 'غادة', 'ديمة', 'العنود', 'مها', 'جود', 'تالا', 'يارا', 'رزان', 'وعد', 'آسر', 'ليان', 'رند', 'فيصل', 'راكان', 'تركي', 'عبدالرحمن', 'صالح', 'حمد', 'زياد', 'إبراهيم', 'علي', 'حسن', 'كريم', 'أمير', 'وليد', 'منيرة', 'أمل', 'شهد', 'حلا', 'نور', 'ملاك', 'بتول', 'لارا'
    ]
    
    BIOS_EN = [
        'just vibing', 'living my best life', 'coffee enthusiast', 'music is life', 'adventure awaits', 'night owl', 'gamer at heart', 'dreamer & doer', 'keeping it real', 'exploring the world', 'art & creativity', 'tech nerd', 'book lover', 'fitness journey', 'sunset chaser', 'positive vibes only', 'work hard play harder', 'stay curious', 'food lover', 'photography', 'learning everyday', 'making memories', 'simple life', 'create & inspire', 'beach vibes', 'nature lover', 'anime fan', 'dog person', 'cat person', 'music producer', 'digital nomad', 'artist', 'coder', 'stay humble', 'level up', 'good times only', 'wanderlust', 'plant parent', 'movie buff', 'rainy days & hot chocolate', 'stargazer', 'retro gaming', '404 bio not found', 'loading...', 'brb touching grass', 'chronically online', 'send memes', 'i like turtles', 'according to all known laws of aviation...', 'just a silly goose', 'probably napping', 'professional overthinker', 'chaotic neutral', 'main character energy', 'no thoughts head empty', 'its giving vibes', 'ctrl+alt+defeat', 'error 404: sleep not found', 'i code, therefore i am', 'plot twist enthusiast', 'collecting moments not things', 'secretly a wizard', 'fueled by caffeine and chaos', 'touch grass speedrunner', '90% sarcasm', 'trust the process'
    ]
    
    BIOS_AR = [
        'الحمدلله', 'مزاجي', 'عاشق القهوة', 'الحياة حلوة', 'ابتسم', 'حياتي بسيطة', 'لا شيء مستحيل', 'كن جميلا ترى الوجود جميلا', 'ما أجمل أن تبدأ من جديد', 'الصمت لغة العظماء', 'في طريقي', 'قلب أبيض', 'كلمة طيبة صدقة', 'اسأل الله التوفيق', 'يا رب', 'هدوء', 'عيش اللحظة', 'بالتوفيق', 'لا تستسلم', 'الله يسعدكم', 'أحب الخير للناس'
    ]
    
    BIOS_EMOJIS = [
        '✌️', '✨', '☕', '☁️', '☀️', '⭐', '🌙', '❄️', '⚓', '⚔️', '⛩️', '⛰️', '☄️', '⌚', '⌨️', '⚽', '⚾', '⛳', '⛹️', '⛸️', '⛷️', '⛹️', '⚔️', '⚡', '⏳', '⏰', '⚖️', '✈️', '⛵', '⚓', '⛽', '⛲', '⛺', '⛅', '⛈️', '⛱️', '⛲', '⛺', '⛅', '⛈️', '⛱️', '⛲', '⛺', '⛅', '⛈️', '⛱️', '⛲', '⛺', '⛅', '⛈️', '⛱️', '⛲'
    ]

    SUPPORTED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}

    def __init__(self, log_callback=None):
        super().__init__(log_callback=log_callback)
        self._pfp_images: List[str] = []
        self._pfp_index = 0
        self._pfp_cache = {}
        self._patch_lock = threading.Lock()
        self._last_patch_time = 0

    def load_pfp_images(self, folder_path: str):
        """Load profile picture images from a folder."""
        self._pfp_images = []
        path = Path(folder_path)
        if not path.exists():
            self._logger.warning(f"PFP folder not found: {folder_path}")
            return
            
        for file in path.iterdir():
            if file.suffix.lower() in self.SUPPORTED_IMAGE_EXTENSIONS:
                self._pfp_images.append(str(file))
        
        random.shuffle(self._pfp_images)
        if self._pfp_images:
            self._logger.info(f"Loaded {len(self._pfp_images)} PFP images from {folder_path}")
        else:
            self._logger.info(f"No images found in {folder_path}")
        
        return self._pfp_images

    def _get_next_pfp(self) -> Optional[str]:
        """Get the next PFP image path (cycles through the list)."""
        if not self._pfp_images:
            return None
        path = self._pfp_images[self._pfp_index % len(self._pfp_images)]
        self._pfp_index += 1
        return path

    def _image_to_base64(self, image_path: str) -> Optional[str]:
        """Convert an image file to a Discord-compatible base64 string."""
        if image_path in self._pfp_cache:
            return self._pfp_cache[image_path]
            
        try:
            with open(image_path, "rb") as f:
                data = f.read()
                b64 = base64.b64encode(data).decode('utf-8')
                res = f"data:image/png;base64,{b64}"
                self._pfp_cache[image_path] = res
                return res
        except Exception as e:
            self._logger.error(f"Failed to encode image: {str(e)}")
            return None

    def _random_display_name(self) -> str:
        """Generate a diverse display name."""
        name = random.choice(self.DISPLAY_NAMES_EN + self.DISPLAY_NAMES_AR)
        if random.random() > 0.8:
            suffix = random.choice(['_', '.', 'x', '-', '~', '!', '^'])
            name = f"{name}{suffix}{random.randint(1, 999)}"
        return name

    def _human_delay(self, action_type: str = "normal") -> float:
        """Generate a human-like delay."""
        if action_type == "short":
            return random.uniform(0.2, 0.7)
        elif action_type == "medium":
            return random.uniform(0.3, 0.8)
        elif action_type == "long":
            return random.uniform(1.0, 2.0)
        elif action_type == "api_retry":
            return random.uniform(3.0, 7.0)
        return random.uniform(0.1, 0.4)

    def process_token(self, token_entry: TokenEntry, **kwargs) -> dict:
        proxy_rotator = kwargs.get('proxy_rotator')
        set_avatar = kwargs.get('set_avatar', False)
        set_display_name = kwargs.get('set_display_name', False)
        set_bio = kwargs.get('set_bio', False)
        cancel_event = kwargs.get('worker_cancel_event')
        
        fixed_name = kwargs.get('fixed_name', "")
        fixed_bio = kwargs.get('fixed_bio', "")
        use_single_pfp = kwargs.get('use_single_pfp', False)
        
        if not (set_avatar or set_display_name or set_bio):
            return {"success": False, "message": "No changes selected"}

        token = token_entry.token
        token_line = token_entry.raw_line
        short = f"{token[:20]}..."
        self.log(token, f"Processing [{short}]", "INFO")

        # 1. Validation & Setup
        proxy = proxy_rotator.get_proxy() if proxy_rotator else None
        api = DiscordAPI(token=token, proxy=proxy)
        
        check_resp = api.get_user_info()
        if not check_resp.success:
            if check_resp.error_type == ApiErrorType.UNAUTHORIZED:
                self.log(token, f"Invalid token [{short}]", "ERROR")
                self.append_to_file("INVALID", token_line, "Result")
                return {"success": False, "status": "invalid", "message": "Invalid Token"}
            if check_resp.error_type == ApiErrorType.FORBIDDEN:
                self.log(token, f"Token locked/forbidden [{short}]", "ERROR")
                self.append_to_file("LOCKED", token_line, "Result")
                return {"success": False, "status": "locked", "message": "Locked/Forbidden"}
            if check_resp.is_rate_limited():
                return {"success": False, "retry_later": True, "status": "rate_limited", "message": "Rate limited during validation"}
            
            return {"success": False, "retry_later": True, "status": "network_error", "message": "Validation timeout"}

        if cancel_event and cancel_event.is_set():
            return {"success": False, "message": "Cancelled", "status": "cancelled"}

        # 2. Gateway Connection (simulate activity)
        # We try to connect to gateway to establish a session
        # This helps in some cases to avoid instant captchas
        try:
            api.connect_to_gateway()
            time.sleep(0.5)
        except:
            pass

        # 3. Build Actions
        actions = []
        if set_display_name:
            name = fixed_name if fixed_name else self._random_display_name()
            actions.append(("Display Name", lambda a, t=name: a.update_profile(display_name=t), name))
        
        if set_bio:
            bio = fixed_bio if fixed_bio else random.choice(self.BIOS_EN + self.BIOS_AR)
            if random.random() > 0.5:
                bio += f" {random.choice(self.BIOS_EMOJIS)}"
            actions.append(("Bio", lambda a, t=bio: a.update_profile(bio=t), bio))
            
        if set_avatar:
            pfp_path = self._get_next_pfp()
            if pfp_path:
                avatar_b64 = self._image_to_base64(pfp_path)
                if avatar_b64:
                    actions.append(("Avatar", lambda a, t=avatar_b64: a.update_profile(avatar=t), "Set"))

        random.shuffle(actions)
        
        applied = []
        had_failure = False
        last_error = ""
        
        # 4. Execute Actions
        for action_name, action_func, success_text in actions:
            if cancel_event and cancel_event.is_set():
                break
                
            time.sleep(self._human_delay("medium"))
            
            # Use global lock for PATCH actions to prevent spamming from multiple threads
            with self._patch_lock:
                now = time.time()
                elapsed = now - self._last_patch_time
                if elapsed < 0.3:
                    time.sleep(0.3 - elapsed)
                
                resp = action_func(api)
                self._last_patch_time = time.time()

            if resp.success:
                applied.append(f"{action_name}: {success_text[:25]}")
            else:
                had_failure = True
                last_error = resp.error_message or "Unknown"
                if resp.is_rate_limited():
                    self.log(token, f"Rate limited on {action_name} — requeuing", "WARNING")
                    return {"success": False, "retry_later": True, "status": "rate_limited", "message": f"Rate limited on {action_name}"}
                if resp.error_type == ApiErrorType.CAPTCHA_REQUIRED:
                    self.log(token, f"Captcha on {action_name} — requeuing", "WARNING")
                    return {"success": False, "retry_later": True, "status": "captcha", "message": "Captcha Required"}
                
                self.log(token, f"{action_name} failed: {last_error}", "ERROR")

        # 5. Finalize
        if applied:
            status = "humanized" if not had_failure else "partial"
            msg = f"Humanized [{short}] — {' | '.join(applied)}"
            if had_failure:
                msg += f" (partial failure: {last_error})"
            
            self.append_to_file("HUMANIZED", f"{token_line} | {msg}", "Result")
            self.log(token, msg, "SUCCESS" if not had_failure else "WARNING")
            return {"success": not had_failure, "status": status, "message": msg}
        else:
            msg = f"All updates failed for [{short}] | Reason: {last_error}"
            self.log(token, msg, "ERROR")
            return {"success": False, "status": "failed", "message": msg}

    def reset(self):
        """Clear output files for a fresh run."""
        self.clear_output()
        self._pfp_index = 0
        self._pfp_cache.clear()

