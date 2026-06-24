# Patchright Browser Skills

Hermes Agent skills for browser automation tasks. Copy to `~/.hermes/skills/` to install.

## Install Skills

```bash
# Copy all skills
cp -r skills/* ~/.hermes/skills/

# Or install specific skill
cp -r skills/research/x-search ~/.hermes/skills/research/
```

## Skills

### Research
| Skill | Description |
|-------|-------------|
| `x-search` | X.com search & data extraction with replies |
| `threads-search` | Threads search & data extraction with comments |

### Social Media
| Skill | Description |
|-------|-------------|
| `instagram-automation` | Instagram DM, post, comment, story |
| `threads-automation` | Threads post, reply, DM, search |
| `x-automation` | X.com post, reply, DM, search |

## Usage

After installing skills, use them in Hermes:

```
# Search X.com
cari di x tentang AI agent

# Search Threads
cari threads tentang startup AI

# Post to Threads
post ke threads tentang promo fal.ai

# Post to X
post ke x tentang promo suno
```

## Creating New Skills

See `~/.hermes/skills/ponytail/SKILL.md` for skill authoring guidelines.
