import OutgoingArrowIcon from './OutgoingArrowIcon'

interface Props {
  /** Used for the accessible name, so each button is distinguishable. */
  label: string
  onClick: () => void
}

/**
 * Opens a paper in a background tab.
 *
 * A sibling of the card rather than a child: the card is itself a `<button>`,
 * and nesting one inside another is invalid HTML and does not reliably click.
 * The caller positions it over the card's top-right corner.
 */
export default function OpenInTabButton({ label, onClick }: Props) {
  return (
    <button
      type="button"
      className="open-in-tab"
      aria-label={`Open ${label} in a background tab`}
      title="Open in a background tab"
      onClick={onClick}
    >
      <OutgoingArrowIcon />
    </button>
  )
}
