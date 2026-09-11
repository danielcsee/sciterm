// Minimal YAML frontmatter reader and writer.
//
// Deliberately dependency-free. It handles the shapes that actually occur in
// skill, agent and command frontmatter -- scalars, quoted scalars, block
// scalars, flat lists, and one level of nested mapping -- and nothing else. A
// full YAML library would be a larger surface than the input justifies, and
// this file has to be readable by anyone auditing what the generator emits.
package main

import (
	"regexp"
	"strings"
)

// Kind distinguishes the three value shapes this parser produces.
type Kind int

const (
	KindScalar Kind = iota
	KindList
	KindMap
)

// Field is one frontmatter entry. Order is preserved because the generated
// files are diffed by humans, and a key that moves on every run is noise.
type Field struct {
	Key    string
	Kind   Kind
	Scalar string
	List   []string
	Map    []Field // scalars only; YAML nesting deeper than this is not parsed
}

// Display renders a value for interpolation into prose, where a Go-style
// slice dump would read badly.
func (f Field) Display() string {
	switch f.Kind {
	case KindList:
		return strings.Join(f.List, ", ")
	case KindMap:
		parts := make([]string, 0, len(f.Map))
		for _, child := range f.Map {
			parts = append(parts, child.Key+": "+child.Scalar)
		}
		return strings.Join(parts, ", ")
	default:
		return f.Scalar
	}
}

// Frontmatter is an ordered set of fields.
type Frontmatter struct {
	fields []Field
}

// Get reports the field under key, and whether it was present at all. The
// distinction matters: `tools:` with an empty value is a restriction to
// nothing, which is not the same as no `tools` key.
func (fm *Frontmatter) Get(key string) (Field, bool) {
	for _, field := range fm.fields {
		if field.Key == key {
			return field, true
		}
	}
	return Field{}, false
}

// String returns a field's scalar form, or "" when it is absent.
func (fm *Frontmatter) String(key string) string {
	field, ok := fm.Get(key)
	if !ok {
		return ""
	}
	return field.Display()
}

// Set appends or replaces a scalar field.
func (fm *Frontmatter) Set(key, value string) {
	for i, field := range fm.fields {
		if field.Key == key {
			fm.fields[i] = Field{Key: key, Kind: KindScalar, Scalar: value}
			return
		}
	}
	fm.fields = append(fm.fields, Field{Key: key, Kind: KindScalar, Scalar: value})
}

// Append adds an already-shaped field, keeping insertion order.
func (fm *Frontmatter) Append(field Field) {
	fm.fields = append(fm.fields, field)
}

var frontmatterRE = regexp.MustCompile(`(?s)\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\z)`)

// scalar strips a quoted or bare value down to its text.
func scalar(raw string) string {
	raw = strings.TrimSpace(raw)
	if len(raw) >= 2 && raw[0] == raw[len(raw)-1] && (raw[0] == '"' || raw[0] == '\'') {
		inner := raw[1 : len(raw)-1]
		if raw[0] == '"' {
			return strings.ReplaceAll(inner, `\"`, `"`)
		}
		return inner
	}
	return raw
}

// splitLines splits on newlines and tolerates CRLF, so a file authored on
// Windows parses the same as one authored anywhere else.
func splitLines(text string) []string {
	lines := strings.Split(text, "\n")
	for i, line := range lines {
		lines[i] = strings.TrimSuffix(line, "\r")
	}
	return lines
}

func indented(line string) bool {
	return strings.HasPrefix(line, " ") || strings.HasPrefix(line, "\t")
}

