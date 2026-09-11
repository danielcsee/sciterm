// The five converters, one per thing Claude Code can hold.
//
// Each maps a Claude concept onto its nearest Codex equivalent and records a
// note wherever the mapping is lossy, rather than guessing. Nothing here reads
// or writes outside the project root, and nothing touches the Claude side.
package main

import (
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

// codexSkillKeys are the frontmatter keys Codex's skill loader understands.
// Anything else is dropped from the frontmatter and, where it carries meaning,
// restated in the body.
var codexSkillKeys = []string{"license", "version", "metadata", "allowed-tools"}

// skipDirs are never descended into when looking for nested CLAUDE.md files.
var skipDirs = map[string]bool{".git": true, "node_modules": true, ".venv": true, ".agents": true}

var (
	importRE     = regexp.MustCompile(`(?m)^@(\S+)[ \t]*$`)
	positionalRE = regexp.MustCompile(`\$[1-9]`)
	shellCallRE  = regexp.MustCompile("!`[^`]+`")
	fileRefRE    = regexp.MustCompile("(?m)(^|[^\\w`])@[\\w./-]+\\.\\w+")
)

// ConvertMemory maps CLAUDE.md onto AGENTS.md, at the root and in every
// subdirectory. Both are directory-scoped instructions with the more deeply
// nested file winning, so the content carries over unchanged.
func ConvertMemory(root string, w *Writer) int {
	var sources []string
	_ = filepath.WalkDir(root, func(path string, entry fs.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		if entry.IsDir() {
			if path != root && skipDirs[entry.Name()] {
				return filepath.SkipDir
			}
			return nil
		}
		if entry.Name() == "CLAUDE.md" {
			sources = append(sources, path)
		}
		return nil
	})
	sort.Strings(sources)

	count := 0
	for _, source := range sources {
		data, err := os.ReadFile(source)
		if err != nil {
			w.Note("could not read %s: %v", w.rel(source), err)
			continue
		}
		text := string(data)
		label := w.rel(source)

		// Claude expands @imports; Codex does not. Rewriting them as
		// instructions keeps the reference without pretending it is inlined.
		if matches := importRE.FindAllStringSubmatch(text, -1); len(matches) > 0 {
			names := make([]string, 0, len(matches))
			for _, match := range matches {
				names = append(names, match[1])
			}
			w.Note("%s uses Claude's @import syntax (%s). Codex does not expand imports; "+
				"the lines were rewritten as instructions to read those files.",
				label, strings.Join(names, ", "))
			text = importRE.ReplaceAllString(text, "Read `$1` and follow it.")
		}

		w.WriteBlock(filepath.Join(filepath.Dir(source), "AGENTS.md"), label, text)
		count++
	}
	return count
}

// skillFrontmatter builds the Codex frontmatter for a converted entry, keeping
// only the keys the loader reads.
func skillFrontmatter(source Frontmatter, name, description string) Frontmatter {
	var out Frontmatter
	out.Set("name", name)
	out.Set("description", description)
	for _, key := range codexSkillKeys {
		if field, ok := source.Get(key); ok {
			field.Key = key
			out.Append(field)
		}
	}
	return out
}

// explicitOnly marks a skill as explicit-invocation-only, which keeps it out
// of Codex's automatic discovery list.
func explicitOnly(destDir string, w *Writer, display, short string) {
	yaml := "interface:\n" +
		fmt.Sprintf("  display_name: %q\n", display) +
		fmt.Sprintf("  short_description: %q\n", short) +
		"policy:\n" +
		"  allow_implicit_invocation: false\n"
	w.WriteString(filepath.Join(destDir, "agents", "openai.yaml"), yaml)
}

// noteModelPin records a dropped model pin. Codex chooses the model per
// session, so carrying the pin would be a promise the format cannot keep.
func noteModelPin(fm Frontmatter, label string, w *Writer) {
	if model := fm.String("model"); model != "" {
		w.Note("%s pins model '%s'. Codex selects the model per session, so the pin was dropped.",
			label, model)
	}
}

// ConvertSkills maps .claude/skills/<name>/ onto <skillsDir>/<name>/.
//
// The two formats are nearly identical -- a directory holding SKILL.md plus
// optional scripts/, references/ and assets/ -- so only the frontmatter needs
// normalising and the support files are copied verbatim.
func ConvertSkills(root, skillsDir string, w *Writer) int {
	srcRoot := filepath.Join(root, ".claude", "skills")
	entries, err := os.ReadDir(srcRoot)
	if err != nil {
		return 0
	}

	count := 0
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		srcDir := filepath.Join(srcRoot, entry.Name())
		skillMD := filepath.Join(srcDir, "SKILL.md")
		data, err := os.ReadFile(skillMD)
		if err != nil {
			continue
		}
		name := entry.Name()
		fm, body := ParseFrontmatter(string(data))
		label := w.rel(skillMD)

		description := fm.String("description")
		if description == "" {
			description = fmt.Sprintf("Project skill %s, imported from Claude Code.", name)
		}
		if declared := fm.String("name"); declared != "" {
			name = declared
		}
		destDir := filepath.Join(skillsDir, entry.Name())

		noteModelPin(fm, label, w)

		preface := ""
		if tools, ok := fm.Get("tools"); ok {
			preface = fmt.Sprintf("\n> Under Claude Code this skill was restricted to these tools: %s. "+
				"Codex does not enforce per-skill tool restrictions; treat it as guidance.\n", tools.Display())
		}

		out := skillFrontmatter(fm, name, description)
		content := out.Dump() + "\n" +
			fmt.Sprintf(genHeaderTemplate, label, tool) + "\n" +
			preface + "\n" +
			strings.TrimLeft(body, "\n")

		if !w.WriteString(filepath.Join(destDir, "SKILL.md"), content) {
			continue
		}
		if strings.EqualFold(fm.String("disable-model-invocation"), "true") {
			explicitOnly(destDir, w, entry.Name(), truncate(description, 100))
		}
		copySupportFiles(srcDir, destDir, w)
		count++
	}
	return count
}

