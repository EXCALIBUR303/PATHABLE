import { useId, useState } from 'react'
import { MapPin, Search, X } from 'lucide-react'
import type { Location } from '../../services/api'

export function LocationSearch({
  label,
  locations,
  value,
  onChange,
  placeholder = 'Search a place',
  description,
  disabled = false,
}: {
  label: string
  locations: Location[]
  value: string
  onChange: (id: string) => void
  placeholder?: string
  description?: string
  disabled?: boolean
}) {
  const id = useId()
  const [text, setText] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const selected = locations.find((location) => location.id === value)
  const results = locations.filter((location) =>
    location.name.toLowerCase().includes(text.toLowerCase()),
  )
  function choose(location: Location) {
    onChange(location.id)
    setText('')
    setOpen(false)
    setActive(0)
  }
  return (
    <div className="location-search">
      <label htmlFor={id}>{label}</label>
      <div className="search-control">
        <MapPin size={17} aria-hidden="true" />
        <input
          id={id}
          role="combobox"
          disabled={disabled}
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls={`${id}-list`}
          aria-activedescendant={open && results[active] ? `${id}-option-${active}` : undefined}
          aria-describedby={description ? `${id}-hint` : undefined}
          value={open ? text : (selected?.name ?? '')}
          placeholder={placeholder}
          autoComplete="off"
          onFocus={() => {
            setText('')
            setOpen(true)
            setActive(0)
          }}
          onBlur={() => setOpen(false)}
          onChange={(event) => {
            setText(event.target.value)
            setOpen(true)
            setActive(0)
          }}
          onKeyDown={(event) => {
            if (event.key === 'ArrowDown') {
              event.preventDefault()
              setOpen(true)
              setActive((index) => Math.min(index + 1, results.length - 1))
            }
            if (event.key === 'ArrowUp') {
              event.preventDefault()
              setActive((index) => Math.max(index - 1, 0))
            }
            if (event.key === 'Enter' && open && results[active]) {
              event.preventDefault()
              choose(results[active])
            }
            if (event.key === 'Escape') setOpen(false)
          }}
        />
        {value ? (
          <button
            type="button"
            className="clear-place"
            aria-label={`Clear ${label.toLowerCase()}`}
            onClick={() => {
              onChange('')
              setText('')
              setOpen(false)
            }}
          >
            <X size={15} />
          </button>
        ) : (
          <Search size={15} aria-hidden="true" />
        )}
      </div>
      {description && (
        <small id={`${id}-hint`} className="muted">
          {description}
        </small>
      )}
      {open && (
        <ul
          id={`${id}-list`}
          className="search-results"
          role="listbox"
          aria-label={`${label} results`}
        >
          {results.length ? (
            results.map((location, index) => (
              <li
                id={`${id}-option-${index}`}
                key={location.id}
                role="option"
                aria-selected={index === active}
                onMouseDown={(event) => {
                  event.preventDefault()
                  choose(location)
                }}
              >
                <MapPin size={16} aria-hidden="true" />
                <span>
                  {location.name}
                  <small>
                    {location.access_points.length} mapped{' '}
                    {location.access_points.length === 1 ? 'entrance' : 'entrances'}
                  </small>
                </span>
              </li>
            ))
          ) : (
            <li className="no-results">No matching places. Try another name.</li>
          )}
        </ul>
      )}
    </div>
  )
}
