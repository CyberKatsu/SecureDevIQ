# Openrouter AI Provider Guide

> Use SecureDevIQ with 100+ LLM models via [Openrouter.ai](https://openrouter.ai/)

## What is Openrouter?

[Openrouter](https://openrouter.ai/) is a unified API gateway that provides access to dozens of Large Language Models, including:

- **OpenAI**: GPT-4, GPT-4 Turbo, GPT-3.5
- **Anthropic**: Claude 3 (Opus, Sonnet, Haiku)
- **Meta**: Llama 2
- **Mistral**: Mistral 7B, Mistral Large
- **Open-source models**: And many more

This allows you to:
- **Try different models** without rewriting code
- **Optimize costs** by choosing cheaper models
- **Use open-source alternatives** to proprietary APIs
- **Switch models dynamically** by changing one environment variable

---

## Setup

### 1. Get an Openrouter API Key

1. Visit [openrouter.ai](https://openrouter.ai/)
2. Click **"Sign Up"** (or login if you have an account)
3. Go to **"Keys"** (in the top navigation or [here](https://openrouter.ai/keys))
4. Click **"Create Key"**
5. Copy your API key (starts with `sk-or-`)

### 2. Configure `.env`

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-YOUR_KEY_HERE
OPENROUTER_MODEL=openai/gpt-4-turbo    # See "Available Models" below
SECRET_KEY=$(openssl rand -hex 32)     # Generate a strong secret
```

### 3. Start the Application

```bash
docker compose up --build
```

Open **http://localhost:5173** and you're ready to go!

---

## Available Models

### Recommended (Best Balance)

| Model | Provider | Price | Speed | Quality | Use Case |
|-------|----------|-------|-------|---------|----------|
| `openai/gpt-4-turbo` | OpenAI | $$ | Fast | Excellent | Default; recommended |
| `anthropic/claude-3-sonnet` | Anthropic | $ | Fast | Excellent | Good alternative to GPT-4 |
| `openai/gpt-3.5-turbo` | OpenAI | $ | Fastest | Good | Budget-friendly option |
| `meta-llama/llama-2-70b-chat` | Meta | $ | Medium | Good | Open-source alternative |

### Most Capable (Higher Cost)

| Model | Provider | Price | Speed | Quality |
|-------|----------|-------|-------|---------|
| `openai/gpt-4` | OpenAI | $$$ | Medium | Best |
| `anthropic/claude-3-opus` | Anthropic | $$$ | Medium | Best |
| `mistralai/mistral-large` | Mistral | $$ | Medium | Very Good |

### Budget-Friendly (Lower Cost)

| Model | Provider | Price | Speed | Quality |
|-------|----------|-------|-------|---------|
| `openai/gpt-3.5-turbo` | OpenAI | $ | Very Fast | Good |
| `meta-llama/llama-2-70b-chat` | Meta | $ | Fast | Good |
| `nousresearch/nous-hermes-2-mixtral-8x7b` | Nous Research | $ | Fast | Good |

### Full Model List

See [openrouter.ai/docs/models](https://openrouter.ai/docs/models) for the complete list of 100+ supported models.

---

## Usage Examples

### Example 1: Use GPT-4 Turbo (Default)

```dotenv
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-xxx
OPENROUTER_MODEL=openai/gpt-4-turbo
```

### Example 2: Use Claude 3 Sonnet (Good Alternative)

```dotenv
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-xxx
OPENROUTER_MODEL=anthropic/claude-3-sonnet
```

### Example 3: Use GPT-3.5 Turbo (Budget Option)

```dotenv
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-xxx
OPENROUTER_MODEL=openai/gpt-3.5-turbo
```

### Example 4: Use Llama 2 (Open Source)

```dotenv
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-xxx
OPENROUTER_MODEL=meta-llama/llama-2-70b-chat
```

---

## Switching Between AI Providers

You can easily switch between Anthropic, Qwen, and Openrouter:

### Switch from Anthropic to Openrouter

**Before:**
```dotenv
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxx
```

**After:**
```dotenv
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-xxx
OPENROUTER_MODEL=openai/gpt-4-turbo
```

Then restart:
```bash
docker compose restart backend
```

### Switch from Openrouter to Anthropic

```dotenv
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxx
```

Then restart:
```bash
docker compose restart backend
```

---

## Pricing & Credits

### Free Trial

Openrouter provides **free credits** (~$5 USD) when you first sign up to try the API.

### Pricing Model

You pay **per 1M tokens** (input and output combined):

| Model | Input | Output |
|-------|-------|--------|
| GPT-4 Turbo | $10 | $30 |
| Claude 3 Sonnet | $3 | $15 |
| GPT-3.5 Turbo | $0.50 | $1.50 |
| Llama 2 70B | $0.70 | $0.90 |

**Example**: Generating 10 challenges and 10 evaluations (assuming ~500 tokens per request):
- **GPT-4 Turbo**: ~$0.10 USD
- **Claude 3 Sonnet**: ~$0.03 USD
- **GPT-3.5 Turbo**: ~$0.01 USD

### Billing & Account

- Set up billing at [openrouter.ai/account/billing/overview](https://openrouter.ai/account/billing/overview)
- View your usage at [openrouter.ai/account/usage](https://openrouter.ai/account/usage)
- Set spending limits to control costs

---

## Troubleshooting

### Issue: "Invalid API Key"

**Check:**
1. API key starts with `sk-or-` (not `sk-ant-` or other prefixes)
2. Copied the full key without extra spaces
3. Set `AI_PROVIDER=openrouter` (not `anthropic` or `qwen`)

**Fix:**
```bash
docker compose logs backend | grep -i openrouter
```

### Issue: "Model not found"

**Check:**
1. Model name is correct from [openrouter.ai/docs/models](https://openrouter.ai/docs/models)
2. Model is spelled exactly right in `OPENROUTER_MODEL`
3. Model is available (some are rate-limited or deprecated)

**Example:**
```dotenv
OPENROUTER_MODEL=openai/gpt-4-turbo  # ✅ Correct
OPENROUTER_MODEL=openai/gpt-4        # ❌ Different model
```

### Issue: "Out of quota" or "Rate limited"

**Causes:**
- You've exhausted your free credits
- You've hit a rate limit (too many requests too fast)
- Model is temporarily unavailable

**Fix:**
1. Add billing to your Openrouter account
2. Switch to a cheaper model temporarily
3. Wait a few minutes if rate-limited
4. Check [openrouter.ai/status](https://openrouter.ai/status) for incidents

---

## Comparing Models

### Challenge Generation Quality

All models produce good challenges, but:
- **GPT-4**: Most creative and detailed scenarios
- **Claude 3 Sonnet**: Excellent balance of quality and speed
- **GPT-3.5**: Good but less creative
- **Llama 2**: Simpler challenges, good for basic training

### Evaluation Quality

All models score submissions fairly, but:
- **GPT-4**: Most thorough feedback
- **Claude 3 Sonnet**: Thoughtful, educational explanations
- **GPT-3.5**: Adequate scores but less detailed
- **Llama 2**: May miss subtle vulnerabilities

### Speed (Latency)

| Model | Generation | Evaluation |
|-------|------------|-----------|
| GPT-3.5 | ~2s | ~2s |
| Llama 2 | ~3s | ~3s |
| Claude 3 Sonnet | ~3s | ~3s |
| GPT-4 Turbo | ~5s | ~5s |

---

## Cost Optimization

### Strategy 1: Use GPT-3.5 for Training

- Cheap ($0.01 per challenge)
- Fast enough for learning
- Good quality for basic challenges

```dotenv
OPENROUTER_MODEL=openai/gpt-3.5-turbo
```

### Strategy 2: Use Claude 3 for Balance

- Moderate cost (~$0.03 per challenge)
- Good balance of speed and quality
- Excellent explanations

```dotenv
OPENROUTER_MODEL=anthropic/claude-3-sonnet
```

### Strategy 3: Use Llama 2 for Budget

- Cheapest option (~$0.01)
- Open-source, no vendor lock-in
- Good for offline self-hosting later

```dotenv
OPENROUTER_MODEL=meta-llama/llama-2-70b-chat
```

### Strategy 4: Mix & Match

Generate challenges with cheaper model, evaluate with better model:
- Generate with GPT-3.5
- Evaluate with Claude 3 Sonnet
- (Would require code changes)

---

## Advanced Configuration

### Custom Base URL

If you have a custom Openrouter endpoint:

```dotenv
OPENROUTER_BASE_URL=https://your-custom-openrouter-endpoint/api/v1
OPENROUTER_API_KEY=sk-or-xxx
```

Default is: `https://openrouter.ai/api/v1`

### Model-Specific Parameters

To pass model-specific parameters, modify `backend/app/services/ai_service.py`:

```python
class OpenrouterProvider(BaseAIProvider):
    def _call(self, system: str, user: str) -> str:
        response = client.chat.completions.create(
            model=s.openrouter_model,
            max_tokens=MAX_TOKENS,
            temperature=0.7,  # ← Add here
            top_p=0.9,        # ← Or here
            messages=[...],
        )
```

---

## Migration Guide

### From Anthropic to Openrouter

```bash
# 1. Update .env
sed -i 's/AI_PROVIDER=anthropic/AI_PROVIDER=openrouter/' .env

# 2. Add Openrouter key
echo "OPENROUTER_API_KEY=sk-or-YOUR_KEY" >> .env

# 3. Comment out Anthropic key (optional)
sed -i 's/^ANTHROPIC_API_KEY=/#ANTHROPIC_API_KEY=/' .env

# 4. Restart
docker compose restart backend
```

### From Qwen to Openrouter

```bash
# 1. Update .env
sed -i 's/AI_PROVIDER=qwen/AI_PROVIDER=openrouter/' .env

# 2. Add Openrouter key
echo "OPENROUTER_API_KEY=sk-or-YOUR_KEY" >> .env

# 3. Restart
docker compose restart backend
```

---

## Further Reading

- [Openrouter Documentation](https://openrouter.ai/docs)
- [Supported Models](https://openrouter.ai/docs/models)
- [API Reference](https://openrouter.ai/docs/api/introduction)
- [Pricing](https://openrouter.ai/pricing)
- [Status & Uptime](https://openrouter.ai/status)

---

## Questions?

- **Openrouter Support**: [support.openrouter.ai](https://support.openrouter.ai/)
- **This Project**: See [CONTRIBUTING.md](CONTRIBUTING.md) for how to report issues
- **General AI Questions**: See [SECURITY.md](SECURITY.md) for security considerations

---

**Happy learning with SecureDevIQ + Openrouter!** 🚀
