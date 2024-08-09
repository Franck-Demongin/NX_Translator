import os
import json

from server import PromptServer
import asyncio
import aiohttp
from aiohttp import web

base_path = os.path.dirname(os.path.realpath(__file__))

# decorator used for create routes from/to server
routes = PromptServer.instance.routes

# DeepL rest API URL and endpoints
DEEPL_API = "https://api.deepl.com/v2/"
DEEPL_FREE_API = "https://api-free.deepl.com/v2/"
DEEPL_TRANSLATE = "translate"
DEEPL_USAGE = "usage"

# DeepL token environment variable
DEEPL_TOKEN = "DEEPL_TOKEN"

# Google translate API URL
GOOGLE_API = "https://translate.googleapis.com/translate_a/single"

def read_token():
    env_path = os.path.join(base_path, ".env")
    if os.access(env_path, os.R_OK):
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith(DEEPL_TOKEN):
                    token = line.split("=")[1].strip()
                    if len(token) == 0:
                        return None
                    return token
        return None

def write_token(token):
    env_path = os.path.join(base_path, ".env")
    if os.path.isfile(env_path):
        os.remove(os.path.join(base_path, ".env"))
    with open(os.path.join(base_path, ".env"), "w") as f:
        f.write(f"DEEPL_TOKEN={token}")

class DeepL:
    ''' Classe DeepL
    DeepL API wrapper, used to translate text in english
    Args: token (str): DeepL API token
    Constants: DEEPL_API, DEEPL_FREE_API, DEEPL_USAGE, DEEPL_TRANSLATE
    '''
    def __init__(self, token:str=None) -> None:
        self.api_url = DEEPL_API
        self.api_free_url = DEEPL_FREE_API
        self.endpoint_usage = DEEPL_USAGE
        self.endpoint_translate = DEEPL_TRANSLATE
        self._token = token
        self._url = asyncio.run(self._get_url())
    
    def _headers(self):
        if self._token is None:
            return {}        
        return {
            "Authorization": f"DeepL-Auth-Key {self._token}",
            "Content-Type": "application/json"
        }
    
    async def _get_url(self):
        if self._token is None:
            return None        
        async with aiohttp.ClientSession() as session:            
            url = f"{self.api_url}{self.endpoint_usage}"
            async with session.get(url, headers=self._headers()) as response:
                if response.status == 200: 
                    return self.api_url            
            url = f"{self.api_free_url}{self.endpoint_usage}"
            async with session.get(url, headers=self._headers()) as response:
                if response.status == 200: 
                    return self.api_free_url            
            return None
    
    async def _usage(self):
        if not self.is_valid():
            return None        
        async with aiohttp.ClientSession() as session:
            url = f"{self._url}{self.endpoint_usage}"            
            async with session.get(url, headers=self._headers()) as response:
                if response.status == 200: 
                    usage = await response.json()
                    return usage["character_count"], usage["character_limit"]            
            return None
    
    async def _translate(self, prompt):
        if not self.is_valid():
            return None        
        async with aiohttp.ClientSession() as session:
            url = f"{self._url}{self.endpoint_translate}" 
            data = {"text": [prompt], "target_lang": "EN-GB"}
            async with session.post(url, headers=self._headers(), json=data) as response:
                if response.status == 200: 
                    translation = await response.json()
                    return translation['translations'][0]['text']            
            return None
    
    def is_valid(self):
        return self._url is not None
    
    def get_token(self):
        return self._token
    
    def get_url(self):
        return self._url
    
    async def set_token(self, token=""):
        if token == "":
            token = None
        self._token = str(token)
        self._url = await self._get_url()
        return self._url

    def usage(self):
        return self._usage()
    
    def translate(self, prompt):
        return self._translate(prompt)


deepl = DeepL(read_token())

class GoogleTranslate:
    def __init__(self, translate_from, translate_to):
        self.payload = {
            "client": "gtx",
            "dt": "t",
            "sl": translate_from,
            "tl": translate_to,
            "q": ""
        }

    async def _translate(self):
        async with aiohttp.ClientSession() as session:
            url = GOOGLE_API
            async with session.post(url, data=self.payload) as response:
                if response.status== 200: 
                    translation = await response.json()
                    return translation[0][0][0]          
            return None
        
    def translate(self, prompt):
        self.payload['q'] = prompt

        return self._translate()

google_translator = GoogleTranslate("auto", "en")

@routes.get('/deeplgettoken')
async def get_token(request):
    resp = {'token': deepl.get_token()}
    return web.Response(body=json.dumps(resp), content_type='application/json')

@routes.post('/deeplsettoken')
async def set_token(request):
    post = await request.json()
    write_token(post['token'])
    await deepl.set_token(post['token'])    
    resp = {'saved': True}
    return web.Response(body=json.dumps(resp), content_type='application/json')

@routes.get('/deeplusage')
async def usage(request):
    if not deepl.is_valid():
        resp = {'used': None}
    else:
        resp = {'used': await deepl.usage()}
    return web.Response(body=json.dumps(resp), content_type='application/json')

@routes.post('/deepltranslate')
async def deepl_translate(request):
    print("Call to DEEPL...")
    post = await request.json()
    if deepl.get_token() is None:
        resp = {
            'text': "No token provided",
            'token_valid': False
        }
    elif not deepl.is_valid():
        resp = {
            'text': "Invalid token",
            'token_valid': False
        }
    else:
        result = await deepl.translate(post['prompt'])
        resp = {
            'text': f"{result}",
            'token_valid': deepl.is_valid()
        }        
    return web.Response(body=json.dumps(resp), content_type='application/json')

@routes.post('/googletranslate')
async def google_translate(request):
    print("Call to GOOGLE...")
    post = await request.json()
    prompt = post['prompt']
    prompt = prompt.replace("\n", "[NL]")
    prompt = prompt.replace(".", "[.]")
    result = await google_translator.translate(prompt)
    result = result.replace("[NL]", "\n")
    result = result.replace("[.]", ".")
    resp = {
        'text': f"{result}",
        'token_valid': deepl.is_valid()
    }        
    return web.Response(body=json.dumps(resp), content_type='application/json')
        
class Nx_Translator:
    '''
    Translate prompt in english with DeepL Translate
    '''
    translators = ["Google Translate", "DeepL"]
    mode = ["replace", "append", "prepend"]
    sep = ["comma", "space", "newline", "none"]
    
    def __init__(self) -> None:
        pass    

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "translator": (s.translators, {"default": "Google Translate"}),
                "mode": (s.mode, {"default": "replace"}),
                "sep": (s.sep, {"default": "comma"}),
                "prompt": ("STRING", {"multiline": True}),
                "text": ("STRING", {"multiline": True}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("translation",)
    FUNCTION = "run"
    OUTPUT_NODE = True

    CATEGORY = "NX_Nodes"

    def run(self, translator='', mode='', sep='', prompt='', text=''):             
        return {"result": (text,)}


WEB_DIRECTORY = "js"

NODE_CLASS_MAPPINGS = {
    "Nx_Translator": Nx_Translator
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Nx_Translator": "♻ Translator"
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]