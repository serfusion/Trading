@echo off
set OPENROUTER_API_KEY=ISI_API_KEY_OPENROUTER_SENDIRI

litellm --model openrouter/deepseek/deepseek-r1-0528:free \
  --api_base https://openrouter.ai/api/v1 \
  --api_key %OPENROUTER_API_KEY% \
  --port 4000