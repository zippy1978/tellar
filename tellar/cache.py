from gptcache import Cache
from gptcache.manager.factory import manager_factory
from gptcache.processor.pre import get_prompt
from langchain_community.cache import GPTCache
import hashlib
import langchain
import os


def init_cache(cache_path: str):
    def init_gptcache(cache_obj: Cache, llm: str):
        hashed_llm = hashlib.sha256(llm.encode()).hexdigest()
        cache_obj.init(
            pre_embedding_func=get_prompt,
            data_manager=manager_factory(
                manager="map", data_dir=os.path.join(cache_path, f"map_cache_{hashed_llm}")),
        )
    langchain.llm_cache = GPTCache(init_gptcache)