// ParseFrontmatter returns the frontmatter and the body that follows it. Text
// with no frontmatter yields an empty set and the whole text as the body.
func ParseFrontmatter(text string) (Frontmatter, string) {
	match := frontmatterRE.FindStringSubmatchIndex(text)
	if match == nil {
		return Frontmatter{}, text
	}
	body := text[match[1]:]
	lines := splitLines(text[match[2]:match[3]])

	var fm Frontmatter
	for i := 0; i < len(lines); {
		line := lines[i]
		i++
		trimmed := strings.TrimSpace(line)
		if trimmed == "" || strings.HasPrefix(trimmed, "#") {
			continue
		}
		if indented(line) { // stray indent with no parent
			continue
		}

		key, rest, _ := strings.Cut(line, ":")
		key = strings.TrimSpace(key)
		rest = strings.TrimSpace(rest)

		// Block scalar: fold or keep the indented lines that follow.
		if rest == "|" || rest == ">" || rest == "|-" || rest == ">-" {
			var block []string
			for i < len(lines) && (strings.TrimSpace(lines[i]) == "" || indented(lines[i])) {
				block = append(block, strings.TrimSpace(lines[i]))
				i++
			}
			joiner := " "
			if strings.HasPrefix(rest, "|") {
				joiner = "\n"
			}
			fm.Append(Field{
				Key:    key,
				Kind:   KindScalar,
				Scalar: strings.TrimSpace(strings.Join(block, joiner)),
			})
			continue
		}

		if rest != "" {
			fm.Append(Field{Key: key, Kind: KindScalar, Scalar: scalar(rest)})
			continue
		}

		// A bare "key:" introduces a list or a nested mapping.
		var children []string
		for i < len(lines) && (strings.TrimSpace(lines[i]) == "" || indented(lines[i])) {
			if child := strings.TrimSpace(lines[i]); child != "" {
				children = append(children, child)
			}
			i++
		}

		switch {
		case len(children) == 0:
			fm.Append(Field{Key: key, Kind: KindScalar})
		case allListItems(children):
			list := make([]string, 0, len(children))
			for _, child := range children {
				list = append(list, scalar(strings.TrimPrefix(child, "- ")))
			}
			fm.Append(Field{Key: key, Kind: KindList, List: list})
		default:
			nested := make([]Field, 0, len(children))
			for _, child := range children {
				childKey, childValue, _ := strings.Cut(child, ":")
				nested = append(nested, Field{
					Key:    strings.TrimSpace(childKey),
					Kind:   KindScalar,
					Scalar: scalar(childValue),
				})
			}
			fm.Append(Field{Key: key, Kind: KindMap, Map: nested})
		}
	}
	return fm, body
}

// emitScalar quotes a value when leaving it bare would change how YAML reads
// it -- an indicator character at the start, a trailing space, an embedded
// ": ", or a newline.
func emitScalar(value string) string {
	needsQuote := value == "" ||
		strings.ContainsRune("\"'{[&*?|>%@`!#", rune(value[0])) ||
		strings.HasSuffix(value, " ") ||
		strings.Contains(value, ": ") ||
		strings.Contains(value, "\n")
	if !needsQuote {
		return value
	}
	escaped := strings.NewReplacer(`\`, `\\`, `"`, `\"`, "\n", " ").Replace(value)
	return `"` + escaped + `"`
}

// Dump renders frontmatter, delimiters included, with a trailing newline.
func (fm *Frontmatter) Dump() string {
	var out strings.Builder
	out.WriteString("---\n")
	for _, field := range fm.fields {
		switch field.Kind {
		case KindMap:
			out.WriteString(field.Key + ":\n")
			for _, child := range field.Map {
				out.WriteString("  " + child.Key + ": " + emitScalar(child.Scalar) + "\n")
			}
		case KindList:
			out.WriteString(field.Key + ":\n")
			for _, item := range field.List {
				out.WriteString("  - " + emitScalar(item) + "\n")
			}
		default:
			out.WriteString(field.Key + ": " + emitScalar(field.Scalar) + "\n")
		}
	}
	out.WriteString("---\n")
	return out.String()
}

func allListItems(lines []string) bool {
	for _, line := range lines {
		if !strings.HasPrefix(line, "- ") {
			return false
		}
	}
	return len(lines) > 0
}
