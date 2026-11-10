const svg = (body: string): string =>
  `data:image/svg+xml;charset=utf-8,${encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 90"><rect width="160" height="90" fill="#eceef2"/>${body}</svg>`
  )}`

export const FALLBACK_COVER = svg(
  '<path d="M68 32h24a6 6 0 0 1 6 6v14a6 6 0 0 1-6 6H68a6 6 0 0 1-6-6V38a6 6 0 0 1 6-6Z" fill="#c8ccd6"/>' +
    '<path d="m74 46 6-6 5 5 4-4 7 9H74Z" fill="#eceef2"/>'
)

export const FALLBACK_AVATAR =
  'data:image/svg+xml;charset=utf-8,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><rect width="40" height="40" fill="#d9dce4"/><circle cx="20" cy="15" r="7" fill="#eceef2"/><path d="M6 40c2-9 8-13 14-13s12 4 14 13Z" fill="#eceef2"/></svg>'
  )
