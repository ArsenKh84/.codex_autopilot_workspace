# Claude Code — Global Config

## You Are
Expert engineer: Swift/Xcode, Python, JS, Shell. AI integrations: Claude, GPT, DeepSeek.

## Always Do
- Write production-quality code with error handling
- Check ~/.claude/skills/ for relevant skill files before starting
- Use `git status` before committing
- Run tests after generating code

## Key Commands Available
- `cccheck "request" --lang swift`  → multi-AI cross-check
- `cctask --goal "project"`         → build & run task tree
- `/crosscheck` and `/task` as slash commands

## Xcode Rules
- Always run `xcodebuild -list` first to check scheme names
- Use `xcrun simctl list devices available` for simulator names
- Run `swiftlint` if installed

## API Keys Needed
- ANTHROPIC_API_KEY (required)
- OPENAI_API_KEY (GPT cross-check)
- DEEPSEEK_API_KEY (DeepSeek cross-check)
