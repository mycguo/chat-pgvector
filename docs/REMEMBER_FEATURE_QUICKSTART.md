# 🚀 Remember Feature - Quick Start Guide

## What is it?

Save information to your knowledge base by simply saying "Remember that..." - no document upload needed!

## Two Ways to Use It

### Method 1: Natural Language in Chat 💬

Just type your command in the main chat:

```
"Remember that I prefer Python over JavaScript"
"Remember: My favorite color is blue"
"Save this: I graduated from MIT in 2020"
"Store that I work remotely"
"Note that I prefer morning meetings"
```

**What happens:**
1. System detects your intent
2. Extracts the information
3. AI enriches it (optional)
4. Saves to knowledge base
5. Shows confirmation

### Method 2: Sidebar UI 🎨

Look for the **"💾 Quick Save"** panel in the sidebar:

1. Type or paste information
2. Check "Enhance with AI" (recommended)
3. Click "💾 Save to Knowledge Base"
4. Done!

## Example Workflow

### Saving Information
```
You: "Remember that Charles prefers working from home"

System: 💾 Saving information: 'charles prefers working from home'
        ✅ Information saved to knowledge base!
        📝 What was saved (enriched version):
        "Charles prefers working from home, which means remote work
        or telecommuting. This indicates a preference for flexibility,
        avoiding commutes, and having a personalized work environment."
```

### Retrieving Information
```
You: "Where does Charles prefer to work?"

System: "Based on your knowledge base, Charles prefers working from home..."
```

## Supported Commands

| Say This | To Save This |
|----------|--------------|
| `Remember that [info]` | Any information |
| `Remember: [info]` | Quick fact |
| `Save this: [info]` | Important detail |
| `Store that [info]` | Long-term info |
| `Note that [info]` | Reminder |

All commands work **case-insensitive**!

## Pro Tips

### ✨ Best Practices
- **Be specific**: "I prefer Python for AI projects" vs "I like Python"
- **Use enrichment**: Makes information more searchable
- **Natural language**: Write as you'd tell a person

### ⚡ Quick Examples

Personal preferences:
```
"Remember that I prefer email over phone calls"
"Note that I'm allergic to peanuts"
"Save this: My favorite coffee is cappuccino"
```

Work information:
```
"Store that I work at TechCorp as Senior Engineer"
"Remember: Team meetings are every Monday at 10am"
"Note that I report to Sarah Johnson"
```

Facts and context:
```
"Remember that I graduated from MIT in 2020"
"Save this: My current project is a RAG chatbot"
"Store that I know Python, JavaScript, and Go"
```

## Running the App

```bash
# Activate virtual environment
source .venv/bin/activate

# Run Streamlit app
streamlit run app.py
```

Then:
1. Open http://localhost:8501
2. Look for the sidebar "💾 Quick Save" or use the chat
3. Start saving information!

## Verification

Test that it works:

1. **Save**: "Remember that my favorite color is blue"
2. **Verify**: See ✅ confirmation
3. **Query**: "What is my favorite color?"
4. **Result**: Should mention blue!

## Testing

Run automated tests:

```bash
source .venv/bin/activate

# Quick test (no API key needed)
pytest tests/test_remember_feature.py::TestRememberIntentDetection -v

# Full test (requires Google API key)
export GOOGLE_API_KEY="your_key"
pytest tests/test_remember_feature.py -v
```

## Troubleshooting

**Command not detected?**
- Make sure it starts with a supported pattern
- Try using the sidebar UI instead

**Information not saved?**
- Check console for errors
- Verify Google API key is set
- Ensure vector store directory is writable

**Can't find saved info?**
- Wait a few seconds after saving
- Query with related terms
- Check that enrichment was enabled

## More Information

- Full documentation: `REMEMBER_FEATURE.md`
- Test suite: `tests/test_remember_feature.py`
- Main code: `app.py` (lines 24-113)

---

**Ready to try it? Start the app and say "Remember that..." in the chat!** 🎉