// copySupportFiles carries everything beside SKILL.md across untouched.
func copySupportFiles(srcDir, destDir string, w *Writer) {
	var extras []string
	_ = filepath.WalkDir(srcDir, func(path string, entry fs.DirEntry, err error) error {
		if err != nil || entry.IsDir() || entry.Name() == "SKILL.md" {
			return nil
		}
		extras = append(extras, path)
		return nil
	})
	sort.Strings(extras)
	for _, extra := range extras {
		relative, err := filepath.Rel(srcDir, extra)
		if err != nil {
			continue
		}
		w.Copy(extra, filepath.Join(destDir, relative))
	}
}

// markdownFiles lists every .md file under root, relative to it, sorted.
func markdownFiles(root string) []string {
	var found []string
	_ = filepath.WalkDir(root, func(path string, entry fs.DirEntry, err error) error {
		if err != nil || entry.IsDir() || !strings.HasSuffix(entry.Name(), ".md") {
			return nil
		}
		if relative, err := filepath.Rel(root, path); err == nil {
			found = append(found, relative)
		}
		return nil
	})
	sort.Strings(found)
	return found
}

// ConvertAgents maps .claude/agents/<name>.md onto a skill.
//
// Codex has no per-repo subagent definition file. A subagent is a named,
// described body of instructions selected by its description -- which is
// exactly what a skill is -- so each becomes a skill that says it may be run
// in a sub-agent.
func ConvertAgents(root, skillsDir string, w *Writer) int {
	srcRoot := filepath.Join(root, ".claude", "agents")
	if info, err := os.Stat(srcRoot); err != nil || !info.IsDir() {
		return 0
	}

	count := 0
	for _, relative := range markdownFiles(srcRoot) {
		path := filepath.Join(srcRoot, relative)
		data, err := os.ReadFile(path)
		if err != nil {
			continue
		}
		fm, body := ParseFrontmatter(string(data))
		label := w.rel(path)

		name := fm.String("name")
		if name == "" {
			name = joinParts(relative, "-")
		}
		description := fm.String("description")
		if description == "" {
			description = fmt.Sprintf("Subagent %s, imported from Claude Code.", name)
		}

		preface := []string{fmt.Sprintf(
			"> Imported from the Claude Code subagent `%s`. It ran in its own context window "+
				"with its own instructions; run it as a focused task, delegating to a sub-agent "+
				"when the work is large enough to justify one.", name)}
		if tools, ok := fm.Get("tools"); ok {
			preface = append(preface, fmt.Sprintf(
				"> The subagent was limited to these tools: %s. Codex does not enforce "+
					"per-agent tool restrictions; treat it as guidance.", tools.Display()))
		}
		noteModelPin(fm, label, w)

		out := skillFrontmatter(fm, name, description)
		content := out.Dump() + "\n" +
			fmt.Sprintf(genHeaderTemplate, label, tool) + "\n\n" +
			strings.Join(preface, "\n") + "\n\n" +
			strings.TrimLeft(body, "\n")

		if w.WriteString(filepath.Join(skillsDir, name, "SKILL.md"), content) {
			count++
		}
	}
	return count
}

