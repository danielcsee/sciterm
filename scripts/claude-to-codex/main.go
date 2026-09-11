// Generate Codex configuration from a repository's Claude Code configuration.
//
//	Reads  CLAUDE.md (root and nested) and .claude/
//	Writes AGENTS.md (root and nested) and .agents/
//
// The Claude side is never modified, moved or deleted. Everything written is
// tracked in a manifest, so re-runs are idempotent and a file written by hand
// is never clobbered.
//
//	go run .              # from this directory; writes it
//	go run . --dry-run    # show the plan, change nothing
//	go run . --prune      # also delete generated files whose source is gone
//
// Verify the result with: codex debug prompt-input | grep -i skill
package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
)

const (
	tool         = "scripts/claude-to-codex"
	manifestName = ".claude-sync.json"

	// Format arguments are (source label, tool) for the first two and
	// (source label) for the closer.
	beginTemplate     = "<!-- BEGIN generated from %s by %s -- edits inside this block are overwritten -->"
	endTemplate       = "<!-- END generated from %s -->"
	genHeaderTemplate = "<!-- Generated from %s by %s. Do not edit; edit the source and re-run. -->"
)

const readmeTemplate = `# .agents

Codex configuration, generated from the Claude Code configuration by
` + "`%[1]s`" + `. **Do not edit these files by hand** -- edit ` + "`CLAUDE.md`" + ` or
` + "`.claude/`" + ` and re-run the generator:

` + "```bash" + `
(cd %[1]s && go run .)
` + "```" + `

Codex discovers ` + "`.agents/skills/*/SKILL.md`" + ` automatically for any session
started inside this repo, the same way it reads ` + "`AGENTS.md`" + `. Verify what it
actually sees with:

` + "```bash" + `
codex debug prompt-input | grep -i %[3]s
` + "```" + `

` + "`%[2]s`" + ` records every generated file so re-runs stay idempotent, files you
wrote yourself are never overwritten, and ` + "`--prune`" + ` can clean up skills whose
Claude counterpart was deleted.

The Claude configuration remains the source of truth; nothing here replaces it.
`

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "claude-to-codex:", err)
		os.Exit(1)
	}
}

func run() error {
	var (
		rootFlag  = flag.String("root", "", "project root (default: nearest ancestor holding CLAUDE.md or .claude/)")
		skillsRel = flag.String("skills-dir", ".agents/skills", "where to write skills; .codex/skills also works")
		dryRun    = flag.Bool("dry-run", false, "show what would change, write nothing")
		force     = flag.Bool("force", false, "overwrite files this tool did not generate")
		prune     = flag.Bool("prune", false, "delete generated files whose source is gone")
	)
	flag.Usage = func() {
		fmt.Fprint(os.Stderr,
			"Generate Codex config (AGENTS.md, .agents/) from Claude config (CLAUDE.md, .claude/).\n\n")
		flag.PrintDefaults()
	}
	flag.Parse()

	root, err := resolveRoot(*rootFlag)
	if err != nil {
		return err
	}

	skillsDir := filepath.Join(root, filepath.FromSlash(*skillsRel))
	w := NewWriter(root, *dryRun, *force)

	counts := []tally{
		{"AGENTS.md files", ConvertMemory(root, w)},
		{"skills", ConvertSkills(root, skillsDir, w)},
		{"subagents", ConvertAgents(root, skillsDir, w)},
		{"commands", ConvertCommands(root, skillsDir, w)},
		{"MCP servers", ConvertMCP(root, w)},
	}
	InspectSettings(root, w)
	w.WriteString(
		filepath.Join(root, ".agents", "README.md"),
		fmt.Sprintf(readmeTemplate, tool, manifestName, filepath.Base(root)),
	)

	var removed []string
	if *prune {
		removed = w.Prune()
	}
	stale := w.Stale()

	report(w, root, counts, removed, stale, *dryRun, *prune)

	if err := w.SaveManifest(); err != nil {
		return fmt.Errorf("could not write the manifest: %w", err)
	}
	if !*dryRun {
		fmt.Println("\nVerify with:  codex debug prompt-input | grep -i skill")
	}
	return nil
}

// resolveRoot honours an explicit --root, and otherwise walks up from the
// working directory. Walking up is what lets the generator run from inside its
// own module directory, which is where `go run .` puts you.
func resolveRoot(explicit string) (string, error) {
	if explicit != "" {
		absolute, err := filepath.Abs(explicit)
		if err != nil {
			return "", err
		}
		if !isProjectRoot(absolute) {
			return "", fmt.Errorf("no CLAUDE.md or .claude/ under %s", absolute)
		}
		return absolute, nil
	}

	dir, err := os.Getwd()
	if err != nil {
		return "", err
	}
	for {
		if isProjectRoot(dir) {
			return dir, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			return "", fmt.Errorf("no CLAUDE.md or .claude/ in any parent of the working directory; pass --root")
		}
		dir = parent
	}
}

func isProjectRoot(dir string) bool {
	if exists(filepath.Join(dir, "CLAUDE.md")) {
		return true
	}
	info, err := os.Stat(filepath.Join(dir, ".claude"))
	return err == nil && info.IsDir()
}

// tally is one line of the summary: how many of a thing were converted.
type tally struct {
	label string
	count int
}

func report(w *Writer, root string, counts []tally, removed, stale []string, dryRun, prune bool) {
	verb := "Wrote"
	if dryRun {
		verb = "Planned"
	}
	fmt.Printf("%s Codex config under %s\n\n", verb, root)

	for _, entry := range counts {
		if entry.count > 0 {
			fmt.Printf("  %3d %s\n", entry.count, entry.label)
		}
	}
	fmt.Println()

	action := "wrote"
	if dryRun {
		action = "would write"
	}
	for _, rel := range w.written {
		fmt.Printf("  %s  %s\n", action, rel)
	}
	if len(w.written) == 0 {
		fmt.Println("  (everything already up to date)")
	}

	deleted := "deleted"
	if dryRun {
		deleted = "would delete"
	}
	for _, rel := range removed {
		fmt.Printf("  %s  %s\n", deleted, rel)
	}

	if len(stale) > 0 && !prune {
		fmt.Printf("\n  %d generated file(s) no longer have a Claude source; re-run with --prune to remove them.\n",
			len(stale))
	}
	if len(w.skipped) > 0 {
		fmt.Println("\nSkipped:")
		for _, item := range w.skipped {
			fmt.Printf("  - %s\n", item)
		}
	}
	if len(w.notes) > 0 {
		fmt.Println("\nNotes (things Codex handles differently):")
		for _, note := range w.notes {
			fmt.Printf("  - %s\n", note)
		}
	}
}
