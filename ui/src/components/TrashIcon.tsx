/** A lidded bin: "delete this permanently". */
export default function TrashIcon() {
  return (
    <svg
      viewBox="0 0 16 16"
      width="13"
      height="13"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {/* Lid and its handle. */}
      <path d="M2.5 4h11M6.5 4V2.5h3V4" />
      {/* Bin, narrowing to the base, with two slats. */}
      <path d="M4 4l.7 9.1a1 1 0 0 0 1 .9h4.6a1 1 0 0 0 1-.9L12 4M6.8 6.8v4.4M9.2 6.8v4.4" />
    </svg>
  )
}