// ConvertCommands maps .claude/commands/**/*.md onto explicit-invocation
// skills.
//
// Codex has no /custom-command surface: a user asks for the command by name
// and Codex routes to the skill. Claude's template syntax has no Codex
// equivalent, so it is left in place and explained rather than expanded.
func ConvertCommands(root, skillsDir string, w *Writer) int {
	srcRoot := filepath.Join(root, ".claude", "commands")
	if info, err := os.Stat(srcRoot); err != nil || !info.IsDir() {
		return 0
	}

	count := 0
	for _, relative := range markdownFiles(srcRoot) {
		path := filepath.Join(srcRoot, relative)
		data, err := os.ReadFile(path)
		if err != nil {
			continue
		}
		fm, body := ParseFrontmatter(string(data))
		label := w.rel(path)
		name := joinParts(relative, "-")
		slash := "/" + joinParts(relative, ":")

		description := fm.String("description")
		if description == "" {
			description = truncate(firstNonEmptyLine(body), 200)
		}
		if description == "" {
			description = fmt.Sprintf("Run the %s command", name)
		}
		if !strings.ContainsAny(lastRune(description), ".!?") {
			description += "."
		}
		description += fmt.Sprintf(" Use when the user asks for the %s command or names it directly.", slash)

		preface := []string{fmt.Sprintf("> Imported from the Claude Code slash command `%s`.", slash)}
		if strings.Contains(body, "$ARGUMENTS") || positionalRE.MatchString(body) {
			hint := ""
			if value := fm.String("argument-hint"); value != "" {
				hint = fmt.Sprintf(" (expected: %s)", value)
			}
			preface = append(preface, "> `$ARGUMENTS` and `$1`..`$9` below stand for what the user "+
				"typed after the command"+hint+". Substitute their words; ask for them if they are missing.")
		}
		if shellCallRE.MatchString(body) {
			preface = append(preface, "> Claude Code pre-ran the ``!`cmd` `` markers below and pasted "+
				"their output. Codex does not: run each one yourself first, then use its output where "+
				"the marker appears.")
		}
		if fileRefRE.MatchString(body) {
			preface = append(preface, "> `@path` references below mean: read that file before continuing.")
		}
		if allowed, ok := fm.Get("allowed-tools"); ok {
			preface = append(preface, fmt.Sprintf("> Claude restricted this command to: %s.", allowed.Display()))
		}

		out := skillFrontmatter(fm, name, description)
		content := out.Dump() + "\n" +
			fmt.Sprintf(genHeaderTemplate, label, tool) + "\n\n" +
			strings.Join(preface, "\n") + "\n\n" +
			strings.TrimLeft(body, "\n")

		if !w.WriteString(filepath.Join(skillsDir, name, "SKILL.md"), content) {
			continue
		}
		explicitOnly(filepath.Join(skillsDir, name), w, name, "Imported from "+slash)
		count++
	}
	if count > 0 {
		w.Note("%d slash command(s) became explicit-invocation skills, so Codex will not reach "+
			"for them on its own -- ask for one by name, or mention it as $<skill-name>.", count)
	}
	return count
}

// ConvertMCP turns .mcp.json into a config.toml fragment.
//
// Codex reads MCP servers from ~/.codex/config.toml, outside the project, and
// this tool does not write outside the project. So the servers are emitted for
// the user to review and append.
func ConvertMCP(root string, w *Writer) int {
	path := filepath.Join(root, ".mcp.json")
	data, err := os.ReadFile(path)
	if err != nil {
		return 0
	}
	var parsed struct {
		Servers map[string]map[string]any `json:"mcpServers"`
	}
	if err := json.Unmarshal(data, &parsed); err != nil {
		w.Note(".mcp.json could not be parsed (%v); MCP servers were not converted.", err)
		return 0
	}
	if len(parsed.Servers) == 0 {
		return 0
	}

	var out strings.Builder
	out.WriteString("# Generated from .mcp.json by " + tool + ".\n")
	out.WriteString("# Codex reads MCP servers from ~/.codex/config.toml, which is outside this\n")
	out.WriteString("# project, so this file is not loaded automatically. Append it yourself:\n#\n")
	out.WriteString("#     cat .agents/codex-mcp-servers.toml >> ~/.codex/config.toml\n#\n")
	out.WriteString("# Review the entries first -- they become available in every Codex session,\n")
	out.WriteString("# not just this project.\n\n")

	for _, name := range sortedKeys(parsed.Servers) {
		config := parsed.Servers[name]
		out.WriteString(fmt.Sprintf("[mcp_servers.%s]\n", name))

		var env map[string]any
		if raw, ok := config["env"].(map[string]any); ok {
			env = raw
		}
		for _, key := range sortedKeys(config) {
			switch key {
			case "command", "args", "url", "startup_timeout_sec":
				out.WriteString(key + " = " + tomlValue(config[key]) + "\n")
			}
		}
		if len(env) > 0 {
			out.WriteString(fmt.Sprintf("\n[mcp_servers.%s.env]\n", name))
			for _, key := range sortedKeys(env) {
				out.WriteString(key + " = " + tomlValue(env[key]) + "\n")
			}
		}
		out.WriteString("\n")
	}

	// The per-server blank line is a separator, not a terminator: trailing ones
	// are trimmed so the file ends with exactly one newline.
	content := strings.TrimRight(out.String(), "\n") + "\n"
	w.WriteString(filepath.Join(root, ".agents", "codex-mcp-servers.toml"), content)
	w.Note("%d MCP server(s) from .mcp.json were written to .agents/codex-mcp-servers.toml. "+
		"Codex will not load them until you append that file to ~/.codex/config.toml.", len(parsed.Servers))
	return len(parsed.Servers)
}

