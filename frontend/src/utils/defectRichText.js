const IMAGE_DATA_URL_PATTERN = /^data:image\/[a-zA-Z0-9.+-]+;base64,/

export const isDataImageUrl = (value = '') => IMAGE_DATA_URL_PATTERN.test(String(value || ''))

export const extractImageSourcesFromHtml = (html = '') => {
  if (!html) {
    return []
  }

  if (typeof window !== 'undefined' && typeof window.DOMParser !== 'undefined') {
    const parser = new window.DOMParser()
    const documentNode = parser.parseFromString(html, 'text/html')
    return Array.from(documentNode.querySelectorAll('img'))
      .map((image) => image.getAttribute('src') || '')
      .filter(Boolean)
  }

  const matches = String(html).match(/<img[^>]+src=["']([^"']+)["']/gi) || []
  return matches
    .map((item) => item.match(/src=["']([^"']+)["']/i)?.[1] || '')
    .filter(Boolean)
}

export const hasRichTextContent = (html = '') => {
  if (!html) {
    return false
  }

  const imageSources = extractImageSourcesFromHtml(html)
  if (imageSources.length) {
    return true
  }

  if (typeof window !== 'undefined' && typeof window.DOMParser !== 'undefined') {
    const parser = new window.DOMParser()
    const documentNode = parser.parseFromString(html, 'text/html')
    return Boolean(documentNode.body.textContent?.trim())
  }

  return Boolean(String(html).replace(/<[^>]+>/g, '').trim())
}

export const dataUrlToFile = (dataUrl, fileName = 'inline-image.png') => {
  const [metadata, base64Content] = String(dataUrl).split(',')
  const mimeMatch = metadata.match(/data:([^;]+)/i)
  const mimeType = mimeMatch?.[1] || 'image/png'
  const binaryString = window.atob(base64Content || '')
  const contentLength = binaryString.length
  const buffer = new Uint8Array(contentLength)

  for (let index = 0; index < contentLength; index += 1) {
    buffer[index] = binaryString.charCodeAt(index)
  }

  return new File([buffer], fileName, { type: mimeType })
}

export const replaceInlineImageDataUrls = async (html, uploadHandler) => {
  const imageSources = extractImageSourcesFromHtml(html)
  const inlineSources = Array.from(new Set(imageSources.filter(isDataImageUrl)))

  if (!inlineSources.length) {
    return html
  }

  const files = inlineSources.map((source, index) => {
    const mimeType = source.match(/^data:([^;]+)/i)?.[1] || 'image/png'
    const extension = mimeType.split('/')[1] || 'png'
    return dataUrlToFile(source, `defect-inline-${index + 1}.${extension}`)
  })

  const uploadedImages = await uploadHandler(files)
  const uploadedUrlMap = new Map()

  inlineSources.forEach((source, index) => {
    const currentItem = uploadedImages?.[index]
    const nextUrl = typeof currentItem === 'string' ? currentItem : currentItem?.url
    if (nextUrl) {
      uploadedUrlMap.set(source, nextUrl)
    }
  })

  if (typeof window !== 'undefined' && typeof window.DOMParser !== 'undefined') {
    const parser = new window.DOMParser()
    const documentNode = parser.parseFromString(html, 'text/html')
    documentNode.querySelectorAll('img').forEach((image) => {
      const source = image.getAttribute('src') || ''
      if (uploadedUrlMap.has(source)) {
        image.setAttribute('src', uploadedUrlMap.get(source))
      }
    })
    return documentNode.body.innerHTML
  }

  let nextHtml = String(html)
  uploadedUrlMap.forEach((url, source) => {
    nextHtml = nextHtml.split(source).join(url)
  })
  return nextHtml
}
