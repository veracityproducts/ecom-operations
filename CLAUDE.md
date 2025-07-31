# Grooved Learning E-commerce Operations

**We are partners! Never make assumptions. If you have questions just ask**

## 🛠️ Development Standards

### UV Package Management
- **Always use UV**: `uv add`, `uv remove`, `uv run` (never pip)
- **Run code**: `uv run script.py` (auto-syncs dependencies)
- **Add dependencies**: `uv add package` then `uv sync`

## 📝 Project Decision Making
- **Always refer to TASKS.md** for current implementation status
- **Review CONTEXT.md** for development context and architectural decisions
- **Update TASKS.md** when starting work on a task (mark as 🟡 In Progress) and when completing a task (mark as ✅ Complete with date)
- **NEVER start work on a task without updating TASKS.md**
- **Never make assumptions about what I think** - Just ask me when you're not sure - we are partners!
- **Follow project-specific CLAUDE.md** for detailed organization rules
- **Practice OCD directory organization**
- **ALWAYS work from the project root directory**
- **NEVER create tests or scripts in the root directory** use a subdirectory within `tests/` or `scripts/` as appropriate
- **NEVER keep multiple versions of the same file** - If you create a new version of a file, date stamp the old one and archive it
- **Always use CLAUDE.md** for project-specific guidelines
  - **Keep it up to date** as the project evolves
  - **Refer to it** before starting any work
- **When creating a new directory** create a short, succinct `CLAUDE.md` file with relevant instructions

### Documentation Lookup
**Always leverage your /.claude/agents/coding_doc_meta_agent.md when writing code**

```bash
# Common libraries for this project
get-library-docs "/unclecode/crawl4ai" "web scraping education" "10000"
get-library-docs "/supabase/supabase" "vector search pgvector" "8000"
get-library-docs "/pydantic/pydantic-ai" "agents tools" "8000"
```

### Clean Code Rules
- **Never create test files in project root**
- **Stick to a mirrored testing structure**, And ensure the directory is organized at the beginning of every conversation. 
- Use descriptive filenames with versions  
- Archive temporary work regularly
- Organize code to prevent directory bloat

## Purpose
Experimentation space for e-commerce operations improvements, particularly focused on:
- Fulfillment optimization
- Shipping automation
- Packing slip generation
- Multi-warehouse coordination
- Cost optimization strategies

## Quick Commands
- `/user:context:save` - Save experiment progress
- `/user:context:resume` - Resume work  
- `/user:prp-create-with-agents` - Create a PRP
- `/user:todo` - Manage technical discoveries

## Context
Working with Grooved Learning's e-commerce operations:
- Shopify Plus platform
- Multiple fulfillment channels (ShipStation, Amazon FBA, direct)
- Educational product focus
- Peak season optimization needs

## Active Experiments
- [ ] Automated packing slip system
- [ ] Shipping cost optimization
- [ ] Multi-warehouse routing logic
- [ ] Integration architecture

## Technical Notes
- UV for Python development
- API-first design
- Modular components
- Error handling priority