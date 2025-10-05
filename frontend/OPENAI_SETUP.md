# OpenAI Setup for Swiss Corp Assistant

## Quick Setup (3 steps)

### 1. Install OpenAI Package
```bash
cd frontend
pip install openai
```

### 2. Get Your OpenAI API Key
- Go to: https://platform.openai.com/api-keys
- Create a new API key
- Copy the key (starts with `sk-...`)

### 3. Set the API Key
Choose one option:

**Option A: Environment Variable (Recommended)**
```bash
export OPENAI_API_KEY='sk-your-actual-key-here'
```

**Option B: Create .env file**
```bash
echo 'OPENAI_API_KEY=sk-your-actual-key-here' > frontend/.env
```

**Option C: Add to your shell profile**
```bash
echo 'export OPENAI_API_KEY="sk-your-actual-key-here"' >> ~/.zshrc
source ~/.zshrc
```

### 4. Restart the App
```bash
cd frontend
uv run python3 -m src.app
```

## Verification

The chat assistant will show:
- ✅ "Swiss Corp Assistant" with real AI responses (if OpenAI is working)
- 🔧 Setup instructions (if OpenAI package missing)
- 🔑 API key instructions (if key not set)
- 🤖 Intelligent fallback responses (if OpenAI unavailable but app works)

## Troubleshooting

**"OpenAI package not installed"**
- Run: `pip install openai`

**"API Key Missing"**
- Set OPENAI_API_KEY environment variable
- Restart the app after setting the key

**"AI service connection trouble"**
- Check your API key is valid
- Verify you have OpenAI credits
- Check internet connection

## Cost Information

- Using GPT-4o-mini (cost-effective model)
- Typical cost: ~$0.001 per conversation
- 300 token limit per response (keeps costs low)

The assistant works with intelligent fallback responses even without OpenAI!