// InspectSettings reports on .claude/settings*.json, which has no faithful
// Codex mapping. These are described, never translated: a permission or hook
// that looks ported but is not enforced is worse than one that is absent.
func InspectSettings(root string, w *Writer) {
	for _, name := range []string{"settings.json", "settings.local.json"} {
		path := filepath.Join(root, ".claude", name)
		data, err := os.ReadFile(path)
		if err != nil {
			continue
		}
		var settings map[string]json.RawMessage
		if err := json.Unmarshal(data, &settings); err != nil {
			w.Note(".claude/%s is not valid JSON; skipped.", name)
			continue
		}
		if present(settings, "permissions") {
			w.Note(".claude/%s defines tool permissions. Codex uses its own sandbox and approval "+
				"policy (`/permissions`, or sandbox settings in ~/.codex/config.toml) and the two "+
				"models do not map one-to-one, so these were NOT converted.", name)
		}
		if present(settings, "hooks") {
			w.Note(".claude/%s defines hooks. Codex supports hooks under [hooks] in "+
				"~/.codex/config.toml with similar events (PreToolUse, PostToolUse, SessionStart), "+
				"but the payload differs. These were NOT converted -- port them by hand.", name)
		}
		if present(settings, "env") {
			w.Note(".claude/%s sets environment variables. Port them to shell_environment_policy "+
				"in ~/.codex/config.toml if Codex needs them.", name)
		}
	}
}

// present reports whether a settings key holds something other than null, {}
// or [] -- an empty block is not a configuration worth warning about.
func present(settings map[string]json.RawMessage, key string) bool {
	raw, ok := settings[key]
	if !ok {
		return false
	}
	switch strings.TrimSpace(string(raw)) {
	case "", "null", "{}", "[]":
		return false
	}
	return true
}

func tomlValue(value any) string {
	switch typed := value.(type) {
	case bool:
		return strconv.FormatBool(typed)
	case float64:
		return strconv.FormatFloat(typed, 'f', -1, 64)
	case []any:
		parts := make([]string, 0, len(typed))
		for _, item := range typed {
			parts = append(parts, tomlValue(item))
		}
		return "[" + strings.Join(parts, ", ") + "]"
	case string:
		return strconv.Quote(typed)
	default:
		return strconv.Quote(fmt.Sprint(typed))
	}
}

func sortedKeys[V any](m map[string]V) []string {
	keys := make([]string, 0, len(m))
	for key := range m {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

// joinParts turns "db/migrate.md" into "db-migrate" or "db:migrate".
func joinParts(relative, separator string) string {
	trimmed := strings.TrimSuffix(relative, filepath.Ext(relative))
	return strings.Join(strings.Split(filepath.ToSlash(trimmed), "/"), separator)
}

func firstNonEmptyLine(text string) string {
	for _, line := range splitLines(text) {
		if trimmed := strings.TrimSpace(line); trimmed != "" {
			return trimmed
		}
	}
	return ""
}

// truncate cuts to a rune count, so a multi-byte character is never split.
func truncate(text string, limit int) string {
	runes := []rune(text)
	if len(runes) <= limit {
		return text
	}
	return string(runes[:limit])
}

func lastRune(text string) string {
	runes := []rune(text)
	if len(runes) == 0 {
		return ""
	}
	return string(runes[len(runes)-1:])
}
