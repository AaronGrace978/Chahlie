# Contributing to Chahlie

Thanks for your interest in contributing to Chahlie - the Boston Coding Agent! This project is an official product of **Cursor Boston**, and we welcome contributions from the community.

## About Cursor Boston

Cursor Boston is Boston's home for AI-powered development. We're a community of developers building with Cursor IDE, sharing knowledge, and creating awesome tools together.

- **Founded by**: Roger Hunt (Cursor Boston Ambassador)
- **CMO**: Aaron Grace
- **GitHub**: [github.com/AaronGrace978/Chahlie](https://github.com/AaronGrace978/Chahlie)

## How to Contribute

### 1. Fork & Clone

```bash
# Fork the repo on GitHub, then:
git clone https://github.com/YOUR_USERNAME/Chahlie.git
cd Chahlie
```

### 2. Set Up Development Environment

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
# Add your OLLAMA_API_KEY to .env
```

### 3. Make Your Changes

- Create a new branch: `git checkout -b feature/your-feature-name`
- Make your changes
- Test locally: `python run.py`
- Commit with clear messages

### 4. Submit a Pull Request

- Push your branch: `git push origin feature/your-feature-name`
- Open a PR on GitHub
- Describe your changes clearly

## What We're Looking For

### Boston Personality Enhancements
- More authentic Boston slang and phrases
- Boston cultural references (sports, landmarks, food)
- Fun Boston facts

### AI Provider Support
- Additional AI backend integrations
- Model recommendations
- Performance optimizations

### UI/UX Improvements
- Better terminal visuals
- New ASCII art
- Color scheme enhancements

### Tool Capabilities
- New coding tools
- Better file operations
- Enhanced shell integration

### Documentation
- README improvements
- Usage examples
- Tutorial content

## Code Style

- Keep it Pythonic and clean
- Add docstrings to functions
- Follow existing patterns in the codebase
- Test your changes before submitting

## Boston Flavor Guidelines

When adding personality to Chahlie:

- **DO**: Use authentic Boston slang naturally
  - "kehd", "wicked", "pissa", "no problemo"
  - Drop R's: "cah", "pahk", "hahd", "smaht"
  
- **DO**: Reference Boston culture
  - Sports: Red Sox, Celtics, Bruins, Patriots
  - Landmarks: Fenway, the Common, Faneuil Hall
  - Food: Dunkin', clam chowdah, lobstah rolls
  
- **DON'T**: Overdo it - keep it natural and fun
- **DON'T**: Use offensive stereotypes

## Cursor Boston Community

Want to get more involved with Cursor Boston?

- Star the repo and share it
- Join discussions in Issues
- Help other contributors
- Spread the word about AI-powered development in Boston!

## Questions?

Open an issue on GitHub or reach out to the maintainers.

---

**Thanks for helping make Chahlie wicked good, kehd!** 🦞

*— The Cursor Boston Team*
