/** Human labels for PubTator's section codes. */
export const SECTION_LABELS: Record<string, string> = {
  ABSTRACT: 'Abstract',
  INTRO: 'Introduction',
  METHODS: 'Methods',
  RESULTS: 'Results',
  DISCUSS: 'Discussion',
  CONCL: 'Conclusion',
  FIG: 'Figures',
  TABLE: 'Tables',
  SUPPL: 'Supplementary',
  APPENDIX: 'Appendix',
  CASE: 'Case',
  ABBR: 'Abbreviations',
  AUTH_CONT: 'Author contributions',
  COMP_INT: 'Competing interests',
  ACK_FUND: 'Acknowledgements',
  KEYWORD: 'Keywords',
}

/** "Results" for RESULTS; an unknown code is shown as it came. */
export function sectionLabel(code: string): string {
  return SECTION_LABELS[code] ?? code
}
